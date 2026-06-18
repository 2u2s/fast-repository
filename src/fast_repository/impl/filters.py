"""Translate keyword filters into SQLAlchemy where-conditions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect

from ..enums import FilterOperator
from ..errors import InvalidFilterError

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.sql import ColumnElement


_OPERATORS: dict[FilterOperator, Callable[[Any, Any], Any]] = {
    FilterOperator.IN: lambda column, value: column.in_(value),
    FilterOperator.NOTIN: lambda column, value: column.not_in(value),
    FilterOperator.NE: lambda column, value: column != value,
    FilterOperator.GT: lambda column, value: column > value,
    FilterOperator.GE: lambda column, value: column >= value,
    FilterOperator.LT: lambda column, value: column < value,
    FilterOperator.LE: lambda column, value: column <= value,
    FilterOperator.LIKE: lambda column, value: column.like(value),
    FilterOperator.ILIKE: lambda column, value: column.ilike(value),
    FilterOperator.IS: lambda column, value: column.is_(value),
}


def build_conditions(
    entity_cls: type[DeclarativeBase],
    filters: dict[str, Any],
) -> list[ColumnElement[bool]]:
    """Build where-conditions from keyword filters.

    A bare ``column=value`` keyword translates to an equality condition.
    A ``column__operator`` keyword applies the named operator (``in``,
    ``notin``, ``ne``, ``gt``, ``ge``, ``lt``, ``le``, ``like``, ``ilike``,
    ``is``). Exact
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
        apply = _OPERATORS.get(operator)
        if separator and name in column_attrs and apply is not None:
            column = column_attrs[name].class_attribute
            conditions.append(apply(column, value))
            continue
        raise InvalidFilterError(
            f"{key!r} does not match any column of {entity_cls.__name__} "
            "or a supported operator."
        )
    return conditions
