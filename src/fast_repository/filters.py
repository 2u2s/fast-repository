"""Translate keyword filters into SQLAlchemy where-conditions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.sql import ColumnElement


class InvalidFilterError(ValueError):
    """Raised when a keyword filter matches no column or operator."""


_OPERATORS: dict[str, Callable[[Any, Any], Any]] = {
    "in": lambda column, value: column.in_(value),
    "gt": lambda column, value: column > value,
    "ge": lambda column, value: column >= value,
    "lt": lambda column, value: column < value,
    "le": lambda column, value: column <= value,
    "like": lambda column, value: column.like(value),
    "ilike": lambda column, value: column.ilike(value),
    "is": lambda column, value: column.is_(value),
}


def build_conditions(
    entity_cls: type[DeclarativeBase],
    filters: dict[str, Any],
) -> list[ColumnElement[bool]]:
    """Build where-conditions from keyword filters.

    A bare ``column=value`` keyword translates to an equality condition.
    A ``column__operator`` keyword applies the named operator (``in``,
    ``gt``, ``ge``, ``lt``, ``le``, ``like``, ``ilike``, ``is``). Exact
    column names take precedence, so a column whose name contains ``__``
    is still addressable.

    Args:
        entity_cls (type[DeclarativeBase]): The mapped entity class.
        filters (dict[str, Any]): Keyword filters to translate.

    Returns:
        list[ColumnElement[bool]]: The translated where-conditions.

    Raises:
        InvalidFilterError: If a keyword matches no mapped column, or its
            operator suffix is unknown.

    """
    column_attrs = inspect(entity_cls).mapper.column_attrs
    conditions: list[ColumnElement[bool]] = []
    for key, value in filters.items():
        if key in column_attrs:
            conditions.append(column_attrs[key].class_attribute == value)
            continue
        name, separator, operator = key.rpartition("__")
        if separator and name in column_attrs and operator in _OPERATORS:
            column = column_attrs[name].class_attribute
            conditions.append(_OPERATORS[operator](column, value))
            continue
        raise InvalidFilterError(
            f"{key!r} does not match any column of {entity_cls.__name__} "
            "or a supported operator."
        )
    return conditions
