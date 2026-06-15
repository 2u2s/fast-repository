# fast-repository

**English** | [한국어](https://github.com/2u2s/fast-repository/blob/main/README.ko.md)

[![PyPI](https://img.shields.io/pypi/v/fast-repository)](https://pypi.org/project/fast-repository/)
[![Python](https://img.shields.io/pypi/pyversions/fast-repository)](https://pypi.org/project/fast-repository/)
[![License](https://img.shields.io/pypi/l/fast-repository)](https://github.com/2u2s/fast-repository/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/fast-repository/month)](https://pepy.tech/project/fast-repository)

Interface-first repository pattern for FastAPI + SQLAlchemy.

Declare the repository interface, get the implementation for free.

## Why

A repository keeps your domain layer depending on abstractions, but writing
the same CRUD implementation for every entity is boilerplate.

**Before** — hand-written, and repeated for every entity:

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase): ...


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]
    status: Mapped[str]


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find(self, id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.id == id))

    async def find_all(
        self,
        name: str | None = None,
        age: int | None = None,
        status: str | None = None,
    ) -> list[User]:
        stmt = select(User)
        if name is not None:
            stmt = stmt.where(User.name == name)
        if age is not None:
            stmt = stmt.where(User.age == age)
        if status is not None:
            stmt = stmt.where(User.status == status)
        return list((await self.session.scalars(stmt)).all())

    async def count(
        self,
        name: str | None = None,
        age: int | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(User)
        if name is not None:
            stmt = stmt.where(User.name == name)
        if age is not None:
            stmt = stmt.where(User.age == age)
        if status is not None:
            stmt = stmt.where(User.status == status)
        return await self.session.scalar(stmt) or 0

    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    # ...and exists(), save_all(), delete_all(), find_all_paginated(),
    #    operator filters (__in / __ne / __like), row locking, soft delete —
    #    all written again for every entity.
```

**After** — `fast-repository` provides all of the above, pattern intact:

```python
from abc import ABC

from fast_repository import AbstractCRUDRepository, CRUDRepository

# Domain layer: depend on this interface.
class AbstractUserRepository(AbstractCRUDRepository[User], ABC): ...

# Infrastructure layer: zero boilerplate, all CRUD methods provided.
class UserRepository(CRUDRepository[User], AbstractUserRepository): ...
```

The entity class is captured from the generic argument (`CRUDRepository[User]`)
at class-definition time — no constructor wiring, no metaclass tricks to learn.

Using a synchronous `Session`? `SyncCRUDRepository` and
`AbstractSyncCRUDRepository` offer the same API without `async`/`await`.

## Installation

```bash
pip install fast-repository
```

Requires Python 3.10+, SQLAlchemy 2.0+ (async or sync), and fastapi-pagination.

## Usage

```python
repo = UserRepository(session)  # AsyncSession

await repo.find(1)                                # SELECT ... WHERE id = 1
await repo.find(1, with_for_update=True)          # ... FOR UPDATE (row lock)
await repo.find(user_id=1, group_id=2)            # composite key by name
await repo.find_all(status="active")              # ... WHERE status = 'active'
await repo.find_all(id__in=[1, 2, 3])             # ... WHERE id IN (1, 2, 3)
await repo.find_all(age__ge=18, name__like="K%") # operator suffixes
await repo.find_all(or_(User.age < 18, User.age >= 65))  # raw SQLAlchemy expressions
await repo.find_all(status__ne="active")          # ... WHERE status != 'active'
await repo.find_all(id__notin=[1, 2, 3])          # ... WHERE id NOT IN (1, 2, 3)
await repo.find_all(order_by=User.age.desc())     # ... ORDER BY age DESC
await repo.find_all_paginated(params=Params(page=1, size=50), status="active")  # params optional under FastAPI
await repo.count(status="active")                 # SELECT count(*) ... WHERE status = 'active'
await repo.exists(id=1)                           # SELECT EXISTS(...) -> bool

await repo.save(user)
await repo.save_all(users)
await repo.delete(user)
await repo.delete_all(users)
```

### Filter syntax

| Keyword                                 | SQL                     |
|-----------------------------------------|-------------------------|
| `column=value`                          | `column = value`        |
| `column__in=[a, b]`                     | `column IN (a, b)`      |
| `column__notin=[a, b]`                  | `column NOT IN (a, b)`  |
| `column__ne=value`                      | `column != value`       |
| `column__gt` / `__ge` / `__lt` / `__le` | `>` / `>=` / `<` / `<=` |
| `column__like` / `__ilike`              | `LIKE` / `ILIKE`        |
| `column__is=None`                       | `IS NULL`               |

Unknown columns and operators raise `InvalidFilterError` instead of being
silently ignored, so a typo can never return unfiltered data.

### Customizing queries

Declare a base `stmt` to change relationship loading or apply a default
filter to every read. Pass it as a class keyword argument:

```python
class UserRepository(
    CRUDRepository[User],
    stmt=select(User).options(selectinload(User.posts)),
):
    ...
```

When omitted, reads default to `select(User)`. For runtime customization you
can also assign `self.stmt` on an instance.

### Typed filters for IDE autocomplete

`find_all`, `count`, and the other read methods take arbitrary keyword filters,
so a type checker can't suggest your entity's columns by name. To get IDE autocomplete,
re-declare the method on your interface like this:

```python
from sqlalchemy.sql import ColumnElement


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    @abstractmethod
    async def find_all(
        self,
        *criteria: ColumnElement[bool],
        status: str | None = None,
        **_,
    ) -> list[User]: ...
```

Wherever a value is typed as `AbstractUserRepository`, the editor now suggests `status=`.
Expose more filters by adding more keywords:

```python
class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    @abstractmethod
    async def find_all(
        self,
        *criteria: ColumnElement[bool],
        status: str | None = None,
        age: int | None = None,
        **_,
    ) -> list[User]: ...
```

This takes effect only when the variable is typed as the interface.

### Pagination with FastAPI

Inside a FastAPI route you do not need to pass `params` at all. When the
response model is a `Page[...]` and `add_pagination(app)` is wired up,
fastapi-pagination parses `?page=`/`?size=` from the query string and
`find_all_paginated` picks them up automatically:

```python
from fastapi import FastAPI
from fastapi_pagination import Page, add_pagination

app = FastAPI()

@app.get("/users", response_model=Page[UserOut])
async def list_users(repo: UserRepo, status: str | None = None) -> Page[User]:
    filters = {"status": status} if status is not None else {}
    return await repo.find_all_paginated(**filters)  # params injected from the request

add_pagination(app)
```

## Documentation

- [Getting Started](https://github.com/2u2s/fast-repository/blob/main/docs/en/getting-started.md) — install, define an entity, wire up a repository.
- [Filtering](https://github.com/2u2s/fast-repository/blob/main/docs/en/filtering.md) — keyword filters, operator suffixes, primary-key lookups, pagination.
- [Customizing queries](https://github.com/2u2s/fast-repository/blob/main/docs/en/customizing-queries.md) — eager-load relationships or apply a default filter to every read.
- [Transactions](https://github.com/2u2s/fast-repository/blob/main/docs/en/transactions.md) — control commit with the `autocommit` flag and group work into a unit of work.
- [Soft delete](https://github.com/2u2s/fast-repository/blob/main/docs/en/soft-delete.md) — opt in to marking rows deleted instead of removing them.
- [FastAPI integration](https://github.com/2u2s/fast-repository/blob/main/docs/en/fastapi.md) — wire the repository into routes with dependency injection.

Runnable [examples](https://github.com/2u2s/fast-repository/blob/main/examples/README.md) cover basic CRUD, filtering, the
`autocommit` flag, and a small FastAPI app.

## License

MIT
