"""Shared enums for the examples.

Lives at the examples package root (not inside ``fastapi_app``) because the
shared ``models.py`` entity references ``UserStatus`` and must be importable by
both the scripts and the FastAPI app.
"""

from __future__ import annotations

from enum import Enum, auto


class UserStatus(str, Enum):
    """A user's account status.

    Values come from ``auto()``; ``_generate_next_value_`` makes each value the
    uppercased member name, so ``UserStatus.ACTIVE.value == "ACTIVE"``. Being a
    ``str`` subclass, members serialize to that string in JSON and render as a
    dropdown in the ``/docs`` schema.
    """

    @staticmethod
    def _generate_next_value_(name: str, *_) -> str:
        return name.upper()

    ACTIVE = auto()
    INACTIVE = auto()
