"""Repository implementations."""

from __future__ import annotations

from .crud import CRUDRepository
from .sync import SyncCRUDRepository

__all__ = ["CRUDRepository", "SyncCRUDRepository"]
