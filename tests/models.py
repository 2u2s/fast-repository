"""Test entities and repositories."""

from __future__ import annotations

from abc import ABC

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fast_repository import (
    AbstractCRUDRepository,
    AbstractSyncCRUDRepository,
    CRUDRepository,
    SyncCRUDRepository,
)


class Base(DeclarativeBase):
    """Declarative base for test entities."""


class User(Base):
    """User entity used across the test suite."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    age: Mapped[int]
    nickname: Mapped[str | None] = mapped_column(default=None)


class Membership(Base):
    """Entity with a composite primary key used in the test suite."""

    __tablename__ = "memberships"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str]


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    """Domain-facing interface for user repositories."""


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    """User repository whose CRUD methods come from the library."""


class MembershipRepository(CRUDRepository[Membership]):
    """Repository for the composite-key entity."""


class AbstractSyncUserRepository(AbstractSyncCRUDRepository[User], ABC):
    """Domain-facing interface for synchronous user repositories."""


class SyncUserRepository(SyncCRUDRepository[User], AbstractSyncUserRepository):
    """Synchronous user repository whose CRUD methods come from the library."""


class SyncMembershipRepository(SyncCRUDRepository[Membership]):
    """Synchronous repository for the composite-key entity."""
