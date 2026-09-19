"""Clearing a JSON column must store SQL NULL, not the JSON value `null`.

By default SQLAlchemy persists an explicit Python None in a JSON column as the
JSON literal `null`. The application treats both as "empty", so nothing
misbehaves -- but `Analysis`'s own docstring promises NULL while an analysis is
queued/running, and a query such as `WHERE result IS NULL` (or
`pending_lock_data IS NOT NULL`, to find analyses awaiting a dancer pick)
silently gets the wrong rows. Found by querying a real Postgres after the
worker had cleared `pending_lock_data`.
"""

from cadence_db import Analysis, User
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


def test_setting_a_json_column_to_none_stores_sql_null(db_engine):
    db = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)()
    try:
        user = User(name="Ada", email="ada@example.com", password_hash="x")
        db.add(user)
        db.commit()
        analysis = Analysis(
            user_id=user.id, workspace_id="w", status="needs_dancer_pick", pending_lock_data={"tracks": []}
        )
        db.add(analysis)
        db.commit()

        assert db.execute(text("select count(*) from analyses where pending_lock_data is not null")).scalar() == 1

        analysis.pending_lock_data = None  # what extract_locked_pose_job does once a dancer is picked
        analysis.result = None
        db.commit()

        still_set = db.execute(
            text("select count(*) from analyses where pending_lock_data is not null or result is not null")
        ).scalar()
        assert still_set == 0, "an explicit None was stored as JSON 'null' instead of SQL NULL"
    finally:
        db.close()
