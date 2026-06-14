"""A minimal FastAPI app wiring the repository in through dependency injection.

The repository depends only on an ``AsyncSession``, so it drops straight into
FastAPI's ``Depends`` system. The route handlers depend on the *abstract*
repository, keeping the domain layer unaware of SQLAlchemy.

Run it::

    uv run uvicorn app:app --app-dir examples --reload

Then open http://127.0.0.1:8000/docs to try the endpoints.

"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_pagination import Page, add_pagination
from models import AbstractUserRepository, Base, User, UserRepository
from pydantic import BaseModel
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


app = FastAPI(lifespan=lifespan)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session."""
    async with session_maker() as session:
        yield session


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AbstractUserRepository:
    """Provide a repository, typed as the abstract interface."""
    return UserRepository(session)


UserRepo = Annotated[AbstractUserRepository, Depends(get_user_repository)]


class UserIn(BaseModel):
    """Request body for creating a user."""

    name: str
    status: str = "active"
    age: int


class UserOut(BaseModel):
    """Response body for a user."""

    id: int
    name: str
    status: str
    age: int

    model_config = {"from_attributes": True}


@app.post("/users", response_model=UserOut)
async def create_user(body: UserIn, repo: UserRepo) -> User:
    """Create a user."""
    return await repo.save(User(**body.model_dump()))


@app.get("/users/{user_id}", response_model=UserOut)
async def read_user(user_id: int, repo: UserRepo) -> User:
    """Read a user by id, or 404 if it does not exist."""
    user = await repo.find(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    return user


@app.get("/users", response_model=Page[UserOut])
async def list_users(
    repo: UserRepo,
    status: str | None = None,
) -> Page[User]:
    """List users, optionally filtered by status, one page at a time."""
    filters = {"status": status} if status is not None else {}
    return await repo.find_all_paginated(**filters)


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, repo: UserRepo) -> None:
    """Delete a user by id, or 404 if it does not exist."""
    user = await repo.find(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    await repo.delete(user)


add_pagination(app)
