# Soft delete

By default `delete` removes rows. Opt into soft deletion and `delete` instead
marks rows as deleted, while reads transparently hide them.

> **Note:** The examples use the async repository. `SyncCRUDRepository` behaves
> the same without `await`.

## Enabling it

Add a soft-delete column to the entity and name it with the `soft_delete` class
keyword. The column may be a `datetime` (set to the deletion time, `NULL` while
alive) or a `bool` (set to `True` when deleted) — the type is detected
automatically:

```python
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class ArticleRepository(CRUDRepository[Article], soft_delete="deleted_at"):
    ...
```

`soft_delete` accepts either the column name or the mapped attribute itself.
Passing the attribute is type-checked and refactor-safe, so a typo is caught at
definition time rather than at runtime:

```python
class ArticleRepository(CRUDRepository[Article], soft_delete=Article.deleted_at):
    ...
```

Naming a column that does not exist, or one that is not a datetime or boolean,
raises `ValueError` when the repository is constructed.

## Deleting

`delete` and `delete_all` now mark rows instead of removing them, honouring the
`autocommit` flag exactly as before:

```python
await repo.delete(article)       # sets deleted_at = now and commits
await repo.delete_all(articles)  # marks each one
```

To remove a row for real, pass `hard=True`:

```python
await repo.delete(article, hard=True)  # physical DELETE
```

## Reading

Every read method filters out soft-deleted rows automatically:

```python
await repo.find(article.id)   # None once the article is soft-deleted
await repo.find_all()         # excludes soft-deleted rows
```

Pass `with_deleted=True` to include them:

```python
await repo.find(article.id, with_deleted=True)
await repo.find_all(status="archived", with_deleted=True)
```

The soft-delete filter is combined with your keyword filters, custom
expressions, and any base `stmt` using `AND`.
