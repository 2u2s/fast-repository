"""Shared entities, repositories, and database helpers for the examples.

Every example imports from here so the SQLAlchemy model, the repository
classes, and the throwaway in-memory database are defined in exactly one place.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fast_repository import AbstractCRUDRepository, CRUDRepository


class Base(DeclarativeBase):
    """Declarative base for the example entities."""


class User(Base):
    """A minimal user entity used throughout the examples."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    age: Mapped[int]


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    """Domain-facing interface — depend on this from your business logic."""


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    """Concrete repository — all CRUD methods come from the library."""


class Article(Base):
    """An entity with a soft-delete column."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class ArticleRepository(CRUDRepository[Article], soft_delete=Article.deleted_at):
    """Soft-deleting repository — delete() marks rows instead of removing them."""


async def make_session() -> AsyncIterator[AsyncSession]:
    """Yield a session backed by a fresh in-memory SQLite database.

    The schema is created on the spot, so each example runs without any
    external database. Async SQLite comes from the ``aiosqlite`` driver
    installed via the ``examples`` dependency group.
    """
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def seed(repo: UserRepository) -> None:
    """Insert a handful of users so reads have something to return."""
    await repo.save_all(
        [
            User(name="Ada", status="active", age=36),
            User(name="Linus", status="active", age=54),
            User(name="Grace", status="inactive", age=85),
            User(name="Kent", status="active", age=64),
        ]
    )
