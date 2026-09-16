from __future__ import annotations

from app.security import auth as auth_service


def test_register_then_login_succeeds(db_session):
    ok, error = auth_service.register_user(db_session, "Ada Lovelace", "ada@example.com", "correct-horse-battery")
    assert ok is True
    assert error is None

    result = auth_service.login_user(db_session, "ada@example.com", "correct-horse-battery")
    assert result.user is not None
    assert result.error is None


def test_login_wrong_password_fails(db_session):
    auth_service.register_user(db_session, "Ada Lovelace", "ada@example.com", "correct-horse-battery")

    result = auth_service.login_user(db_session, "ada@example.com", "wrong-password")
    assert result.user is None
    assert result.error == "Invalid email or password."


def test_register_duplicate_email_rejected(db_session):
    auth_service.register_user(db_session, "Ada", "ada@example.com", "correct-horse-battery")
    ok, error = auth_service.register_user(db_session, "Ada Two", "ada@example.com", "another-password")
    assert ok is False
    assert "already exists" in error


def test_register_weak_password_rejected(db_session):
    ok, error = auth_service.register_user(db_session, "Ada", "ada@example.com", "short")
    assert ok is False
    assert "12 characters" in error


def test_lockout_after_max_failed_attempts(db_session):
    auth_service.register_user(db_session, "Ada", "ada@example.com", "correct-horse-battery")

    for _ in range(auth_service.MAX_FAILED_ATTEMPTS):
        auth_service.login_user(db_session, "ada@example.com", "wrong-password")

    result = auth_service.login_user(db_session, "ada@example.com", "correct-horse-battery")
    assert result.user is None
    assert "Too many login attempts" in result.error


def test_email_is_case_and_whitespace_insensitive(db_session):
    auth_service.register_user(db_session, "Ada", "  Ada@Example.com  ", "correct-horse-battery")
    result = auth_service.login_user(db_session, "ada@example.com", "correct-horse-battery")
    assert result.user is not None


def test_session_round_trip(db_session):
    auth_service.register_user(db_session, "Ada", "ada@example.com", "correct-horse-battery")
    login_result = auth_service.login_user(db_session, "ada@example.com", "correct-horse-battery")

    session = auth_service.create_session(db_session, login_result.user.id)
    fetched_user = auth_service.get_user_for_token(db_session, session.token)
    assert fetched_user is not None
    assert fetched_user.id == login_result.user.id

    auth_service.delete_session(db_session, session.token)
    assert auth_service.get_user_for_token(db_session, session.token) is None


def test_legacy_sha256_hash_upgrades_on_successful_login(db_session):
    from cadence_db import User

    legacy_hash = auth_service._legacy_sha256("correct-horse-battery")
    user = User(name="Ada", email="ada@example.com", password_hash=legacy_hash)
    db_session.add(user)
    db_session.commit()

    result = auth_service.login_user(db_session, "ada@example.com", "correct-horse-battery")
    assert result.user is not None
    assert not auth_service._is_legacy_sha256(result.user.password_hash)
