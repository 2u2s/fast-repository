"""Dependency wiring for the user endpoints.

The repository takes an ``AsyncSession`` in its constructor, so a dependency can
build one per request. It is returned typed as the *interface*, so
route handlers depend on the domain contract rather than on SQLAlchemy.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from models import UserRepository, UserRepositoryInterface
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepositoryInterface:
    """Provide a repository, typed as the interface."""
    return UserRepository(session)


UserRepo = Annotated[UserRepositoryInterface, Depends(get_user_repository)]
