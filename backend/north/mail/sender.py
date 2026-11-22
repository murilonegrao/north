"""Delivery: the worker runs this in a thread, beside the job loop (a long job never delays a
password reset link).

Each pass claims due messages with FOR UPDATE SKIP LOCKED, sends them over one SMTP
connection, and records the outcome. Temporary failures retry with backoff; a permanent refusal
(5xx) or the last attempt ends as "failed". A message queued more than a day ago is dropped as
"expired" instead of sent late (a reset link would be dead anyway).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from north.repository.models import EmailOutbox
from north.settings import Settings, get_settings

log = logging.getLogger("north.mail")

BATCH = 20
POLL_EVERY = 5.0
TIMEOUT = 20
RETRY_AFTER = (60, 300, 1800, 7200)  # seconds after attempts 1..4; attempt 5 is the last
MAX_ATTEMPTS = len(RETRY_AFTER) + 1
MAX_AGE = dt.timedelta(hours=24)
NOT_CONFIGURED = "email is not configured on the worker (NORTH_SMTP_HOST, NORTH_MAIL_FROM)"


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Permanent(Exception):
    """The server refused for good: retrying will not help."""


def build(row: EmailOutbox, settings: Settings) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = row.to_addr
    msg["Subject"] = row.subject
    msg["Date"] = formatdate(localtime=False)
    domain = parseaddr(settings.mail_from or "")[1].rpartition("@")[2] or None
    msg["Message-ID"] = make_msgid(domain=domain)
    if settings.mail_reply_to:
        msg["Reply-To"] = settings.mail_reply_to
    # RFC 3834: no out-of-office replies to automatic messages.
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content(row.body)
    return msg


def connect(settings: Settings) -> smtplib.SMTP:
    host, port = settings.smtp_host or "", settings.smtp_port
    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT, context=context)
    else:
        smtp = smtplib.SMTP(host, port, timeout=TIMEOUT)
        if settings.smtp_security == "starttls":
            smtp.starttls(context=context)
        elif settings.smtp_security != "none":
            raise ValueError(f"NORTH_SMTP_SECURITY must be ssl, starttls or none, "
                             f"not {settings.smtp_security!r}")
    if settings.smtp_username:
        smtp.login(settings.smtp_username, settings.smtp_password or "")
    return smtp


def deliver(smtp: smtplib.SMTP, msg: EmailMessage) -> None:
    try:
        refused = smtp.send_message(msg)
    except smtplib.SMTPRecipientsRefused as e:
        raise Permanent(f"recipient refused: {e.recipients}") from None
    except smtplib.SMTPResponseException as e:
        if 500 <= e.smtp_code < 600:
            raise Permanent(f"{e.smtp_code} {e.smtp_error!r}") from None
        raise
    if refused:
        raise Permanent(f"recipient refused: {refused}")


def _settle(row: EmailOutbox, error: str | None, *, permanent: bool = False) -> None:
    if error is None:
        row.status, row.sent_at, row.last_error = "sent", now(), None
        if row.sensitive:
            row.body = "[removed after sending: it held a single-use link]"
        return
    row.attempts += 1
    row.last_error = error[:500]
    if permanent or row.attempts >= MAX_ATTEMPTS:
        row.status = "failed"
    else:
        row.next_attempt_at = now() + dt.timedelta(seconds=RETRY_AFTER[row.attempts - 1])


def send_due(db: Session, settings: Settings | None = None, *, connector=connect) -> int:
    """One pass; returns the number of messages sent."""
    settings = settings or get_settings()
    t = now()
    db.execute(update(EmailOutbox)
               .where(EmailOutbox.status == "queued", EmailOutbox.created_at < t - MAX_AGE)
               .values(status="expired", last_error="not sent within 24 hours"))
    db.commit()
    rows = db.scalars(select(EmailOutbox)
                      .where(EmailOutbox.status == "queued", EmailOutbox.next_attempt_at <= t)
                      .order_by(EmailOutbox.id).limit(BATCH)
                      .with_for_update(skip_locked=True)).all()
    if not rows:
        db.commit()
        return 0
    if not settings.mail_configured():
        for row in rows:  # they wait; the admin shows why
            if row.last_error != NOT_CONFIGURED:
                row.last_error = NOT_CONFIGURED
            row.next_attempt_at = t + dt.timedelta(minutes=1)
        db.commit()
        return 0
    sent = 0
    try:
        smtp = connector(settings)
    except Exception as e:  # server down, wrong password, TLS: every row retries later
        error = f"connect: {type(e).__name__}: {e}"
        log.warning("smtp %s", error)
        auth_failed = isinstance(e, smtplib.SMTPAuthenticationError)
        for row in rows:
            _settle(row, error)
            if auth_failed:  # do not hammer the account into a lockout
                row.next_attempt_at = max(row.next_attempt_at, t + dt.timedelta(minutes=30))
        db.commit()
        return 0
    try:
        for row in rows:
            try:
                deliver(smtp, build(row, settings))
            except Permanent as e:
                _settle(row, str(e), permanent=True)
            except Exception as e:
                _settle(row, f"{type(e).__name__}: {e}")
            else:
                _settle(row, None)
                sent += 1
    finally:
        with contextlib.suppress(Exception):
            smtp.quit()
        db.commit()
    if sent:
        log.info("sent %d email(s)", sent)
    return sent


class MailSender(threading.Thread):
    """Daemon thread of the worker process, with its own database session."""

    def __init__(self, sessions: sessionmaker[Session], stop: threading.Event) -> None:
        super().__init__(name="mail-sender", daemon=True)
        self.sessions, self.stop = sessions, stop

    def run(self) -> None:
        settings = get_settings()
        if not settings.mail_configured():
            log.warning("%s; messages stay queued", NOT_CONFIGURED)
        while not self.stop.is_set():
            try:
                with self.sessions() as db:
                    while send_due(db, settings) == BATCH and not self.stop.is_set():
                        pass
            except Exception:  # never let a database blip end the thread
                log.exception("mail pass failed")
            self.stop.wait(POLL_EVERY)
