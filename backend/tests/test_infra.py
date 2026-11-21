"""Static checks on the deployment files (supply chain, least privilege). No Docker needed."""

from __future__ import annotations

import re

import pytest

from north.settings import Settings
from tests.conftest import REPO


def test_settings_reads_migration_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NORTH_DATABASE_URL", "postgresql+psycopg://north_app@db/north")
    monkeypatch.setenv("NORTH_MIGRATION_DATABASE_URL", "postgresql+psycopg://north_owner@db/north")
    s = Settings()
    assert "north_app" in (s.database_url or "")
    assert "north_owner" in (s.migration_database_url or "")


def test_compose_app_does_not_use_the_superuser() -> None:
    compose = (REPO / "compose.yaml").read_text()
    assert "NORTH_DATABASE_URL: postgresql+psycopg://north_app:" in compose
    assert "NORTH_MIGRATION_DATABASE_URL: postgresql+psycopg://north_owner:" in compose
    assert "unset NORTH_MIGRATION_DATABASE_URL && exec uvicorn" in compose
    assert "./deploy/postgres/init:/docker-entrypoint-initdb.d:ro" in compose
    init = (REPO / "deploy" / "postgres" / "init" / "10-roles.sql").read_text()
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO north_app" in init
    assert "ALTER SCHEMA public OWNER TO north_owner" in init
    assert not re.search(r"(?i)grant\s+(all|create)[^;]*north_app", init)


def test_dockerfile_pins_base_images_by_digest() -> None:
    text = (REPO / "Dockerfile").read_text()
    images = re.findall(r"^FROM\s+(\S+)", text, re.M) + re.findall(r"COPY --from=(\S+/\S+)", text)
    assert len(images) == 3
    for image in images:
        assert re.search(r"@sha256:[0-9a-f]{64}$", image), image
    assert "npm ci --ignore-scripts" in text


def test_workflow_least_privilege_and_pinned_actions() -> None:
    wf = (REPO / ".github" / "workflows" / "imagem.yml").read_text()
    assert re.search(r"^permissions:\n  contents: read$", wf, re.M)
    for ref in re.findall(r"uses:\s*(\S+)", wf):
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", ref), ref
    assert wf.count("persist-credentials: false") == wf.count("actions/checkout@")
    assert "github.ref == 'refs/heads/main'" in wf
    assert re.search(r"--with jsonschema==\d+\.\d+\.\d+ ", wf)
