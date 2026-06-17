# Customizing queries

**English** | [한국어](../ko/customizing-queries.md)

Every read method (`find`, `find_all`, `find_all_paginated`) builds on a base
select statement, `stmt`. It defaults to `select(YourEntity)`. Override it to
eager-load relationships or apply a filter to every read.

> **Note:** This applies equally to `SyncCRUDRepository`. The examples use
> `CRUDRepository`, but swap in `SyncCRUDRepository` and it behaves the same.

## At class-definition time

Pass `stmt` as a class keyword argument. 

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class UserRepository(
    CRUDRepository[User],
    stmt=select(User).options(selectinload(User.posts)),
):
    ...
```

Now every read eager-loads `posts`. Subclasses inherit the custom statement
unless they declare their own.

### A default filter on every read

Because `stmt` is a full select, it can carry a `where` clause that scopes all
reads — useful for an "active rows only" repository:

```python
class ActiveUserRepository(
    CRUDRepository[User],
    stmt=select(User).where(User.status == "active"),
):
    ...
```

`find_all()` on this repository returns only active users, and keyword filters
are added on top of the base condition.

## Adding custom query methods

`CRUDRepositoryInterface` declares only generic CRUD. For a query it does not
cover, declare it on a domain interface and implement it on the concrete
repository. Callers depend on the interface, so the custom query is part of the
contract — not an implementation detail leaking through.

```python
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import func, select
from typing_extensions import TypedDict

from fast_repository import CRUDRepository, CRUDRepositoryInterface


class ArticleStats(TypedDict):
    author_id: int
    article_count: int
    first_created_at: datetime
    last_created_at: datetime


class ArticleRepositoryInterface(CRUDRepositoryInterface[Article], ABC):
    @abstractmethod
    async def find_stats_by_user(self) -> list[ArticleStats]:
        """Per-author article counts and first/last creation times."""


class ArticleRepository(CRUDRepository[Article], ArticleRepositoryInterface):
    async def find_stats_by_user(self) -> list[ArticleStats]:
        result = await self.session.execute(
            select(
                Article.author_id,
                func.count(Article.id),
                func.min(Article.created_at),
                func.max(Article.created_at),
            )
            .group_by(Article.author_id)
            .order_by(Article.author_id)
        )
        return [
            ArticleStats(
                author_id=author_id,
                article_count=count,
                first_created_at=first,
                last_created_at=last,
            )
            for author_id, count, first, last in result.all()
        ]
```

`self.session` exposes the live session, so you can build SQLAlchemy statements directly.
Because callers work against `ArticleRepositoryInterface`, they never handle the session
themselves — the custom method behaves like any other.

See [`examples/05_custom_queries.py`](../../examples/05_custom_queries.py).

## How filters compose

Keyword filters from [filtering](filtering.md) are appended to whatever `stmt`
already defines. The base statement sets the starting point (joins, loader
options, default conditions); per-call filters narrow it further. The two are
independent, so a custom `stmt` and keyword filters work together without
special handling.
