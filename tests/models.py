"""Test entities and repositories."""

from __future__ import annotations

from abc import ABC
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fast_repository import (
    CRUDRepository,
    CRUDRepositoryInterface,
    SyncCRUDRepository,
    SyncCRUDRepositoryInterface,
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


class AbstractUserRepository(CRUDRepositoryInterface[User], ABC):
    """Domain-facing interface for user repositories."""


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    """User repository whose CRUD methods come from the library."""


class MembershipRepository(CRUDRepository[Membership]):
    """Repository for the composite-key entity."""


class AbstractSyncUserRepository(SyncCRUDRepositoryInterface[User], ABC):
    """Domain-facing interface for synchronous user repositories."""


class SyncUserRepository(SyncCRUDRepository[User], AbstractSyncUserRepository):
    """Synchronous user repository whose CRUD methods come from the library."""


class SyncMembershipRepository(SyncCRUDRepository[Membership]):
    """Synchronous repository for the composite-key entity."""


class Article(Base):
    """Entity with a datetime soft-delete column."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class Note(Base):
    """Entity with a boolean soft-delete column."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str]
    archived: Mapped[bool] = mapped_column(default=False)


class ArticleRepository(CRUDRepository[Article], soft_delete="deleted_at"):
    """Soft-deleting repository keyed on a datetime column."""


class NoteRepository(CRUDRepository[Note], soft_delete="archived"):
    """Soft-deleting repository keyed on a boolean column."""


class SyncArticleRepository(SyncCRUDRepository[Article], soft_delete="deleted_at"):
    """Synchronous soft-deleting repository keyed on a datetime column."""
