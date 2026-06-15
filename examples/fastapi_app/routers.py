"""HTTP endpoints for users, delegating all persistence to the repository.

Handlers depend only on the ``UserRepo`` alias, never on SQLAlchemy directly.
``update`` is just ``save`` — load, mutate, save. The list and count endpoints
share one filter-building helper so the two stay in lockstep.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from models import User
from sqlalchemy.sql import ColumnElement

from .dependencies import UserRepo
from .dtos import UserIn, UserListParams, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

_ORDER_COLUMNS = {"id": User.id, "name": User.name, "age": User.age}


def _order_by(order: str) -> ColumnElement[Any]:
    """Translate an ``order`` value like ``-age`` into a SQLAlchemy order term.

    Unknown columns fall back to the primary key, so the input is always safe.

    """
    descending = order.startswith("-")
    key = order[1:] if descending else order
    column = _ORDER_COLUMNS.get(key, User.id)
    return column.desc() if descending else column.asc()


def _filters(params: UserListParams) -> dict[str, Any]:
    """Build repository keyword filters from the query parameters."""
    filters: dict[str, Any] = {}
    if params.status is not None:
        filters["status"] = params.status
    if params.min_age is not None:
        filters["age__ge"] = params.min_age
    return filters


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserIn, repo: UserRepo) -> User:
    """Create a user."""
    return await repo.save(
        User(
            name=body.name,
            status=body.status,
            age=body.age,
        )
    )


@router.get("/{user_id}", response_model=UserOut)
async def read_user(user_id: int, repo: UserRepo) -> User:
    """Read a user by id, or 404 if it does not exist."""
    user = await repo.find(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate, repo: UserRepo) -> User:
    """Update the supplied fields of a user — update is just save."""
    user = await repo.find(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    if body.name is not None:
        user.name = body.name
    if body.status is not None:
        user.status = body.status
    if body.age is not None:
        user.age = body.age
    return await repo.save(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, repo: UserRepo) -> None:
    """Delete a user by id, or 404 if it does not exist."""
    user = await repo.find(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    await repo.delete(user)


@router.get("", response_model=Page[UserOut])
async def list_users(
    repo: UserRepo,
    params: Annotated[UserListParams, Depends()],
) -> Page[User]:
    """List users with optional status / min-age filters and ordering."""
    return await repo.find_all_paginated(
        order_by=_order_by(params.order), **_filters(params)
    )


@router.get("/stats/count")
async def count_users(
    repo: UserRepo,
    params: Annotated[UserListParams, Depends()],
) -> dict[str, int]:
    """Count users matching the same filters as the list endpoint."""
    return {"count": await repo.count(**_filters(params))}
