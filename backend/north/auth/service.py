"""Accounts, login, sessions and throttling. Pure database logic, no HTTP.

Sessions are server-side rows; the browser holds only a random token whose sha256 is stored,
so a copy of the table opens nothing. Login is two steps when the account has TOTP: the
password gives a short "pending" session that can only submit a code, and a valid code
replaces it with a new full session (a new token, so a pending token is never promoted).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import secrets
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from north.auth import audit, totp
from north.auth.passwords import check_policy, hash_password, verify_password
from north.repository.models import AdminSession, LoginAttempt, User
from north.settings import Settings, get_settings

ROLES = ("admin", "curator", "viewer")
RANK = {"viewer": 0, "curator": 1, "admin": 2}
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")

# Throttling windows: failures per account and per address in the last 15 minutes.
WINDOW = dt.timedelta(minutes=15)
MAX_FAILURES_PER_USER = 5
MAX_FAILURES_PER_IP = 20
PENDING_TTL = dt.timedelta(minutes=5)
TOUCH_EVERY = dt.timedelta(seconds=60)


class AuthError(Exception):
    """Generic on purpose: the message never says whether the account exists."""


class Throttled(AuthError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("too many attempts")
        self.retry_after = retry_after


class Forbidden(Exception):
    pass


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def check_username(username: str) -> str:
    u = normalize_username(username)
    if not USERNAME_RE.match(u):
        raise ValueError("3 to 64 characters: letters, digits, dot, dash, underscore")
    return u


# ----------------------------------------------------------------------------- sessions


@dataclass
class IssuedSession:
    token: str  # goes to the cookie, never stored
    session: AdminSession


def stage(sess: AdminSession, user: User, settings: Settings | None = None) -> str:
    """What the session may do: totp (code pending), change_password, enroll_totp, or ok."""
    settings = settings or get_settings()
    if not sess.mfa_ok:
        return "totp"
    if user.must_change_password:
        return "change_password"
    if settings.admin_require_totp and not user.totp_secret:
        return "enroll_totp"
    return "ok"


def _issue(db: Session, user: User, *, mfa_ok: bool, ip: str | None,
           user_agent: str | None, settings: Settings) -> IssuedSession:
    token = secrets.token_urlsafe(32)
    t = now()
    ttl = dt.timedelta(hours=settings.session_max_hours) if mfa_ok else PENDING_TTL
    sess = AdminSession(token_hash=token_hash(token), csrf_token=secrets.token_urlsafe(32),
                        user_id=user.id, mfa_ok=mfa_ok, created_at=t, last_seen_at=t,
                        expires_at=t + ttl, ip=ip, user_agent=(user_agent or "")[:200] or None)
    db.add(sess)
    db.flush()
    return IssuedSession(token, sess)


def lookup(db: Session, token: str | None, settings: Settings | None = None
           ) -> tuple[AdminSession, User] | None:
    """The live session for a cookie token, touched at most once a minute; None otherwise."""
    if not token or len(token) > 100:
        return None
    settings = settings or get_settings()
    sess = db.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash(token)))
    if sess is None or sess.revoked_at is not None:
        return None
    t = now()
    idle = dt.timedelta(minutes=settings.session_idle_minutes)
    if sess.expires_at <= t or sess.last_seen_at + idle <= t:
        return None
    user = db.get(User, sess.user_id)
    if user is None or user.disabled:
        return None
    if t - sess.last_seen_at >= TOUCH_EVERY:
        sess.last_seen_at = t
        db.commit()
    return sess, user


def revoke(db: Session, sess: AdminSession) -> None:
    sess.revoked_at = now()


def revoke_all(db: Session, user_id: int, *, except_id: int | None = None) -> None:
    stmt = (update(AdminSession)
            .where(AdminSession.user_id == user_id, AdminSession.revoked_at.is_(None))
            .values(revoked_at=now()))
    if except_id is not None:
        stmt = stmt.where(AdminSession.id != except_id)
    db.execute(stmt)


# ------------------------------------------------------------------------------- login


def _failures(db: Session, column, value: str, since: dt.datetime) -> int:
    return db.scalar(select(func.count()).select_from(LoginAttempt).where(
        column == value, LoginAttempt.ok.is_(False), LoginAttempt.at > since)) or 0


def check_throttle(db: Session, username: str, ip: str | None) -> None:
    since = now() - WINDOW
    over_user = _failures(db, LoginAttempt.username, username, since) >= MAX_FAILURES_PER_USER
    over_ip = ip is not None and _failures(db, LoginAttempt.ip, ip, since) >= MAX_FAILURES_PER_IP
    if over_user or over_ip:
        raise Throttled(retry_after=int(WINDOW.total_seconds()))


def _attempt(db: Session, username: str, ip: str | None, stage_: str, ok: bool) -> None:
    db.add(LoginAttempt(username=username[:64], ip=ip, stage=stage_, ok=ok))


def login_password(db: Session, username: str, password: str, *, ip: str | None,
                   user_agent: str | None, settings: Settings | None = None) -> IssuedSession:
    settings = settings or get_settings()
    name = normalize_username(username)[:64]
    check_throttle(db, name, ip)
    user = db.scalar(select(User).where(User.username == name))
    ok, rehash = verify_password(user.password_hash if user else None, password)
    if not ok or user is None or user.disabled:
        _attempt(db, name, ip, "password", False)
        audit.record(db, "login_failed", actor=name, ip=ip, stage="password")
        db.commit()
        raise AuthError("invalid credentials")
    _attempt(db, name, ip, "password", True)
    if rehash:
        user.password_hash = hash_password(password)
    issued = _issue(db, user, mfa_ok=not user.totp_secret, ip=ip, user_agent=user_agent,
                    settings=settings)
    if issued.session.mfa_ok:
        user.last_login_at = now()
        audit.record(db, "login", actor=user, ip=ip)
    db.commit()
    return issued


def login_totp(db: Session, sess: AdminSession, user: User, code: str, *, ip: str | None,
               user_agent: str | None, settings: Settings | None = None) -> IssuedSession:
    """Second step: a valid code replaces the pending session with a new full one."""
    settings = settings or get_settings()
    if sess.mfa_ok or not user.totp_secret:
        raise AuthError("no code expected")
    check_throttle(db, user.username, ip)
    step = totp.verify(user.totp_secret, code, last_step=user.totp_last_step)
    if step is None:
        _attempt(db, user.username, ip, "totp", False)
        audit.record(db, "login_failed", actor=user, ip=ip, stage="totp")
        db.commit()
        raise AuthError("invalid code")
    _attempt(db, user.username, ip, "totp", True)
    user.totp_last_step = step
    user.last_login_at = now()
    revoke(db, sess)
    issued = _issue(db, user, mfa_ok=True, ip=ip, user_agent=user_agent, settings=settings)
    audit.record(db, "login", actor=user, ip=ip)
    db.commit()
    return issued


def change_password(db: Session, sess: AdminSession, user: User, current: str, new: str, *,
                    ip: str | None) -> None:
    ok, _ = verify_password(user.password_hash, current)
    if not ok:
        _attempt(db, user.username, ip, "password_change", False)
        db.commit()
        raise AuthError("current password is wrong")
    if current == new:
        raise ValueError("the new password must differ from the current one")
    check_policy(new, username=user.username)
    user.password_hash = hash_password(new)
    user.must_change_password = False
    user.password_changed_at = now()
    revoke_all(db, user.id, except_id=sess.id)
    audit.record(db, "password_changed", actor=user, ip=ip)
    db.commit()


def totp_setup(db: Session, user: User, settings: Settings | None = None) -> dict[str, str]:
    """A new pending secret; it replaces the active one only after a code confirms it."""
    settings = settings or get_settings()
    secret = totp.new_secret()
    user.totp_pending_secret = secret
    db.commit()
    uri = totp.provisioning_uri(secret, user.username, settings.totp_issuer)
    return {"secret": secret, "uri": uri, "qr": totp.qr_svg_data_uri(uri)}


def totp_confirm(db: Session, sess: AdminSession, user: User, code: str, *,
                 ip: str | None) -> None:
    if not user.totp_pending_secret:
        raise AuthError("no setup in progress")
    check_throttle(db, user.username, ip)
    step = totp.verify(user.totp_pending_secret, code)
    if step is None:
        _attempt(db, user.username, ip, "totp_setup", False)
        db.commit()
        raise AuthError("invalid code")
    replaced = user.totp_secret is not None
    user.totp_secret = user.totp_pending_secret
    user.totp_pending_secret = None
    user.totp_last_step = step
    revoke_all(db, user.id, except_id=sess.id)
    audit.record(db, "totp_replaced" if replaced else "totp_enrolled", actor=user, ip=ip)
    db.commit()


# ------------------------------------------------------------------------------- users


def _admins_left(db: Session, excluding: int) -> int:
    return db.scalar(select(func.count()).select_from(User).where(
        User.role == "admin", User.disabled.is_(False), User.id != excluding)) or 0


def create_user(db: Session, username: str, role: str, password: str, *,
                actor: User | str, ip: str | None = None,
                must_change_password: bool = True) -> User:
    name = check_username(username)
    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")
    check_policy(password, username=name)
    if db.scalar(select(User).where(User.username == name)) is not None:
        raise ValueError("username already exists")
    user = User(username=name, role=role, password_hash=hash_password(password),
                must_change_password=must_change_password)
    db.add(user)
    db.flush()
    audit.record(db, "user_created", actor=actor, target=f"user:{name}", ip=ip, role=role)
    db.commit()
    return user


def update_user(db: Session, user: User, *, actor: User, ip: str | None = None,
                role: str | None = None, disabled: bool | None = None,
                reset_password: str | None = None, reset_totp: bool = False) -> User:
    """Admin changes to another account. The last active admin cannot be demoted or disabled."""
    if user.id == actor.id:
        raise Forbidden("change your own account on the account page")
    changes: dict[str, object] = {}
    losing_admin = (user.role == "admin" and not user.disabled
                    and ((role is not None and role != "admin") or disabled is True))
    if losing_admin and _admins_left(db, user.id) == 0:
        raise Forbidden("the last active admin cannot be demoted or disabled")
    if role is not None and role != user.role:
        if role not in ROLES:
            raise ValueError(f"role must be one of {', '.join(ROLES)}")
        changes["role"] = [user.role, role]
        user.role = role
    if disabled is not None and disabled != user.disabled:
        changes["disabled"] = disabled
        user.disabled = disabled
    if reset_password is not None:
        check_policy(reset_password, username=user.username)
        user.password_hash = hash_password(reset_password)
        user.must_change_password = True
        changes["password_reset"] = True
    if reset_totp:
        user.totp_secret = None
        user.totp_pending_secret = None
        user.totp_last_step = None
        changes["totp_reset"] = True
    if changes:
        # Any change to access ends the account's sessions: the new rules apply at once.
        revoke_all(db, user.id)
    audit.record(db, "user_updated", actor=actor, target=f"user:{user.username}", ip=ip,
                 **changes)
    db.commit()
    return user


def purge_old_attempts(db: Session, older_than_days: int = 30) -> int:
    """Housekeeping for the worker: login attempts are only needed for throttling and audit."""
    cut = now() - dt.timedelta(days=older_than_days)
    rows = db.query(LoginAttempt).filter(LoginAttempt.at < cut).delete()
    db.query(AdminSession).filter(AdminSession.expires_at < cut).delete()
    db.commit()
    return rows
