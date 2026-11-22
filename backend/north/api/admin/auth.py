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


class EmailBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class TokenBody(BaseModel):
    token: str = Field(min_length=10, max_length=100)


class ResetBody(TokenBody):
    new: str = Field(min_length=1, max_length=1024)


class ForgotBody(BaseModel):
    login: str = Field(min_length=1, max_length=254)


class PreferencesBody(BaseModel):
    locale: str | None = None
    notify_jobs: bool | None = None


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


# ------------------------------------------------------------------- email (record 0007)

FORGOT_REPLY = {"ok": True, "detail": "if the account has a confirmed email address, a link "
                                      "was sent to it"}


@router.post("/forgot")
def forgot(body: ForgotBody, request: Request, db: Db) -> object:
    """Same answer whether or not the account exists (no enumeration)."""
    try:
        service.request_password_reset(db, body.login, ip=client_ip(request))
    except service.Throttled as e:
        return _throttled(e)
    return FORGOT_REPLY


@router.post("/reset")
def reset(body: ResetBody, request: Request, db: Db) -> object:
    try:
        service.reset_password(db, body.token, body.new, ip=client_ip(request))
    except service.AuthError:
        raise HTTPException(400, {"field": "token", "message": "invalid or expired link"}) \
            from None
    except (WeakPassword, ValueError) as e:
        raise HTTPException(400, {"field": "new", "message": str(e)}) from None
    return {"ok": True}


@router.post("/email/verify")
def verify_email(body: TokenBody, request: Request, db: Db) -> object:
    try:
        user = service.verify_email(db, body.token, ip=client_ip(request))
    except service.AuthError:
        raise HTTPException(400, "invalid or expired link") from None
    return {"ok": True, "email": user.email}


@router.post("/email")
def change_email(body: EmailBody, auth: Annotated[Auth, Depends(require())]) -> object:
    try:
        service.change_email(auth.db, auth.user, body.email, body.password, ip=auth.ip)
    except service.AuthError:
        raise HTTPException(400, {"field": "password", "message": "password is wrong"}) \
            from None
    except ValueError as e:
        raise HTTPException(400, {"field": "email", "message": str(e)}) from None
    return _state(auth.user, auth.session, auth.stage)


@router.post("/email/resend")
def resend_verification(auth: Annotated[Auth, Depends(require())]) -> object:
    try:
        sent = service.resend_verification(auth.db, auth.user, ip=auth.ip)
    except service.Throttled as e:
        return _throttled(e)
    return {"ok": sent}


@router.post("/email/test")
def test_email(auth: Annotated[Auth, Depends(require())]) -> object:
    try:
        to = service.send_test_email(auth.db, auth.user, ip=auth.ip)
    except service.Throttled as e:
        return _throttled(e)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return {"ok": True, "to": to}


@router.patch("/preferences")
def preferences(body: PreferencesBody, auth: Annotated[Auth, Depends(require())]) -> object:
    try:
        service.set_preferences(auth.db, auth.user, locale=body.locale,
                                notify_jobs=body.notify_jobs)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return _state(auth.user, auth.session, auth.stage)
