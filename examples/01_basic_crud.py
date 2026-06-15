"""Basic CRUD: create, read, update, and delete a single entity.

Run it::

    uv run python examples/01_basic_crud.py
"""

from __future__ import annotations

import asyncio

from enums import UserStatus
from models import User, UserRepository, make_session


async def main() -> None:
    """Walk through one entity's full create/read/update/delete lifecycle."""
    async for session in make_session():
        repo = UserRepository(session)

        # Create — save() persists and commits.
        user = await repo.save(User(name="Ada", status=UserStatus.ACTIVE, age=36))
        print(f"created: id={user.id} name={user.name}")

        # Read — find() looks the entity up by its primary key.
        fetched = await repo.find(user.id)
        assert fetched is not None
        print(f"found:   {fetched.name}, age {fetched.age}")

        # Update — mutate the entity and save() again (same method as create).
        fetched.age = 37
        await repo.save(fetched)
        print(f"updated: age is now {fetched.age}")

        # Delete — delete() removes the row and commits.
        await repo.delete(fetched)
        print(f"deleted: find() now returns {await repo.find(user.id)}")


if __name__ == "__main__":
    asyncio.run(main())
