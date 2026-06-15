"""Filtering: keyword filters, operator suffixes, ordering, pagination, count, exists.

Run it::

    uv run python examples/02_filtering.py
"""

from __future__ import annotations

import asyncio

from enums import UserStatus
from fastapi_pagination import Params
from models import User, UserRepository, make_session, seed
from sqlalchemy import func, or_

from fast_repository import InvalidFilterError


async def main() -> None:
    """Query seeded users with filter operators, ordering, count, and exists."""
    async for session in make_session():
        repo = UserRepository(session)
        await seed(repo)

        # A bare keyword is an equality filter.
        active = await repo.find_all(status=UserStatus.ACTIVE)
        print(f"active users: {[u.name for u in active]}")

        # An __operator suffix applies that operator.
        veterans = await repo.find_all(age__ge=60)
        print(f"age >= 60:    {[u.name for u in veterans]}")

        names = await repo.find_all(name__in=["Ada", "Grace"])
        print(f"name in (...): {[u.name for u in names]}")

        like = await repo.find_all(name__like="A%")
        print(f"name like A%: {[u.name for u in like]}")

        # __ne and __notin negate a match.
        not_active = await repo.find_all(status__ne=UserStatus.ACTIVE)
        print(f"status != active: {[u.name for u in not_active]}")

        others = await repo.find_all(name__notin=["Ada", "Grace"])
        print(f"name not in (Ada, Grace): {[u.name for u in others]}")

        # Positional arguments are raw SQLAlchemy expressions, combined with AND.
        young_or_old = await repo.find_all(or_(User.age < 40, User.age >= 80))
        print(f"age <40 or >=80: {[u.name for u in young_or_old]}")

        # Any SQLAlchemy expression works, e.g. a function call.
        short_names = await repo.find_all(func.length(User.name) <= 4)
        print(f"name length <= 4: {[u.name for u in short_names]}")

        # Expressions and keyword filters can be mixed.
        active_seniors = await repo.find_all(User.age >= 60, status=UserStatus.ACTIVE)
        print(f"active and >=60: {[u.name for u in active_seniors]}")

        # order_by takes raw SQLAlchemy order expressions (single or list).
        by_age = await repo.find_all(order_by=User.age.desc())
        print(f"oldest first: {[(u.name, u.age) for u in by_age]}")

        # Pagination returns a Page ordered by primary key; order_by is also accepted
        # and the primary key is appended automatically as a tie-breaker.
        page = await repo.find_all_paginated(
            Params(page=1, size=2), status=UserStatus.ACTIVE
        )
        print(f"page 1/size 2: {[u.name for u in page.items]} of {page.total} total")

        # count() and exists() take the same filters as find_all.
        active_count = await repo.count(status=UserStatus.ACTIVE)
        print(f"active count: {active_count}")

        has_ada = await repo.exists(name="Ada")
        print(f"Ada exists: {has_ada}")

        # A typo raises instead of silently returning unfiltered rows.
        try:
            await repo.find_all(stauts="active")
        except InvalidFilterError as error:
            print(f"rejected typo: {error}")


if __name__ == "__main__":
    asyncio.run(main())
