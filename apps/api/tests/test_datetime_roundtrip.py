"""Times written to the database must come back meaning the same instant.

The auth code stores timezone-aware UTC datetimes (session expiry, lockout
end) and, on the way back, treats any naive value as UTC. That's only right
if the database *stored* UTC. SQLite keeps whatever it's given; Postgres
converts an aware value using the *server session's* time zone before
storing it in a column without a time zone -- so on a server that isn't set
to UTC, sessions would silently expire hours early or late and lockouts
would end at the wrong time.

These tests pass on SQLite regardless. Their teeth are on Postgres: run the
suite with CADENCE_TEST_DATABASE_URL pointing at a database whose time zone
is not UTC (`ALTER DATABASE ... SET timezone = 'Asia/Kolkata'`).
"""

from datetime import datetime, timedelta, timezone

from cadence_db import LoginSecurity, UserSession
from sqlalchemy.orm import sessionmaker

from app.security import auth

TOLERANCE = timedelta(seconds=60)
PASSWORD = "correct-horse-battery"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _fresh_session(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)()


def test_session_expiry_is_stored_and_read_back_as_the_same_instant(db_engine):
    db = _fresh_session(db_engine)
    try:
        ok, error = auth.register_user(db, "Ada", "ada@example.com", PASSWORD)
        assert ok, error
        user = auth.login_user(db, "ada@example.com", PASSWORD).user
        token = auth.create_session(db, user.id).token
    finally:
        db.close()

    reader = _fresh_session(db_engine)  # a new session, so nothing is served from the identity map
    try:
        stored = reader.get(UserSession, token).expires_at
    finally:
        reader.close()

    expected = datetime.now(timezone.utc) + auth.SESSION_DURATION
    assert abs(_as_utc(stored) - expected) < TOLERANCE, (
        f"session expiry drifted by {_as_utc(stored) - expected} -- the database isn't round-tripping UTC"
    )


def test_a_fresh_session_is_still_valid_after_a_round_trip(db_engine):
    db = _fresh_session(db_engine)
    try:
        auth.register_user(db, "Ada", "ada@example.com", PASSWORD)
        user = auth.login_user(db, "ada@example.com", PASSWORD).user
        token = auth.create_session(db, user.id).token
    finally:
        db.close()

    reader = _fresh_session(db_engine)
    try:
        assert auth.get_user_for_token(reader, token) is not None
    finally:
        reader.close()


def test_lockout_end_is_stored_and_read_back_as_the_same_instant(db_engine):
    db = _fresh_session(db_engine)
    try:
        auth.register_user(db, "Ada", "ada@example.com", PASSWORD)
        for _ in range(auth.MAX_FAILED_ATTEMPTS):
            auth.login_user(db, "ada@example.com", "definitely-not-the-password")
    finally:
        db.close()

    reader = _fresh_session(db_engine)
    try:
        stored = reader.get(LoginSecurity, "ada@example.com").locked_until
    finally:
        reader.close()

    assert stored is not None, "five failed logins should have locked the account"
    expected = datetime.now(timezone.utc) + auth.LOCKOUT_DURATION
    assert abs(_as_utc(stored) - expected) < TOLERANCE, (
        f"lockout end drifted by {_as_utc(stored) - expected}"
    )
