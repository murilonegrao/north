"""Email (record 0007): templates, the outbox, the sender, reset and verification links,
security notices. Database tests need NORTH_TEST_DATABASE_URL."""

from __future__ import annotations

import datetime as dt
import re
import smtplib
from email.message import EmailMessage
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from north.auth import service
from north.mail import messages, outbox, sender
from north.repository.models import AdminSession, EmailOutbox, Job, User, UserToken
from north.settings import Settings
from tests.test_admin_api import NEW_PASSWORD, client, env, login, onboard  # noqa: F401

SAMPLE = {"username": "ana", "url": "https://x.test/admin/reset#token=abc", "hours": 24,
          "minutes": 30, "ip": "203.0.113.9", "new_email": "new@example.org",
          "agent": "Firefox", "failures": 5, "admin": "bia", "changes": "  - role",
          "id": 7, "title": "Download and load", "status": "failed", "error": "boom"}


# ------------------------------------------------------------------------------ units


@pytest.mark.parametrize("locale", messages.LOCALES)
@pytest.mark.parametrize("kind", messages.kinds())
def test_every_template_renders(kind: str, locale: str) -> None:
    subject, body = messages.render(kind, locale, public_url="https://north.example/", **SAMPLE)
    assert "\n" not in subject and subject.startswith("North")
    assert "{" not in body and "}" not in body
    assert "https://north.example/admin" in body  # signature
    if kind in messages.SECURITY:
        assert messages.catalog(locale)["footer"]["security"] in body


def test_locales_have_the_same_keys() -> None:
    en, pt = messages.catalog("en"), messages.catalog("pt-BR")
    assert set(en["messages"]) == set(pt["messages"])
    assert set(en["changes"]) == set(pt["changes"])
    for k in en["messages"]:
        for part in ("subject", "body"):
            assert set(re.findall(r"{(\w+)}", en["messages"][k][part])) == \
                set(re.findall(r"{(\w+)}", pt["messages"][k][part])), (k, part)


@pytest.mark.parametrize("raw,ok", [
    ("Ana@Example.org ", "ana@example.org"), ("a.b+tag@sub.example.co", "a.b+tag@sub.example.co"),
    ("no-at.example.org", None), ("a@b", None), ("a b@example.org", None),
    ("a@example.org\nBcc: x@evil.test", None), ("<a@example.org>", None),
    ("x" * 65 + "@a.org", None),
])
def test_normalize_email(raw: str, ok: str | None) -> None:
    if ok is None:
        with pytest.raises(ValueError):
            outbox.normalize_email(raw)
    else:
        assert outbox.normalize_email(raw) == ok


def mail_settings(**kw: Any) -> Settings:
    base = {"smtp_host": "smtp.test", "mail_from": "North <north@harpia.test>",
            "public_url": "https://north.test"}
    return Settings(**{**base, **kw})


def test_build_headers() -> None:
    row = EmailOutbox(to_addr="ana@example.org", subject="North: hi", body="hello\n")
    msg = sender.build(row, mail_settings(mail_reply_to="help@harpia.test"))
    assert msg["From"] == "North <north@harpia.test>"
    assert msg["Auto-Submitted"] == "auto-generated"
    assert msg["Message-ID"].endswith("@harpia.test>")
    assert msg["Reply-To"] == "help@harpia.test"
    assert msg.get_content_type() == "text/plain"


def test_build_refuses_header_injection() -> None:
    row = EmailOutbox(to_addr="ana@example.org", subject="hi\nBcc: x@evil.test", body="x")
    with pytest.raises(ValueError):
        sender.build(row, mail_settings())


# ------------------------------------------------------------------- database helpers


class FakeSmtp:
    def __init__(self, fail: dict[str, Exception] | None = None) -> None:
        self.sent: list[EmailMessage] = []
        self.fail = fail or {}

    def send_message(self, msg: EmailMessage) -> dict:
        exc = self.fail.get(str(msg["To"]))
        if exc:
            raise exc
        self.sent.append(msg)
        return {}

    def quit(self) -> None:
        pass


def rows(session: Session, kind: str | None = None) -> list[EmailOutbox]:
    session.expire_all()
    q = select(EmailOutbox).order_by(EmailOutbox.id)
    if kind:
        q = q.where(EmailOutbox.kind == kind)
    return list(session.scalars(q))


def verified(session: Session, name: str = "ana", email: str = "ana@example.org") -> User:
    user = session.scalar(select(User).where(User.username == name))
    user.email, user.email_verified_at = email, dt.datetime.now(dt.UTC)
    session.commit()
    return user


def token_in(row: EmailOutbox) -> str:
    m = re.search(r"#token=([\w-]+)", row.body)
    assert m, row.body
    return m.group(1)


@pytest.fixture
def ip_header(monkeypatch: pytest.MonkeyPatch, env: Any) -> None:  # noqa: F811
    from north.settings import get_settings
    monkeypatch.setenv("NORTH_CLIENT_IP_HEADER", "x-test-ip")
    get_settings.cache_clear()


# ------------------------------------------------------------------- reset and verify


def test_forgot_and_reset(client: TestClient, session: Session) -> None:  # noqa: F811
    onboard(client, session)
    verified(session)
    r = client.post("/api/admin/auth/forgot", json={"login": "ANA@example.org"})
    assert r.status_code == 200 and r.json()["ok"] is True
    [row] = rows(session, "password_reset")
    assert row.to_addr == "ana@example.org" and row.sensitive
    assert "https://" not in row.body or "/admin/reset#token=" in row.body
    token = token_in(row)

    r = client.post("/api/admin/auth/reset", json={"token": token, "new": "short"})
    assert r.status_code == 400 and r.json()["detail"]["field"] == "new"
    r = client.post("/api/admin/auth/reset", json={"token": token, "new": "a new long pass phrase"})
    assert r.status_code == 200, r.text
    # Single use, sessions ended, owner told.
    again = client.post("/api/admin/auth/reset",
                        json={"token": token, "new": "another long phrase"})
    assert again.status_code == 400
    assert session.scalar(select(AdminSession).where(AdminSession.revoked_at.is_(None))) is None
    assert rows(session, "password_changed")
    # The second factor is still required.
    r = client.post("/api/admin/auth/login",
                    json={"username": "ana", "password": "a new long pass phrase"})
    assert r.json()["stage"] == "totp"


def test_forgot_says_nothing_about_accounts(client: TestClient,  # noqa: F811
                                            session: Session) -> None:
    onboard(client, session)  # no email at all
    session.add(User(username="bob", role="viewer", password_hash="x", email="bob@example.org"))
    session.commit()  # bob: unverified address
    answers = {client.post("/api/admin/auth/forgot", json={"login": login_}).text
               for login_ in ("ana", "bob", "bob@example.org", "nobody", "x@y.org")}
    assert len(answers) == 1
    assert rows(session, "password_reset") == []


def test_forgot_is_limited_per_account(client: TestClient, session: Session) -> None:  # noqa: F811
    onboard(client, session)
    verified(session)
    for _ in range(5):
        assert client.post("/api/admin/auth/forgot", json={"login": "ana"}).status_code == 200
    resets = rows(session, "password_reset")
    assert len(resets) == service.MAX_RESETS_PER_ACCOUNT
    # Only the newest link works.
    tokens = session.scalars(select(UserToken).where(UserToken.purpose == "reset_password",
                                                     UserToken.used_at.is_(None))).all()
    assert len(tokens) == 1


def test_expired_reset_link(client: TestClient, session: Session) -> None:  # noqa: F811
    onboard(client, session)
    verified(session)
    client.post("/api/admin/auth/forgot", json={"login": "ana"})
    token = token_in(rows(session, "password_reset")[0])
    tok = session.scalar(select(UserToken))
    tok.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
    session.commit()
    r = client.post("/api/admin/auth/reset", json={"token": token, "new": "a new long pass phrase"})
    assert r.status_code == 400


def test_email_change_needs_password_and_verification(client: TestClient,  # noqa: F811
                                                      session: Session) -> None:
    a = onboard(client, session)
    r = a.post("/api/admin/auth/email", json={"email": "ana@example.org", "password": "wrong!"})
    assert r.status_code == 400 and r.json()["detail"]["field"] == "password"
    r = a.post("/api/admin/auth/email", json={"email": "Ana@Example.org", "password": NEW_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == "ana@example.org"
    assert r.json()["user"]["email_verified"] is False
    [row] = rows(session, "verify_email")
    token = token_in(row)
    # Unverified: no reset link.
    client.post("/api/admin/auth/forgot", json={"login": "ana"})
    assert rows(session, "password_reset") == []

    r = client.post("/api/admin/auth/email/verify", json={"token": token})
    assert r.status_code == 200 and r.json()["email"] == "ana@example.org"
    assert a.get("/api/admin/auth/me").json()["user"]["email_verified"] is True

    # A new address: the old (verified) one is told, and an old link no longer verifies.
    r = a.post("/api/admin/auth/email", json={"email": "new@example.org", "password": NEW_PASSWORD})
    [changed] = rows(session, "email_changed")
    assert changed.to_addr == "ana@example.org" and "new@example.org" in changed.body
    first = token_in(rows(session, "verify_email")[-1])
    a.post("/api/admin/auth/email", json={"email": "third@example.org", "password": NEW_PASSWORD})
    assert client.post("/api/admin/auth/email/verify", json={"token": first}).status_code == 400


def test_email_unique(client: TestClient, session: Session) -> None:  # noqa: F811
    a = onboard(client, session)
    session.add(User(username="bob", role="viewer", password_hash="x", email="bob@example.org"))
    session.commit()
    r = a.post("/api/admin/auth/email", json={"email": "bob@example.org", "password": NEW_PASSWORD})
    assert r.status_code == 400 and r.json()["detail"]["field"] == "email"


def test_test_email_and_preferences(client: TestClient, session: Session) -> None:  # noqa: F811
    a = onboard(client, session)
    assert a.post("/api/admin/auth/email/test").status_code == 400  # no address yet
    a.post("/api/admin/auth/email", json={"email": "ana@example.org", "password": NEW_PASSWORD})
    r = a.patch("/api/admin/auth/preferences", json={"locale": "pt-BR", "notify_jobs": False})
    assert r.json()["user"]["locale"] == "pt-BR" and r.json()["user"]["notify_jobs"] is False
    assert a.patch("/api/admin/auth/preferences", json={"locale": "fr"}).status_code == 400
    for _ in range(service.TEST_EMAILS_PER_HOUR):
        assert a.post("/api/admin/auth/email/test").json()["to"] == "ana@example.org"
    assert a.post("/api/admin/auth/email/test").status_code == 429
    assert rows(session, "test")[0].subject == "North: email de teste"


# ------------------------------------------------------------------- security notices


def relogin(client: TestClient, session: Session) -> None:  # noqa: F811
    """Sign in again; codes are accepted once and only near the current step, so forget the
    last accepted step between quick sign-ins."""
    user = verified(session)
    user.totp_last_step = None
    session.commit()
    login(client, session)


def test_new_sign_in_notice(client: TestClient, session: Session, ip_header: None) -> None:  # noqa: F811
    onboard(client, session)
    client.headers["x-test-ip"] = "203.0.113.1"
    relogin(client, session)
    assert len(rows(session, "new_sign_in")) == 1  # first sign-in from this address
    relogin(client, session)
    assert len(rows(session, "new_sign_in")) == 1  # known now
    client.headers["x-test-ip"] = "198.51.100.7"
    relogin(client, session)
    [_, last] = rows(session, "new_sign_in")
    assert "198.51.100.7" in last.body


def test_lockout_notice_once(client: TestClient, session: Session) -> None:  # noqa: F811
    onboard(client, session)
    verified(session)
    for _ in range(service.MAX_FAILURES_PER_USER + 2):
        client.post("/api/admin/auth/login", json={"username": "ana", "password": "nope nope"})
    assert len(rows(session, "login_locked")) == 1


def test_admin_changes_are_told(client: TestClient, session: Session) -> None:  # noqa: F811
    a = onboard(client, session)
    bob = service.create_user(session, "bob", "viewer", "temporary password 1", actor="test")
    verified(session, "bob", "bob@example.org")
    r = a.patch(f"/api/admin/users/{bob.id}", json={"role": "curator"})
    assert r.status_code == 200, r.text
    [row] = rows(session, "access_changed")
    assert row.to_addr == "bob@example.org" and "viewer → curator" in row.body
    r = a.patch(f"/api/admin/users/{bob.id}", json={"email": "bob2@example.org"})
    assert r.json()["email"] == "bob2@example.org" and r.json()["email_verified"] is False
    assert rows(session, "email_changed")[0].to_addr == "bob@example.org"
    assert rows(session, "verify_email")[0].to_addr == "bob2@example.org"


def test_password_change_notice(client: TestClient, session: Session) -> None:  # noqa: F811
    a = onboard(client, session)
    verified(session)
    r = a.post("/api/admin/auth/password", json={"current": NEW_PASSWORD,
                                                  "new": "yet another pass phrase"})
    assert r.status_code == 200
    assert rows(session, "password_changed")[0].to_addr == "ana@example.org"


# ------------------------------------------------------------------------------ sender


def queue_one(session: Session, to: str = "ana@example.org", kind: str = "test",
              **values: Any) -> EmailOutbox:
    row = outbox.queue(session, kind, to, username="ana", **values)
    session.commit()
    return row


def test_sender_sends_and_blanks_links(session: Session) -> None:
    queue_one(session)
    queue_one(session, kind="password_reset", url="https://x/admin/reset#token=secret",
              ip="1.2.3.4", minutes=30)
    fake = FakeSmtp()
    assert sender.send_due(session, mail_settings(), connector=lambda s: fake) == 2
    assert [m["To"] for m in fake.sent] == ["ana@example.org"] * 2
    assert "token=secret" in fake.sent[1].get_content()
    test_row, reset_row = rows(session)
    assert test_row.status == reset_row.status == "sent"
    assert "secret" not in reset_row.body and "secret" not in test_row.body


def test_sender_retries_and_gives_up(session: Session) -> None:
    queue_one(session, to="temp@example.org")
    queue_one(session, to="gone@example.org")
    fake = FakeSmtp({"temp@example.org": smtplib.SMTPServerDisconnected("bye"),
                     "gone@example.org": smtplib.SMTPRecipientsRefused(
                         {"gone@example.org": (550, b"no such user")})})
    assert sender.send_due(session, mail_settings(), connector=lambda s: fake) == 0
    temp, gone = rows(session)
    assert temp.status == "queued" and temp.attempts == 1
    assert temp.next_attempt_at > dt.datetime.now(dt.UTC) + dt.timedelta(seconds=50)
    assert gone.status == "failed" and "refused" in (gone.last_error or "")
    temp.attempts, temp.next_attempt_at = sender.MAX_ATTEMPTS - 1, dt.datetime.now(dt.UTC)
    session.commit()
    sender.send_due(session, mail_settings(), connector=lambda s: fake)
    assert rows(session)[0].status == "failed"


def test_sender_connect_failure_and_not_configured(session: Session) -> None:
    queue_one(session)

    def broken(_: Settings) -> Any:
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    assert sender.send_due(session, mail_settings(), connector=broken) == 0
    [row] = rows(session)
    assert row.status == "queued" and "connect" in (row.last_error or "")
    assert row.next_attempt_at > dt.datetime.now(dt.UTC) + dt.timedelta(minutes=29)

    row.next_attempt_at = dt.datetime.now(dt.UTC)
    session.commit()
    sender.send_due(session, Settings(smtp_host=None), connector=broken)
    [row] = rows(session)
    assert row.status == "queued" and row.last_error == sender.NOT_CONFIGURED


def test_sender_expires_old_messages(session: Session) -> None:
    row = queue_one(session)
    row.created_at = dt.datetime.now(dt.UTC) - dt.timedelta(hours=25)
    session.commit()
    fake = FakeSmtp()
    sender.send_due(session, mail_settings(), connector=lambda s: fake)
    assert fake.sent == [] and rows(session)[0].status == "expired"


def test_failed_scheduled_job_emails_admins(session: Session) -> None:
    for name, role in (("ana", "admin"), ("bia", "admin"), ("cal", "curator"), ("dan", "admin")):
        service.create_user(session, name, role, "temporary password 1", actor="test")
        verified(session, name, f"{name}@example.org")
    dan = session.scalar(select(User).where(User.username == "dan"))
    dan.notify_jobs = False
    session.commit()
    job = Job(kind="us.sync", status="failed", error="ValueError: boom")
    session.add(job)
    session.commit()
    assert outbox.job_outcome(session, job, "Download and load") == 2
    sent = rows(session, "job_failed")
    assert sorted(r.to_addr for r in sent) == ["ana@example.org", "bia@example.org"]
    assert f"/admin/jobs/{job.id}" in sent[0].body and "boom" in sent[0].body


def test_overview_reports_mail(client: TestClient, session: Session) -> None:  # noqa: F811
    a = onboard(client, session)
    queue_one(session)
    mail = a.get("/api/admin/overview").json()["mail"]
    assert mail["queued"] == 1 and mail["last_error"] is None
