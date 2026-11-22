"""Queue a message in the caller's transaction; the worker's sender delivers it.

The web process never talks to the SMTP server (its egress policy allows only DNS and
Postgres). A message commits with the event it describes, so a rolled back change sends
nothing and a committed one is never forgotten.
"""

from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from north.mail import messages
from north.repository.models import EmailOutbox, Job, User
from north.settings import Settings, get_settings

# Deliberately simple: one @, no spaces or control characters, a dot in the domain. The
# verification link is the real test.
EMAIL_RE = re.compile(r"^[^@\s\x00-\x1f\x7f<>,;\"]{1,64}@[a-z0-9-]+(\.[a-z0-9-]+)+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("not a valid email address")
    return email


def queue(db: Session, kind: str, to: str, *, locale: str = "en", user: User | None = None,
          settings: Settings | None = None, **values: object) -> EmailOutbox:
    settings = settings or get_settings()
    subject, body = messages.render(kind, locale, public_url=settings.public_url, **values)
    row = EmailOutbox(kind=kind, to_addr=to, subject=subject, body=body,
                      user_id=user.id if user else None,
                      sensitive=kind in messages.SENSITIVE)
    db.add(row)
    return row


def to_user(db: Session, user: User, kind: str, *, require_verified: bool = True,
            settings: Settings | None = None, **values: object) -> EmailOutbox | None:
    """A message to an account's address; None when it has none (or not verified)."""
    if not user.email or (require_verified and user.email_verified_at is None):
        return None
    return queue(db, kind, user.email, locale=user.locale, user=user, settings=settings,
                 username=user.username, **values)


def job_outcome(db: Session, job: Job, title: str,
                settings: Settings | None = None) -> int:
    """A failed or attention job: email whoever asked for it, or every admin for a scheduled
    job. Only verified addresses with job emails on. Returns the number of messages queued."""
    settings = settings or get_settings()
    if job.requested_by is not None:
        users = [u for u in [db.get(User, job.requested_by)] if u is not None]
    else:
        users = list(db.scalars(select(User).where(User.role == "admin")))
    url = f"{settings.public_url.rstrip('/')}/admin/jobs/{job.id}"
    error = (job.error or "").strip()[:2000]
    n = 0
    for user in users:
        if user.disabled or not user.notify_jobs:
            continue
        status = messages.phrase(user.locale, "status", job.status)
        if to_user(db, user, "job_failed", settings=settings, id=job.id, title=title,
                   status=status, error=error, url=url):
            n += 1
    return n


def recent_count(db: Session, user_id: int, kind: str, since: dt.datetime) -> int:
    return db.scalar(select(func.count()).select_from(EmailOutbox).where(
        EmailOutbox.user_id == user_id, EmailOutbox.kind == kind,
        EmailOutbox.created_at > since)) or 0
