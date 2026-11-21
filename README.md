<p align="center"><img src="web/public/sigil-north.svg" width="72" height="72" alt="North sigil"></p>

# North

*A map of US master's programs for international students.*

North maps, verifies and compares on-campus master's programs in the US from the point of view of someone who needs an F-1 visa and brings dependents. Every data point carries its source, date and verification status, so unknown data is never confused with negative data.

> **Not immigration advice; check the official source.**

**Status: pre-alpha.** The first data slice works locally: 132 master's programs in Texas (computing, data science, data and business analytics, information systems) loaded from official files (IPEDS, the DHS STEM list, SEVP, DAPIP), served by `/api/programs` and shown in a list and detail view in four UI languages. Fields that only exist on each program's site (English minimums, funding, deadlines, program tuition) show as "not yet collected" until the manual pilot and LLM-assisted extraction. See the [execution plan](docs/execution-plan.md).

## Run it

Requires Docker with Compose.

```sh
docker compose up --build
```

Then open <http://localhost:8000/>. The API health check is at <http://localhost:8000/api/health> and the OpenAPI docs at <http://localhost:8000/api/docs>.

Compose also starts PostgreSQL 17 (published on `127.0.0.1:5436`, data in the named volume `north_north-db`). The app applies the migrations (`alembic upgrade head`, as the schema owner `north_owner`) and then serves as `north_app`, a role that may only read and write rows; both roles are created by `deploy/postgres/init/10-roles.sql` when the volume is first initialized (passwords: `NORTH_OWNER_DB_PASSWORD`, `NORTH_APP_DB_PASSWORD`, local defaults otherwise). A volume created before that script existed has no such roles: run `deploy/postgres/adopt-existing.sql` once (commands at the top of the file), or re-initialize it with `docker compose down -v` (deletes the local data) and load the sample again. Override the host ports with `NORTH_HOST_PORT` and `NORTH_DB_HOST_PORT` if they are taken. `docker compose down` keeps the volume; `docker compose down -v` deletes it.

### Load the sample data

The programs API (`/api/programs` with filters and `sort`/`order`, `/api/programs/{id}`, `/api/facets`, `/api/sources`; contract v0.2 in [docs/api/programs-v0.md](docs/api/programs-v0.md)) serves what was ingested from the official files: IPEDS HD/C_A/IC_AY, the DHS STEM list, the SEVP certified school list and the DAPIP export. Download them once into `spikes/_raw/` (git-ignored; each `docs/sources/<source>.md` has a "Local sample" section with the URLs and paths), then:

```sh
docker compose up -d --build
scripts/load_local_sample.sh        # STATE=TX by default; about 2 minutes (the SEVP PDF is parsed)
curl 'http://localhost:8000/api/programs?cip_family=11&limit=3'
curl 'http://localhost:8000/api/programs?sort=tuition&order=asc&limit=3'   # cheapest first, unknown tuition last
curl 'http://localhost:8000/api/facets'                                  # counts for the filter panel
```

The loader runs inside the app image with the files mounted read-only. Re-running it is safe: a file already ingested for the same state is skipped (idempotent on source + sha256; for the DHS list the digest covers the CSV and its `.meta.json`). If the official DHS PDF is in `spikes/_raw/dhs_stem/` (or `DHS_PDF` points at it), its sha256 is checked against the meta's `file_sha256` and a mismatch is refused. Per-source commands: `uv run python -m north.ingest.us.cli --help`.

## Development

Backend (Python 3.12, [uv](https://docs.astral.sh/uv/)):

```sh
cd backend
uv sync
export NORTH_DATABASE_URL=postgresql+psycopg://north:<password>@127.0.0.1:5436/north
uv run alembic upgrade head
uv run uvicorn north.api.app:app --reload --port 8000
uv run ruff check . && uv run pytest
```

Database tests (ingestion of the synthetic files in `backend/tests/fixtures/`, and the API) need `NORTH_TEST_DATABASE_URL`, a database they may wipe; without it they are skipped with a message. One way, on the compose database:

```sh
docker compose exec -T db psql -U north -d north \
  -c "CREATE ROLE north_test LOGIN PASSWORD 'north-test'" -c "CREATE DATABASE north_test OWNER north_test"
NORTH_TEST_DATABASE_URL=postgresql+psycopg://north_test:north-test@127.0.0.1:5436/north_test uv run pytest
```

Web (Node 22.18 or later):

```sh
cd web
npm ci
npm run dev          # http://localhost:5173/, proxies /api to http://127.0.0.1:8000
npm run test -- --run
npm run build        # web/dist, served by the backend when present
```

Schema validation: `uv run --with jsonschema python -I schema/validate.py`.

Settings are environment variables with the `NORTH_` prefix; see [`.env.example`](.env.example).

## Layout

| Path | Content |
|---|---|
| `backend/north/` | `api` (FastAPI), `domain` (pure rules, `countries/us`), `repository`, `ingest/us`, `extract`; dependency rules in [UML §6](docs/uml-model.md) |
| `web/` | Vue 3 + Vite + TypeScript + vue-i18n; locales `en` (source), `es`, `pt-BR`, `zh-Hans` |
| `schema/` | program JSON Schema and its validator |
| `data/reference/` | versioned reference data (DHS STEM list, CIP → ISCED-F) |
| `docs/` | [requirements](docs/requirements.md), [UML model](docs/uml-model.md), [execution plan](docs/execution-plan.md), [decision records](docs/decisions/), [sources](docs/sources/), [methodology](docs/methodology/) |

## Translations

English is the source language. The `es`, `pt-BR` and `zh-Hans` files in `web/src/locales/` are machine translated (marked with `"_meta": {"machine_translated": true}`) and await review by native speakers. A test fails if any locale misses a key from `en`.

## License

Code: [GNU AGPL-3.0](LICENSE). Data in `data/` and curated program data: [CC BY 4.0](DATA_LICENSE.md). Contributions: see [CONTRIBUTING.md](CONTRIBUTING.md).
