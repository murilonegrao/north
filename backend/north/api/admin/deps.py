"""Session, role and CSRF checks for the admin API."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from north.auth import service
from north.repository.db import session_scope
from north.repository.models import AdminSession, User
from north.settings import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "X-CSRF-Token"

Db = Annotated[Session, Depends(session_scope)]


def cookie_name() -> str:
    # __Host-: the browser only accepts it Secure, for this host, with Path=/ (no subdomain
    # can set or read it).
    return "__Host-north_admin" if get_settings().cookie_secure else "north_admin"


def client_ip(request: Request) -> str | None:
    header = get_settings().client_ip_header
    if header:
        value = request.headers.get(header, "").split(",")[0].strip()
        if value:
            return value[:64]
    return request.client.host if request.client else None


def user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def set_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(cookie_name(), token, max_age=s.session_max_hours * 3600, path="/",
                        secure=s.cookie_secure, httponly=True, samesite="strict")


def clear_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(cookie_name(), path="/", secure=s.cookie_secure, httponly=True,
                           samesite="strict")


@dataclass
class Auth:
    db: Session
    session: AdminSession
    user: User
    stage: str
    ip: str | None


def optional_auth(request: Request, db: Db) -> Auth | None:
    found = service.lookup(db, request.cookies.get(cookie_name()))
    if found is None:
        return None
    sess, user = found
    return Auth(db, sess, user, service.stage(sess, user), client_ip(request))


def require(min_role: str = "viewer",
            stages: tuple[str, ...] = ("ok",)) -> Callable[..., Auth]:
    """Dependency: a live session in one of `stages`, with at least `min_role`, and the CSRF
    header on state-changing requests."""
    def dependency(request: Request,
                   auth: Annotated[Auth | None, Depends(optional_auth)]) -> Auth:
        if auth is None:
            raise HTTPException(401, "login required")
        if request.method not in SAFE_METHODS:
            sent = request.headers.get(CSRF_HEADER, "")
            if not hmac.compare_digest(sent.encode(), auth.session.csrf_token.encode()):
                raise HTTPException(403, "missing or invalid CSRF token")
        if auth.stage not in stages:
            raise HTTPException(403, {"stage": auth.stage})
        if service.RANK[auth.user.role] < service.RANK[min_role]:
            raise HTTPException(403, "your role does not allow this")
        return auth
    return dependency


Viewer = Annotated[Auth, Depends(require("viewer"))]
Curator = Annotated[Auth, Depends(require("curator"))]
Admin = Annotated[Auth, Depends(require("admin"))]


def user_view(user: User) -> dict[str, object]:
    return {"id": user.id, "username": user.username, "role": user.role,
            "has_totp": user.totp_secret is not None, "disabled": user.disabled,
            "must_change_password": user.must_change_password,
            "last_login_at": user.last_login_at, "created_at": user.created_at}
