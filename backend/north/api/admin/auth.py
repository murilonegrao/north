"""Login (password, then TOTP), logout, the current session, password and TOTP changes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from north.api.admin.deps import (
    Auth,
    Db,
    clear_cookie,
    client_ip,
    optional_auth,
    require,
    set_cookie,
    user_agent,
    user_view,
)
from north.auth import service
from north.auth.passwords import WeakPassword
from north.repository.models import AdminSession, User

router = APIRouter(prefix="/auth")


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class CodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class PasswordBody(BaseModel):
    current: str = Field(min_length=1, max_length=1024)
    new: str = Field(min_length=1, max_length=1024)


def _state(user: User, sess: AdminSession, stage: str) -> dict[str, object]:
    return {"user": user_view(user), "stage": stage, "csrf": sess.csrf_token}


def _throttled(e: service.Throttled) -> JSONResponse:
    return JSONResponse({"detail": "too many attempts, try again later"}, status_code=429,
                        headers={"Retry-After": str(e.retry_after)})


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response, db: Db) -> object:
    try:
        issued = service.login_password(db, body.username, body.password,
                                        ip=client_ip(request), user_agent=user_agent(request))
    except service.Throttled as e:
        return _throttled(e)
    except service.AuthError:
        raise HTTPException(401, "invalid username or password") from None
    user = issued.session.user
    set_cookie(response, issued.token)
    return _state(user, issued.session, service.stage(issued.session, user))


@router.post("/totp")
def login_totp(body: CodeBody, request: Request, response: Response,
               auth: Annotated[Auth, Depends(require(stages=("totp",)))]) -> object:
    try:
        issued = service.login_totp(auth.db, auth.session, auth.user, body.code, ip=auth.ip,
                                    user_agent=user_agent(request))
    except service.Throttled as e:
        return _throttled(e)
    except service.AuthError:
        raise HTTPException(401, "invalid code") from None
    set_cookie(response, issued.token)
    return _state(auth.user, issued.session, service.stage(issued.session, auth.user))


@router.get("/me")
def me(auth: Annotated[Auth | None, Depends(optional_auth)]) -> object:
    if auth is None:
        raise HTTPException(401, "login required")
    return _state(auth.user, auth.session, auth.stage)


ANY_STAGE = ("totp", "change_password", "enroll_totp", "ok")


@router.post("/logout")
def logout(response: Response,
           auth: Annotated[Auth, Depends(require(stages=ANY_STAGE))]) -> object:
    service.revoke(auth.db, auth.session)
    auth.db.commit()
    clear_cookie(response)
    return {"ok": True}


@router.post("/password")
def change_password(body: PasswordBody, auth: Annotated[Auth, Depends(require(
        stages=("change_password", "enroll_totp", "ok")))]) -> object:
    try:
        service.change_password(auth.db, auth.session, auth.user, body.current, body.new,
                                ip=auth.ip)
    except service.AuthError:
        raise HTTPException(400, {"field": "current", "message": "current password is wrong"}) \
            from None
    except (WeakPassword, ValueError) as e:
        raise HTTPException(400, {"field": "new", "message": str(e)}) from None
    return _state(auth.user, auth.session, service.stage(auth.session, auth.user))


@router.post("/totp/setup")
def totp_setup(auth: Annotated[Auth, Depends(require(stages=("enroll_totp", "ok")))]) -> object:
    return service.totp_setup(auth.db, auth.user)


@router.post("/totp/confirm")
def totp_confirm(body: CodeBody,
                 auth: Annotated[Auth, Depends(require(stages=("enroll_totp", "ok")))]) -> object:
    try:
        service.totp_confirm(auth.db, auth.session, auth.user, body.code, ip=auth.ip)
    except service.Throttled as e:
        return _throttled(e)
    except service.AuthError:
        raise HTTPException(400, "invalid code") from None
    return _state(auth.user, auth.session, service.stage(auth.session, auth.user))
