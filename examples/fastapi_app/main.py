"""Assemble the FastAPI app: lifespan, the users router, and pagination.

Run it::

    uv run uvicorn fastapi_app.main:app --app-dir examples --reload

Then open http://127.0.0.1:8000/docs to try the endpoints. It writes to a local
``examples.db`` file (safe to delete).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi_pagination import add_pagination

from .database import lifespan
from .routers import router

app = FastAPI(lifespan=lifespan)
app.include_router(router)
add_pagination(app)
