"""Programmatic access to the Alembic migrations, for tests and scripts.

Day to day, use the CLI from packages/db (`alembic upgrade head`), which reads
DATABASE_URL like the apps do. This exists so a test can point Alembic at a
specific database without touching the environment.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config(database_url: str | None = None) -> Config:
    """An Alembic Config pointing at the migrations shipped inside this
    package. If `database_url` is given it wins over DATABASE_URL."""

    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    if database_url:
        # ConfigParser treats '%' as interpolation, and URLs can contain %-escapes.
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config
