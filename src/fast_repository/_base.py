"""Transport-agnostic logic shared by the sync and async repositories.

This module holds everything that does not touch the database session: entity
capture, primary-key resolution, and statement building. The concrete
repositories add the thin execution layer that runs the statements.
"""

from __future__ import annotations

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

    from .locking import DbLockInfo

EntityT = TypeVar("EntityT", bound=DeclarativeBase)

_UNSET: Any = object()


class _BaseCRUDRepository(Generic[EntityT]):
    """Entity binding and statement building shared by every repository.

    Not part of the public API. Use ``CRUDRepository`` or
    ``SyncCRUDRepository`` instead.
    """

    _entity_cls: ClassVar[type[DeclarativeBase]]
    stmt: ClassVar[Select[tuple[Any]]]

    def __init_subclass__(
        cls, stmt: Select[tuple[Any]] | None = None, **kwargs: Any
    ) -> None:
        """Capture the entity class and base statement from the subclass."""
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

    def _ensure_entity_bound(self) -> None:
        """Raise if the repository was subclassed without a concrete entity."""
        if not hasattr(type(self), "_entity_cls"):
            raise TypeError(
                f"{type(self).__name__} must subclass a CRUD repository with a "
                "concrete entity, e.g. CRUDRepository[User]."
            )

    @property
    def _pks(self) -> tuple[InstrumentedAttribute[Any], ...]:
        """Primary-key attributes of the entity, in column order."""
        mapper = inspect(self._entity_cls).mapper
        return tuple(
            mapper.get_property_by_column(column).class_attribute
            for column in mapper.primary_key
        )

    def _find_statement(
        self,
        pk: Any,
        keys: dict[str, Any],
        with_for_update: bool | DbLockInfo,
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
        stmt = self.stmt.where(condition)
        if with_for_update is not False:
            options: dict[str, Any] = (
                {} if with_for_update is True else dict(with_for_update)
            )
            stmt = stmt.with_for_update(**options)
        return stmt

    def _find_all_statement(self, filters: dict[str, Any]) -> Select[tuple[Any]]:
        """Build the select for a filtered collection read."""
        stmt = self.stmt
        conditions = build_conditions(self._entity_cls, filters)
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt

    def _paginated_statement(self, filters: dict[str, Any]) -> Select[tuple[Any]]:
        """Build the select for a paginated read, ordered by primary key."""
        stmt = self.stmt.order_by(*self._pks)
        conditions = build_conditions(self._entity_cls, filters)
        if conditions:
            stmt = stmt.where(*conditions)
        return stmt
