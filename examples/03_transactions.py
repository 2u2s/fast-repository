"""Transactions: controlling commit with the autocommit flag.

``save``, ``save_all``, ``delete``, and ``delete_all`` commit by default.
Pass ``autocommit=False`` to only flush — generated values are populated and
the change is visible inside the transaction, but nothing is committed, so the
caller owns the transaction boundary (the unit-of-work pattern).

Run it::

    uv run python examples/03_transactions.py
"""

from __future__ import annotations

import asyncio

from enums import UserStatus
from models import User, UserRepository, make_session


async def main() -> None:
    """Contrast autocommit=False (flush only) with the default commit."""
    async for session in make_session():
        repo = UserRepository(session)

        # autocommit=False flushes: the primary key is assigned...
        new_user = User(name="Ada", status=UserStatus.ACTIVE, age=36)
        user = await repo.save(new_user, autocommit=False)
        print(f"flushed: id={user.id} is populated before commit")

        # ...but nothing is committed, so a rollback undoes it.
        await session.rollback()
        print(f"after rollback: find() returns {await repo.find(user.id)}")

        # The default, autocommit=True, commits immediately and survives a rollback.
        committed = await repo.save(
            User(name="Linus", status=UserStatus.ACTIVE, age=54)
        )
        await session.rollback()
        print(f"after commit: find() returns {(await repo.find(committed.id)).name}")


if __name__ == "__main__":
    asyncio.run(main())
