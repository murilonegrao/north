"""Accounts (admin only). Nobody edits their own access here: that is the account page."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from north.api.admin.deps import Admin, user_view
from north.auth import service
from north.auth.passwords import WeakPassword
from north.repository.models import User

router = APIRouter(prefix="/users")


class NewUser(BaseModel):
    username: str = Field(max_length=64)
    role: str
    password: str = Field(max_length=1024)
    email: str | None = Field(default=None, max_length=254)


class UserPatch(BaseModel):
    role: str | None = None
    disabled: bool | None = None
    reset_password: str | None = Field(default=None, max_length=1024)
    reset_totp: bool = False
    email: str | None = Field(default=None, max_length=254)


@router.get("")
def list_users(auth: Admin) -> object:
    return [user_view(u) for u in auth.db.scalars(select(User).order_by(User.username))]


@router.post("")
def create_user(body: NewUser, auth: Admin) -> object:
    try:
        user = service.create_user(auth.db, body.username, body.role, body.password,
                                   actor=auth.user, ip=auth.ip, email=body.email or None)
    except (WeakPassword, ValueError) as e:
        raise HTTPException(400, str(e)) from None
    return JSONResponse(jsonable_encoder(user_view(user)), status_code=201)


@router.patch("/{user_id}")
def patch_user(user_id: int, body: UserPatch, auth: Admin) -> object:
    user = auth.db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "no such user")
    try:
        service.update_user(auth.db, user, actor=auth.user, ip=auth.ip, role=body.role,
                            disabled=body.disabled, reset_password=body.reset_password,
                            reset_totp=body.reset_totp, email=body.email or None)
    except service.Forbidden as e:
        raise HTTPException(403, str(e)) from None
    except (WeakPassword, ValueError) as e:
        raise HTTPException(400, str(e)) from None
    return user_view(user)
