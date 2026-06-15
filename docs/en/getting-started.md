# Getting Started

**English** | [한국어](../ko/getting-started.md)

This guide takes you from installation to a working repository.

## Install

```bash
pip install fast-repository
```

`fast-repository` needs Python 3.10+, SQLAlchemy 2.0+, and fastapi-pagination.
They are pulled in automatically.

## 1. Define an entity

Any SQLAlchemy declarative model works:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    ...


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    age: Mapped[int]
```

## 2. Declare the interface

Subclass `CRUDRepositoryInterface` with your entity. This is the type your
domain layer depends on — it knows nothing about SQLAlchemy:

```python
from abc import ABC

from fast_repository import CRUDRepositoryInterface


class UserRepositoryInterface(CRUDRepositoryInterface[User], ABC):
    ...
```

## 3. Get the implementation for free

Subclass `CRUDRepository` with the same entity. Every CRUD method is provided —
there is no body to write:

```python
from fast_repository import CRUDRepository


class UserRepository(CRUDRepository[User], UserRepositoryInterface):
    ...
```

The entity class is captured from the generic argument (`CRUDRepository[User]`)
at class-definition time, so no constructor wiring is needed beyond the session.

> **Note:** The class must be subclassed with a concrete entity. Instantiating
> `CRUDRepository[User]` directly, or subclassing without an entity, raises
> `TypeError`.

## 4. Use it

Construct the repository with an `AsyncSession` and call its methods:

```python
repo = UserRepository(session)

user = await repo.save(User(name="Ada", status="active", age=36))
fetched = await repo.find(user.id)
everyone = await repo.find_all()
await repo.delete(user)
```

## Synchronous repositories

Prefer a synchronous `Session`? Use `SyncCRUDRepository` and
`SyncCRUDRepositoryInterface`. The API is identical — just without `async`/`await`:

```python
from fast_repository import SyncCRUDRepositoryInterface, SyncCRUDRepository


class UserRepositoryInterface(SyncCRUDRepositoryInterface[User], ABC):
    ...


class UserRepository(SyncCRUDRepository[User], UserRepositoryInterface):
    ...


repo = UserRepository(session)  # a sqlalchemy.orm.Session

user = repo.save(User(name="Ada", status="active", age=36))
fetched = repo.find(user.id)
everyone = repo.find_all()
repo.delete(user)
```

Filtering, `with_for_update`, the `autocommit` flag, and base-`stmt`
customization all work the same as the async repository.

## Next steps

- [Filtering](filtering.md) — query with keyword filters and operators.
- [Customizing queries](customizing-queries.md) — eager-load relationships or
  apply a default filter to every read.
- [Transactions](transactions.md) — control commit with the `autocommit` flag.
- [Soft delete](soft-delete.md) — mark rows deleted instead of removing them.
- [FastAPI integration](fastapi.md) — wire the repository into routes with
  dependency injection.
- [Runnable examples](../../examples/README.md) — scripts and a small FastAPI app.
