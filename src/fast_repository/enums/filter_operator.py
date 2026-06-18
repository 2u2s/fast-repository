"""Operators accepted in keyword filters."""

from __future__ import annotations

from enum import Enum, auto


class FilterOperator(str, Enum):
    """Operator suffixes accepted in ``column__operator`` keyword filters.

    Each member's value is the suffix written after ``__`` in a filter keyword,
    e.g. ``age__gt=18`` selects :attr:`GT`.
    """

    @staticmethod
    def _generate_next_value_(name: str, *_) -> str:
        return name.lower()

    IN = auto()
    NOTIN = auto()
    NE = auto()
    GT = auto()
    GE = auto()
    LT = auto()
    LE = auto()
    LIKE = auto()
    ILIKE = auto()
    IS = auto()
