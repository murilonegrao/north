"""Runtime settings, read from environment variables with the ``NORTH_`` prefix."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NORTH_", extra="ignore")

    # PostgreSQL URL (SQLAlchemy format) used by the API and the loaders: a DML-only role
    # (north_app in compose.yaml).
    database_url: str | None = None
    # URL of the role that owns the schema (north_owner), used only by Alembic migrations.
    # When unset, migrations fall back to database_url (a single-role setup, e.g. tests).
    migration_database_url: str | None = None
    # Directory of the Vue build. When unset, the usual locations are tried (see web_dist_dir).
    web_dist: Path | None = None

    # ---- Admin area (docs/design/admin-and-sync.md, record 0006)
    # Raw official files (worker only): fetched or accepted uploads, never overwritten.
    raw_dir: Path | None = None
    # Uploads land here first (the web process writes only here; the worker moves them).
    incoming_dir: Path | None = None
    # Largest upload accepted, in MiB (Cloudflare cuts request bodies at 100 MB).
    upload_max_mib: int = 95
    # Session cookie: Secure and the __Host- prefix. Turn off only for plain-http local runs.
    cookie_secure: bool = True
    # A second factor (TOTP) is required before any admin action. Off only for local runs.
    admin_require_totp: bool = True
    session_idle_minutes: int = 120
    session_max_hours: int = 12
    # Request header that carries the client address set by the edge proxy (for example
    # cf-connecting-ip behind Cloudflare). Unset: the TCP peer address is used.
    client_ip_header: str | None = None
    # Shown as the issuer in authenticator apps.
    totp_issuer: str = "North admin"

    def web_dist_dir(self) -> Path | None:
        """Return the first existing Vue build directory, or None if there is none."""
        if self.web_dist is not None:
            return self.web_dist if self.web_dist.is_dir() else None
        here = Path(__file__).resolve()
        # Image layout: /app/north/settings.py -> /app/web/dist
        # Source tree:  <repo>/backend/north/settings.py -> <repo>/web/dist
        for candidate in (here.parents[1] / "web" / "dist", here.parents[2] / "web" / "dist"):
            if candidate.is_dir():
                return candidate
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
