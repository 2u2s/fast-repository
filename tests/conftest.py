"""Shared fixtures for the test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tests.models import Base, User, UserRepository


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def repo(session: AsyncSession) -> UserRepository:
    return UserRepository(session)


@pytest_asyncio.fixture
async def users(session: AsyncSession) -> list[User]:
    seeded = [
        User(name="user-0", status="active", age=20),
        User(name="user-1", status="active", age=30),
        User(name="user-2", status="inactive", age=40),
    ]
    session.add_all(seeded)
    await session.commit()
    return seeded
