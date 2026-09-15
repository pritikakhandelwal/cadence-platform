from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import SESSION_COOKIE_NAME, get_current_user
from ..models import User
from ..rate_limit import login_rate_limit, register_rate_limit
from ..security import auth as auth_service
from ..security.input_validation import validate_registration_fields

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str

    model_config = {"from_attributes": True}


@router.post("/register", status_code=201, dependencies=[Depends(register_rate_limit)])
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    validation = validate_registration_fields(
        body.name, body.email, body.password, body.confirm,
        password_minimum=auth_service.PASSWORD_MINIMUM_LENGTH,
    )
    if not validation.ok:
        raise HTTPException(status_code=400, detail=validation.error)

    ok, error = auth_service.register_user(db, body.name, body.email, body.password)
    if not ok:
        raise HTTPException(status_code=400, detail=error)
    return {"registered": True}


@router.post("/login", dependencies=[Depends(login_rate_limit)])
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    result = auth_service.login_user(db, body.email, body.password)
    if not result.user:
        raise HTTPException(status_code=401, detail=result.error)

    session = auth_service.create_session(db, result.user.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=int(auth_service.SESSION_DURATION.total_seconds()),
    )
    return UserOut.model_validate(result.user)


@router.post("/logout")
def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    cadence_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if cadence_session:
        auth_service.delete_session(db, cadence_session)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"loggedOut": True}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
