---
name: run-checks
description: Run North locally and every check (backend lint and tests, web tests and build, schema validation, Docker smoke test). Use before finishing any change, when asked to "run the tests", "check everything", "does it still work", or to start the app locally.
---

# Run North and its checks

Run from the repository root. Stop at the first failure, show the output and fix the cause; do not skip a step silently.

## 1. Backend

```sh
cd backend
uv sync
uv run ruff check .
uv run pytest
```

`test_architecture.py` fails if `north/domain` imports from `api`, `repository`, `ingest` or `extract`. Move the code; do not weaken the test.

## 2. Schema

```sh
uv run --with jsonschema python -I schema/validate.py
uv run --with jsonschema python -I schema/csv_to_json.py --self-test
uv run --with jsonschema --with pyyaml python -I schema/validate_placement.py
```

The last line checks the placement item bank (`data/placement/items/*.yaml`, record 0008/T21): schema, unique ids, one `bank_version`, at least 4 items per band.

The validator checks the example and a set of documents that must be rejected (for example a confirmed value without a source). If you changed the schema, regenerate the pilot spreadsheet header: `uv run --with jsonschema python -I schema/csv_to_json.py --print-header > docs/methodology/pilot-template.csv`.

## 3. Web

```sh
cd web
npm ci
npm run test -- --run
npm run build
```

The locale test fails if a language misses a key from `en`, has a key `en` does not have, or lacks its `_meta` translation status.

## 4. Docker smoke test

```sh
docker compose up -d --build
curl -fsS http://localhost:8000/api/health
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:8000/en/
docker compose down
```

Ports can be changed with `NORTH_HOST_PORT` and `NORTH_DB_HOST_PORT`. `docker compose down` keeps the database volume; only use `down -v` if the user asks to delete it.

## Report

Say which steps ran and passed, which failed (with the error) and which you could not run and why.
