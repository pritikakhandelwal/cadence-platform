"""Alembic environment for the shared Cadence schema.

The database URL comes from, in order: an explicit `sqlalchemy.url` on the
Alembic config (what tests and `cadence_db.migrate.alembic_config()` set), the
`DATABASE_URL` environment variable (what the API and worker read), then the
same SQLite default as `cadence_db.db`.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from cadence_db import models  # noqa: F401  (registers every model on Base.metadata)
from cadence_db.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    return (
        config.get_main_option("sqlalchemy.url")
        or os.getenv("DATABASE_URL")
        or "sqlite:///./cadence.db"
    )


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite can't ALTER most things in place; batch mode rebuilds the table instead.
            render_as_batch=url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
