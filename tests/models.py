"""Test entities and repositories."""

from __future__ import annotations

from abc import ABC

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fast_repository import AbstractCRUDRepository, CRUDRepository


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


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    """Domain-facing interface for user repositories."""


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    """User repository whose CRUD methods come from the library."""
