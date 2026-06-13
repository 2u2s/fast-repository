"""Async CRUD repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy.orm import DeclarativeBase

from ._base import _UNSET, _BaseCRUDRepository
from .abstract import AbstractCRUDRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination.bases import AbstractParams
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql import ColumnElement

    from .locking import DbLockInfo

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class CRUDRepository(
    _BaseCRUDRepository[EntityT],
    AbstractCRUDRepository[EntityT],
    Generic[EntityT],
):
    """Ready-made async CRUD repository for a SQLAlchemy entity.

    Subclass with a concrete entity to get a working repository::

        class UserRepository(CRUDRepository[User]):
            ...

    The entity class is captured from the generic argument at class-definition
    time, so no constructor wiring is needed beyond the session. The class must
    be subclassed; instantiating ``CRUDRepository[User]`` directly is not
    supported.

    Customize the base ``stmt`` to add relationship-loading options or a default
    filter applied to all reads, either at class-definition time::

        class ActiveUserRepository(
            CRUDRepository[User], stmt=select(User).where(User.active)
        ):
            ...

    or per instance by assigning ``self.stmt``.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async session.

        Args:
            session (AsyncSession): The async database session.

        Raises:
            TypeError: If the class was subclassed without a concrete entity.

        """
        self._ensure_entity_bound()
        self.session = session

    async def find(
        self,
        pk: Any = _UNSET,
        *,
        with_for_update: bool | DbLockInfo = False,
        **keys: Any,
    ) -> EntityT | None:
        """Find an entity by its primary key."""
        return await self.session.scalar(
            self._find_statement(pk, keys, with_for_update)
        )

    async def find_all(
        self, *criteria: ColumnElement[bool], **filters: Any
    ) -> list[EntityT]:
        """Find all entities matching the given criteria and filters."""
        result = await self.session.scalars(self._find_all_statement(criteria, filters))
        return list(result.unique().all())

    async def find_all_paginated(
        self,
        params: AbstractParams | None = None,
        *criteria: ColumnElement[bool],
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given criteria and filters."""
        return await apaginate(
            self.session, self._paginated_statement(criteria, filters), params
        )

    async def save(self, entity: EntityT, *, autocommit: bool = True) -> EntityT:
        """Persist an entity (create or update)."""
        self.session.add(entity)
        await self._finish(autocommit)
        return entity

    async def save_all(
        self, entities: Sequence[EntityT], *, autocommit: bool = True
    ) -> list[EntityT]:
        """Persist multiple entities (create or update)."""
        self.session.add_all(entities)
        await self._finish(autocommit)
        return list(entities)

    async def delete(self, entity: EntityT, *, autocommit: bool = True) -> None:
        """Hard-delete an entity."""
        await self.session.delete(entity)
        await self._finish(autocommit)

    async def delete_all(
        self, entities: Sequence[EntityT], *, autocommit: bool = True
    ) -> None:
        """Hard-delete multiple entities."""
        for entity in entities:
            await self.session.delete(entity)
        await self._finish(autocommit)

    async def _finish(self, autocommit: bool) -> None:
        """Commit the transaction, or flush when the caller manages it."""
        if autocommit:
            await self.session.commit()
        else:
            await self.session.flush()
