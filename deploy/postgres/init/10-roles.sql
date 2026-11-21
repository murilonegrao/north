-- Runs once, when the postgres container initializes an empty data directory
-- (/docker-entrypoint-initdb.d). Creates the two roles North uses instead of the superuser:
--   north_owner  owns the schema and its objects; used only by `alembic upgrade head`.
--   north_app    DML only (SELECT, INSERT, UPDATE, DELETE); used by the API and the loaders.
-- Passwords come from the db container environment (compose.yaml). An existing volume is not
-- re-initialized: see adopt-existing.sql, or `docker compose down -v` for a clean local re-init.

\set ON_ERROR_STOP on
\getenv owner_password NORTH_OWNER_DB_PASSWORD
\getenv app_password NORTH_APP_DB_PASSWORD

CREATE ROLE north_owner LOGIN PASSWORD :'owner_password';
CREATE ROLE north_app LOGIN PASSWORD :'app_password';

ALTER SCHEMA public OWNER TO north_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO north_app;

-- Every table and sequence the owner creates (the migrations) is usable by the app, DML only.
ALTER DEFAULT PRIVILEGES FOR ROLE north_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO north_app;
ALTER DEFAULT PRIVILEGES FOR ROLE north_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO north_app;
