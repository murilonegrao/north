"""Alembic environment.

URL: ``-x url=...``, else ``NORTH_MIGRATION_DATABASE_URL`` (the schema owner), else
``NORTH_DATABASE_URL``.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from north.repository.models import Base
from north.settings import get_settings

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    settings = get_settings()
    url = (context.get_x_argument(as_dictionary=True).get("url")
           or config.get_main_option("sqlalchemy.url")
           or settings.migration_database_url or settings.database_url)
    if not url:
        raise RuntimeError("set NORTH_MIGRATION_DATABASE_URL or NORTH_DATABASE_URL")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
