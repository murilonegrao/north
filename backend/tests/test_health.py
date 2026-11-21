from fastapi.testclient import TestClient

from north import __version__
from north.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_openapi_docs() -> None:
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").json()["info"]["title"] == "North API"


def test_spa_fallback(tmp_path) -> None:
    from fastapi import FastAPI

    from north.api.app import mount_web

    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)")
    (tmp_path / "index.html").write_text("<!doctype html><div id=app></div>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    web = FastAPI()
    mount_web(web, tmp_path)
    c = TestClient(web)

    assert "id=app" in c.get("/pt-br/").text
    assert c.get("/pt-br/").headers["cache-control"] == "no-cache"
    assert c.get("/assets/app-123.js").status_code == 200
    assert c.get("/favicon.svg").text == "<svg/>"
    assert c.get("/api/unknown").status_code == 404
