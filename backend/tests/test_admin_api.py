"""Admin API and worker against PostgreSQL (needs NORTH_TEST_DATABASE_URL).

The client talks https so the production cookie (__Host-, Secure, SameSite=Strict) is used.
"""

from __future__ import annotations

import time
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from north.api.app import app
from north.auth import service, totp
from north.jobs import queue, registry, worker
from north.jobs.registry import JobKind
from north.repository.db import session_scope
from north.repository.models import AuditEntry, Job, LoginAttempt, Schedule, User
from north.settings import get_settings
from tests.conftest import FIXTURES

PASSWORD = "first temporary password"
NEW_PASSWORD = "a much better pass phrase"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("NORTH_RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("NORTH_INCOMING_DIR", str(tmp_path / "incoming"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def client(session: Session, env: Path) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[session_scope] = override
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides.clear()


def make_user(session: Session, name: str = "ana", role: str = "admin") -> User:
    return service.create_user(session, name, role, PASSWORD, actor="test")


class Admin:
    """A logged-in browser: cookie in the client, CSRF token kept here."""

    def __init__(self, client: TestClient, csrf: str) -> None:
        self.c, self.csrf = client, csrf

    def _h(self, kw: dict[str, Any]) -> dict[str, Any]:
        kw["headers"] = {"X-CSRF-Token": self.csrf, **kw.get("headers", {})}
        return kw

    def post(self, url: str, **kw: Any) -> Any:
        return self.c.post(url, **self._h(kw))

    def patch(self, url: str, **kw: Any) -> Any:
        return self.c.patch(url, **self._h(kw))

    def put(self, url: str, **kw: Any) -> Any:
        return self.c.put(url, **self._h(kw))

    def get(self, url: str, **kw: Any) -> Any:
        return self.c.get(url, **kw)


def code_for(session: Session, name: str, ahead: int = 0) -> str:
    """A code newer than the last accepted one (codes are never accepted twice)."""
    user = session.scalar(select(User).where(User.username == name))
    session.refresh(user)
    step = totp.current_step() + ahead
    if user.totp_last_step is not None and step <= user.totp_last_step:
        step = user.totp_last_step + 1
    return totp.code_at(user.totp_secret or user.totp_pending_secret, step)


def onboard(client: TestClient, session: Session, name: str = "ana",
            role: str = "admin") -> Admin:
    """First login: temporary password -> new password -> TOTP enrolment -> stage ok."""
    make_user(session, name, role)
    r = client.post("/api/admin/auth/login", json={"username": name, "password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["stage"] == "change_password"
    a = Admin(client, r.json()["csrf"])
    r = a.post("/api/admin/auth/password", json={"current": PASSWORD, "new": NEW_PASSWORD})
    assert r.json()["stage"] == "enroll_totp", r.text
    setup = a.post("/api/admin/auth/totp/setup").json()
    assert setup["qr"].startswith("data:image/svg+xml")
    r = a.post("/api/admin/auth/totp/confirm", json={"code": code_for(session, name)})
    assert r.json()["stage"] == "ok", r.text
    return a


def login(client: TestClient, session: Session, name: str = "ana") -> Admin:
    r = client.post("/api/admin/auth/login", json={"username": name, "password": NEW_PASSWORD})
    assert r.json()["stage"] == "totp", r.text
    a = Admin(client, r.json()["csrf"])
    r = a.post("/api/admin/auth/totp", json={"code": code_for(session, name, ahead=1)})
    assert r.status_code == 200, r.text
    return Admin(client, r.json()["csrf"])


# ------------------------------------------------------------------------------ auth


def test_cookie_flags_and_headers(client: TestClient, session: Session) -> None:
    make_user(session)
    r = client.post("/api/admin/auth/login", json={"username": "ana", "password": PASSWORD})
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("__Host-north_admin=")
    for flag in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert flag.lower() in cookie.lower()
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-robots-tag"] == "noindex, nofollow"


def test_full_onboarding_then_relogin(client: TestClient, session: Session) -> None:
    a = onboard(client, session)
    assert a.get("/api/admin/auth/me").json()["user"]["has_totp"] is True
    assert a.post("/api/admin/auth/logout").status_code == 200
    assert client.get("/api/admin/auth/me").status_code == 401
    b = login(client, session)
    assert b.get("/api/admin/overview").status_code == 200
    actions = [e.action for e in session.scalars(select(AuditEntry).order_by(AuditEntry.id))]
    # The first login has no TOTP yet, so the password alone opens the (restricted) session.
    assert actions[:5] == ["user_created", "login", "password_changed", "totp_enrolled", "login"]


def test_wrong_password_is_generic_and_throttled(client: TestClient, session: Session) -> None:
    make_user(session)
    for name in ("ana", "nobody"):
        r = client.post("/api/admin/auth/login", json={"username": name, "password": "nope"})
        assert r.status_code == 401
        assert r.json()["detail"] == "invalid username or password"
    for _ in range(service.MAX_FAILURES_PER_USER - 1):
        client.post("/api/admin/auth/login", json={"username": "ana", "password": "nope"})
    r = client.post("/api/admin/auth/login", json={"username": "ana", "password": PASSWORD})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    assert session.scalar(select(LoginAttempt).where(LoginAttempt.ok.is_(True))) is None


def test_pending_session_cannot_do_anything(client: TestClient, session: Session) -> None:
    onboard(client, session)
    client.cookies.clear()
    r = client.post("/api/admin/auth/login", json={"username": "ana", "password": NEW_PASSWORD})
    a = Admin(client, r.json()["csrf"])
    assert a.get("/api/admin/overview").status_code == 403
    assert a.post("/api/admin/jobs", json={"kind": "us.fetch"}).status_code == 403
    assert a.post("/api/admin/auth/totp", json={"code": "000000"}).status_code == 401


def test_csrf_and_cross_site(client: TestClient, session: Session) -> None:
    a = onboard(client, session)
    assert client.post("/api/admin/jobs", json={"kind": "us.fetch"}).status_code == 403
    r = client.post("/api/admin/jobs", json={"kind": "us.fetch"},
                    headers={"X-CSRF-Token": a.csrf, "Origin": "https://evil.example"})
    assert r.status_code == 403 and "cross-site" in r.text
    r = a.post("/api/admin/jobs", json={"kind": "us.fetch"},
               headers={"Origin": "https://testserver"})
    assert r.status_code == 201  # same origin passes the middleware


def test_disabled_user_loses_session(client: TestClient, session: Session) -> None:
    a = onboard(client, session)
    user = session.scalar(select(User).where(User.username == "ana"))
    user.disabled = True
    session.commit()
    assert a.get("/api/admin/overview").status_code == 401


def test_audit_log_is_append_only(session: Session) -> None:
    make_user(session)
    with pytest.raises(Exception, match="append-only"):
        session.execute(text("update audit_log set action = 'x'"))
    session.rollback()


# ------------------------------------------------------------------------------ roles


def test_roles_and_last_admin(client: TestClient, session: Session) -> None:
    a = onboard(client, session)
    r = a.post("/api/admin/users", json={"username": "Bob", "role": "viewer",
                                         "password": "a temporary pass phrase"})
    assert r.status_code == 201 and r.json()["username"] == "bob"
    bob_id = r.json()["id"]
    ana_id = session.scalar(select(User.id).where(User.username == "ana"))
    assert a.patch(f"/api/admin/users/{ana_id}", json={"role": "viewer"}).status_code == 403
    assert a.patch(f"/api/admin/users/{bob_id}", json={"role": "curator"}).json()["role"] == \
        "curator"
    assert a.post("/api/admin/users", json={"username": "x", "role": "admin",
                                            "password": "short"}).status_code == 400
    assert len(a.get("/api/admin/audit").json()) >= 4


def test_viewer_cannot_run_jobs_or_manage_users(client: TestClient, session: Session) -> None:
    v = onboard(client, session, "vera", "viewer")
    assert v.get("/api/admin/jobs").status_code == 200
    assert v.post("/api/admin/jobs", json={"kind": "us.fetch"}).status_code == 403
    assert v.get("/api/admin/users").status_code == 403
    assert v.get("/api/admin/audit").status_code == 403
    kinds = {k["name"]: k["allowed"] for k in v.get("/api/admin/job-kinds").json()}
    assert kinds == {"us.fetch": False, "us.sync": False, "us.recompute": False,
                     "ie.load": False}


# ------------------------------------------------------------------------------ jobs


def test_enqueue_dedupe_cancel(client: TestClient, session: Session) -> None:
    a = onboard(client, session)
    r = a.post("/api/admin/jobs", json={"kind": "us.sync", "params": {"states": "tx"}})
    assert r.status_code == 201 and r.json()["params"] == {"states": "TX", "fetch": True}
    job_id = r.json()["id"]
    again = a.post("/api/admin/jobs", json={"kind": "us.sync"})
    assert again.status_code == 409 and again.json()["job_id"] == job_id
    assert a.post("/api/admin/jobs", json={"kind": "us.sync",
                                           "params": {"states": "ZZ"}}).status_code == 400
    assert a.post("/api/admin/jobs", json={"kind": "us.accept_upload"}).status_code == 404
    assert a.post(f"/api/admin/jobs/{job_id}/cancel").json()["status"] == "cancelled"


def _worker(engine: Engine) -> worker.Worker:
    return worker.Worker(sessionmaker(bind=engine, expire_on_commit=False))


def test_upload_is_placed_by_the_worker(client: TestClient, session: Session, engine: Engine,
                                        env: Path) -> None:
    a = onboard(client, session)
    zpath = env / "dapip.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for n in ("InstitutionCampus.csv", "AccreditationRecords.csv"):
            z.write(FIXTURES / "dapip" / n, f"export/{n}")
    r = a.put("/api/admin/uploads?filename=DAPIP_export.zip", content=zpath.read_bytes())
    assert r.status_code == 201, r.text
    job_id = r.json()["id"]
    assert list((env / "incoming").iterdir())  # the web process wrote only here
    assert _worker(session.get_bind()).tick() is True
    job = a.get(f"/api/admin/jobs/{job_id}").json()
    assert job["status"] == "succeeded", job
    assert job["result"]["kind"] == "dapip" and job["result"]["status"] == "new"
    assert (env / "raw" / "dapip" / "extracted" / "InstitutionCampus.csv").is_file()
    assert not list((env / "incoming").iterdir())
    assert any("recognised as dapip" in line["line"] for line in job["logs"])

    r = a.put("/api/admin/uploads?filename=notes.txt", content=b"hello")
    _worker(session.get_bind()).tick()
    job = a.get(f"/api/admin/jobs/{r.json()['id']}").json()
    assert job["status"] == "failed" and "not recognised" in job["error"]


def test_upload_rejects_bad_names_and_size(client: TestClient, session: Session,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    a = onboard(client, session)
    # Only the base name is kept, so a path cannot leave incoming/.
    assert a.put("/api/admin/uploads?filename=../x.zip", content=b"PK").json()["params"][
        "file"].endswith("__x.zip")
    assert a.put("/api/admin/uploads?filename=a%20b.zip", content=b"PK").status_code == 400
    assert a.put("/api/admin/uploads?filename=.hidden", content=b"PK").status_code == 400
    assert a.put("/api/admin/uploads?filename=e.zip", content=b"").status_code == 400
    monkeypatch.setattr(get_settings(), "upload_max_mib", 0)
    assert a.put("/api/admin/uploads?filename=big.zip", content=b"PK" * 10).status_code == 413


def test_worker_cancel_and_failure(session: Session, monkeypatch: pytest.MonkeyPatch,
                                   env: Path) -> None:
    def slow(ctx: Any, params: dict) -> dict:
        for i in range(400):
            ctx.log(f"tick {i}")
            time.sleep(0.01)
        return {}

    def boom(ctx: Any, params: dict) -> dict:
        raise RuntimeError("parser exploded")

    fake = {"t.slow": JobKind("t.slow", "slow", "", slow),
            "t.boom": JobKind("t.boom", "boom", "", boom)}
    monkeypatch.setattr(registry, "kinds", lambda: fake)
    monkeypatch.setattr(worker, "HEARTBEAT_EVERY", 0.05)
    slow_job = queue.enqueue(session, "t.slow", {}, actor="test")
    boom_job = queue.enqueue(session, "t.boom", {}, actor="test")
    session.execute(text("update jobs set cancel_requested = true where id = :i"),
                    {"i": slow_job.id})
    session.commit()
    w = _worker(session.get_bind())
    assert w.tick() and w.tick()
    session.expire_all()
    assert session.get(Job, slow_job.id).status == "cancelled"
    failed = session.get(Job, boom_job.id)
    assert failed.status == "failed" and failed.error == "RuntimeError: parser exploded"


def test_schedules_enqueue_once(session: Session) -> None:
    queue.sync_schedules(session)
    row = session.get(Schedule, "us-sync-weekly")
    assert row is not None and row.every_hours == 168
    row.next_run_at = queue.now().replace(year=2020)
    session.commit()
    first = queue.run_due_schedules(session)
    assert len(first) == 1
    assert row.next_run_at > queue.now()
    row.next_run_at = queue.now().replace(year=2020)
    session.commit()
    assert queue.run_due_schedules(session) == []  # the first one is still queued


def test_stale_running_job_is_reaped(session: Session) -> None:
    job = queue.enqueue(session, "us.fetch", {}, actor="test")
    job.status = "running"
    job.heartbeat_at = queue.now().replace(year=2020)
    session.commit()
    assert queue.reap_stale(session) == 1
    session.refresh(job)
    assert job.status == "failed"


# ------------------------------------------------------------- private contacts (record 0009)


def test_contacts_are_admin_only_and_every_read_is_audited(client: TestClient, session: Session,
                                                           tmp_path: Path) -> None:
    from north.ingest.ie.load import ingest_list
    from tests.ie_lists import CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE, ilep_v1, write_list

    ingest_list(session, write_list(tmp_path / "ilep.xlsx", ilep_v1()), "ie_ilep")
    a = onboard(client, session, "ana", "admin")
    listed = a.get("/api/admin/institutions?country=IE").json()
    assert {i["id"]: i["contacts"] for i in listed} == {"ie-0901": 1, "ie-0902": 1, "ie-0903": 1}
    assert FAKE_EMAIL not in str(listed)  # the list never carries the contacts themselves
    assert not session.scalars(select(AuditEntry).where(
        AuditEntry.action == "institution_contacts_read")).all()

    r = a.get("/api/admin/institutions/ie-0901/contacts")
    assert r.status_code == 200, r.text
    c = r.json()["contacts"]
    assert [(x["name"], x["email"], x["phone"], x["source"]) for x in c] == [
        (CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE, "ie_ilep")]
    entry = session.scalars(select(AuditEntry).where(
        AuditEntry.action == "institution_contacts_read")).one()
    assert entry.target == "ie-0901" and entry.actor == "ana" and entry.at is not None
    assert FAKE_EMAIL not in str(entry.detail) and CONTACT_NAME not in str(entry.detail)
    assert a.get("/api/admin/institutions/ie-9999/contacts").status_code == 404
    assert a.get("/api/admin/institutions/IE%20X/contacts").status_code == 422

    for name, role in (("cora", "curator"), ("vera", "viewer")):
        u = onboard(client, session, name, role)
        assert u.get("/api/admin/institutions/ie-0901/contacts").status_code == 403
        assert u.get("/api/admin/institutions").status_code == 403
    assert len(session.scalars(select(AuditEntry).where(
        AuditEntry.action == "institution_contacts_read")).all()) == 1
