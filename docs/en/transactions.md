# Transactions

**English** | [한국어](../ko/transactions.md)

The write methods — `save`, `save_all`, `delete`, `delete_all` — commit by
default. Pass `autocommit=False` to keep the transaction open and commit it
yourself, which is how you group several operations into one unit of work.

> **Note:** The examples use the async repository. `SyncCRUDRepository` behaves
> the same without `await`.

## Commit (the default)

Each write flushes and commits immediately:

```python
await repo.save(user)          # INSERT/UPDATE, then COMMIT
await repo.delete(user)        # DELETE, then COMMIT
```

Reads (`find`, `find_all`, `find_all_paginated`) never commit.

## Flush only — `autocommit=False`

With `autocommit=False` the write is flushed but not committed: the SQL is sent
(so server-generated values like primary keys are populated) while the
transaction stays open for you to commit or roll back.

```python
user = await repo.save(User(name="Ada"), autocommit=False)
print(user.id)            # populated by the flush

await repo.session.commit()   # or .rollback()
```

## Grouping work into one transaction

Pass `autocommit=False` to every write and commit once at the end, so the whole
unit either lands together or not at all:

```python
await accounts.save(debit, autocommit=False)
await accounts.save(credit, autocommit=False)
await accounts.session.commit()   # both, or neither on error
```

In FastAPI this often lives in the dependency that yields the session — the
route handlers call the repository with `autocommit=False`, and the dependency
commits when the request finishes.

## Row locking

To lock rows for update within a transaction, see `with_for_update` in the
[filtering guide](filtering.md#locking-rows-for-update).
