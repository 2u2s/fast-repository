"""Generic CRUD repository implementation."""

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
from fastapi_pagination import Page

from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import and_, inspect, select
from sqlalchemy.orm import DeclarativeBase

from .abstract import AbstractCRUDRepository
from .filters import build_conditions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination.bases import AbstractParams
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute

EntityT = TypeVar("EntityT", bound=DeclarativeBase)

_UNSET: Any = object()


class CRUDRepository(AbstractCRUDRepository[EntityT], Generic[EntityT]):
    """Ready-made CRUD repository for a SQLAlchemy entity.

    Subclass with a concrete entity to get a working repository::

        class UserRepository(CRUDRepository[User]):
            ...

    The entity class is captured from the generic argument at
    class-definition time, so no constructor wiring is needed beyond the
    session. Note that the class must be subclassed; instantiating
    ``CRUDRepository[User]`` directly is not supported.

    """

    _entity_cls: ClassVar[type[DeclarativeBase]]
    stmt: ClassVar[Select[tuple[Any]]]
    """Base select statement used by every read method.

    Defaults to ``select(cls._entity_cls)``. Customize it to add relationship-loading
    options or a default filter applied to all reads, either at class-definition time::

        class ActiveUserRepository(
            CRUDRepository[User], stmt=select(User).where(User.active)
        ):
            ...

    or per instance by assigning ``self.stmt``.
    
    """

    def __init_subclass__(
        cls, stmt: Select[tuple[Any]] | None = None, **kwargs: Any
    ) -> None:
        """Capture the entity class and base statement from the subclass.

        Args:
            stmt (Select | None): Optional base select statement declared at
                class-definition time, e.g.
                ``class R(CRUDRepository[User], stmt=select(User).where(...))``.
                When omitted, defaults to ``select(cls._entity_cls)``.
            **kwargs (Any): Forwarded to ``super().__init_subclass__``.

        """
        super().__init_subclass__(**kwargs)
        for base in getattr(cls, "__orig_bases__", cls.__bases__):
            origin = get_origin(base)
            if isinstance(origin, type) and issubclass(origin, CRUDRepository):
                (entity_cls,) = get_args(base)
                if isinstance(entity_cls, type) and issubclass(
                    entity_cls, DeclarativeBase
                ):
                    cls._entity_cls = entity_cls
        if stmt is not None:
            cls.stmt = stmt
        elif not hasattr(cls, "stmt") and hasattr(cls, "_entity_cls"):
            cls.stmt = select(cls._entity_cls)

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): The async database session.

        Raises:
            TypeError: If the class was subclassed without a concrete entity, e.g.
                ``class UserRepository(CRUDRepository)``.

        """
        if not hasattr(type(self), "_entity_cls"):
            raise TypeError(
                f"{type(self).__name__} must subclass CRUDRepository with a "
                "concrete entity, e.g. CRUDRepository[User]."
            )
        self.session = session

    @property
    def _pks(self) -> tuple[InstrumentedAttribute[Any], ...]:
        """Primary-key attributes of the entity, in column order."""
        mapper = inspect(self._entity_cls).mapper
        return tuple(
            mapper.get_property_by_column(column).class_attribute
            for column in mapper.primary_key
        )

    async def find(self, pk: Any = _UNSET, **keys: Any) -> EntityT | None:
        """Find an entity by its primary key.

        Pass a single-column primary key positionally. A composite primary key
        must be supplied as keyword arguments naming each key column::

            await repo.find(1)
            await repo.find(user_id=1, group_id=2)

        Args:
            pk (Any): Single-column primary-key value. Omit when using keyword
                arguments.
            **keys (Any): Primary-key values named by their column, used for
                composite keys.

        Returns:
            EntityT | None: The entity, or None if it does not exist.

        Raises:
            ValueError: If no key is supplied, if both positional and keyword
                keys are given, if the supplied keys do not match the entity's
                primary-key columns, or if a composite key is passed
                positionally.

        """
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
        entity: EntityT | None = await self.session.scalar(
            self.stmt.where(condition)
        )
        return entity

    async def find_all(self, **filters: Any) -> list[EntityT]:
        """Find all entities matching the given filters.

        Args:
            **filters: Keyword filters applied as where-conditions.

        Returns:
            list[EntityT]: The matching entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """
        stmt = self.stmt
        conditions = build_conditions(self._entity_cls, filters)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self.session.scalars(stmt)
        return list(result.unique().all())

    async def find_all_paginated(
        self,
        params: AbstractParams | None = None,
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given filters.

        Args:
            params (AbstractParams | None): Pagination parameters. If None,
                they are resolved from the current FastAPI request context.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            Page[EntityT]: The paginated entities, ordered by primary key.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """
        stmt = self.stmt.order_by(*self._pks)
        conditions = build_conditions(self._entity_cls, filters)
        if conditions:
            stmt = stmt.where(*conditions)
        return await apaginate(self.session, stmt, params)

    async def save(self, entity: EntityT) -> EntityT:
        """Persist an entity (create or update) and commit.

        Args:
            entity (EntityT): The entity to persist.

        Returns:
            EntityT: The persisted entity.

        """
        self.session.add(entity)
        await self.session.commit()
        return entity

    async def save_all(self, entities: Sequence[EntityT]) -> list[EntityT]:
        """Persist multiple entities (create or update) and commit.

        Args:
            entities (Sequence[EntityT]): The entities to persist.

        Returns:
            list[EntityT]: The persisted entities.

        """
        self.session.add_all(entities)
        await self.session.commit()
        return list(entities)

    async def delete(self, entity: EntityT) -> None:
        """Hard-delete an entity and commit.

        Args:
            entity (EntityT): The entity to delete.

        """
        await self.session.delete(entity)
        await self.session.commit()

    async def delete_all(self, entities: Sequence[EntityT]) -> None:
        """Hard-delete multiple entities and commit.

        Args:
            entities (Sequence[EntityT]): The entities to delete.

        """
        for entity in entities:
            await self.session.delete(entity)
        await self.session.commit()
