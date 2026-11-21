-- For a database initialized before init/10-roles.sql existed (objects owned by the superuser).
-- Run once as the superuser, after creating the roles (init/10-roles.sql with the same env vars):
--   docker compose exec -T -e NORTH_OWNER_DB_PASSWORD=... -e NORTH_APP_DB_PASSWORD=... db \
--     psql -U north -d north -f - < deploy/postgres/init/10-roles.sql
--   docker compose exec -T db psql -U north -d north -f - < deploy/postgres/adopt-existing.sql
-- It moves every table (and its owned sequences) in public to north_owner and grants the app
-- DML on what already exists; later objects are covered by the default privileges.

\set ON_ERROR_STOP on

DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO north_owner', t.tablename);
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO north_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO north_app;
