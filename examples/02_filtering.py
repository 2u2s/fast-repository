"""Filtering: keyword filters, operator suffixes, and pagination.

Run it::

    uv run python examples/02_filtering.py
"""

from __future__ import annotations

import asyncio

from fastapi_pagination import Params
from models import User, UserRepository, make_session, seed
from sqlalchemy import func, or_

from fast_repository import InvalidFilterError


async def main() -> None:
    """Query the seeded users with equality, operator, and pagination filters."""
    async for session in make_session():
        repo = UserRepository(session)
        await seed(repo)

        # A bare keyword is an equality filter.
        active = await repo.find_all(status="active")
        print(f"active users: {[u.name for u in active]}")

        # An __operator suffix applies that operator.
        veterans = await repo.find_all(age__ge=60)
        print(f"age >= 60:    {[u.name for u in veterans]}")

        names = await repo.find_all(name__in=["Ada", "Grace"])
        print(f"name in (...): {[u.name for u in names]}")

        like = await repo.find_all(name__like="A%")
        print(f"name like A%: {[u.name for u in like]}")

        # Positional arguments are raw SQLAlchemy expressions, combined with AND.
        young_or_old = await repo.find_all(or_(User.age < 40, User.age >= 80))
        print(f"age <40 or >=80: {[u.name for u in young_or_old]}")

        # Any SQLAlchemy expression works, e.g. a function call.
        short_names = await repo.find_all(func.length(User.name) <= 4)
        print(f"name length <= 4: {[u.name for u in short_names]}")

        # Expressions and keyword filters can be mixed.
        active_seniors = await repo.find_all(User.age >= 60, status="active")
        print(f"active and >=60: {[u.name for u in active_seniors]}")

        # Pagination returns a fastapi-pagination Page, ordered by primary key.
        page = await repo.find_all_paginated(Params(page=1, size=2), status="active")
        print(f"page 1/size 2: {[u.name for u in page.items]} of {page.total} total")

        # A typo raises instead of silently returning unfiltered rows.
        try:
            await repo.find_all(stauts="active")
        except InvalidFilterError as error:
            print(f"rejected typo: {error}")


if __name__ == "__main__":
    asyncio.run(main())
