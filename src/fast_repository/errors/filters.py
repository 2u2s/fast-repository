"""Errors raised while translating keyword filters."""

from __future__ import annotations


class InvalidFilterError(ValueError):
    """Raised when a keyword filter matches no column or operator."""
