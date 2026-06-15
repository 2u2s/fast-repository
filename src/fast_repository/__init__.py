"""Interface-first repository pattern for FastAPI and SQLAlchemy."""

from __future__ import annotations

from .crud import CRUDRepository
from .filters import InvalidFilterError
from .interface import CRUDRepositoryInterface, SyncCRUDRepositoryInterface
from .locking import DbLockInfo
from .sync import SyncCRUDRepository

__all__ = [
    "CRUDRepository",
    "CRUDRepositoryInterface",
    "DbLockInfo",
    "InvalidFilterError",
    "SyncCRUDRepository",
    "SyncCRUDRepositoryInterface",
]
