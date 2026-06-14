# Filtering

`find_all` and `find_all_paginated` accept keyword filters that translate to
SQL where-conditions.

> **Note:** The examples below use the async repository. With
> `SyncCRUDRepository` the calls are identical — just drop the `await`.

## Equality

A bare `column=value` keyword is an equality condition:

```python
await repo.find_all(status="active")        # WHERE status = 'active'
await repo.find_all(status="active", age=36)  # ... AND age = 36
```

Multiple keywords are combined with `AND`.

## Operator suffixes

Append `__operator` to a column name to apply an operator:

| Keyword                                 | SQL                     |
|-----------------------------------------|-------------------------|
| `column=value`                          | `column = value`        |
| `column__ne=value`                      | `column != value`       |
| `column__in=[a, b]`                     | `column IN (a, b)`      |
| `column__notin=[a, b]`                  | `column NOT IN (a, b)`  |
| `column__gt` / `__ge` / `__lt` / `__le` | `>` / `>=` / `<` / `<=` |
| `column__like` / `__ilike`              | `LIKE` / `ILIKE`        |
| `column__is=None`                       | `IS NULL`               |

```python
await repo.find_all(age__ge=18)             # WHERE age >= 18
await repo.find_all(status__ne="active")    # WHERE status != 'active'
await repo.find_all(id__in=[1, 2, 3])       # WHERE id IN (1, 2, 3)
await repo.find_all(id__notin=[1, 2, 3])    # WHERE id NOT IN (1, 2, 3)
await repo.find_all(name__like="K%")        # WHERE name LIKE 'K%'
await repo.find_all(deleted_at__is=None)    # WHERE deleted_at IS NULL
```

Exact column names take precedence, so a column whose own name contains `__` is
still addressable directly.

## Custom SQLAlchemy expressions

When the keyword syntax is not enough, pass raw SQLAlchemy boolean expressions
as positional arguments. They are added to the query's `WHERE` clause exactly as
SQLAlchemy's own `select().where(...)` would, so anything you can express there
works — `or_`, `and_`, negation, function calls, JSON path checks, and more:

```python
from sqlalchemy import func, or_

await repo.find_all(or_(User.status == "inactive", User.age >= 30))
await repo.find_all(func.jsonb_path_exists(User.data, "$.role"))
```

Positional expressions and keyword filters can be combined; everything is joined
with `AND`:

```python
await repo.find_all(or_(User.age < 18, User.age >= 65), status="active")
```

`find_all_paginated` accepts the same expressions, after the `params` argument:

```python
await repo.find_all_paginated(Params(page=1, size=50), User.age >= 30)
```

## Ordering

`find_all` and `find_all_paginated` accept an `order_by` keyword that takes raw
SQLAlchemy order expressions — either a single expression or a list:

```python
await repo.find_all(order_by=User.age.desc())
await repo.find_all(order_by=[User.status, User.age.desc()])
```

`find_all_paginated` always appends the primary key as a tie-breaker after any
`order_by` expressions you supply, so paging is stable across requests. When
`order_by` is omitted, pagination orders by primary key alone.

## Unknown filters raise

An unknown column or operator raises `InvalidFilterError` (a subclass of
`ValueError`) instead of being silently ignored, so a typo can never return
unfiltered data:

```python
from fast_repository import InvalidFilterError

try:
    await repo.find_all(stauts="active")  # typo
except InvalidFilterError as error:
    ...
```

## Finding by primary key

`find` looks an entity up by its primary key. Pass a single-column key
positionally:

```python
await repo.find(1)
```

Supply a composite key as keyword arguments naming each key column:

```python
await repo.find(user_id=1, group_id=2)
```

`find` returns the entity or `None`. Passing a composite key positionally, or
keys that do not match the entity's primary-key columns, raises `ValueError`.

## Locking rows for update

Pass `with_for_update` to `find` to acquire a row lock (`SELECT ... FOR UPDATE`),
typically inside a transaction before modifying the row. `True` emits a plain
`FOR UPDATE`:

```python
user = await repo.find(1, with_for_update=True)
```

A mapping forwards its options to SQLAlchemy's `Select.with_for_update`. The
keys are described by the `DbLockInfo` type (`nowait`, `read`, `skip_locked`,
`key_share`, `of`):

```python
from fast_repository import DbLockInfo

await repo.find(1, with_for_update={"nowait": True})
await repo.find(1, with_for_update={"skip_locked": True})
```

The default, `with_for_update=False`, reads without a lock. Locking is
dialect-specific; databases that do not support `FOR UPDATE` (such as SQLite)
ignore it.

## Pagination

`find_all_paginated` accepts the same filters and returns a fastapi-pagination
`Page`. Results are ordered by primary key by default; pass `order_by` to
supply your own ordering (the primary key is always appended as a tie-breaker —
see [Ordering](#ordering)):

```python
from fastapi_pagination import Params

page = await repo.find_all_paginated(Params(page=1, size=50), status="active")
page.items   # the rows on this page
page.total   # total matching rows
```

When `params` is omitted, they are resolved from the current FastAPI request
context.

## Counting and existence

`count` and `exists` take the same positional expressions and keyword filters
as `find_all` (ordering does not apply to them) and respect the soft-delete
filter; they also support `with_deleted=True`:

```python
await repo.count(status="active")     # number of matching rows
await repo.exists(email="a@b.com")    # True if any row matches
```
