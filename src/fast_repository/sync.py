"""Synchronous CRUD repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import DeclarativeBase

from ._base import _UNSET, _BaseCRUDRepository
from .abstract import SyncCRUDRepositoryInterface

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination.bases import AbstractParams
    from sqlalchemy.orm import Session
    from sqlalchemy.sql import ColumnElement

    from .locking import DbLockInfo

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class SyncCRUDRepository(
    _BaseCRUDRepository[EntityT],
    SyncCRUDRepositoryInterface[EntityT],
    Generic[EntityT],
):
    """Ready-made synchronous CRUD repository for a SQLAlchemy entity.

    The synchronous counterpart to ``CRUDRepository``. Subclass with a concrete
    entity to get a working repository::

        class UserRepository(SyncCRUDRepository[User]):
            ...

    The entity class is captured from the generic argument at class-definition
    time, so no constructor wiring is needed beyond the session. The class must
    be subclassed; instantiating ``SyncCRUDRepository[User]`` directly is not
    supported.

    Customize the base ``stmt`` to add relationship-loading options or a default
    filter applied to all reads, either at class-definition time::

        class ActiveUserRepository(
            SyncCRUDRepository[User], stmt=select(User).where(User.active)
        ):
            ...

    or per instance by assigning ``self.stmt``.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a synchronous session.

        Args:
            session (Session): The database session.

        Raises:
            TypeError: If the class was subclassed without a concrete entity.

        """
        self._ensure_entity_bound()
        self.session = session

    def find(
        self,
        pk: Any = _UNSET,
        *,
        with_for_update: bool | DbLockInfo = False,
        with_deleted: bool = False,
        **keys: Any,
    ) -> EntityT | None:
        """Find an entity by its primary key."""
        return self.session.scalar(
            self._find_statement(pk, keys, with_for_update, with_deleted)
        )

    def find_all(
        self,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> list[EntityT]:
        """Find all entities matching the given criteria and filters."""
        result = self.session.scalars(
            self._find_all_statement(criteria, filters, order_by, with_deleted)
        )
        return list(result.unique().all())

    def find_all_paginated(
        self,
        params: AbstractParams | None = None,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given criteria and filters."""
        return paginate(
            self.session,
            self._paginated_statement(criteria, filters, order_by, with_deleted),
            params,
        )

    def count(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> int:
        """Count entities matching the given criteria and filters."""
        total = self.session.scalar(
            self._count_statement(criteria, filters, with_deleted)
        )
        return total or 0

    def exists(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> bool:
        """Return whether any entity matches the given criteria and filters."""
        return bool(
            self.session.scalar(self._exists_statement(criteria, filters, with_deleted))
        )

    def save(self, entity: EntityT, *, autocommit: bool = True) -> EntityT:
        """Persist an entity (create or update)."""
        self.session.add(entity)
        self._finish(autocommit)
        return entity

    def save_all(
        self, entities: Sequence[EntityT], *, autocommit: bool = True
    ) -> list[EntityT]:
        """Persist multiple entities (create or update)."""
        self.session.add_all(entities)
        self._finish(autocommit)
        return list(entities)

    def delete(
        self, entity: EntityT, *, hard: bool = False, autocommit: bool = True
    ) -> None:
        """Delete an entity (soft delete when configured, else hard delete)."""
        if self._soft_delete_column is not None and not hard:
            self._mark_deleted(entity)
        else:
            self.session.delete(entity)
        self._finish(autocommit)

    def delete_all(
        self,
        entities: Sequence[EntityT],
        *,
        hard: bool = False,
        autocommit: bool = True,
    ) -> None:
        """Delete multiple entities (soft delete when configured, else hard)."""
        if self._soft_delete_column is not None and not hard:
            for entity in entities:
                self._mark_deleted(entity)
        else:
            for entity in entities:
                self.session.delete(entity)
        self._finish(autocommit)

    def _finish(self, autocommit: bool) -> None:
        """Commit the transaction, or flush when the caller manages it."""
        if autocommit:
            self.session.commit()
        else:
            self.session.flush()
