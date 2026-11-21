"""FastAPI application: JSON API under /api and the Vue build with SPA fallback."""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from north import __version__
from north.api.programs import router as programs_router
from north.repository.db import DatabaseNotConfigured
from north.settings import get_settings

app = FastAPI(
    title="North API",
    version=__version__,
    summary="A map of US master's programs for international students.",
    docs_url=None,  # served below, with its own Content-Security-Policy
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# ----------------------------------------------------------------------- security headers
# Defense in depth: Traefik sets some of these too. No HSTS here, TLS terminates at Traefik.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
_INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.S | re.I)


def inline_script_hashes(html: str) -> list[str]:
    """CSP source expressions (``'sha256-…'``) for every inline ``<script>`` in ``html``."""
    return ["'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
            for body in _INLINE_SCRIPT.findall(html)]


def content_security_policy(script_hashes: Iterable[str] = (), *, script_hosts: str = "",
                            style_extra: str = "", img_extra: str = "") -> str:
    """The SPA policy; the Swagger page adds its CDN through the keyword arguments."""
    script = " ".join(["'self'", *script_hashes, *filter(None, [script_hosts])])
    style = " ".join(filter(None, ["'self'", style_extra]))
    img = " ".join(filter(None, ["'self' data:", img_extra]))
    return (f"default-src 'self'; script-src {script}; style-src {style}; img-src {img}; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
            "form-action 'self'; object-src 'none'")


# Without a web build only the API answers; JSON needs no script at all.
app.state.csp = content_security_policy()


@app.middleware("http")
async def _security_headers(request: Request,
                            call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    # A route may set its own policy (the Swagger page does); the SPA policy is the default.
    response.headers.setdefault("Content-Security-Policy", request.app.state.csp)
    return response


SWAGGER_CDN = "https://cdn.jsdelivr.net"


@app.api_route("/api/docs", methods=["GET", "HEAD"], include_in_schema=False)
def api_docs() -> HTMLResponse:
    """Swagger UI. Only this page may load the Swagger CDN and run its inline bootstrap."""
    page = get_swagger_ui_html(openapi_url=app.openapi_url or "/api/openapi.json",
                               title=f"{app.title} - Swagger UI")
    html = bytes(page.body).decode()
    csp = content_security_policy(inline_script_hashes(html), script_hosts=SWAGGER_CDN,
                                  style_extra=f"{SWAGGER_CDN} 'unsafe-inline'", img_extra="https://fastapi.tiangolo.com")
    page.headers["Content-Security-Policy"] = csp
    return page


app.include_router(programs_router)


@app.exception_handler(DatabaseNotConfigured)
def _no_database(_: Request, __: DatabaseNotConfigured) -> JSONResponse:
    # Generic on purpose: configuration details (variable names) stay out of responses.
    return JSONResponse(status_code=503, content={"detail": "database not configured"})


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check used by Docker, Kubernetes and the web status line."""
    return {"status": "ok", "version": __version__}


def mount_web(application: FastAPI, dist: Path) -> None:
    """Serve the Vue build: hashed assets, loose root files, and index.html for any other path.

    The CSP allows exactly the inline scripts of this build's index.html (the theme script),
    hashed here at startup so the policy never drifts from the file.
    """
    index = (dist / "index.html").read_text(encoding="utf-8")
    application.state.csp = content_security_policy(inline_script_hashes(index))
    assets = dist / "assets"
    if assets.is_dir():
        application.mount("/assets", StaticFiles(directory=assets), name="assets")
    root_files = {f.name for f in dist.iterdir() if f.is_file() and f.name != "index.html"}

    @application.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
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
