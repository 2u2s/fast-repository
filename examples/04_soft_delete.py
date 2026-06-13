"""Soft delete: mark rows deleted instead of removing them.

``ArticleRepository`` opts in with ``soft_delete=Article.deleted_at``, so
``delete`` stamps the column and reads hide the row unless asked otherwise.

Run it::

    uv run python examples/04_soft_delete.py
"""

from __future__ import annotations

import asyncio

from models import Article, ArticleRepository, make_session


async def main() -> None:
    """Soft-delete an article, then show how reads treat it."""
    async for session in make_session():
        repo = ArticleRepository(session)
        article = await repo.save(Article(title="Hello"))
        article_id = article.id

        # delete() marks the row instead of removing it.
        await repo.delete(article)
        print(f"deleted_at set:        {article.deleted_at is not None}")

        # Reads hide soft-deleted rows by default...
        print(f"find (default):        {await repo.find(article_id)}")
        print(f"find_all (default):    {await repo.find_all()}")

        # ...unless you ask for them.
        found = await repo.find(article_id, with_deleted=True)
        print(f"find with_deleted:     {found.title if found else None}")

        # hard=True removes the row for real.
        await repo.delete(found, hard=True)
        print(
            f"after hard delete:     {await repo.find(article_id, with_deleted=True)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
