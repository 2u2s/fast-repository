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
from sqlalchemy import inspect, select
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
    def _pk(self) -> InstrumentedAttribute[Any]:
        """Primary-key attribute of the entity.

        Raises:
            TypeError: If the entity has a composite primary key.

        """
        mapper = inspect(self._entity_cls).mapper
        if len(mapper.primary_key) != 1:
            raise TypeError(
                f"{type(self).__name__} requires a single-column primary "
                f"key; {self._entity_cls.__name__} has "
                f"{len(mapper.primary_key)} primary-key columns."
            )
        pk_property = mapper.get_property_by_column(mapper.primary_key[0])
        return pk_property.class_attribute

    async def find(self, pk: Any) -> EntityT | None:
        """Find an entity by its primary key.

        Args:
            pk (Any): Primary-key value of the entity.

        Returns:
            EntityT | None: The entity, or None if it does not exist.

        """
        entity: EntityT | None = await self.session.scalar(
            self.stmt.where(self._pk == pk)
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
        stmt = self.stmt.order_by(self._pk)
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
