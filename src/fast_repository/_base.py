"""Transport-agnostic logic shared by the sync and async repositories.

This module holds everything that does not touch the database session: entity
capture, primary-key resolution, soft-delete bookkeeping, and statement
building. The concrete repositories add the thin execution layer that runs the
statements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    TypeVar,
    get_args,
    get_origin,
)

from sqlalchemy import and_, inspect, select
from sqlalchemy.orm import DeclarativeBase

from .filters import build_conditions

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.orm import InstrumentedAttribute
    from sqlalchemy.sql import ColumnElement

    from .locking import DbLockInfo

EntityT = TypeVar("EntityT", bound=DeclarativeBase)

_UNSET: Any = object()


class _BaseCRUDRepository(Generic[EntityT]):
    """Entity binding and statement building shared by every repository.

    Not part of the public API. Use ``CRUDRepository`` or
    ``SyncCRUDRepository`` instead.
    """

    _entity_cls: ClassVar[type[DeclarativeBase]]
    _soft_delete_column: ClassVar[str | None] = None
    stmt: ClassVar[Select[tuple[Any]]]

    def __init_subclass__(
        cls,
        stmt: Select[tuple[Any]] | None = None,
        soft_delete: str | InstrumentedAttribute[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Capture the entity class, base statement, and soft-delete column.

        ``soft_delete`` may be a column name or the mapped attribute itself
        (e.g. ``Article.deleted_at``); a mapped attribute is normalized to its
        column name.
        """
        super().__init_subclass__(**kwargs)
        for base in getattr(cls, "__orig_bases__", cls.__bases__):
            origin = get_origin(base)
            if isinstance(origin, type) and issubclass(origin, _BaseCRUDRepository):
                (entity_cls,) = get_args(base)
                if isinstance(entity_cls, type) and issubclass(
                    entity_cls, DeclarativeBase
                ):
                    cls._entity_cls = entity_cls
        if stmt is not None:
            cls.stmt = stmt
        elif not hasattr(cls, "stmt") and hasattr(cls, "_entity_cls"):
            cls.stmt = select(cls._entity_cls)
        if soft_delete is not None:
            cls._soft_delete_column = (
                soft_delete if isinstance(soft_delete, str) else soft_delete.key
            )

    def _ensure_entity_bound(self) -> None:
        """Raise if the repository is missing an entity or misconfigured.

        Raises:
            TypeError: If the class was subclassed without a concrete entity.
            ValueError: If ``soft_delete`` names a column that is not a mapped
                datetime or boolean column of the entity.

        """
        if not hasattr(type(self), "_entity_cls"):
            raise TypeError(
                f"{type(self).__name__} must subclass a CRUD repository with a "
                "concrete entity, e.g. CRUDRepository[User]."
            )
        if self._soft_delete_column is not None:
            self._alive_condition()  # validate the configured column eagerly

    @property
    def _pks(self) -> tuple[InstrumentedAttribute[Any], ...]:
        """Primary-key attributes of the entity, in column order."""
        mapper = inspect(self._entity_cls).mapper
        return tuple(
            mapper.get_property_by_column(column).class_attribute
            for column in mapper.primary_key
        )

    def _soft_delete_attr(self) -> InstrumentedAttribute[Any]:
        """The mapped attribute backing soft deletion.

        Only call when ``_soft_delete_column`` is set.
        """
        column = self._soft_delete_column
        mapper = inspect(self._entity_cls).mapper
        if column not in mapper.column_attrs:
            raise ValueError(
                f"soft_delete column {column!r} is not a mapped column of "
                f"{self._entity_cls.__name__}."
            )
        return mapper.column_attrs[column].class_attribute

    def _alive_condition(self) -> ColumnElement[bool] | None:
        """Where-condition selecting non-deleted rows, or None when disabled."""
        if self._soft_delete_column is None:
            return None
        attr = self._soft_delete_attr()
        python_type = attr.type.python_type
        if issubclass(python_type, bool):
            return attr.is_(False)
        if issubclass(python_type, datetime):
            return attr.is_(None)
        raise ValueError(
            f"soft_delete column {self._soft_delete_column!r} must be a datetime "
            f"or boolean column of {self._entity_cls.__name__}."
        )

    def _soft_delete_value(self) -> Any:
        """The value written to the soft-delete column to mark a row deleted."""
        attr = self._soft_delete_attr()
        python_type = attr.type.python_type
        if issubclass(python_type, bool):
            return True
        return datetime.now(timezone.utc)

    def _mark_deleted(self, entity: EntityT) -> None:
        """Set the soft-delete column on an entity in place."""
        setattr(entity, self._soft_delete_column, self._soft_delete_value())

    def _find_statement(
        self,
        pk: Any,
        keys: dict[str, Any],
        with_for_update: bool | DbLockInfo,
        with_deleted: bool,
    ) -> Select[tuple[Any]]:
        """Build the select for a primary-key lookup, with optional row lock."""
        pk_attrs = self._pks
        if keys:
            if pk is not _UNSET:
                raise ValueError(
                    "Pass the primary key positionally or as keywords, not both."
                )
            expected = {attr.key for attr in pk_attrs}
            if keys.keys() != expected:
                raise ValueError(
                    f"{self._entity_cls.__name__} primary key is "
                    f"{sorted(expected)}; got {sorted(keys)}."
                )
            condition = and_(*(attr == keys[attr.key] for attr in pk_attrs))
        elif pk is _UNSET:
            raise ValueError("find() requires a primary-key value.")
        elif len(pk_attrs) != 1:
            columns = ", ".join(f"{attr.key}=..." for attr in pk_attrs)
            raise ValueError(
                f"{self._entity_cls.__name__} has a composite primary key; "
                f"pass its columns as keyword arguments, e.g. find({columns})."
            )
        else:
            condition = pk_attrs[0] == pk
        conditions = [condition, *self._alive_conditions(with_deleted)]
        stmt = self.stmt.where(*conditions)
        if with_for_update is not False:
            options: dict[str, Any] = (
                {} if with_for_update is True else dict(with_for_update)
            )
            stmt = stmt.with_for_update(**options)
        return stmt

    def _find_all_statement(
        self,
        criteria: tuple[ColumnElement[bool], ...],
        filters: dict[str, Any],
        with_deleted: bool,
    ) -> Select[tuple[Any]]:
        """Build the select for a filtered collection read."""
        conditions = (
            *criteria,
            *build_conditions(self._entity_cls, filters),
            *self._alive_conditions(with_deleted),
        )
        stmt = self.stmt
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    def _paginated_statement(
        self,
        criteria: tuple[ColumnElement[bool], ...],
        filters: dict[str, Any],
        with_deleted: bool,
    ) -> Select[tuple[Any]]:
        """Build the select for a paginated read, ordered by primary key."""
        conditions = (
            *criteria,
            *build_conditions(self._entity_cls, filters),
            *self._alive_conditions(with_deleted),
        )
        stmt = self.stmt.order_by(*self._pks)
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    def _alive_conditions(self, with_deleted: bool) -> tuple[ColumnElement[bool], ...]:
        """The non-deleted filter as a tuple, empty when it does not apply."""
        if with_deleted:
            return ()
        alive = self._alive_condition()
        return () if alive is None else (alive,)
