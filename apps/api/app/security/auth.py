"""Account registration, password hashing, and login protection.

Ported from legacy/cadence-streamlit/modules/auth.py, same algorithm and
constants, adapted from raw sqlite3 to SQLAlchemy against the shared
User/LoginSecurity models so it works against Postgres in production.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import LoginSecurity, User, UserSession
from .input_validation import validate_registration_fields

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
PASSWORD_MINIMUM_LENGTH = 12
SESSION_DURATION = timedelta(days=7)

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    type=Type.ID,
)


@dataclass(frozen=True)
class LoginResult:
    user: User | None
    error: str | None = None


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_legacy_sha256(stored_hash: str) -> bool:
    return len(stored_hash) == 64 and all(c in "0123456789abcdef" for c in stored_hash.lower())


def hash_password(password: str) -> str:
    """Hash a new password with Argon2id."""

    return _password_hasher.hash(password)


def _verify_password(stored_hash: str, password: str) -> tuple[bool, bool]:
    """Return (valid, should_upgrade_hash) for a stored password hash."""

    if _is_legacy_sha256(stored_hash):
        return hmac.compare_digest(stored_hash, _legacy_sha256(password)), True

    try:
        _password_hasher.verify(stored_hash, password)
        return True, _password_hasher.check_needs_rehash(stored_hash)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False, False


def _get_lock_message(db: Session, email: str, now: datetime) -> str | None:
    row = db.get(LoginSecurity, email)
    if not row or not row.locked_until:
        return None

    locked_until = row.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)

    if locked_until <= now:
        row.failed_attempts = 0
        row.locked_until = None
        db.commit()
        return None

    remaining_minutes = max(1, int((locked_until - now).total_seconds() / 60) + 1)
    return f"Too many login attempts. Try again in about {remaining_minutes} minutes."


def _record_failed_login(db: Session, email: str, now: datetime) -> None:
    row = db.get(LoginSecurity, email)
    attempts = (row.failed_attempts if row else 0) + 1
    locked_until = now + LOCKOUT_DURATION if attempts >= MAX_FAILED_ATTEMPTS else None

    if row:
        row.failed_attempts = attempts
        row.locked_until = locked_until
        row.updated_at = now
    else:
        db.add(
            LoginSecurity(
                email=email,
                failed_attempts=attempts,
                locked_until=locked_until,
                updated_at=now,
            )
        )
    db.commit()


def _clear_login_failures(db: Session, email: str) -> None:
    row = db.get(LoginSecurity, email)
    if row:
        db.delete(row)
        db.commit()


def register_user(db: Session, name: str, email: str, password: str) -> tuple[bool, str | None]:
    """Register a user with an Argon2id password hash.

    Returns (ok, error). Caller is expected to have already run
    validate_registration_fields for a nicer field-level error, but this
    re-checks so the function is safe to call directly (e.g. from tests).
    """

    validation = validate_registration_fields(
        name, email, password, password, password_minimum=PASSWORD_MINIMUM_LENGTH
    )
    if not validation.ok:
        return False, validation.error

    user = User(
        name=name.strip(),
        email=_normalise_email(email),
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False, "An account with that email already exists."
    return True, None


def login_user(db: Session, email: str, password: str) -> LoginResult:
    """Authenticate a user and protect accounts from repeated guessing."""

    normalised_email = _normalise_email(email)
    now = datetime.now(timezone.utc)

    lock_message = _get_lock_message(db, normalised_email, now)
    if lock_message:
        return LoginResult(user=None, error=lock_message)

    user = db.query(User).filter(User.email == normalised_email).first()
    if not user:
        _record_failed_login(db, normalised_email, now)
        return LoginResult(user=None, error="Invalid email or password.")

    valid, should_upgrade_hash = _verify_password(user.password_hash, password)
    if not valid:
        _record_failed_login(db, normalised_email, now)
        return LoginResult(user=None, error="Invalid email or password.")

    if should_upgrade_hash:
        user.password_hash = hash_password(password)

    _clear_login_failures(db, normalised_email)
    db.commit()
    return LoginResult(user=user)


def create_session(db: Session, user_id: str) -> UserSession:
    now = datetime.now(timezone.utc)
    session = UserSession(
        token=secrets.token_urlsafe(48),
        user_id=user_id,
        created_at=now,
        expires_at=now + SESSION_DURATION,
    )
    db.add(session)
    db.commit()
    return session


def get_user_for_token(db: Session, token: str) -> User | None:
    if not token:
        return None
    session = db.get(UserSession, token)
    if not session:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session.user


def delete_session(db: Session, token: str) -> None:
    session = db.get(UserSession, token)
    if session:
        db.delete(session)
        db.commit()
