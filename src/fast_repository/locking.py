"""Row-locking options for read methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

    _LockTarget = type[DeclarativeBase] | InstrumentedAttribute[Any]


class DbLockInfo(TypedDict, total=False):
    """Row-locking options forwarded to SQLAlchemy's ``Select.with_for_update``.

    Every key is optional. Passing an empty mapping (or ``True`` to the read
    method) requests a plain ``FOR UPDATE``. See the SQLAlchemy documentation for
    ``Select.with_for_update`` for the exact semantics of each option.
    """

    nowait: bool
    read: bool
    skip_locked: bool
    key_share: bool
    of: _LockTarget | Sequence[_LockTarget]
