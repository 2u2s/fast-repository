"""Shared entities, repositories, and database helpers for the examples.

Every example imports from here so the SQLAlchemy model, the repository classes, and the
throwaway in-memory database are defined in exactly one place.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from enums import UserStatus
from sqlalchemy import ForeignKey, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing_extensions import TypedDict

from fast_repository import CRUDRepository, CRUDRepositoryInterface


def _utcnow() -> datetime:
    """Default timestamp for newly created articles."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for the example entities."""


class User(Base):
    """A minimal user entity used throughout the examples."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[UserStatus]
    age: Mapped[int]


class UserRepositoryInterface(CRUDRepositoryInterface[User], ABC):
    """Domain-facing interface — depend on this from your business logic."""


class UserRepository(CRUDRepository[User], UserRepositoryInterface):
    """Concrete repository — all CRUD methods come from the library."""


class Article(Base):
    """An article authored by a user, with a soft-delete column."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class ArticleStats(TypedDict):
    """Per-author aggregates returned by ``find_stats_by_user``."""

    author_id: int
    article_count: int
    first_created_at: datetime
    last_created_at: datetime


class ArticleRepositoryInterface(CRUDRepositoryInterface[Article], ABC):
    """Domain interface that extends CRUD with a custom aggregate query.

    ``CRUDRepositoryInterface`` only declares generic CRUD. A query it does not
    cover is declared here, so business logic depending on this interface sees
    it as part of the contract — not an implementation detail.
    """

    @abstractmethod
    async def find_stats_by_user(self) -> list[ArticleStats]:
        """Return per-author article counts and first/last creation times."""


class ArticleRepository(
    CRUDRepository[Article],
    ArticleRepositoryInterface,
    soft_delete=Article.deleted_at,
):
    """Soft-deleting repository that also implements ``find_stats_by_user``."""

    async def find_stats_by_user(self) -> list[ArticleStats]:
        """Group live articles by author via a SQLAlchemy aggregate query.

        ``self.session`` is the live session, so any SQLAlchemy statement is
        available here. The ``deleted_at IS NULL`` filter keeps the aggregate
        consistent with the repository's soft-delete reads.
        """
        result = await self.session.execute(
            select(
                Article.author_id,
                func.count(Article.id),
                func.min(Article.created_at),
                func.max(Article.created_at),
            )
            .where(Article.deleted_at.is_(None))
            .group_by(Article.author_id)
            .order_by(Article.author_id)
        )
        return [
            ArticleStats(
                author_id=author_id,
                article_count=count,
                first_created_at=first,
                last_created_at=last,
            )
            for author_id, count, first, last in result.all()
        ]


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
            User(name="Ada", status=UserStatus.ACTIVE, age=36),
            User(name="Linus", status=UserStatus.ACTIVE, age=54),
            User(name="Grace", status=UserStatus.INACTIVE, age=85),
            User(name="Kent", status=UserStatus.ACTIVE, age=64),
        ]
    )
