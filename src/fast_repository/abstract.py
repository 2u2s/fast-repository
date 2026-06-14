"""Abstract repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy.orm import DeclarativeBase

from .locking import DbLockInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination import Page
    from fastapi_pagination.bases import AbstractParams
    from sqlalchemy.sql import ColumnElement

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class AbstractCRUDRepository(ABC, Generic[EntityT]):
    """Interface for CRUD repositories.

    Declare a domain-facing repository interface by subclassing this class, then obtain
    a working implementation by subclassing ``CRUDRepository`` with the same entity.

    Example:
        Declare the interface in the domain layer::

            class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
                ...

        Implement it in the infrastructure layer with zero boilerplate::

            class UserRepository(CRUDRepository[User], AbstractUserRepository):
                ...

    """

    @abstractmethod
    async def find(
        self,
        pk: Any = None,
        *,
        with_for_update: bool | DbLockInfo = False,
        with_deleted: bool = False,
        **keys: Any,
    ) -> EntityT | None:
        """Find an entity by its primary key.

        Pass a single-column primary key positionally; supply a composite
        primary key as keyword arguments naming each key column. Pass
        ``with_for_update`` to acquire a row lock.

        Args:
            pk (Any): Single-column primary-key value. Omit when using keyword
                arguments.
            with_for_update (bool | DbLockInfo): Row-locking options. ``False``
                (the default) reads without a lock; ``True`` locks with a plain
                ``FOR UPDATE``; a mapping is forwarded to
                ``Select.with_for_update``.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **keys (Any): Primary-key values named by their column, used for
                composite keys.

        Returns:
            EntityT | None: The entity, or None if it does not exist.

        """

    @abstractmethod
    async def find_all(
        self,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> list[EntityT]:
        """Find all entities matching the given criteria and filters.

        Positional ``criteria`` are raw SQLAlchemy boolean expressions, e.g.
        ``or_(User.status == "active", User.age >= 18)`` or a function call such
        as ``func.jsonb_path_exists(...)``. A bare ``column=value`` keyword
        translates to an equality condition; a ``column__operator`` keyword
        applies the named operator (``in``, ``notin``, ``ne``, ``gt``, ``ge``,
        ``lt``, ``le``, ``like``, ``ilike``, ``is``). All conditions are
        combined with ``AND``.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            order_by (Any): One SQLAlchemy order expression (e.g.
                ``Entity.col.desc()``) or a sequence of them. ``None`` (the
                default) applies no ordering.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            list[EntityT]: The matching entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    async def find_all_paginated(
        self,
        params: AbstractParams | None = None,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given criteria and filters.

        Args:
            params (AbstractParams | None): Pagination parameters. If None,
                they are resolved from the current FastAPI request context.
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions, as in
                ``find_all``.
            order_by (Any): One SQLAlchemy order expression or a sequence of
                them, applied before the primary-key tie-breaker. ``None``
                (the default) orders by primary key alone. If it already
                includes the primary key, a harmless duplicate ordering term
                is emitted.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            Page[EntityT]: The paginated entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    async def count(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> int:
        """Count entities matching the given criteria and filters.

        Accepts the same positional ``criteria`` and keyword ``filters`` as
        ``find_all``. The base statement's own conditions and the soft-delete
        filter are respected.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            int: The number of matching entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    async def exists(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> bool:
        """Return whether any entity matches the given criteria and filters.

        Accepts the same positional ``criteria`` and keyword ``filters`` as
        ``find_all``.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            bool: True if at least one entity matches.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    async def save(self, entity: EntityT, *, autocommit: bool = True) -> EntityT:
        """Persist an entity (create or update).

        Args:
            entity (EntityT): The entity to persist.
            autocommit (bool): When True, commit the transaction. When False,
                only flush so generated values are populated while leaving the
                transaction open for the caller to commit.

        Returns:
            EntityT: The persisted entity.

        """

    @abstractmethod
    async def save_all(
        self, entities: Sequence[EntityT], *, autocommit: bool = True
    ) -> list[EntityT]:
        """Persist multiple entities (create or update).

        Args:
            entities (Sequence[EntityT]): The entities to persist.
            autocommit (bool): When True, commit the transaction. When False,
                only flush so generated values are populated while leaving the
                transaction open for the caller to commit.

        Returns:
            list[EntityT]: The persisted entities.

        """

    @abstractmethod
    async def delete(
        self, entity: EntityT, *, hard: bool = False, autocommit: bool = True
    ) -> None:
        """Delete an entity.

        Soft-deletes when the repository has soft-delete enabled, otherwise
        hard-deletes. Pass ``hard=True`` to force a hard delete regardless.

        Args:
            entity (EntityT): The entity to delete.
            hard (bool): Force a physical delete even when soft-delete is
                enabled.
            autocommit (bool): When True, commit the transaction. When False,
                only flush, leaving the transaction open for the caller to
                commit.

        """

    @abstractmethod
    async def delete_all(
        self,
        entities: Sequence[EntityT],
        *,
        hard: bool = False,
        autocommit: bool = True,
    ) -> None:
        """Delete multiple entities.

        Soft-deletes when the repository has soft-delete enabled, otherwise
        hard-deletes. Pass ``hard=True`` to force a hard delete regardless.

        Args:
            entities (Sequence[EntityT]): The entities to delete.
            hard (bool): Force a physical delete even when soft-delete is
                enabled.
            autocommit (bool): When True, commit the transaction. When False,
                only flush, leaving the transaction open for the caller to
                commit.

        """


class AbstractSyncCRUDRepository(ABC, Generic[EntityT]):
    """Interface for synchronous CRUD repositories.

    The synchronous counterpart to ``AbstractCRUDRepository``. Declare a
    domain-facing interface by subclassing this class, then obtain a working
    implementation by subclassing ``SyncCRUDRepository`` with the same entity.

    Example:
        Declare the interface in the domain layer::

            class AbstractUserRepository(AbstractSyncCRUDRepository[User], ABC):
                ...

        Implement it in the infrastructure layer with zero boilerplate::

            class UserRepository(SyncCRUDRepository[User], AbstractUserRepository):
                ...

    """

    @abstractmethod
    def find(
        self,
        pk: Any = None,
        *,
        with_for_update: bool | DbLockInfo = False,
        with_deleted: bool = False,
        **keys: Any,
    ) -> EntityT | None:
        """Find an entity by its primary key.

        Pass a single-column primary key positionally; supply a composite
        primary key as keyword arguments naming each key column. Pass
        ``with_for_update`` to acquire a row lock.

        Args:
            pk (Any): Single-column primary-key value. Omit when using keyword
                arguments.
            with_for_update (bool | DbLockInfo): Row-locking options. ``False``
                (the default) reads without a lock; ``True`` locks with a plain
                ``FOR UPDATE``; a mapping is forwarded to
                ``Select.with_for_update``.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **keys (Any): Primary-key values named by their column, used for
                composite keys.

        Returns:
            EntityT | None: The entity, or None if it does not exist.

        """

    @abstractmethod
    def find_all(
        self,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> list[EntityT]:
        """Find all entities matching the given criteria and filters.

        Positional ``criteria`` are raw SQLAlchemy boolean expressions, e.g.
        ``or_(User.status == "active", User.age >= 18)`` or a function call such
        as ``func.jsonb_path_exists(...)``. A bare ``column=value`` keyword
        translates to an equality condition; a ``column__operator`` keyword
        applies the named operator (``in``, ``notin``, ``ne``, ``gt``, ``ge``,
        ``lt``, ``le``, ``like``, ``ilike``, ``is``). All conditions are
        combined with ``AND``.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            order_by (Any): One SQLAlchemy order expression (e.g.
                ``Entity.col.desc()``) or a sequence of them. ``None`` (the
                default) applies no ordering.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            list[EntityT]: The matching entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    def find_all_paginated(
        self,
        params: AbstractParams | None = None,
        *criteria: ColumnElement[bool],
        order_by: Any = None,
        with_deleted: bool = False,
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given criteria and filters.

        Args:
            params (AbstractParams | None): Pagination parameters. If None,
                they are resolved from the current FastAPI request context.
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions, as in
                ``find_all``.
            order_by (Any): One SQLAlchemy order expression or a sequence of
                them, applied before the primary-key tie-breaker. ``None``
                (the default) orders by primary key alone. If it already
                includes the primary key, a harmless duplicate ordering term
                is emitted.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            Page[EntityT]: The paginated entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    def count(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> int:
        """Count entities matching the given criteria and filters.

        Accepts the same positional ``criteria`` and keyword ``filters`` as
        ``find_all``. The base statement's own conditions and the soft-delete
        filter are respected.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            int: The number of matching entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    def exists(
        self,
        *criteria: ColumnElement[bool],
        with_deleted: bool = False,
        **filters: Any,
    ) -> bool:
        """Return whether any entity matches the given criteria and filters.

        Accepts the same positional ``criteria`` and keyword ``filters`` as
        ``find_all``.

        Args:
            *criteria (ColumnElement[bool]): SQLAlchemy where-expressions.
            with_deleted (bool): When the repository has soft-delete enabled,
                include soft-deleted rows. Ignored otherwise.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            bool: True if at least one entity matches.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    def save(self, entity: EntityT, *, autocommit: bool = True) -> EntityT:
        """Persist an entity (create or update).

        Args:
            entity (EntityT): The entity to persist.
            autocommit (bool): When True, commit the transaction. When False,
                only flush so generated values are populated while leaving the
                transaction open for the caller to commit.

        Returns:
            EntityT: The persisted entity.

        """

    @abstractmethod
    def save_all(
        self, entities: Sequence[EntityT], *, autocommit: bool = True
    ) -> list[EntityT]:
        """Persist multiple entities (create or update).

        Args:
            entities (Sequence[EntityT]): The entities to persist.
            autocommit (bool): When True, commit the transaction. When False,
                only flush so generated values are populated while leaving the
                transaction open for the caller to commit.

        Returns:
            list[EntityT]: The persisted entities.

        """

    @abstractmethod
    def delete(
        self, entity: EntityT, *, hard: bool = False, autocommit: bool = True
    ) -> None:
        """Delete an entity.

        Soft-deletes when the repository has soft-delete enabled, otherwise
        hard-deletes. Pass ``hard=True`` to force a hard delete regardless.

        Args:
            entity (EntityT): The entity to delete.
            hard (bool): Force a physical delete even when soft-delete is
                enabled.
            autocommit (bool): When True, commit the transaction. When False,
                only flush, leaving the transaction open for the caller to
                commit.

        """

    @abstractmethod
    def delete_all(
        self,
        entities: Sequence[EntityT],
        *,
        hard: bool = False,
        autocommit: bool = True,
    ) -> None:
        """Delete multiple entities.

        Soft-deletes when the repository has soft-delete enabled, otherwise
        hard-deletes. Pass ``hard=True`` to force a hard delete regardless.

        Args:
            entities (Sequence[EntityT]): The entities to delete.
            hard (bool): Force a physical delete even when soft-delete is
                enabled.
            autocommit (bool): When True, commit the transaction. When False,
                only flush, leaving the transaction open for the caller to
                commit.

        """
