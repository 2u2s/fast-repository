"""Abstract repository interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi_pagination import Page
    from fastapi_pagination.bases import AbstractParams

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
    async def find(self, pk: Any) -> EntityT | None:
        """Find an entity by its primary key.

        Args:
            pk (Any): Primary-key value of the entity.

        Returns:
            EntityT | None: The entity, or None if it does not exist.

        """

    @abstractmethod
    async def find_all(self, **filters: Any) -> list[EntityT]:
        """Find all entities matching the given filters.

        A bare ``column=value`` keyword translates to an equality condition.
        A ``column__operator`` keyword applies the named operator (``in``,
        ``gt``, ``ge``, ``lt``, ``le``, ``like``, ``ilike``, ``is``).

        Args:
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
        **filters: Any,
    ) -> Page[EntityT]:
        """Find a page of entities matching the given filters.

        Args:
            params (AbstractParams | None): Pagination parameters. If None,
                they are resolved from the current FastAPI request context.
            **filters (Any): Keyword filters applied as where-conditions.

        Returns:
            Page[EntityT]: The paginated entities.

        Raises:
            InvalidFilterError: If a keyword matches no mapped column.

        """

    @abstractmethod
    async def save(self, entity: EntityT) -> EntityT:
        """Persist an entity (create or update).

        Args:
            entity (EntityT): The entity to persist.

        Returns:
            EntityT: The persisted entity.

        """

    @abstractmethod
    async def save_all(self, entities: Sequence[EntityT]) -> list[EntityT]:
        """Persist multiple entities (create or update).

        Args:
            entities (Sequence[EntityT]): The entities to persist.

        Returns:
            list[EntityT]: The persisted entities.

        """

    @abstractmethod
    async def delete(self, entity: EntityT) -> None:
        """Delete an entity.

        Args:
            entity (EntityT): The entity to delete.

        """

    @abstractmethod
    async def delete_all(self, entities: Sequence[EntityT]) -> None:
        """Delete multiple entities.

        Args:
            entities (Sequence[EntityT]): The entities to delete.

        """
