<p align="center"><img src="web/public/sigil-north.svg" width="72" height="72" alt="North sigil"></p>

# North

*A map of US master's programs for international students.*

North maps, verifies and compares on-campus master's programs in the US from the point of view of someone who needs an F-1 visa and brings dependents. Every data point carries its source, date and verification status, so unknown data is never confused with negative data.

> **Not immigration advice; check the official source.**

**Status: pre-alpha.** Only the code skeleton exists (Phase 3 of the [execution plan](docs/execution-plan.md)): a FastAPI backend with `/api/health`, a Vue 3 web shell with four UI languages, Docker and CI. No program data is served yet. The first pilot state is Texas.

## Run it

Requires Docker with Compose.

```sh
docker compose up --build
```

Then open <http://localhost:8000/>. The API health check is at <http://localhost:8000/api/health> and the OpenAPI docs at <http://localhost:8000/api/docs>.

Compose also starts PostgreSQL 17 (published on `127.0.0.1:5436`, data in the named volume `north_north-db`). The app does not use it yet; it arrives in Phase 5. Override the host ports with `NORTH_HOST_PORT` and `NORTH_DB_HOST_PORT` if they are taken. `docker compose down` keeps the volume; `docker compose down -v` deletes it.

## Development

Backend (Python 3.12, [uv](https://docs.astral.sh/uv/)):

```sh
cd backend
uv sync
uv run uvicorn north.api.app:app --reload --port 8000
uv run ruff check . && uv run pytest
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
