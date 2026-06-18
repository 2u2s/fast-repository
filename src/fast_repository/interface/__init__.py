"""Repository interfaces."""

from __future__ import annotations

from .crud import CRUDRepositoryInterface
from .sync import SyncCRUDRepositoryInterface

__all__ = ["CRUDRepositoryInterface", "SyncCRUDRepositoryInterface"]
