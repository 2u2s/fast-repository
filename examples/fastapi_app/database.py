"""SQLAlchemy infrastructure for the example app.

Owns the engine, the session maker, the application ``lifespan`` (schema
creation and engine disposal), and the request-scoped ``get_session``
dependency. Nothing here is fast-repository specific — it is the plumbing any
async SQLAlchemy app needs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from models import Base
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

engine = create_async_engine("sqlite+aiosqlite:///./examples.db")
session_maker = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the schema on startup, dispose the engine on shutdown."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session."""
    async with session_maker() as session:
        yield session
