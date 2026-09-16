"""Persisted rows. Kept dialect-agnostic (String/DateTime/JSON, no
Postgres-only types) so the same models work against SQLite in tests
and Postgres in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    joined_on: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LoginSecurity(Base):
    """Failed-login tracking, keyed by normalised email (mirrors the
    legacy Streamlit app's lockout behaviour)."""

    __tablename__ = "login_security"

    email: Mapped[str] = mapped_column(String(254), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class UserSession(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped["User"] = relationship()


class Analysis(Base):
    """One dance-analysis run.

    `result` holds the AnalysisResult payload (packages/schema) once a
    worker job has produced a final (complete/rejected) outcome; NULL
    while queued/running/needs_dancer_pick.

    `pending_lock_data` holds the raw detections a detect_tracks_job
    produced when it couldn't confidently auto-lock a single dancer
    (multiple comparably-sized tracks -- see
    apps/worker/worker/pipeline/quality.py's is_lock_ambiguous). A
    future POST /analyses/{id}/lock endpoint would read this to finish
    the job without re-running YOLO; that endpoint doesn't exist yet,
    so today `needs_dancer_pick` is a real, correctly-detected status
    with no way for a user to act on it. See STATUS.md.
    """

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    workspace_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pending_lock_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
