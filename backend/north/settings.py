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
