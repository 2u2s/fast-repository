"""Custom query methods: declare on the interface, implement on the repository.

``CRUDRepositoryInterface`` covers generic CRUD. When a repository needs a query
the base interface does not provide, declare it on a domain interface
(``ArticleRepositoryInterface``) and implement it on the concrete repository
(``ArticleRepository``). Callers depend on the interface, so the custom query is
part of the contract; they never touch the SQLAlchemy aggregate underneath.

Run it::

    uv run python examples/05_custom_queries.py

"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from models import (
    Article,
    ArticleRepository,
    ArticleRepositoryInterface,
    UserRepository,
    make_session,
    seed,
)


def _at(month: int, day: int) -> datetime:
    """A fixed UTC timestamp so the aggregates are deterministic."""
    return datetime(2026, month, day, tzinfo=timezone.utc)


async def main() -> None:
    """Seed articles for two authors, then aggregate them per author."""
    async for session in make_session():
        # Seed users 1..4 so the articles below reference real authors.
        await seed(UserRepository(session))

        # Type the variable as the interface: find_stats_by_user is in its contract.
        repo: ArticleRepositoryInterface = ArticleRepository(session)
        await repo.save_all(
            [
                Article(title="Intro", author_id=1, created_at=_at(1, 5)),
                Article(title="Deep dive", author_id=1, created_at=_at(2, 10)),
                Article(title="Recap", author_id=1, created_at=_at(3, 1)),
                Article(title="Hello", author_id=2, created_at=_at(1, 20)),
            ]
        )

        print("stats per user:")
        for stats in await repo.find_stats_by_user():
            print(
                f"  author {stats['author_id']}: {stats['article_count']} articles, "
                f"first {stats['first_created_at'].date()}, "
                f"last {stats['last_created_at'].date()}"
            )

        # The custom query respects soft delete: removing a row drops the count.
        recap = await repo.find_all(title="Recap")
        await repo.delete(recap[0])

        print("after soft-deleting author 1's last article:")
        for stats in await repo.find_stats_by_user():
            print(
                f"  author {stats['author_id']}: {stats['article_count']} articles, "
                f"last {stats['last_created_at'].date()}"
            )


if __name__ == "__main__":
    asyncio.run(main())
