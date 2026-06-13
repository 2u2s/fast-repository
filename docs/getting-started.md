# Getting Started

This guide takes you from installation to a working repository.

## Install

```bash
pip install fast-repository
```

`fast-repository` needs Python 3.10+, SQLAlchemy 2.0+ (async), and
fastapi-pagination. They are pulled in automatically.

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

Subclass `AbstractCRUDRepository` with your entity. This is the type your
domain layer depends on — it knows nothing about SQLAlchemy:

```python
from abc import ABC

from fast_repository import AbstractCRUDRepository


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    ...
```

## 3. Get the implementation for free

Subclass `CRUDRepository` with the same entity. Every CRUD method is provided —
there is no body to write:

```python
from fast_repository import CRUDRepository


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    ...
```

The entity class is captured from the generic argument (`CRUDRepository[User]`)
at class-definition time, so no constructor wiring is needed beyond the session.

!!! note
    The class must be subclassed with a concrete entity. Instantiating
    `CRUDRepository[User]` directly, or subclassing without an entity, raises
    `TypeError`.

## 4. Use it

Construct the repository with an `AsyncSession` and call its methods:

```python
repo = UserRepository(session)

user = await repo.save(User(name="Ada", status="active", age=36))
fetched = await repo.find(user.id)
everyone = await repo.find_all()
await repo.delete(user)
```

## Next steps

- [Filtering](filtering.md) — query with keyword filters and operators.
- [Customizing queries](customizing-queries.md) — eager-load relationships or
  apply a default filter to every read.
- [Runnable examples](../examples/README.md) — scripts and a small FastAPI app.
