"""Shared fixtures for the test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from tests.models import Base, SyncUserRepository, User, UserRepository


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


@pytest.fixture
def sync_session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_maker = sessionmaker(engine, expire_on_commit=False)
    with session_maker() as session:
        yield session
    engine.dispose()


@pytest.fixture
def sync_repo(sync_session: Session) -> SyncUserRepository:
    return SyncUserRepository(sync_session)


@pytest.fixture
def sync_users(sync_session: Session) -> list[User]:
    seeded = [
        User(name="user-0", status="active", age=20),
        User(name="user-1", status="active", age=30),
        User(name="user-2", status="inactive", age=40),
    ]
    sync_session.add_all(seeded)
    sync_session.commit()
    return seeded
