# Examples

Runnable examples for `fast-repository`. Each script creates its own throwaway
SQLite database, so nothing external is needed.

## Setup

Install the example dependencies (FastAPI, Uvicorn, aiosqlite):

```bash
uv sync --group examples
```

## Scripts

Run each from the project root:

```bash
uv run python examples/01_basic_crud.py    # create, read, update, delete
uv run python examples/02_filtering.py     # filters, operators, ordering, pagination, count/exists
uv run python examples/03_transactions.py  # the autocommit flag (commit vs flush)
uv run python examples/04_soft_delete.py   # soft delete, with_deleted, hard delete
```

## FastAPI app

A minimal app showing the repository injected through `Depends`:

```bash
uv run uvicorn app:app --app-dir examples --reload
```

Then open http://127.0.0.1:8000/docs to try the endpoints. It writes to a local
`examples.db` file (safe to delete).

## Shared code

`models.py` holds the entities (`User`, `Article`), the repository classes, and
the in-memory database helper that every script imports.
