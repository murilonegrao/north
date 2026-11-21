---
title: "Decision record 0002 — after the data spikes"
status: accepted
date: 2026-11-21
supersedes: none
inputs: [spikes/*/RESULT.md, docs/sources/*, docs/methodology/score-proposal.md §6]
---

# 0002 — Decisions after the data spikes

The author accepted every recommendation of the round-2 questionnaire (R1–R18) and the list of changes applied without asking (A1–A16). This record is the single source for the names used in the SRS, the UML and the schema. When those documents disagree with this one, this one wins.

## Findings that drove the decisions

- Q09: the Scorecard still has master's data by program (99 institution × CIP4 pairs in Texas), but only 4-digit CIP, no graduate tuition, and 70% of earnings suppressed. IPEDS has the same universe with 6-digit CIP, graduate non-resident tuition (`TUITION7`) and graduates on temporary visas (`CNRALT`).
- Q10: the SEVP list is a PDF only, with no UNITID/OPEID. 95 of 110 Texas graduate institutions match IPEDS exactly by name + city, 6 approximately, 8 not at all.
- No 52.12xx code is on the DHS STEM list (2024-07-22). Every 30.71xx code is.
- ice.gov, studyinthestates.dhs.gov and huduser.gov block scripts; nces.ed.gov is unreliable.
- No official CIP 2020 → ISCED-F table exists; Statistics Canada maps CIP Canada 2016 → ISCED-F 2013.
- The US removed the regional/national accreditor distinction in 2020.

## Decisions (R1–R18)

| # | Decision | Exact consequence |
|---|---|---|
| R1 | Keep 52.12 in scope, flagged | Programs whose primary CIP is 52.12xx carry the flag `no_stem_opt_extension`; the UI says so on the card; `post_study_work` scores them on the 12-month OPT only |
| R2 | Add 30.71 | Scope CIPs: 11.xx, 52.12xx, 30.70xx, 30.71xx |
| R3 | IPEDS first | FR-02 becomes Must and is the primary discovery source (files C<year>_A, HD<year>, IC<year>_AY). Scorecard Field of Study becomes enrichment (earnings, debt, by UNITID + CIP4) under BR-13 |
| R4 | Official files by upload | New FR-26: an admin uploads official source files in the curation screen (DHS STEM list PDF, SEVP PDF, IPEDS files, Scorecard FoS file, DAPIP export, HUD FMR file). Each upload becomes a `source_files` row (source, file_version, sha256, uploaded_by, uploaded_at). Ingestion runs on an uploaded file; `ingestion_runs.source_file_id` points to it; uniqueness on (source, sha256) gives idempotency. Automatic download is optional per source, never required |
| R5 | SEVP matching | Exact name + city match → automatic. Anything else → `reconciliation_tasks`. Once confirmed, the SEVP campus code is stored on the campus (`campuses.sevp_campus_code`) and future matches use it. The SEVP school code is not unique and is not an identifier |
| R6 | Rent benchmark | HUD FMR by county (locality scheme `us_county_fips`). Bedrooms = ceil((1 + dependents) / 2), max 4. A family of 5 → 3 bedrooms |
| R7 | HUD FY files | Downloaded once a year in a browser and uploaded (R4 flow). No HUD account |
| R8 | Exchange rates | ECB only (SDMX API, no key). Store EUR/xxx rates as published in `fx_rates` (source = `ecb`); cross rates through EUR at evaluation time; lookup takes the latest rate on or before the requested date |
| R9 | CIP → ISCED-F | `classification_maps.origin` ∈ {`derived_official`, `proposed`}; Statistics Canada pairs are `derived_official`; the 7 proposals need author review. Also `classification_maps.partial` (bool) and `notes` |
| R10 | Accreditation | BR-04 criterion becomes "institutional accreditation by a recognized accreditor". `institutions.accreditation` is a VerifiedValue whose value is `{accreditor, scheme: "us_ed_recognized", institutional: true}`. "Regional" is not shown |
| R11 | I-20 source | The international office (DSO), through its official page or a written reply, counts as `confirmed_official` for `immigration.i20_issued_for_program`. The department page alone is `reported_by_program`. SEVP certification lives on the campus/institution; the I-20 lives on the program |
| R12 | Status polarity | Keep the 5 statuses. For yes/no fields, a confirmed "no" is always `confirmed_negative` (never `confirmed_official` + false). Numeric and text fields never use `confirmed_negative`. "Test not accepted" is a yes/no field (`accepted: false`), not a number |
| R13 | Source kind | VerifiedValue gets `source_kind` ∈ {`page`, `official_list`, `correspondence`, `uploaded_file`}. For `correspondence`, `source_url` may be null; the message is stored privately (never in the repo or the public API) and the public view shows "written reply from the international office, <date>". No names or email addresses are ever stored in public fields |
| R14 | No English score | The profile accepts `english.target` (test + overall) when there is no real score. A program passes English against a target with outcome `pass_with_caveat` |
| R15 | Funding in the cost | The main `period_total_net` subtracts guaranteed funding only. `CostEstimate` adds `period_total_with_competitive_funding` beside it |
| R16 | Unknown in the score | Fixed neutral 50. `Evaluation` shows `score`, `score_range` (min–max) and `certainty` (0–100%) |
| R17 | Location | New `localities` table (id, country_code, scheme, code, name), e.g. scheme `us_county_fips`, code `48453`. New `campuses` table (id, institution_id, name, city, locality_id, sevp_campus_code, latitude, longitude). Each program belongs to one campus. HUD rent is stored once per locality in `rent_benchmarks` (locality_id, source, fiscal_year, bedrooms, amount, currency, source_file_id) |
| R18 | Deadlines | `admissions.deadlines` is a list where each item (term, kind, date) is its own VerifiedValue |

## Applied without asking (A1–A16)

| # | Change |
|---|---|
| A1 | Envelope field names follow the UML: `value`, `status`, `source_kind`, `source_url`, `evidence`, `verified_at` (NFR-01 is reworded) |
| A2 | Field paths follow the UML: `admissions.english.*` (FR-13 is reworded) |
| A3 | BR-02 wording: "only `confirmed_negative` fails *by itself*; comparing a known value against the profile can also fail" |
| A4 | `confirmed_negative` requires `source_url` (or `source_kind = correspondence`) and `verified_at`; `extracted_unverified` requires `source_url` and `evidence`; `unknown` has no value |
| A5 | "STEM confirmed" in BR-06 means confirmed **and** eligible |
| A6 | `funding` is an object: `available_to_masters` (VerifiedValue, yes/no) + `opportunities` (list) |
| A7 | The program's primary classification is a VerifiedValue (status and source); `program_classifications` gets a `verified` jsonb column |
| A8 | `program_eligibilities` gets `result` (VerifiedValue), `rule_version`, and `claim_mismatch` (bool: the program claims STEM but the CIP disagrees). `immigration.stem_opt_claimed_by_program` stays in the schema |
| A9 | `Evaluation` gets `score_range`, `certainty` and a per-criterion breakdown |
| A10 | Immigration risk criteria come from `docs/methodology/score-proposal.md` §4 (pending author review) |
| A11 | `in_strategy` is derived from modality and F-1 compatibility, not stored as a free bool |
| A12 | `institutions.carnegie_classification` column |
| A13 | Score bands (post-study work months, earnings and cost bands) live in the country module; weights stay global |
| A14 | `eligibility_rules.params` jsonb; the US STEM rule uses `{"whole_series": ["14", "26", "27", "40"]}` |
| A15 | Identifier schemes: add `dapip` to `institution_identifiers`; the SEVP campus code lives on `campuses` |
| A16 | DAPIP contact names, phones and emails are dropped at ingestion (NFR-10). The proposed OPT fee rule (Federal Register 2026-20660, 2026-10-08) is added to `migration_rules` as a rule to check |

## Clarifications (2026-11-21)

Raised while applying this record. They are part of the record.

| # | Point | Clarification |
|---|---|---|
| K1 | ID clash | A1–A16 here are not the A1–A3 of record 0001. Cite them as **0002/A1** etc. |
| K2 | Budget period | The profile budget is for the **whole program**. The UI may accept a per-year amount and multiply by the program length; the stored value is the total |
| K3 | `pass_with_caveat` | It is a **per-criterion** outcome (English against a target score). Filter aggregation: any `fail` → `fail`; else any `undetermined` → `undetermined`; else any `pass_with_caveat` → `pass_with_caveat`; else `pass`. A target score below the program minimum is handled by K8 |
| K4 | CronJob vs upload | The CronJob (D7) runs only sources that allow automatic download (today: ECB rates) and re-processes the latest uploaded files when rules change. Every other source enters by upload (FR-26) |
| K5 | HUD geography | HUD publishes FMR by FMR area, not by county. The locality stays the county (`us_county_fips`); the HUD county file maps each county to its FMR area, and `rent_benchmarks` stores the FMR of that area per county. Column names of the county file are still to confirm (`docs/sources/hud-fmr.md`) |
| K6 | File years | Each IPEDS file has its own year (e.g. C2024_A with IC2023_AY). `source_files.file_version` records each one; no rule requires matching years |
| K7 | SEVP code | Stored on `campuses.sevp_campus_code`, not as an `institution_identifiers` scheme |
| K8 | Target below the minimum | Replaces the last sentence of K3. A real score or a target below the minimum goes to the conditional-admission check: confirmed → `pass_with_caveat`, unknown → `undetermined`, no → `fail` ("score or target below the minimum"). This matches UC04 1a, where a profile with no score still passes with caveat at programs with conditional admission |
| K9 | Evidence from correspondence | The public `evidence` may quote a sentence from an email reply, never names, signatures or addresses. The full message stays private |
| K10 | Uploaded files | `source_kind = uploaded_file` still needs `source_url`: the official download page of that file. Only `correspondence` may have a null URL |
| K11 | Yes/no with details | SEVP authorization and institutional accreditation are yes/no fields with details: a confirmed absence is `value: false` + `confirmed_negative`. `extracted_unverified` + false is allowed until the curator decides |
| K12 | Certainty and range | `certainty` = share of the total weight covered by known data. `score_range` = the score with every unknown sub-item at 0 and at 100 |
| K13 | Field details | Test acceptance uses flat fields `<test>_accepted` so the paths fixed in 0002/A2 stay. Deadline items also keep `term_year` and `applicant`. `programs.institution_id` is dropped (the institution comes through the campus). `programs.in_strategy` stays as a derived, indexed column. `schema_version` stays 0 until the pilot |

## Open after this record

- Review the 7 proposed CIP → ISCED-F rows.
- Review the risk criteria (A10) and the score bands with pilot data.
- Check by hand the 8 Texas institutions with no SEVP match (and Strayer University: same name, different city).
- Profile fields still missing: GPA and GRE; a parameter for non-housing family expenses (score-proposal gaps 10 and 14).
