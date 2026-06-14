# fast-repository

**English** | [한국어](https://github.com/2u2s/fast-repository/blob/main/README.ko.md)

Interface-first repository pattern for FastAPI + SQLAlchemy.

Declare the repository interface, get the implementation for free.

## Why

A repository keeps your domain layer depending on abstractions, but writing
the same CRUD implementation for every entity is boilerplate.
`fast-repository` removes that boilerplate while keeping the pattern intact:

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
await repo.find_all_paginated(params=Params(page=1, size=50), status="active")
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

## Documentation

- [Getting Started](https://github.com/2u2s/fast-repository/blob/main/docs/en/getting-started.md) — install, define an entity, wire up a repository.
- [Filtering](https://github.com/2u2s/fast-repository/blob/main/docs/en/filtering.md) — keyword filters, operator suffixes, primary-key lookups, pagination.
- [Customizing queries](https://github.com/2u2s/fast-repository/blob/main/docs/en/customizing-queries.md) — eager-load relationships or apply a default filter to every read.
- [Transactions](https://github.com/2u2s/fast-repository/blob/main/docs/en/transactions.md) — control commit with the `autocommit` flag and group work into a unit of work.
- [Soft delete](https://github.com/2u2s/fast-repository/blob/main/docs/en/soft-delete.md) — opt in to marking rows deleted instead of removing them.

Runnable [examples](https://github.com/2u2s/fast-repository/blob/main/examples/README.md) cover basic CRUD, filtering, the
`autocommit` flag, and a small FastAPI app.

## License

MIT
