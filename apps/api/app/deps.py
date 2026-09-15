from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security.auth import get_user_for_token

SESSION_COOKIE_NAME = "cadence_session"


def get_current_user(
    cadence_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    user = get_user_for_token(db, cadence_session or "")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user
