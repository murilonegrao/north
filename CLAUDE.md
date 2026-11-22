# North — notes for coding agents

North maps US master's programs for international students who bring their families. Every value shown to a user carries its source, date and verification status. Read `README.md` first; the planning documents are in `docs/`.

## Ground rules

- **English only** in code, comments, docs, commit messages and file names. UI text goes through i18n (`web/src/locales/`).
- **No personal data in the repo.** No names, emails, phone numbers or private correspondence, including contact fields found in official files. Contacts from official lists (ILEP, TrustEd, DAPIP, IPEDS HD) are kept only in the private `institution_contacts` table, admin-only and audited, never in public fields, exports, logs or the repo; test fixtures use made-up contacts (record 0009). Email replies from international offices are stored privately; the public side only says "written reply from the international office, <date>" and may quote one sentence (record 0002/K9).
- **Never read, print or commit `.env`.** Use `.env.example` for variable names.
- **Unknown is never negative** (BR-02). Only `confirmed_negative` fails the filter by itself. Do not turn a missing value into `false` or `0`.
- **Decision records win.** If `docs/requirements.md` or `docs/uml-model.md` disagree with `docs/decisions/`, the newest decision record is right. New decisions get a new record (skill `decision-record`).
- **Official sources only.** Government data or the program's own site. Rankings and aggregators are leads, never sources, and are never scraped (C-05).

## Where things are

| Need | Look at |
|---|---|
| What the system must do | `docs/requirements.md` (SRS; FR, NFR, BR, C) |
| Model, flows, tables | `docs/uml-model.md` (diagrams in Mermaid) |
| Why a choice was made | `docs/decisions/0001…` |
| Phases and what is next | `docs/execution-plan.md` |
| A data source's format and limits | `docs/sources/<source>.md` |
| The program data contract | `schema/program.schema.json`, example in `schema/examples/` |
| Manual data collection | `docs/methodology/pilot-guide.md` |

## Code layout and rules

- `backend/north/domain/` is pure Python: no imports from `api`, `repository`, `ingest` or `extract`, no I/O. Country-specific rules live in `domain/countries/<country>/` behind a common interface; the core never names a country. `backend/tests/test_architecture.py` enforces the import rule.
- `backend/north/ingest/<country>/` reads **uploaded official files** (FR-26); government sites block scripts, so automatic download is optional.
- Admin area (record 0006): `backend/north/auth/` (passwords, TOTP, sessions), `backend/north/jobs/` (Postgres queue, worker `python -m north.jobs.worker`, registry), `backend/north/api/admin/`, `web/src/admin/` (lazy chunk, en + pt-BR only). Country job kinds live in `ingest/<country>/jobs.py`.
- Email (record 0007): `backend/north/mail/` (outbox, SMTP sender thread of the worker, plain-text templates in `mail/locales/`). The web process only queues; it never talks to SMTP. Links use `NORTH_PUBLIC_URL`, never the request host.
- The web app is Vue 3 + TypeScript. CSS uses logical properties (`margin-inline`, not `margin-left`) so right-to-left languages work.
- Visual identity is **A Forja** (record 0003): one accent, ember `#D96C2C`; tokens in `web/src/styles/tokens.css`. Do not add colors; fix the hierarchy instead.

## Checks before you finish

Use the `run-checks` skill, or run:

```sh
cd backend && uv run ruff check . && uv run pytest
cd web && npm run test -- --run && npm run build
uv run --with jsonschema python -I schema/validate.py
uv run --with jsonschema --with pyyaml python -I schema/validate_placement.py
```

## Project skills

In `.claude/skills/`: `run-checks`, `curate-program`, `add-translation`, `add-data-source`, `decision-record`.
