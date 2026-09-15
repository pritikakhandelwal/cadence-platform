"""Account registration, password hashing, and login protection."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from modules.database import get_connection


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
PASSWORD_MINIMUM_LENGTH = 12

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    type=Type.ID,
)


@dataclass(frozen=True)
class LoginResult:
    user: tuple | None
    error: str | None = None


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_legacy_sha256(stored_hash: str) -> bool:
    return len(stored_hash) == 64 and all(character in "0123456789abcdef" for character in stored_hash.lower())


def hash_password(password: str) -> str:
    """Hash a new password with Argon2id."""

    return _password_hasher.hash(password)


def _verify_password(stored_hash: str, password: str) -> tuple[bool, bool]:
    """Return ``(valid, should_upgrade_hash)`` for a stored password hash."""

    if _is_legacy_sha256(stored_hash):
        return hmac.compare_digest(stored_hash, _legacy_sha256(password)), True

    try:
        _password_hasher.verify(stored_hash, password)
        return True, _password_hasher.check_needs_rehash(stored_hash)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False, False


def _get_lock_message(conn: sqlite3.Connection, email: str, now: datetime) -> str | None:
    row = conn.execute(
        "SELECT locked_until FROM login_security WHERE email = ?",
        (email,),
    ).fetchone()
    if not row or not row[0]:
        return None

    locked_until = datetime.fromisoformat(row[0])
    if locked_until <= now:
        conn.execute(
            "UPDATE login_security SET failed_attempts = 0, locked_until = NULL WHERE email = ?",
            (email,),
        )
        conn.commit()
        return None

    remaining_minutes = max(1, int((locked_until - now).total_seconds() / 60) + 1)
    return f"Too many login attempts. Try again in about {remaining_minutes} minutes."


def _record_failed_login(conn: sqlite3.Connection, email: str, now: datetime) -> None:
    row = conn.execute(
        "SELECT failed_attempts FROM login_security WHERE email = ?",
        (email,),
    ).fetchone()
    attempts = (row[0] if row else 0) + 1
    locked_until = now + LOCKOUT_DURATION if attempts >= MAX_FAILED_ATTEMPTS else None

    conn.execute(
        """
        INSERT INTO login_security(email, failed_attempts, locked_until, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            failed_attempts = excluded.failed_attempts,
            locked_until = excluded.locked_until,
            updated_at = excluded.updated_at
        """,
        (email, attempts, locked_until.isoformat() if locked_until else None, now.isoformat()),
    )
    conn.commit()


def _clear_login_failures(conn: sqlite3.Connection, email: str) -> None:
    conn.execute("DELETE FROM login_security WHERE email = ?", (email,))


def register_user(name: str, email: str, password: str) -> bool:
    """Register a user with an Argon2id password hash."""

    from modules.input_validation import validate_registration_fields

    validation = validate_registration_fields(
        name,
        email,
        password,
        password,
        password_minimum=PASSWORD_MINIMUM_LENGTH
    )
    if not validation.ok:
        return False

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name.strip(), _normalise_email(email), hash_password(password)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(email: str, password: str) -> LoginResult:
    """Authenticate a user and protect accounts from repeated guessing."""

    normalised_email = _normalise_email(email)
    now = datetime.now(timezone.utc)
    conn = get_connection()

    try:
        lock_message = _get_lock_message(conn, normalised_email, now)
        if lock_message:
            return LoginResult(user=None, error=lock_message)

        row = conn.execute(
            """
            SELECT id, name, email, joined_on, password
            FROM users
            WHERE lower(email) = ?
            """,
            (normalised_email,),
        ).fetchone()
        if not row:
            _record_failed_login(conn, normalised_email, now)
            return LoginResult(user=None, error="Invalid email or password.")

        user = row[:4]
        valid, should_upgrade_hash = _verify_password(row[4], password)
        if not valid:
            _record_failed_login(conn, normalised_email, now)
            return LoginResult(user=None, error="Invalid email or password.")

        if should_upgrade_hash:
            conn.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (hash_password(password), user[0]),
            )
        _clear_login_failures(conn, normalised_email)
        conn.commit()
        return LoginResult(user=user)
    finally:
        conn.close()
