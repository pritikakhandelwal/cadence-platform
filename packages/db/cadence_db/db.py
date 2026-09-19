"""Database engine/session setup, shared by apps/api and apps/worker.

Both processes talk to the same DATABASE_URL (Postgres in prod, SQLite
by default/in tests) so a worker job can write an analysis result and
the API can read it back without a callback API between them --
matching the architecture diagram in ROADMAP.md, where both the API
and the workers connect to PostgreSQL directly.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cadence.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session, closes it after the request."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables that don't exist yet -- for dev and tests.

    `create_all` never alters an existing table, so it can't carry a database
    through a schema change. For any database whose data must survive, use the
    Alembic migrations instead (`alembic upgrade head` from packages/db).
    Don't mix the two on one database: one built by `create_all` has no
    `alembic_version` table, so a later `upgrade head` would try to create
    tables that already exist. apps/api/tests/test_migrations.py keeps the two
    schema sources identical."""

    from . import models  # noqa: F401  (registers models on Base)

    Base.metadata.create_all(bind=engine)
