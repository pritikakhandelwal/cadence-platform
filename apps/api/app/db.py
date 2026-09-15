"""Database engine/session setup.

Production uses Postgres (set DATABASE_URL, e.g.
postgresql+psycopg2://user:pass@host:5432/cadence). Tests and local
scratch runs default to a SQLite file so nobody needs Postgres running
just to run `pytest`. Models avoid Postgres-only column types so both
dialects work identically.
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables that don't exist yet. Fine for now; move to real
    migrations (Alembic) before Phase 7 if the schema needs to evolve
    without dropping data."""

    from . import models  # noqa: F401  (registers models on Base)

    Base.metadata.create_all(bind=engine)
