"""Input limits, LIKE escaping, error messages, security headers and the country registry."""

from __future__ import annotations

import ast
import base64
import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import north
from north.api.app import app, inline_script_hashes, mount_web
from north.repository.db import DatabaseNotConfigured, session_scope
from north.repository.models import Program


@pytest.fixture
def no_db() -> Iterator[TestClient]:
    """A client whose session dependency must never be used (validation fails first)."""
    def override() -> Iterator[None]:
        yield None

    app.dependency_overrides[session_scope] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client(session: Session, loaded: dict) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[session_scope] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------- validation (no DB)

@pytest.mark.parametrize("qs", [
    "offset=100001", "offset=9223372036854775808", "offset=-1",
    "q=a%00b", "city=Aus%00tin", "q=" + "x" * 201,
])
def test_list_rejects_bad_parameters(no_db: TestClient, qs: str) -> None:
    assert no_db.get(f"/api/programs?{qs}").status_code == 422


@pytest.mark.parametrize("pid", ["abc", "900001_110701", "900001-110701%00", "%00", "IE-ILEP-1",
                                 "a-b-c-d-e-f-g", "x" * 13 + "-1", "-900001", "900001-"])
def test_program_id_pattern(no_db: TestClient, pid: str) -> None:
    assert no_db.get(f"/api/programs/{pid}").status_code == 422


@pytest.mark.parametrize("qs", ["limit=0", "limit=501", "limit=x"])
def test_sources_limit_bounds(no_db: TestClient, qs: str) -> None:
    assert no_db.get(f"/api/sources?{qs}").status_code == 422


def test_503_does_not_name_the_variable() -> None:
    def override() -> Iterator[None]:
        raise DatabaseNotConfigured("NORTH_DATABASE_URL is not set")
        yield None

    app.dependency_overrides[session_scope] = override
    try:
        r = TestClient(app).get("/api/programs")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json() == {"detail": "database not configured"}
    assert "NORTH_" not in r.text


# ----------------------------------------------------------------------- security headers

COMMON = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "same-origin",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
}


def _directives(csp: str) -> dict[str, str]:
    return {d.split(" ", 1)[0]: d.split(" ", 1)[1] for d in (p.strip() for p in csp.split(";"))}


def test_api_responses_carry_security_headers() -> None:
    r = TestClient(app).get("/api/health")
    for name, value in COMMON.items():
        assert r.headers[name] == value
    assert "strict-transport-security" not in r.headers  # TLS terminates at Traefik
    csp = _directives(r.headers["content-security-policy"])
    assert csp["default-src"] == "'self'"
    assert csp["frame-ancestors"] == "'none'"
    assert "unsafe-inline" not in csp["script-src"] and "unsafe-inline" not in csp["style-src"]


def test_spa_csp_hashes_the_inline_theme_script(tmp_path: Path) -> None:
    script = "\n  document.documentElement.dataset.theme = 'dark'\n"
    (tmp_path / "index.html").write_text(
        f"<!doctype html><head><script>{script}</script>"
        '<script type="module" src="/assets/app.js"></script></head><div id=app></div>')
    web = FastAPI()
    web.state.csp = ""
    mount_web(web, tmp_path)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert web.state.csp.count("'sha256-") == 1
    assert f"script-src 'self' 'sha256-{digest}';" in web.state.csp
    d = _directives(web.state.csp)
    assert d == {"default-src": "'self'", "script-src": f"'self' 'sha256-{digest}'",
                 "style-src": "'self'", "img-src": "'self' data:", "font-src": "'self'",
                 "connect-src": "'self'", "frame-ancestors": "'none'", "base-uri": "'self'",
                 "form-action": "'self'", "object-src": "'none'"}


def test_real_build_hash_matches_index_html() -> None:
    index = Path(north.__file__).resolve().parents[2] / "web" / "dist" / "index.html"
    if not index.is_file():
        pytest.skip("no web build")
    hashes = inline_script_hashes(index.read_text(encoding="utf-8"))
    assert len(hashes) == 1  # the theme script; module scripts have src=


def test_docs_page_policy_allows_only_the_swagger_cdn() -> None:
    r = TestClient(app).get("/api/docs")
    assert r.status_code == 200
    d = _directives(r.headers["content-security-policy"])
    assert "https://cdn.jsdelivr.net" in d["script-src"]
    assert "unsafe-inline" not in d["script-src"]
    assert d["script-src"].count("'sha256-") == 1  # the Swagger bootstrap script
    assert d["frame-ancestors"] == "'none'"
    assert r.headers["x-frame-options"] == "DENY"
    # The SPA and the API keep the strict policy.
    spa = TestClient(app).get("/api/health").headers["content-security-policy"]
    assert "cdn.jsdelivr.net" not in spa


# ----------------------------------------------------------------------- country registry

def test_registry_resolves_the_state_country() -> None:
    from north.domain.countries import (
        country_of_subdivision,
        country_of_subdivision_id,
        rules_for,
    )

    assert country_of_subdivision("tx") == "US"
    assert country_of_subdivision_id("US-TX") == "US"
    us = rules_for("us")
    assert us.subdivision_id("tx") == "US-TX"
    assert us.local_subdivision("US-TX") == "TX"
    assert us.cip_family("11.0701") == "11" and us.cip_family("14.0901") is None
    assert us.program_sources[0] == "ipeds_hd"
    with pytest.raises(KeyError):
        rules_for("ZZ")


def test_api_never_imports_a_country_module() -> None:
    """CLAUDE.md: the core never names a country; it goes through the registry."""
    pkg = Path(north.__file__).parent
    countries = {d.name for d in (pkg / "domain" / "countries").iterdir()
                 if (d / "__init__.py").is_file()}
    assert "us" in countries
    offenders = []
    for file in (pkg / "api").rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
                if node.module == "north.domain.countries":
                    names += [f"{node.module}.{a.name}" for a in node.names
                              if a.name in countries]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            offenders += [f"{file.name}: {n}" for n in names
                          if n.startswith("north.domain.countries.")]
    assert offenders == []


# ----------------------------------------------------------------------- database-backed

def test_search_wildcards_match_literally(client: TestClient, session: Session) -> None:
    def ids(q: str) -> set[str]:
        r = client.get("/api/programs", params={"q": q})
        assert r.status_code == 200, r.text
        return {i["id"] for i in r.json()["items"]}

    assert ids("%") == set() and ids("_") == set() and ids("\\") == set()
    assert len(ids("a")) > 1  # plain search still works
    p = session.get(Program, "900001-110701")
    assert p is not None
    p.name = "Computer Science 100% online_x\\y"
    session.commit()
    assert ids("%") == {"900001-110701"}
    assert ids("_x") == {"900001-110701"}
    assert ids("\\y") == {"900001-110701"}
    assert ids("100%") == {"900001-110701"}


def test_offset_cap_and_sources_limit(client: TestClient) -> None:
    r = client.get("/api/programs?offset=100000")
    assert r.status_code == 200 and r.json()["items"] == []
    assert len(client.get("/api/sources?limit=2").json()) == 2
    assert len(client.get("/api/sources").json()) == 6


def test_valid_unknown_program_id_is_404(client: TestClient) -> None:
    assert client.get("/api/programs/999999-999999").status_code == 404


def test_unregistered_state_matches_nothing(client: TestClient) -> None:
    r = client.get("/api/programs?state=ZZ")
    assert r.status_code == 200 and r.json()["total"] == 0
    f = client.get("/api/facets?state=ZZ").json()
    assert f["total"] == 0 and f["tuition"]["currency"] == "USD"


def test_head_on_spa_and_docs(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<!doctype html><script>1</script><div id=app></div>")
    web = FastAPI()
    mount_web(web, tmp_path)
    r = TestClient(web).head("/en/programs")
    assert r.status_code == 200 and r.content == b""
    docs = TestClient(app).head("/api/docs")
    assert docs.status_code == 200
    assert "cdn.jsdelivr.net" in docs.headers["content-security-policy"]
