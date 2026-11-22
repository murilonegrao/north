---
title: "Execution Plan — North"
type: execution-plan
project: north
version: 5
status: approved
language: en
created: 2026-11-20
updated: 2026-11-22
base: [requirements.md v2.0, uml-model.md 1.1, decisions/0002-after-data-spikes.md, decisions/0008-placement-ireland-all-levels.md]
---

# Execution Plan — North

This plan turns SRS 1.3 into deliverables that fit **one part-time developer** (C-06). The principle is the same as in the SRS: first one complete, reliable pilot state, then scale. The order is **requirements → UML → code structure → implementation**.

> [!note] Version 4
> Applies decision record 0002 (`docs/decisions/0002-after-data-spikes.md`, R1–R18 and A1–A16) and SRS 1.3: CIPs include 30.71 (52.12 kept, flagged); IPEDS first, official files by upload (FR-26), SEVP reconciliation, localities and rent benchmarks; refreshed next steps. Version 3 was the English translation of version 2.

> [!note] Version 5 (record 0008)
> The scope grew to the English placement test, Ireland and every US level and field. The work is cut into four slices, E1–E4, in the order the author chose (0008/T1), after the admin area already built. Each slice ends with something usable; curation stays on demand by slice (T11), so "everything ingested" never means "everything verified".

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

> **Order changed (record 0004, 2026-11-21).** The official-data slice of Phase 5 comes first (database, ingestion of the official files, programs API, list and detail screens). Then the manual pilot, reduced to site-only fields; then LLM-assisted extraction (Phase 8 moves up); then the rest of the backend and frontend MVP and release v0.1. The phases below keep their numbers for reference.

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

### Security before production

Not needed for local runs; all of them block the first public deployment.

- **Security headers:** CSP (`default-src 'self'`, no inline scripts), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS and `frame-ancestors 'none'`, set in a Traefik middleware (or in the app if the ingress cannot).
- **Rate limiting** at the ingress (Traefik `RateLimit` middleware) for `/api`, stricter on login and upload routes.
- **Image scan** in CI: Trivy on the built image, failing on fixable HIGH/CRITICAL, before the push to GHCR.
- **Branch protection on `main`:** pull requests only, the `testes` check required, no force push.
- **GHCR package visibility** decided and set explicitly (public image, or private with an image pull secret in the cluster).
- **FR-26 uploads in a worker**, not in the request: size limit at the ingress, time and memory limits per run, the parsers' existing caps (zip size and ratio, xlsx rows and columns, PDF pages) kept as a second line.
- Database roles as in `compose.yaml`: migrations as the schema owner (initContainer), the API as a DML-only role; no superuser credentials in the app.

**Up to here: ~15 weeks part time.**

## Phase 8 — LLM-assisted extraction (v0.2, 3–4 weeks)

FR-12 to FR-15, NFR-04, NFR-13, UML §3.2 and §5.4.
- Polite crawler: robots.txt, 1 req/s per domain, only `.edu` and official domains.
- Configurable LLM provider (Q07); *structured output* in the schema, with an evidence excerpt per field and a cost cap per run.
- Review queue in the curation screen, which already exists from Phase 6.
- The ~20 pilot programs become the *gold set* for measuring extractor precision before using it in another state.

## Phase 9 — Scale (ongoing)

More states, other CIPs, wave-2 UI languages and beyond (NFR-14), periodic re-verification of immigration rules and, if a contributor or a concrete need appears, a second country.

## Round-3 slices (record 0008)

| Slice | Requirements | Content | Done when |
|---|---|---|---|
| **E1 English placement v0** (2–3 weeks) | FR-28, FR-29, FR-35, NFR-17–19, BR-19, BR-20 | item bank YAML + schema (`data/placement/items/`, `schema/placement-item.schema.json`); about 65 original items; listening scripts and pre-generated audio; scoring in `domain/placement/` (pure); `data/reference/cefr_test_mappings.csv` from `docs/sources/cefr-test-mappings.md`; test and result screens in every wave-1 language; result in the browser with export and retake | the sponsor takes it end to end; the band of 5 people with a recent official score within one half-band (SO6; may close after release) |
| **E2 Ireland English courses** (2 weeks) | FR-30, FR-31, FR-33, FR-34, FR-16, BR-18, BR-21 | `ie` country module (`domain/countries/ie`: authorization on the programme, family rule, money and stay rules); `ingest/ie/` for ILEP, TrustEd and CSO RIQ02 with contact columns dropped; `kind = language_course`; exam-name map; `program_identifiers`; `curation_slices` with "Dublin English courses"; English-course search filtered by the placement band | the Dublin slice lists every ILEP/TrustEd English course with exam, levels, hours and the ILEP-end notice; price and start dates curated for the courses the sponsor shortlists |
| **E3 Ireland higher education** (2 weeks) | FR-32, FR-21, BR-04, BR-08 | QQI register ingestion (NFQ 6–10, ISCED-F), linking to the immigration lists with reconciliation; `travelling_party` in the profile; Irish family criterion and cost | Irish HE search with Stamp 2 status per programme and the family criterion explained |
| **E4 US every level and field** (2–3 weeks) | FR-02, FR-03, FR-10, FR-11, NFR-02, BR-01, BR-11, BR-17 | national IPEDS ingestion at every award level (incl. `IC<year>_PY`); generic `level`; STEM rule by level; "official data only" label; indexes and a load test over about 280,000 programs; the existing 132 Texas tech master's become the first slice | listing p95 < 500 ms over the full table; the Texas slice coverage unchanged |

Letters for the author (0008/T8): QQI (TrustEd terms, NFQ codes) and SEVP (English-training flag); drafts kept privately, outside the repository.

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

1. Send the QQI and SEVP emails (0008/T8); review the source code → ISCED level map when it is proposed (0008/T12).
2. Validate the SRS 2.0 baseline (round-3 changes) and close it in §9.1.
3. Start E1: item bank schema, scoring module and the CEFR mapping file; write the first items.
4. Still open from earlier: the manual pilot of site fields (Phase 4) and LLM-assisted extraction (Phase 8) continue on the Texas slice; k3s steps 4–5 and the Postgres backup before curated data goes live.
