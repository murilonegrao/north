---
title: "Execution Plan — North"
type: execution-plan
project: north
version: 4
status: approved
language: en
created: 2026-11-20
updated: 2026-11-21
base: [requirements.md v1.3, uml-model.md (being closed as 1.0), decisions/0002-after-data-spikes.md]
---

# Execution Plan — North

This plan turns SRS 1.3 into deliverables that fit **one part-time developer** (C-06). The principle is the same as in the SRS: first one complete, reliable pilot state, then scale. The order is **requirements → UML → code structure → implementation**.

> [!note] Version 4
> Applies decision record 0002 (`docs/decisions/0002-after-data-spikes.md`, R1–R18 and A1–A16) and SRS 1.3: CIPs include 30.71 (52.12 kept, flagged); IPEDS first, official files by upload (FR-26), SEVP reconciliation, localities and rent benchmarks; refreshed next steps. Version 3 was the English translation of version 2.

## Decisions that shape the plan (SRS §3.4)

| Decision | Effect on the plan |
|---|---|
| **A1** curation in the database, with a screen and login | the MVP gets login (FR-25), an edit screen and a history table (FR-09); the database becomes the only copy of curated data, so **backup becomes a prerequisite** (NFR-16) |
| **A2** other countries in the structure only | generic model (identifiers, classification, authorization, eligibilities and currency per scheme; rules in one module per country, C-09), but only the `us` module is implemented |
| **A3** research reports outside the repo | the public repo starts with only the SRS, UML, plan and ADRs |
| **Q01** public data · **Q03** profile in the browser | search open without login; the API evaluates without storing the profile |
| **Q04** pilot in **Texas** | a large state: the manual pilot uses a sample; v0.1 may cover a slice that satisfies BR-11 |
| **Q05 + R2** CIPs 11.xx, 52.12xx, 30.70xx, 30.71xx | four CIP families in the first ingestion; 52.12xx flagged `no_stem_opt_extension` (R1) |
| **Q06/Q06b** multilingual UI, most common languages first | `vue-i18n` in the first frontend commit; wave 1 (v0.1) en, es, pt-BR, zh-Hans; wave 2 hi, fr, ar, vi, ko, ja; more on demand (NFR-14) |
| **Q07** configurable LLM · **Q08** internal pages | extractor with the provider set by environment variable; the API serves only the evidence excerpt |
| **Q11** AGPL-3.0 + CC BY 4.0 | `LICENSE` and `DATA_LICENSE` in the first commit |
| **Record 0002** (R1–R18, A1–A16) | IPEDS is the primary discovery source and Scorecard is enrichment (R3); official files are uploaded by the admin (FR-26, R4); SEVP is matched by name + city with reconciliation tasks (R5); new `localities`, `campuses`, `rent_benchmarks`, `source_files` tables (R17, R4); ECB rates (R8); score with neutral 50, range and certainty (R16) |
| **D1–D7** deployment | app `north` following the `k3s-gitops` pattern, single public image, database through Crossplane, indexable, live from Phase 3, ingestion by CronJob |

---

## Phase 0 — Decisions ✅ (2026-11-20)

Questionnaire answered; SRS at baseline 1.0. Q09 and Q10 were answered by the Phase 2 spikes, and the decisions they opened (R1–R18) are in `docs/decisions/0002-after-data-spikes.md` (SRS 1.3).

## Phase 1 — UML modeling (1 week) ← **now**

> **Status (2026-11-21):** the decisions R1–R18 (and the changes A1–A16) are in `docs/decisions/0002-after-data-spikes.md`; the record is the source of names for the SRS, the UML and the schema. The UML is being updated with them and closed as version 1.0 (new `localities`, `campuses`, `source_files`, `rent_benchmarks`; `source_kind` on `VerifiedValue`; `score_range` and `certainty` on `Evaluation`; IPEDS-first ingestion sequence).

The draft is in `uml-model.md`, with 8 Mermaid diagrams:

1. Use cases (with UC11 login, new because of A1)
2. Domain classes (`VerifiedValue` as the central piece)
3. States: data status, extraction review, state coverage
4. Activities: the elimination filter with pass / fail / undetermined
5. Sequences: ingestion, profile simulation, curation, extraction review
6. Components (rule: `domain` depends on nothing)
7. Deployment on k3s
8. Physical model (ER) of Postgres

What is left in this phase:
- **Review the diagrams with the author**, especially the domain (2), the filter (4) and the ER (8), which are the most expensive to change later.
- **Define the score formula per criterion** (BR-05): how "cost" or "funding" become 0–100. Proposal in `docs/methodology/score-proposal.md`; neutral 50 and funding in the cost decided (R15, R16), bands to calibrate with pilot data.
- **Check rendering on GitHub.** The Mermaid syntax was checked by hand but has not been rendered yet.
- Close version 1.0 of the model.

**Exit criterion:** every Must FR in the SRS appears in at least one diagram, and the diagram names become the names of tables, modules and endpoints.

## Phase 2 — Data spikes ✅ (2026-11-21)

> **Done.** Q09: yes, but IPEDS is needed for the 6-digit CIP and graduate tuition. Q10: SEVP is a PDF only; 95 of 110 Texas graduate institutions (86%) match exactly by name + city, and the rest go to reconciliation. 52.12 is not on the STEM list; 30.71 is. Government sites block scripts. Results in `spikes/*/RESULT.md` and `docs/sources/`; the decisions they opened (R1–R18) were accepted in `docs/decisions/0002-after-data-spikes.md`.

Throwaway scripts in `spikes/` + one note in `docs/sources/<source>.md` each.

| Spike | Question | What it changes |
|---|---|---|
| S-1 Scorecard | does the *field of study* data for master's (`credential.level = 5`) cover Texas in the target CIPs? | Q09; UML sequence 5.1 |
| S-2 IPEDS | completions by UNITID × CIP × master's; graduate tuition | main source, if S-1 fails |
| S-3 DHS STEM list | format (PDF), current version, reproducible parser | `eligibility_rules` |
| S-4 SEVP | download of the certified school list? does it match UNITID/OPEID? | Q10; FR-04 automatic or curation |
| S-5 DAPIP | accreditation and join key | FR-05 |
| S-6 HUD FMR | rent by county and bedrooms; county ↔ campus city | living cost (BR-07) |

**Exit criterion:** know how many Texas master's programs automatic discovery finds and what fraction matches SEVP and STEM without a human. If the answer changes the UML, update it before Phase 3.

## Phase 3 — Code structure and first deployment (1 week)

> **Status (2026-11-21):** the local skeleton exists (backend, web, Dockerfile, compose, CI; health at `/api/health`); it runs with `docker compose up --build`, not deployed yet.

Starts only with UML 1.0. The structure follows the component diagram:

```
north/
├── README.md · LICENSE (AGPL-3.0) · DATA_LICENSE (CC BY 4.0) · CONTRIBUTING.md
├── docs/            SRS, UML model, decisions/ (decision records), sources, methodology
├── schema/          program JSON Schema (VerifiedValue envelope + dimensions)
├── data/reference/  versioned STEM list, CIP table, initial immigration rules
├── backend/         uv, FastAPI, SQLAlchemy, Alembic
│   └── north/
│       ├── domain/      filter, score, cost, risk (pure, no I/O)
│       ├── api/         routes, curator auth
│       ├── repository/
│       ├── ingest/us/
│       └── extract/     (empty until Phase 8)
├── web/             Vue 3 + Vite + TS + vue-i18n
├── Dockerfile       two stages: Vue build → Python image
├── compose.yaml     postgres + app (NFR-12)
└── .github/workflows/imagem.yml   jobs testes and imagem, the cluster's standard CI
```

**First deployment (D6)**, following the checklist in `k3s-gitops` `docs/app-nova.md`:
1. Public repository `murilonegrao/north`; public image `ghcr.io/murilonegrao/north` (D4).
2. `manifests/north/` from the cluster's app template: Deployment **without** initContainer and with no database yet, Service, Ingress `north.harpia.info`, headers middleware **without** `noindex` (D5).
3. `app.yaml` with `imagens: north=ghcr.io/murilonegrao/north`.
4. Check: a push to `main` brings `/health` live on its own.

**Deliverable:** `https://north.harpia.info/health` responding, with green CI and automatic deployment.

## Phase 4 — Manual pilot in Texas (2–3 weeks, starts together with Phase 2)

1. ~20 Texas master's programs in the four CIP families (11.xx, 52.12xx, 30.70xx, 30.71xx), chosen for variety: public and private, large and small, with and without known funding. The candidate list is `docs/methodology/pilot-candidates.csv` and the procedure is `docs/methodology/pilot-guide.md`.
2. Fill in a spreadsheet using the schema field names (or directly in JSON validated by the schema). A script imports it into the database in Phase 5.
3. For each field, note where it was, whether it was there and how long it took.
4. At the end: schema v1, the list of fields that only come by email from the international office, and an estimate of what the LLM will be able to extract.

**Deliverable:** real data for ~20 programs and `docs/methodology/pilot-report.md`.

## Phase 5 — Backend MVP (4–5 weeks)

One week more than in the previous plan, because of curation with login (A1).

| Block | Requirements | Content |
|---|---|---|
| 5.1 Model | BR-01, C-03, C-09 | ER tables (UML §8, already generic per country), Alembic migrations; database through Crossplane (D3), migration initContainer as in the other apps on the cluster |
| 5.2 Domain | FR-18–21, BR-02–08, BR-17 | core (aggregation, score with neutral 50, range and certainty, cost with guaranteed vs competitive funding and ECB exchange rate) + `domain/countries/us` (criteria, `us.stem_opt`, risk, F-2 rule); each box in the activity diagram becomes a test |
| 5.3 Ingestion | FR-02, 26, 03, 04, 05, 06, 01, 07 | UML §5.1, in this order: **(1) uploads** — official file upload in the curation screen, `source_files` with sha256, idempotent on (source, sha256) (FR-26, R4); **(2) IPEDS first** — `C<year>_A`, `HD<year>`, `IC<year>_AY` create institutions, campuses and programs by UNITID × 6-digit CIP (FR-02, R3); then the DHS STEM rule in `eligibility_rules` (FR-03, BR-17); **(3) SEVP reconciliation** — parse the PDF, match by `campuses.sevp_campus_code`, else name + city, exact automatic and the rest as `reconciliation_tasks` (FR-04, R5); DAPIP institutional accreditation, contacts dropped (FR-05); **(4) localities and rent** — `localities` (`us_county_fips`) from IPEDS `COUNTYCD`, HUD FMR county file into `rent_benchmarks` (FR-06, R6, R7); ECB rates into `fx_rates` (R8); then Scorecard FoS enrichment by UNITID + CIP4 (FR-01). Every run records `ingestion_runs.source_file_id` (FR-07). Automatic download optional per source; CronJob `north-ingest` (D7) only for sources that allow it (ECB) |
| 5.4 Curation | FR-08, 09, 25 | single-account login, `PATCH` with source validation (`source_kind`, BR-15; correspondence stored privately), `field_changes` in the same transaction (UML §5.3); reconciliation task queue |
| 5.5 Pilot importer | — | loads the Phase 4 data as `reported_by_program` with source |
| 5.6 Public API | FR-16, 17, 20, 23, 24 | `GET /programs`, `GET /programs/{id}`, `POST /evaluate` (no storage), CSV, `GET /states/{id}/coverage` |

**Prerequisites in `k3s-gitops`:** step 4 (Sealed Secrets, for `north-env`) and step 5 (Crossplane, for the database). **Postgres server backup with a restore test** (NFR-16) before the first curated data enters production. It needs to move up in priority in the platform roadmap.

## Phase 6 — Frontend MVP (3–4 weeks)

1. **Profile**, saved in the browser and shareable by link.
2. **List** with filters and one badge per dimension in three distinct visuals: confirmed, unknown and negative (NFR-05).
3. **Detail**: each value with source, date and status; notice of the current immigration rule (FR-24); stable URL, its own title and description for indexing (NFR-15).
4. **Comparison** of 2–5 programs.
5. **Curation**: login, field editing with source (including `source_kind`) and history, official file upload (FR-26), reconciliation task queue (SEVP matches).
6. State **coverage**.
7. i18n with vue-i18n and lazy-loaded locale files; wave-1 languages (en, es, pt-BR, zh-Hans) complete for v0.1; RTL-ready CSS (logical properties) from the start; translation platform set up before v0.1.
8. On every screen: "this is not immigration advice" notice (NFR-11), minimum width of 360 px, axe checks (NFR-06), strings only through i18n (NFR-14). Sitemap.

## Phase 7 — Release v0.1 "Texas" (1 week)

- The chosen Texas slice satisfies the BR-11 checklist.
- Manual review of a sample of the ingested data.
- Dump of curated data published with the release (FR-23, CC BY 4.0).
- Issue templates: "wrong data", "new program", "new state".
- Announce it in communities of Brazilians planning to study abroad.

**Up to here: ~15 weeks part time.**

## Phase 8 — LLM-assisted extraction (v0.2, 3–4 weeks)

FR-12 to FR-15, NFR-04, NFR-13, UML §3.2 and §5.4.
- Polite crawler: robots.txt, 1 req/s per domain, only `.edu` and official domains.
- Configurable LLM provider (Q07); *structured output* in the schema, with an evidence excerpt per field and a cost cap per run.
- Review queue in the curation screen, which already exists from Phase 6.
- The ~20 pilot programs become the *gold set* for measuring extractor precision before using it in another state.

## Phase 9 — Scale (ongoing)

More states, other CIPs, wave-2 UI languages and beyond (NFR-14), periodic re-verification of immigration rules and, if a contributor or a concrete need appears, a second country.

---

## Schedule

```
Week:        1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
F1 UML      ████
F2 Spikes   ████
F3 Struct.      ████
F4 Pilot    ████████████
F5 Backend              ████████████████████
F6 Front                            ████████████████
F7 v0.1                                             ████
                                                       ▲ v0.1 Texas
k3s-gitops  ··step 4··step 5··Postgres backup··   (F5 prerequisites)
```

## Execution risks

| Risk | Mitigation |
|---|---|
| UML becomes an end in itself | one week, with an objective exit criterion (every Must FR covered) |
| Spikes show low automatic coverage | the manual pilot already produces useful data; ingestion becomes a suggestion and curation decides |
| Government sites block scripted downloads | ingestion runs on files the admin uploads (FR-26); automatic download is optional per source |
| Texas too large for v0.1 | an explicit slice (for example, public institutions first), declared in the coverage dashboard |
| `k3s-gitops` steps 4/5 are delayed | Phase 3 does not depend on them; Phase 5 can start with a local database in compose |
| Loss of curated data | backup with a tested restore before production, plus the per-release dump |

## Immediate next steps

1. Author review of the open items from record 0002: the 7 proposed CIP → ISCED-F rows (R9) and the immigration risk criteria in `docs/methodology/score-proposal.md` §4 (A10).
2. Start the manual pilot (Phase 4) with `docs/methodology/pilot-candidates.csv`, following `docs/methodology/pilot-guide.md`; check by hand the Texas institutions with no SEVP match.
3. Close `uml-model.md` as 1.0 with the record 0002 names; then start Phase 3 (code structure and first deployment).
4. In `k3s-gitops`: continue with step 4.1 (Sealed Secrets) and queue the Postgres backup before Phase 5.
