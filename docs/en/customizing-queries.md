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

## How filters compose

Keyword filters from [filtering](filtering.md) are appended to whatever `stmt`
already defines. The base statement sets the starting point (joins, loader
options, default conditions); per-call filters narrow it further. The two are
independent, so a custom `stmt` and keyword filters work together without
special handling.
