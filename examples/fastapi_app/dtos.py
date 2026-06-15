"""Request/response DTOs and list-query parameters for the user endpoints."""

from __future__ import annotations

from enums import UserStatus
from pydantic import BaseModel


class UserIn(BaseModel):
    """Request body for creating a user."""

    name: str
    status: UserStatus = UserStatus.ACTIVE
    age: int


class UserUpdate(BaseModel):
    """Request body for partially updating a user.

    Every field is optional; only the fields the client actually sends are
    applied (see the router's ``exclude_unset`` handling).

    """

    name: str | None = None
    status: UserStatus | None = None
    age: int | None = None


class UserOut(BaseModel):
    """Response body for a user."""

    id: int
    name: str
    status: UserStatus
    age: int

    model_config = {"from_attributes": True}


class UserListParams(BaseModel):
    """Query parameters shared by the list and count endpoints.

    ``order`` accepts a column name (``id``, ``name``, ``age``) optionally
    prefixed with ``-`` for descending, e.g. ``-age``.

    """

    status: UserStatus | None = None
    min_age: int | None = None
    order: str = "id"
