"""FastAPI application: JSON API under /api and the Vue build with SPA fallback."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from north import __version__
from north.api.programs import router as programs_router
from north.repository.db import DatabaseNotConfigured
from north.settings import get_settings

app = FastAPI(
    title="North API",
    version=__version__,
    summary="A map of US master's programs for international students.",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


app.include_router(programs_router)


@app.exception_handler(DatabaseNotConfigured)
def _no_database(_: Request, exc: DatabaseNotConfigured) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check used by Docker, Kubernetes and the web status line."""
    return {"status": "ok", "version": __version__}


def mount_web(application: FastAPI, dist: Path) -> None:
    """Serve the Vue build: hashed assets, loose root files, and index.html for any other path."""
    assets = dist / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=assets), name="assets")
    root_files = {f.name for f in dist.iterdir() if f.is_file() and f.name != "index.html"}

    @application.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        # Loose files at the build root (favicon and similar); simple names only.
        if path in root_files:
            return FileResponse(dist / path)
        # The shell is never cached: files under /assets carry a hash in their name, it does not.
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})


_dist = get_settings().web_dist_dir()
if _dist is not None:
    mount_web(app, _dist)
