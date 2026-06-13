"""Tests for soft-delete support."""

from __future__ import annotations

import pytest
from fastapi_pagination import Params
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from fast_repository import CRUDRepository
from tests.models import (
    Article,
    ArticleRepository,
    Note,
    NoteRepository,
    SyncArticleRepository,
)


@pytest.mark.asyncio
async def test_delete_soft_marks_instead_of_removing(session: AsyncSession) -> None:
    repo = ArticleRepository(session)
    article = await repo.save(Article(title="hello"))

    await repo.delete(article)

    assert article.deleted_at is not None  # marked, not removed
    assert await repo.find(article.id) is None  # excluded by default
    assert await repo.find(article.id, with_deleted=True) is article  # still there


@pytest.mark.asyncio
async def test_find_all_excludes_soft_deleted_unless_requested(
    session: AsyncSession,
) -> None:
    repo = ArticleRepository(session)
    kept = await repo.save(Article(title="kept"))
    gone = await repo.save(Article(title="gone"))

    await repo.delete(gone)

    assert [a.id for a in await repo.find_all()] == [kept.id]
    with_deleted = await repo.find_all(with_deleted=True)
    assert sorted(a.id for a in with_deleted) == sorted([kept.id, gone.id])


@pytest.mark.asyncio
async def test_find_all_paginated_excludes_soft_deleted(session: AsyncSession) -> None:
    repo = ArticleRepository(session)
    await repo.save_all([Article(title="a"), Article(title="b")])
    gone = await repo.save(Article(title="c"))

    await repo.delete(gone)

    page = await repo.find_all_paginated(Params(page=1, size=50))
    assert page.total == 2


@pytest.mark.asyncio
async def test_hard_delete_physically_removes(session: AsyncSession) -> None:
    repo = ArticleRepository(session)
    article = await repo.save(Article(title="hello"))

    await repo.delete(article, hard=True)

    assert await repo.find(article.id, with_deleted=True) is None


@pytest.mark.asyncio
async def test_delete_all_soft_marks_every_entity(session: AsyncSession) -> None:
    repo = ArticleRepository(session)
    articles = await repo.save_all([Article(title="a"), Article(title="b")])

    await repo.delete_all(articles)

    assert await repo.find_all() == []
    assert len(await repo.find_all(with_deleted=True)) == 2


@pytest.mark.asyncio
async def test_soft_delete_respects_autocommit_false(session: AsyncSession) -> None:
    repo = ArticleRepository(session)
    article = await repo.save(Article(title="hello"))
    article_id = article.id  # capture before rollback expires the instance

    await repo.delete(article, autocommit=False)
    assert await repo.find(article_id) is None  # flushed: hidden in transaction

    await session.rollback()
    assert await repo.find(article_id) is not None  # not committed: restored


@pytest.mark.asyncio
async def test_boolean_soft_delete_sets_true(session: AsyncSession) -> None:
    repo = NoteRepository(session)
    note = await repo.save(Note(body="hello"))

    await repo.delete(note)

    assert note.archived is True
    assert await repo.find(note.id) is None
    assert await repo.find(note.id, with_deleted=True) is note


@pytest.mark.asyncio
async def test_unknown_soft_delete_column_raises(session: AsyncSession) -> None:
    class BadColumn(CRUDRepository[Article], soft_delete="missing"):
        """Names a column that does not exist."""

    with pytest.raises(ValueError, match="not a mapped column"):
        BadColumn(session)


@pytest.mark.asyncio
async def test_unsupported_soft_delete_type_raises(session: AsyncSession) -> None:
    class BadType(CRUDRepository[Article], soft_delete="title"):
        """Points at a non-datetime, non-boolean column."""

    with pytest.raises(ValueError, match="datetime or boolean"):
        BadType(session)


@pytest.mark.asyncio
async def test_soft_delete_accepts_mapped_attribute(session: AsyncSession) -> None:
    class MappedArticleRepository(
        CRUDRepository[Article], soft_delete=Article.deleted_at
    ):
        """Configured with the mapped attribute instead of a column name."""

    assert MappedArticleRepository._soft_delete_column == "deleted_at"

    repo = MappedArticleRepository(session)
    article = await repo.save(Article(title="hello"))

    await repo.delete(article)

    assert article.deleted_at is not None
    assert await repo.find(article.id) is None
    assert await repo.find(article.id, with_deleted=True) is article


def test_sync_delete_soft_marks_instead_of_removing(sync_session: Session) -> None:
    repo = SyncArticleRepository(sync_session)
    article = repo.save(Article(title="hello"))

    repo.delete(article)

    assert article.deleted_at is not None
    assert repo.find(article.id) is None
    assert repo.find(article.id, with_deleted=True) is article


def test_sync_find_all_excludes_soft_deleted(sync_session: Session) -> None:
    repo = SyncArticleRepository(sync_session)
    kept = repo.save(Article(title="kept"))
    gone = repo.save(Article(title="gone"))

    repo.delete(gone)

    assert [a.id for a in repo.find_all()] == [kept.id]
    assert len(repo.find_all(with_deleted=True)) == 2
