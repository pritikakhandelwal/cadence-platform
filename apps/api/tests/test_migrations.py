"""The Alembic migrations and the SQLAlchemy models must describe the same schema.

The app still uses `Base.metadata.create_all` for dev and tests, and Alembic for
anything that has to evolve without dropping data, so there are two sources of
truth for the schema. These tests are what keeps them from drifting: change a
model without writing a migration and `test_migrations_produce_exactly_the_models_schema`
fails.

Runs on SQLite by default, and on Postgres when CADENCE_TEST_DATABASE_URL is set
(the database is wiped first -- use a throwaway one).
"""

import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from cadence_db import Base
from cadence_db.migrate import alembic_config
from sqlalchemy import create_engine, inspect, text


@pytest.fixture()
def empty_database(tmp_path):
    """(url, engine) for a database with nothing in it."""

    url = os.getenv("CADENCE_TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'migrations.db'}"
    engine = create_engine(url)

    def wipe():
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    wipe()
    yield url, engine
    wipe()
    engine.dispose()


def _application_tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_there_is_exactly_one_migration_head():
    # two heads means two people wrote a migration off the same parent
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"migration history has branched: {heads}"


def test_migrations_produce_exactly_the_models_schema(empty_database):
    url, engine = empty_database

    command.upgrade(alembic_config(url), "head")

    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)
    assert differences == [], (
        "the models and the migrations disagree -- did you change a model without "
        f"`alembic revision --autogenerate`?\n{differences}"
    )
    assert _application_tables(engine) == set(Base.metadata.tables)


def test_the_migration_can_be_undone_completely(empty_database):
    url, engine = empty_database
    config = alembic_config(url)

    command.upgrade(config, "head")
    assert _application_tables(engine)
    command.downgrade(config, "base")

    assert _application_tables(engine) == set()


def test_upgrading_twice_is_a_no_op(empty_database):
    url, engine = empty_database
    config = alembic_config(url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")  # already at head -- must not try to recreate tables

    assert _application_tables(engine) == set(Base.metadata.tables)
