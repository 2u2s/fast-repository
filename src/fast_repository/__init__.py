"""Interface-first repository pattern for FastAPI and SQLAlchemy."""

from __future__ import annotations

from .errors import InvalidFilterError
from .impl import CRUDRepository, SyncCRUDRepository
from .interface import CRUDRepositoryInterface, SyncCRUDRepositoryInterface
from .types import DbLockInfo

__all__ = [
    "CRUDRepository",
    "CRUDRepositoryInterface",
    "DbLockInfo",
    "InvalidFilterError",
    "SyncCRUDRepository",
    "SyncCRUDRepositoryInterface",
]
