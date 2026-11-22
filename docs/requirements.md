---
title: "Software Requirements Specification — North"
type: requirements
project: north
version: 2.1
status: baseline
level: M
language: en
created: 2026-11-20
updated: 2026-11-22
---

# Software Requirements Specification — North

*A map of study programs, from English courses to doctorates, for international students who bring their families*

**Author:** Murilo · **Version:** 2.1 · **Date:** 2026-11-22 · **Rigor level:** M (own product, MVP)

> [!note] Address and public repo
> The planned address is `north.harpia.info`. The repository will be public, so this document contains no personal data: the family appears only as a **user profile** (number of dependents, whether the spouse can work), never with names. This SRS is written in English, like the rest of the repository.

## Version history

| Version | Date | Author | What changed |
|---|---|---|---|
| 0.1 | 2026-11-20 | Murilo | first version, based on the 4 research reports and the plan |
| 1.0 | 2026-11-20 | Murilo | baseline: decision questionnaire answered (§3.4), deployment decisions (D1–D7), curator auth (FR-25), i18n (NFR-14), license and deployment (C-07 to C-09) |
| 1.1 | 2026-11-20 | Murilo | model ready for multiple countries (C-09 detailed; BR-01, BR-03, BR-04, BR-05, BR-07 and glossary adjusted), with no change in scope |
| 1.2 | 2026-11-21 | Murilo | English translation; IDs renamed (RF→FR, RNF→NFR, RN→BR, RP→C, OE→SO) and status enums translated; multilingual UI requirement (NFR-14 rewritten, Q06b, translation risk, glossary) |
| 1.3 | 2026-11-21 | Murilo | decisions after the data spikes (record 0002): Q09/Q10 answered; R1–R18 in §3.4; CIPs add 30.71 and flag 52.12; IPEDS first (FR-02 Must), Scorecard as enrichment (FR-01 Should); official file upload (new FR-26); SEVP matching by name + city with reconciliation; DAPIP institutional accreditation; HUD FMR by county (FR-06 Should); score with neutral 50, range and certainty; target English score; guaranteed vs competitive funding; ECB exchange rates; BR-15 to BR-17; NFR-01 field names follow the UML |
| 1.4 | 2026-11-21 | Murilo | UML 1.0 and open items approved; visual identity "A Forja" as C-10 (record 0003) |
| 1.5 | 2026-11-22 | Murilo | admin area, worker and job queue (record 0006): FR-25 becomes username + password + TOTP with roles; FR-26 uploads go through the admin and a worker |
| 1.6 | 2026-11-22 | Murilo | email from the admin area (record 0007): new FR-27; FR-25 allows password reset by email with the second factor still required |
| 2.0 | 2026-11-22 | Murilo | scope change after elicitation round 3 (record 0008): English placement test, Ireland (English courses and higher education at NFQ 6–10) and every US award level and field; new SO6–SO9, FR-28 to FR-35, NFR-17 to NFR-19, BR-18 to BR-21; FR-02, FR-03, FR-10, FR-11, FR-16, FR-20, FR-21, FR-26, NFR-02, C-09, BR-01, BR-04, BR-07, BR-08, BR-11 and BR-17 changed; new user class and persona update |
| 2.1 | 2026-11-22 | Murilo | contacts from official lists (ILEP, TrustEd, DAPIP, IPEDS HD) kept privately for the admin (record 0009): NFR-10, FR-05 and FR-30 changed |

---

## 1. Introduction

### 1.1 Purpose of this document
Specify the requirements of North (FastAPI backend, Vue frontend) and serve as the baseline for development. The audience is the author and anyone who contributes to the repository.

### 1.2 Context and problem
Anyone who wants a master's degree in the US and plans to bring their family must combine information that is scattered and written in different ways:

- **immigration** (is the school SEVP-certified? does it issue an I-20 for this program? is the program's CIP on the DHS STEM list?);
- the **real cost** for a family, not just tuition;
- **funding** (assistantships, the only affordable route);
- **admissions** (minimum English score, whether an undergraduate degree in another field is accepted);
- **return** (graduate employability and salaries).

For many of them the first step is not the degree but the **English**: without an official score they cannot apply, and the cheapest legal way to raise it while working part time is a long English course abroad, for example in Ireland on a Stamp 2 permission. That step has its own official lists, rules and family consequences (in Ireland a student cannot bring dependants), and it should be chosen with the score the target degree asks for in mind (elicitation round 3, record 0008).

Today this is done by hand, program by program, on websites that hide data and change every year. Aggregators (rankings, commercial search engines) leave out the immigration layer, mix confirmed information with marketing, and do not say where each data point came from.

**Evidence:** four independent research reports (Claude, ChatGPT, Gemini, DeepSeek, 2026-11-20) reached the same conclusions: the right unit is the program, the immigration filter comes first, official data covers only discovery, and the rest depends on reading each program's website.

### 1.3 Objectives and expected benefits
- **General objective:** cut the time from "nothing mapped" to "a shortlist with a source for every data point" from weeks to hours, for the whole path: English course, degree, work after the degree.
- **Specific objectives:**
  - SO1: automatically build, from official sources, the universe of master's programs in a state, with CIP, STEM and SEVP cross-checked.
  - SO2: record every data point with source, date and verification status.
  - SO3: apply an elimination filter and a score, both configurable per user profile.
  - SO4: estimate the total cost for a family, keeping the four cost figures separate.
  - SO5: extract from program websites, with an LLM and human review, the fields that no public database provides.
  - SO6: give a user an estimated CEFR band per skill in at most 25 minutes, with the matching ranges of seven English tests taken only from the test owners' official tables. Verified when the band of at least 5 people with a recent official score lands within one half-band of it.
  - SO7: list every Stamp 2 eligible English course in Ireland from the official lists (ILEP and TrustEd Ireland), filterable by city, exam, entry and exit CEFR level and weekly hours, with the risk of losing eligibility when ILEP ends shown per course.
  - SO8: discover programs at every degree level and in every field that official sources list, in the US and Ireland, without breaking BR-02 and without asking the curator to verify what nobody looks at.
  - SO9: for a chosen degree program, show the gap between the user's estimated band and the program's minimum English score as a target score, which then filters the English courses.
- **Benefits:** decisions based on official sources; unknown data is never confused with negative data; a method that works for any state; an open dataset useful to other students.

### 1.4 Scope
**North** maps, verifies and compares study programs abroad from the point of view of someone who needs a student permission and plans to bring dependents, now or in a later step: English language courses, and degree programs at every level. Two countries are in scope: the US and Ireland (record 0008).

| In scope | Out of scope (this version) |
|---|---|
| English placement test v0: grammar, vocabulary, reading and listening; estimated CEFR band per skill and the ranges of seven tests from their official tables (FR-28, FR-29) | Speaking and writing assessment; adaptive testing; any claim of an official score |
| Ireland: English courses on the ILEP and TrustEd Ireland lists; every higher-education programme at NFQ 6–10 on QQI's register, with Stamp 2 eligibility per programme (FR-30 to FR-32) | Irish programmes below NFQ 6; CAO data (all rights reserved) |
| US: every IPEDS award level (certificates to doctorates) and every CIP; the tech CIPs (11.xx, 52.12xx, 30.70xx, 30.71xx) stay as the first curated slice. 52.12xx stays flagged: no STEM OPT extension (R1, BR-17) | US English (ESL) programs by automatic ingestion: no official list exists; leads are curated by hand (record 0008/T14) |
| Ingestion of official sources (IPEDS first, then Scorecard, DHS STEM list, SEVP list, DAPIP, HUD FMR, ECB exchange rates; ILEP, TrustEd Ireland, QQI register, CSO rents), mostly from official files uploaded by the administrator (FR-26) | Scraping commercial aggregators (U.S. News, Peterson's etc.) |
| Every ingested program published as "official data only"; curation with source and status per field on demand, by curation slice (BR-11) | Applying or submitting applications through the platform |
| LLM-assisted extraction from the program website, with a review queue | Immigration or legal advice |
| Elimination filter, score and immigration risk, with criteria from each country module | Online programs without a student permission (stored, but marked as outside the strategy) |
| Family cost simulator per profile, with who travels in each step | Countries other than the US and Ireland (the model is generic, C-09) |
| Side-by-side comparison and CSV export | Native mobile app |

### 1.5 Solution and environment overview
A web application with three parts:

```
[Official sources]──ingestion (jobs)──┐
                                      ▼
[Program site]──crawler──► [raw pages] ──LLM──► [pending extractions]
                                      │                          │ human review
                                      ▼                          ▼
                                PostgreSQL (relational + JSONB) ◄─ curation
                                      │
                           FastAPI (REST + OpenAPI)
                                      │
                           Vue 3 (search, comparison, profile, curation)
```

Deployment: a single image (Vue build served by FastAPI), published to GHCR by CI and deployed to k3s following the `k3s-gitops` repository pattern (Image Updater + ArgoCD). Details in C-08.

## 2. Stakeholders and users

### 2.1 Sponsor
| Role | Responsibility |
|---|---|
| Project author | defines scope, prioritizes, approves the baseline |

### 2.2 System users
| Class | Function | Approx. number | Priority |
|---|---|---|---|
| **Researcher** (visitor) | searches, filters, compares, simulates cost with their own profile | open | favored |
| **English learner** (visitor) | takes the placement test, sees their estimated band and the target score, picks an English course | open | favored |
| **Curator** | edits fields, attaches sources, verifies data, reviews extractions | 1 (one account) in the MVP | favored |
| **Administrator** | triggers ingestions, configures CIPs, weights and sources | 1 | other |

### 2.3 Other stakeholders
| Stakeholder | Interest | Involvement |
|---|---|---|
| International students with families | decide based on reliable data | consulted (issues, feedback, "wrong data" issue) |
| Open source contributors | add states and fix data | partner |
| Universities | have correct data about their programs | informed (correction channel) |

### 2.4 Persona
**Working professional with a family:** a professional with 4+ years of experience in technology, an undergraduate degree in another field, a spouse and children. Wants an on-campus STEM master's that leads to OPT. Cannot afford full tuition without an assistantship. No official English test score yet. Fluent with technology and wants to see the source of every number.

**Update (round 3, 2026-11-22):** the same persona now starts **before** the degree. Listening is weaker than reading. They plan 6–8 months of English abroad while working part time, going alone first, then a degree that the family can join. Where the family fits in each step depends on the country's rules, which is what North must make visible.

## 3. Requirements elicitation

### 3.1 Information sources
- **Documents:** four LLM research reports on the topic (2026-11-20) and the plan that consolidates them. These documents are kept **outside the public repository** because they contain the author's personal data (decision A3).
- **Official sources analyzed in the Phase 2 spikes:** IPEDS, College Scorecard (Field of Study file and API), DHS STEM list, SEVP school list, DAPIP, HUD Fair Market Rents, ECB exchange rates, CIP → ISCED-F mappings. Notes in `docs/sources/`, results in `spikes/*/RESULT.md`.
- **Round 3 (2026-11-22):** ILEP and TrustEd Ireland lists, QQI's register (EU open-data copy), Irish immigration rules and CSO rents, IPEDS and Scorecard at every award level, 8 CFR 214.2, the test owners' official CEFR tables. Notes in `docs/sources/`, results in `spikes/s7_ie_lists/` and `spikes/s8_us_levels/`, framing in `docs/elicitation/round-3-scope.md`.
- **Person:** the author, who is also the first user (persona).

### 3.2 Techniques used and why
| Session | Technique | Date | Why | Evidence |
|---|---|---|---|---|
| S01 | Document analysis (4 research reports) | 2026-11-20 | four independent views reveal consensus and disagreements | research reports (kept outside the repository) |
| S02 | Synthesis and architecture decision | 2026-11-20 | resolve disagreements (Mongo × Postgres, pilot state) | consolidated plan (kept outside the repository) |
| S03 | Closed-question decision questionnaire | 2026-11-20 | settle what only the sponsor can decide | §3.4 (answered in an interactive questionnaire) |
| S04 | Manual pilot (1 state, ~20 programs) | pending | find out which fields the websites expose, before automating | `docs/methodology/pilot-guide.md`, `pilot-candidates.csv` |
| S05 | Data spikes (S-1 to S-6, plus FX and ISCED) | 2026-11-21 | answer Q09 and Q10 with real files instead of assumptions | `spikes/*/RESULT.md`, `docs/sources/` |
| S06 | Round-2 decision questionnaire | 2026-11-21 | settle the choices the spikes opened (R1–R18) | `docs/decisions/0002-after-data-spikes.md` |
| S07 | Document analysis: Irish lists and rules, US award levels, CEFR tables (spikes S-7, S-8 and desk research) | 2026-11-22 | the new scope is normative: rules and lists before decisions | `docs/sources/*.md`, `spikes/s7_ie_lists/`, `spikes/s8_us_levels/` |
| S08 | Round-3 decision questionnaire | 2026-11-22 | scope order, family policy, levels and model choices only the sponsor can make (Q13–Q34) | `docs/decisions/0008-placement-ireland-all-levels.md` |
| S09 | Prototype of the placement test, validated by tasks with the sponsor and calibrated against real scores | pending | the sponsor recognizes a good test when taking it; SO6 needs real scores | `docs/design/english-placement-v0.md` |

### 3.3 Elicitation summary
The four reports agreed on: the program as the unit; the immigration filter before quality; official sources for discovery and the program website for the rest; a manual phase before automation. They disagreed on storage (spreadsheet, PostgreSQL, MongoDB), settled in favor of PostgreSQL + JSONB (Q-D1), and on the pilot state (Missouri, Texas, Florida), settled in favor of Texas (Q04). DeepSeek added financial return as a dimension. Gemini added keeping the raw page for reprocessing. ChatGPT brought the principle that unknown ≠ negative, which became a business rule (BR-02).

**Limit of this elicitation:** the Phase 2 spikes are done; the manual pilot (S04) is not. The spikes showed that the Scorecard still has master's data by program in Texas, but only with 4-digit CIP, no graduate tuition and 70% of earnings suppressed, so IPEDS (6-digit CIP, `TUITION7`, `CNRALT`) becomes the primary discovery source. The SEVP list exists only as a PDF with no UNITID/OPEID; name + city matching links 95 of 110 Texas graduate institutions exactly and leaves the rest for reconciliation. No 52.12xx code is on the DHS STEM list while every 30.71xx code is, and ice.gov, studyinthestates.dhs.gov and huduser.gov block scripts, so official files are uploaded by hand (FR-26). Which program-level fields the websites actually expose is still unknown until the pilot.

### 3.4 Questions and decisions

**Decided** (Q-D1 to Q-D3 in S02; the rest in the 2026-11-20 questionnaire):

| # | Question | Answer | Affected requirement |
|---|---|---|---|
| Q-D1 | Storage | PostgreSQL with JSONB for heterogeneous fields | C-03 |
| Q-D2 | Stack | FastAPI + Vue | C-01, C-02 |
| Q-D3 | Code visibility | public repository | NFR-09, NFR-10 |
| A1 | Where curated data lives | **in the database**, edited through a screen with login; per-field history in a table | FR-08, FR-09, FR-25 |
| A2 | Other countries | **structure only**: `country` field, sources in `ingest/us/`, immigration rules per country | C-09 |
| A3 | Source research reports | **outside the repository** (they contain personal data) | §3.1 |
| Q01 | Public data? | **(a) public search app** | FR-16 to FR-24 open to visitors |
| Q02 | Curators | **one curator, one account**; external contributions through issues | FR-25 |
| Q03 | Researcher profile | **(a) browser only**, with a shareable link; nothing on the server | FR-20, NFR-10 |
| Q04 | Pilot state | **(b) Texas** | BR-11, §10 |
| Q05 | Initial CIPs | **(c) 11.xx + 52.12 + 30.70**; others to be defined after the pilot (30.71 added by R2) | §1.4, FR-02 |
| Q06 | Language | **(c) EN first, i18n from the start, PT soon after** | NFR-14 |
| Q06b | UI languages | multilingual, most common first: wave 1 en, es, pt-BR, zh-Hans; wave 2 hi, fr, ar, vi, ko, ja | NFR-14, NFR-15 |
| Q07 | LLM provider | **(b) configurable through an environment variable** | FR-13 |
| Q08 | Raw pages | **(a) internal use only**; the API serves only the evidence excerpt | FR-12, FR-17 |
| Q11 | License | **(a) AGPL-3.0 for code + CC BY 4.0 for data** | C-07 |
| Q12 | Hosting | **own k3s cluster** (single node), `k3s-gitops` pattern | C-08 |
| D1 | App name | repository `murilonegrao/north` → image `ghcr.io/murilonegrao/north`, namespace `north`, host `north.harpia.info` | C-08 |
| D2 | Images | **one image** (Vue served by FastAPI), like the other apps on the same cluster | C-08 |
| D3 | Database | **declared through Crossplane** (XRD `Banco`) on the existing Postgres server | C-08 |
| D4 | GHCR image | **public** | C-07 |
| D5 | Indexing | **indexable** (no `noindex`), with a sitemap | NFR-15 |
| D6 | First deployment | **in Phase 3**, with only `/health`; after that, every push to `main` goes live | C-08 |
| D7 | Periodic ingestions | **CronJob** in the cluster, same image, different command | FR-07, UC05 |

**Decided by the Phase 2 spikes** (facts, not choices; 2026-11-21):

| # | Question | Answer | Affected requirement |
|---|---|---|---|
| Q09 | Does Scorecard still provide master's data per program (field of study + credential level)? | **(a) yes by coverage** (99 institution × CIP4 pairs at 48 Texas institutions, same universe as IPEDS), **but** only 4-digit CIP, no graduate tuition and 70% of earnings suppressed. IPEDS is still made a Must and the primary discovery source (R3) | FR-01, FR-02 |
| Q10 | Does the SEVP list have a structured download? | **(b) no**: only a PDF (13,807 campuses, no UNITID/OPEID). The PDF is parsed and matched by name + city: 95 of 110 Texas graduate institutions exact, 6 approximate, 1 exact name in another city, 8 not matched. FR-04 becomes assisted curation (R5) | FR-04, FR-26 |

**Decided in the round-2 questionnaire** (2026-11-21, record `docs/decisions/0002-after-data-spikes.md`). The record is the source of truth for names and rules; where this SRS disagrees, the record wins. The record also lists 16 changes applied without asking; this SRS cites them as **0002/A1 … 0002/A16** so they are not confused with decisions A1–A3 above.

| # | Question | Answer | Affected requirement |
|---|---|---|---|
| R1 | 52.12 is not on the STEM list | **keep in scope, flagged** `no_stem_opt_extension`; the card says so; `post_study_work` uses the 12-month OPT only | §1.4, BR-17, FR-03 |
| R2 | 30.71 (Data Analytics) | **added**: scope CIPs 11.xx, 52.12xx, 30.70xx, 30.71xx | §1.4, FR-02 |
| R3 | Primary discovery source | **IPEDS first** (`C<year>_A`, `HD<year>`, `IC<year>_AY`); Scorecard Field of Study becomes enrichment (earnings, debt by UNITID + CIP4) | FR-01, FR-02, BR-13 |
| R4 | Sites that block scripts | **official files by upload** in the curation screen; each upload is a `source_files` row; automatic download optional, never required | FR-26, FR-07, NFR-03 |
| R5 | SEVP matching | **exact name + city → automatic**; anything else → reconciliation task; confirmed SEVP campus code stored in `campuses.sevp_campus_code`; the SEVP school code is not an identifier | FR-04, UC05 |
| R6 | Rent benchmark | **HUD FMR by county** (`us_county_fips`); bedrooms = ceil((1 + dependents) / 2), max 4 | FR-06, FR-21 |
| R7 | HUD fiscal-year files | **downloaded once a year in a browser and uploaded**; no HUD account | FR-06, FR-26 |
| R8 | Exchange rates | **ECB only** (SDMX API, no key); EUR/xxx rates stored as published; cross rates through EUR; latest rate on or before the date | FR-21, BR-07, C-09 |
| R9 | CIP → ISCED-F | `classification_maps.origin` ∈ {`derived_official`, `proposed`}, plus `partial` and `notes`; 7 proposals await author review | C-09 |
| R10 | Accreditation | **institutional accreditation by a recognized accreditor**; "regional" is not shown | BR-04, FR-05 |
| R11 | I-20 source | **the international office (DSO)**, by official page or written reply, counts as `confirmed_official`; the department page alone is `reported_by_program`; SEVP lives on the campus/institution, the I-20 on the program | BR-04, BR-06, BR-09 |
| R12 | Status polarity | **keep the 5 statuses**; a confirmed "no" on a yes/no field is always `confirmed_negative`; numeric and text fields never use it; "test not accepted" is a yes/no field | BR-02 |
| R13 | Source kind | VerifiedValue gets **`source_kind`** ∈ {`page`, `official_list`, `correspondence`, `uploaded_file`}; correspondence is stored privately | BR-15, NFR-01, NFR-10 |
| R14 | No English score | profile accepts **`english.target`** (test + overall); passing against a target gives `pass_with_caveat` | FR-18, FR-20, UC04 |
| R15 | Funding in the cost | **`period_total_net` subtracts guaranteed funding only**; `period_total_with_competitive_funding` is shown beside it | FR-21, BR-07 |
| R16 | Unknown in the score | **fixed neutral 50**; `score`, `score_range` and `certainty` shown | FR-19 |
| R17 | Location | new **`localities`** and **`campuses`** tables; each program belongs to one campus; HUD rent stored once per locality in `rent_benchmarks` | BR-01, FR-06 |
| R18 | Deadlines | `admissions.deadlines` is a list; **each item is its own VerifiedValue** | BR-16 |

**Decided in the round-3 questionnaire** (2026-11-22, record `docs/decisions/0008-placement-ireland-all-levels.md`, cited as **0008/T1 … T24** and **0008/C1 … C3**). The record wins where this SRS disagrees.

| # | Question | Answer | Affected requirement |
|---|---|---|---|
| Q13 | Order of the slices | placement → Ireland English → Ireland HE → US every level (T1) | execution plan |
| Q14 | Family when it joins later | `Profile.travelling_party` per program kind; Stamp 2 dependants fail with the rule cited; NFQ 10 research `pass_with_caveat` (T2) | FR-20, FR-21, BR-04, BR-08 |
| Q15 | Irish programmes shown | **every register programme at NFQ 6–10**, with Stamp 2 eligibility per programme (T3, C1) | FR-30–32, BR-18 |
| Q16 | Irish HE levels | NFQ 6–10, every field (T4) | §1.4, FR-32 |
| Q17 | ILEP → TrustEd | automatic link on provider number + exact title, else reconciliation; never negative automatically; `ie.ilep_end` rule (T6) | FR-31, BR-18 |
| Q18 | Irish rent | CSO RIQ02 by location and bedrooms, county fallback (T7) | FR-33, FR-21 |
| Q19 | Letters to publishers | the author emails QQI and SEVP; provisional until replies (T8) | §10 |
| Q20 | US levels | **every award level at once** (T9) | FR-02 |
| Q21 | US fields | **every CIP**; tech CIPs as the first curated slice (T10) | §1.4, FR-02 |
| Q22 | Curation at this scale | ingest everything as "official data only", curate on demand by slice (T11) | FR-10, FR-11, BR-11 |
| Q23 | Level in the model | ISCED 2011 level + credential, source codes as classifications (T12) | BR-01, FR-16 |
| Q24 | English courses in the model | `Program.kind = language_course` with its own fields (T13) | BR-01, FR-30 |
| Q25 | US ESL | ask SEVP; leads curated by hand for one city (T14) | §1.4 |
| Q26 | F-1 fixed 4-year admission | **not recorded until the effective date is confirmed** (T15) | §10 |
| Q27 | Tests in the placement result | **all seven** (T17) | FR-29 |
| Q28 | Result label | grammar, vocabulary, reading and listening; writing and speaking not tested (T18) | FR-29, NFR-17 |
| Q29 | TOEFL 0–120 scale | secondary until 2028-01-31 (T19) | FR-29 |
| Q30 | TOEFL minimums | `admissions.english.toefl_ibt_scale` (T20) | FR-18 |
| Q31 | Item bank | versioned YAML in the repo (T21) | FR-28, NFR-18 |
| Q32 | Listening audio | pre-generated files (T22) | FR-28 |
| Q33 | Placement → course filter | now (T23) | FR-35 |
| Q34 | CEFR descriptors | none quoted until the licence is read (T24) | NFR-18 |

### 3.5 Techniques not used
Interviews and surveys with other students are deferred until after the MVP. For now the sponsor is the only target user.

## 4. Functional requirements

### 4.1 List

**Ingestion and discovery**
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-01 | enrich the programs found by FR-02 with the College Scorecard Field of Study file (earnings and debt by UNITID + CIP4, `CREDLEV = 5`), stored with the CIP4 they were measured at and the BR-13 caveat; never used for discovery (R3) | Should | UC05 |
| FR-02 | import from IPEDS, as the **primary discovery source** for the US, the institutions and programs of **every award level and every CIP** nationwide (record 0008/T9, T10), using the files `C<year>_A` (completions by UNITID × 6-digit CIP × award level, including `CNRALT`), `HD<year>` (institution, city, county, coordinates), `IC<year>_AY` (charges: undergraduate `TUITION3`/`FEE3` out of state, graduate `TUITION7`/`FEE7`, professional doctorates `OSPROF1..9`) and `IC<year>_PY` (charges of certificate-only institutions), stored as institution reference values, never as "verified". The award level becomes a classification (scheme `us_ipeds_awlevel`) mapped to the generic `level` (BR-01). A UNITID × CIP6 × level with 0 completions in the latest year is created as "to confirm" and not published (R3) | Must | UC05 |
| FR-03 | import the DHS STEM list (uploaded PDF, FR-26) as a versioned rule (`eligibility_rules`) and evaluate each program's 6-digit primary CIP against it, only for bachelor's, master's and doctoral degrees; other levels get `confirmed_negative` with the reason "level not eligible" (BR-03, BR-17, record 0008/T16) | Must | UC05 |
| FR-04 | import the SEVP certified school list from the uploaded PDF (FR-26) and match it against campuses: by `campuses.sevp_campus_code` when the link already exists; otherwise by normalized name + city + state, where an exact match is accepted automatically and anything else opens a reconciliation task. A confirmed match stores the SEVP campus code on the campus; the SEVP school code is never used as an identifier; an institution missing from a new list version opens a reconciliation task and is not marked "not certified" automatically (R5) | Must | UC05 |
| FR-05 | import from the DAPIP export (FR-26) the **institutional** accreditation of each institution (accreditor, status, scheme `us_ed_recognized`), joined by `dapip`/OPEID/UNITID identifiers; programmatic accreditation is not used in the MVP; administrator contacts go only to the private `institution_contacts` table (R10, 0002/A15, record 0009, NFR-10) | Should | UC05 |
| FR-06 | import the HUD Fair Market Rent county file of the current fiscal year from an uploaded file (FR-26), and store one rent per locality (`us_county_fips`), fiscal year and bedroom count (0–4) in `rent_benchmarks`; campuses link to their county through `localities` (from IPEDS `COUNTYCD`). Raised from Could to Should because FR-21 needs it (R6, R7, R17) | Should | UC05 |
| FR-07 | record every ingestion run (source, date, file version, source file, counts, errors) and allow re-running without duplicating records; `ingestion_runs.source_file_id` points to the uploaded file (FR-26) | Must | UC05 |
| FR-26 | let the administrator upload official source files in the curation screen (DHS STEM list PDF, SEVP PDF, IPEDS files, Scorecard Field of Study file, DAPIP export, HUD FMR file; ILEP and TrustEd Ireland XLSX, QQI register export, CSO RIQ02 file). Each upload becomes a `source_files` row (source, file_version, sha256, uploaded_by, uploaded_at), unique on (source, sha256), so uploading the same file twice is idempotent. Ingestion runs on an uploaded file; automatic download is optional per source, never required (R4) | Must | UC05 |

**Curation and verification**
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-08 | let the curator edit any field of a program, attaching the source URL, date and verification status | Must | UC06 |
| FR-09 | keep a per-field change history (previous value, new value, author, date, source) | Must | UC06 |
| FR-10 | show a coverage dashboard **per curation slice** (FR-34): how many programs, how many with each dimension verified, which items are pending; programs outside every slice count as "official data only" (record 0008/T11) | Must | UC09 |
| FR-11 | mark a curation slice as "complete" only when the BR-11 checklist is satisfied for every program in it | Should | UC09 |
| FR-25 | authenticate the curator/administrator before any edit, ingestion or review, with username, password (Argon2id) and a TOTP second factor; roles `viewer`, `curator`, `admin`; every admin action in an append-only audit log; search stays open without login (record 0006). A forgotten password can be reset through a single-use link sent to the account's verified email; the TOTP code is still required (record 0007/E7) | Must | UC05–UC09 |
| FR-27 | send email to admin accounts through an outbox the worker delivers over SMTP: address confirmation, password reset links, security notices (password, authenticator, address or access changed, sign-in from a new address, sign-in paused) and failed-job notices; plain text in the account's admin language; no email to the public (record 0007) | Should | UC11 |

**Ireland ingestion** (record 0008/T3–T7)
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-30 | import the ILEP XLSX (FR-26): English-language rows become programs of kind `language_course` with `cefr_entry`, `cefr_exit`, `exam` (normalized through `data/reference/ie_exam_names.csv`), `weeks` and `hours_per_week` parsed from the free text (raw text kept as evidence); higher-education rows become degree programs; each row gives `Program.intl_authorization` with scheme `ie_ilep` as `confirmed_official`; provider by `ie_provider_no`, city by text match on the address; contact name, email and phone go only to the private `institution_contacts` table (record 0009, NFR-10) | Must | UC05 |
| FR-31 | import the TrustEd Ireland XLSX the same way (scheme `ie_trusted`, provider number without the `TE` prefix), and reconcile the move from ILEP: a programme that leaves ILEP links to a TrustEd row automatically when provider number and normalized title match exactly, otherwise a reconciliation task (`ie_list_move`) is opened; no programme becomes `confirmed_negative` automatically (BR-18); the announced ILEP end is a `migration_rules` row shown on affected programmes | Must | UC05 |
| FR-32 | import every active programme at NFQ 6–10 from QQI's register (EU open-data copy) as a degree program (identifier scheme `ie_irq`) with its NFQ level (classification `ie_nfq`) and ISCED-F field; link it to ILEP/TrustEd rows by provider and exact title, the rest by reconciliation; a programme with no list row is `unknown` for Stamp 2 (BR-18) | Must | UC05 |
| FR-33 | import the CSO RIQ02 rent table (RTB data) into `rent_benchmarks`, one value per location (`ie_cso_riq02`), quarter and bedroom count (1, 2, 3, 4+), with the county (`ie_county`) as fallback for campuses whose town has no value | Should | UC05 |
| FR-34 | let the curator define curation slices (name, country, filter) that group programs for coverage, completeness and extraction; the first slices are the Texas tech master's and the Dublin English courses (record 0008/T11) | Must | UC09 |

**English placement** (record 0008/T17–T24, `docs/design/english-placement-v0.md`)
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-28 | run a placement test of about 60–70 original items in four skills (grammar 20, vocabulary 15, reading 3 texts × 4, listening 3 clips × 4 with pre-generated audio and its script), loaded from the versioned item bank in `data/placement/items/`; it takes at most 25 minutes and runs without an account | Must | UC12 |
| FR-29 | compute a band per skill (the highest band with ≥ 70% correct and every lower band ≥ 70%) and an overall band (median of the skills; with an even count, the lower of the two middle bands), and show the matching ranges of IELTS Academic, TOEFL iBT (1–6, with the 0–120 concordance as secondary until 2028-01-31), Cambridge English Scale, Duolingo, PTE Academic, LanguageCert Academic and Trinity ISE, taken only from `data/reference/cefr_test_mappings.csv`; per-skill ranges only where the test owner publishes them; the result keeps the label of BR-19 | Must | UC12 |
| FR-35 | keep the placement result in the browser (with JSON export and monthly retake showing the change per skill), use it as the profile's estimated band to filter English courses (`cefr_entry` ≤ overall band), and, for a degree program the user picked, show the gap to its English minimum as a target score that the English-course search can use (SO9) | Must | UC12, UC04 |

**Assisted extraction**
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-12 | download a program's official pages (admissions, international, tuition, assistantships) and store the raw content with URL and date, for internal use only (never served by the API) | Should | UC07 |
| FR-13 | extract with an LLM, from the raw page, the schema fields (paths as in the UML, e.g. `admissions.english.*`), returning valid JSON with the source sentence for each value; provider and model come from environment variables | Should | UC07 |
| FR-14 | put every extraction in a review queue; the curator accepts, corrects or rejects each field | Should | UC08 |
| FR-15 | reprocess stored pages when the schema gains a new field, without downloading them again | Could | UC07 |

**Search and decision**
| ID | The system shall… | Priority | UC |
|---|---|---|---|
| FR-16 | list programs with filters by country, subdivision, kind (degree or English course), level, field (ISCED-F, CIP), STEM, student authorization, modality, cost range, funding, minimum English score, CEFR entry and exit level, exam, weekly hours, verification status and "official data only" vs curated | Must | UC01 |
| FR-17 | show a program's detail page with each value accompanied by source, date and verification status | Must | UC02 |
| FR-18 | apply the elimination filter (BR-04) with the outcomes pass, pass with caveat, fail and undetermined, and show, for each program that does not pass, which criterion failed or is undetermined | Must | UC01 |
| FR-19 | compute a 0–100 score with configurable weights (BR-05) and the immigration risk separately (BR-06). An unknown sub-item scores a fixed neutral 50; every evaluation shows `score`, `score_range` (min–max, with uncertain sub-items at 0 and 100), `certainty` (0–100%, the share of weight whose data is known) and a per-criterion breakdown (R16, 0002/A9). Score bands live in the country module; weights stay global (0002/A13) | Must | UC04 |
| FR-20 | accept a profile (budget as an amount with currency for the whole program (the UI may accept a yearly amount and multiply by program length; record 0002/K2); English score, or `english.target` (test + overall) when there is no real score (R14), or the estimated band from the placement test (FR-35); dependents; whether the spouse can work; `travelling_party` per program kind, default English course alone and degree with family (record 0008/T2); undergraduate field) and recompute filter, score and cost; the profile stays in the browser only and can be shared by link, and the API receives it per request without storing it | Must | UC04 |
| FR-21 | estimate the family's total cost, keeping the four figures separate (BR-07), counting the dependents only when they travel for that program's kind (BR-08); the net total subtracts guaranteed funding only, with a second total that also subtracts competitive funding (R15); rent uses the benchmark of the campus locality (US: HUD FMR; Ireland: CSO RIQ02) with bedrooms = ceil((1 + travelling dependents) / 2), max 4 (R6, record 0008/T7); currency conversion uses ECB rates (R8) | Must | UC04 |
| FR-22 | compare 2 to 5 programs side by side | Should | UC03 |
| FR-23 | export the filtered list as CSV, with the source and verification columns; also publish a full dump of the curated data (CC BY 4.0) with each release | Should | UC10 |
| FR-24 | show on immigration fields a notice with the date the current rule was last checked | Must | UC02 |

### 4.2 Detailed specifications (critical requirements)

**FR-03 — Flag STEM by CIP** · Must
- **Description:** the system shall flag a program as confirmed STEM only when its assigned CIP is on the current version of the DHS STEM list.
- **Rationale:** STEM status grants the OPT extension, and the program's marketing name does not guarantee the classification (SO1).
- **Origin:** S01 (ChatGPT, Claude) · DHS STEM list.
- **Acceptance criteria:** Given a program with primary CIP 11.0701 and a current list containing 11.0701, when ingestion runs, then the `us.stem_opt` eligibility result is `confirmed_official` with value true, the `rule_version` and the list date. Given a program with primary CIP 52.1201 (not on the list), then the result is `confirmed_negative` and the program carries the flag `no_stem_opt_extension` (BR-17). Given a program whose page claims STEM while its CIP is not on the list, then `claim_mismatch = true` (BR-03). Given a program with no known CIP, then the result is `unknown`, never `confirmed_negative`.
- **Rules:** BR-02, BR-03, BR-17.

**FR-13 — LLM extraction** · Should
- **Description:** from a raw page, the system shall produce valid JSON in the program schema, with each value accompanied by the literal excerpt that supports it.
- **Rationale:** minimum English score, funding and deadlines exist only on the program website (SO5).
- **Acceptance criteria:** Given a page with "minimum TOEFL iBT score of 80", then `admissions.english.toefl_ibt_min = 80`, `evidence` contains the excerpt, `source_kind = page`, `source_url` is the page URL and `status = extracted_unverified`. Given a field missing from the page, then it comes back with no value and status `unknown`, never an invented value.
- **Rules:** BR-02, BR-10.

**FR-18 — Elimination filter** · Must
- **Description:** the system shall classify each program as pass, pass with caveat, fail or undetermined for the profile, naming the criterion.
- **Acceptance criteria:** Given a profile with TOEFL 75 and a program with a minimum of 80 and no conditional admission, then the result is `fail` with the criterion "English". If the minimum is unknown, the result is `undetermined`, neither `pass` nor `fail`. Given a profile with no real score and `english.target` TOEFL 90, and a program with a known minimum of 80, then English is `pass_with_caveat` (R14); if the target is below the minimum, the conditional-admission check applies as for a real score: confirmed → `pass_with_caveat`, unknown → `undetermined`, no → `fail` with the reason "score or target below the minimum" (record 0002/K8). `pass_with_caveat` is a per-criterion outcome; the filter aggregates as `fail` > `undetermined` > `pass_with_caveat` > `pass` (record 0002/K3). Given a program with a test marked as not accepted (`accepted: false`, `confirmed_negative`), then a profile with only that test fails English (R12).
- **Rules:** BR-02, BR-04.

**FR-21 — Family cost** · Must
- **Description:** the system shall compute, per program and profile, (1) tuition + fees, (2) the I-20 financial requirement, (3) estimated living cost and (4) the period total net of funding (`period_total_net`), showing the source of each part. `period_total_net` subtracts only funding whose availability is `guaranteed`; `period_total_with_competitive_funding` is shown beside it and also subtracts competitive funding (R15). Rent comes from the HUD FMR of the campus locality for the fiscal year in force, with bedrooms = ceil((1 + dependents) / 2), capped at 4 (R6). Values in another currency are converted with ECB rates: EUR/xxx rates as published, cross rates through EUR, using the latest rate on or before the evaluation date; the rate, its date and the source are shown with the result (R8).
- **Acceptance criteria:** Given a profile with 4 dependents (a family of 5) and a spouse without work authorization, then the household income considered for the period is the student's only (stipend, if any) and the housing cost uses the 3-bedroom FMR (ceil(5 / 2) = 3). Given 1 dependent, then 1 bedroom; given 6 or more dependents, then 4 bedrooms (the cap). Given a program whose only assistantship is competitive, then `period_total_net` subtracts nothing and `period_total_with_competitive_funding` subtracts it.
- **Rules:** BR-07, BR-08.

**FR-26 — Official file upload** · Must
- **Description:** the administrator uploads an official source file in the curation screen; the system stores it, computes its sha256 and creates a `source_files` row (source, file_version, sha256, uploaded_by, uploaded_at). An ingestion run is started on that file, and `ingestion_runs.source_file_id` points to it.
- **Rationale:** ice.gov, studyinthestates.dhs.gov and huduser.gov block scripts, and nces.ed.gov is unreliable; ingestion cannot depend on automatic download (R4).
- **Acceptance criteria:** Given a SEVP PDF already uploaded, when the same file is uploaded again, then no new `source_files` row is created (unique on source + sha256) and re-running the ingestion changes nothing (NFR-03). Given a source with an optional automatic downloader, when the download fails, then the run is recorded as failed and the upload path still works.
- **Rules:** BR-09, BR-15.

**FR-29 — Placement result** · Must
- **Description:** from the answers, the system shall compute a CEFR band per skill and overall, and show the ranges of the seven tests from the official tables, labelled as an estimate.
- **Rationale:** the persona has no official score; the band chooses the English course and the gap to the degree's minimum becomes the target (SO6, SO9).
- **Origin:** S08 (Q27–Q30) · `docs/sources/cefr-test-mappings.md`.
- **Acceptance criteria:** Given grammar answers with A2 100%, B1 75%, B2 50%, then the grammar band is B1. Given B1 at 65% and B2 at 80%, then the band is A2 (a lower band below 70% caps it). Given skill bands B1, B2, B2, B1, then the overall band is B1 (with an even count, the lower of the two middle bands) and the IELTS range shown is the one the mapping file gives for B1, with its citation. Given the result screen, then it says "Grammar, vocabulary, reading and listening. Writing and speaking were not tested." and "estimate, not an official score". Given a test whose owner publishes no per-skill table (IELTS), then no per-skill IELTS range is shown. Given a date after 2028-01-31, then the TOEFL 0–120 range is not shown.
- **Rules:** BR-19, BR-20.

**FR-31 — ILEP to TrustEd move** · Must
- **Acceptance criteria:** Given programme `0058/0003` on the old ILEP file and, on the new files, no ILEP row but a TrustEd row from provider `TE0058` with the same normalized title, then the programme keeps its identity, gains scheme `ie_trusted`, and its authorization stays `confirmed_official` with the new source file. Given the same case with a different title, then a reconciliation task is opened and the authorization keeps its last confirmed value with a "to confirm" marker, never `confirmed_negative`.
- **Rules:** BR-02, BR-18.

### 4.3 User stories (initial backlog)
| ID | As a… I want… so that… | FR |
|---|---|---|
| US-01 | as a researcher, I want to see only the programs that pass my filter, so that I don't waste time on unfeasible ones | FR-16, FR-18 |
| US-02 | as a researcher, I want to know where each number came from, so that I can trust or check it | FR-17 |
| US-03 | as a researcher, I want to enter my family and budget, so that I see the real cost | FR-20, FR-21 |
| US-04 | as a curator, I want to run the ingestion for a state and see what is already covered, so that I know where to work | FR-01–07, FR-10, FR-26 |
| US-05 | as a curator, I want to review what the LLM extracted field by field, so that I don't publish invented data | FR-13, FR-14 |
| US-06 | as an English learner, I want to know my level and the score I need, so that I pick an English course that gets me there | FR-28, FR-29, FR-35 |
| US-07 | as an English learner, I want to see which Dublin courses keep their visa eligibility after ILEP ends, so that I don't lose my permission halfway | FR-30, FR-31 |
| US-08 | as a researcher, I want to see whether my family can come with me in each step, so that I plan who travels when | FR-20, BR-04, BR-08 |

## 5. Non-functional requirements and constraints

### 5.1 Non-functional requirements
| ID | Characteristic | Requirement | Priority | How to verify |
|---|---|---|---|---|
| NFR-01 | Suitability / traceability | Every verifiable value uses the envelope field names of the UML: `value`, `status`, `source_kind`, `source_url`, `evidence`, `verified_at` (0002/A1). 100% of displayed values have a `status`, a `source_kind` and a `verified_at`, and a `source_url` unless `source_kind = correspondence`; a value without a source never appears as confirmed. `confirmed_negative` requires `source_url` (or `source_kind = correspondence`) and `verified_at`; `extracted_unverified` requires `source_url` and `evidence`; `unknown` has no value (0002/A4) | Must | API contract test + JSON Schema validation |
| NFR-02 | Performance | a filtered listing responds with p95 < 500 ms over the whole program table (about 280,000 programs: US every level and field, Ireland; record 0008/C3) | Should | load test |
| NFR-03 | Reliability | ingestions are idempotent; re-running the same source and version neither changes nor duplicates records | Must | integration test |
| NFR-04 | Responsible crawling | the crawler respects robots.txt, limits itself to 1 request/s per domain, uses a generic project user-agent and only accesses university and official government domains | Must | test and configuration review |
| NFR-05 | Usability | search screens work from 360 px wide; unknown data is visually distinct from negative data | Must | UI review |
| NFR-06 | Accessibility | WCAG 2.1 AA on public screens | Should | automated + manual audit |
| NFR-07 | Maintainability | the program schema is versioned (JSON Schema) and validated at the API, curation and extractor inputs | Must | tests |
| NFR-08 | Maintainability | test coverage ≥ 80% on the filter, score and cost rules | Should | coverage report |
| NFR-09 | Security | no secrets in the repository; keys (LLM, optional source APIs such as api.data.gov) only through environment variables; curation and admin endpoints authenticated | Must | secret scanning in CI |
| NFR-10 | Privacy | no personal researcher data is stored on the server (Q03: the profile stays in the browser). Contact names, titles, phones and emails found in official lists (ILEP and TrustEd Ireland, DAPIP, IPEDS HD) are stored privately in `institution_contacts`, readable only by the `admin` role through the admin API, each read audited, replaced by every new list, and never in the public API, exports, the data dump or the repository (record 0009). Correspondence used as a source (e.g. a reply from an international office) is stored privately, never in the repository, the public API or the data dump; public fields never hold names or email addresses (R13, BR-15) | Must | review + ingestion test |
| NFR-11 | Transparency | every page shows the notice "this is not immigration advice; check the official source" | Must | UI review |
| NFR-12 | Portability | the whole system starts with `docker compose up` in a clean environment | Should | CI |
| NFR-13 | Cost | LLM extraction logs tokens and cost per page; there is a configurable cap per run | Should | logs |
| NFR-14 | Internationalization | The UI is multilingual. English is the default and source language; every UI string goes through i18n from the first commit. Languages ship in waves, most widely used by the audience first: wave 1 (v0.1) en, es, pt-BR, zh-Hans; wave 2 hi, fr, ar, vi, ko, ja; more on demand. Translations are UI strings and help texts only; program data stays in English. Dates, numbers and currency use the viewer's locale (Intl). Layout uses CSS logical properties so right-to-left languages (ar) work without a redesign. Each language has its own URL prefix with hreflang tags (see NFR-15). A missing translation falls back to English, never to an empty string or a key. | Must | CI check for missing keys + RTL visual review |
| NFR-15 | Findability | program pages are indexable, with a stable URL, their own title and description, and a sitemap | Should | review |
| NFR-17 | Transparency | the placement result always says it is an estimate, names the skills tested and the ones not tested, and cites the official table and check date behind every test range; no test owner's document, prose or logo is reproduced | Must | UI review + test |
| NFR-18 | Maintainability / licensing | placement items are original, versioned (`bank_version`) and validated against `schema/placement-item.schema.json` in CI; no CEFR descriptor or test-owner item is copied | Must | CI + review |
| NFR-19 | Accessibility | every listening clip has its script available after the answer is given; the test works with keyboard only and at 360 px | Should | manual audit |
| NFR-16 | Recoverability | since curated data lives in the database (A1), the database has a daily backup with a restore test before curated data enters production | Must | restore test |

### 5.2 Constraints
| ID | Type | Constraint |
|---|---|---|
| C-01 | process | Python backend with FastAPI; API documented with OpenAPI |
| C-02 | process | Vue 3 frontend |
| C-03 | process | PostgreSQL; heterogeneous fields (English, deadlines, funding) in JSONB |
| C-04 | project | public repository: code, issues and documentation are open |
| C-05 | project | data sources are official only, or the program's own website; commercial aggregators serve only as leads, with no scraping |
| C-06 | project | one developer, part time; the MVP must fit in one pilot state |
| C-07 | project | AGPL-3.0 license for code and CC BY 4.0 for data; public image on GHCR |
| C-08 | process | deployment following the `k3s-gitops` pattern (`docs/app-nova.md`): CI `imagem.yml` with jobs `testes` and `imagem`, tag `sha-<7>`, Image Updater + ArgoCD; app `north`; database through Crossplane; secrets as a sealed `north-env` (Sealed Secrets) |
| C-09 | project | the model accepts any country without data migration; **the US and Ireland are in scope** (record 0008): (a) country and subdivision (ISO 3166) instead of "state", and localities per scheme (`us_county_fips`, `ie_cso_riq02`, `ie_county`) for campus location (R17); (b) institution identifiers per scheme (`unitid`, `opeid`, `dapip`, `ror`, `ie_provider_no`…), never as primary key; the SEVP campus code lives on the campus (0002/A15); (c) program classification per scheme (CIP, IPEDS award level, NFQ), mapped to ISCED-F and to the generic level through `classification_maps` with `origin` `derived_official` or `proposed` (R9, 0008/T12); (d) authorization to enroll foreign students per scheme, on the campus (`sevp`) or on the program (`ie_ilep`, `ie_trusted`) (0008/T5); (e) work eligibilities as versioned rules per country (`us.stem_opt`); (f) every monetary value has a currency (ISO 4217) and a dated exchange rate with a source (ECB, R8); (g) visa rules, family rules and filter criteria in one module per country (`domain/countries/us`, `domain/countries/ie`), with a common interface; ingestions in `ingest/<country>/` |
| C-10 | project | the UI follows the author's visual identity "A Forja": one accent (ember `#D96C2C`), neutral charcoal/parchment palette, dark theme by default, fixed type roles (JetBrains Mono, Inter, Spectral), self-hosted fonts, the North sigil as a small signature (record 0003) |

## 6. Business rules

| ID | Rule |
|---|---|
| BR-01 | The unit of record is the **program** (institution + kind + level + primary classification + campus). `kind` is `degree` or `language_course` (0008/T13); `level` is a VerifiedValue with the ISCED 2011 level and the credential, and the source code (IPEDS award level, NFQ level) is kept as a classification (0008/T12); language courses have no ISCED level. Each program belongs to one campus; a campus belongs to an institution and to a locality (e.g. a US county). Institution, campus, locality, subdivision and country are related entities (R17). The program's primary classification is itself a verifiable value, with status and source (0002/A7). |
| BR-02 | **Unknown ≠ negative.** Every verifiable field has one of these statuses: `confirmed_official`, `reported_by_program`, `extracted_unverified`, `unknown`, `confirmed_negative`. Only `confirmed_negative` fails the filter *by itself*; comparing a known value against the profile can also fail (e.g. a TOEFL minimum above the profile's score) (0002/A3). For yes/no fields, a confirmed "no" is always `confirmed_negative`, never `confirmed_official` + false. Numeric and text fields never use `confirmed_negative`. "Test not accepted" is a yes/no field (`accepted: false`), not a number (R12). |
| BR-03 | STEM (rule `us.stem_opt`, stored in `eligibility_rules`) is `confirmed_official` with value true only if the program's 6-digit primary CIP is on the current version of the DHS list, or belongs to a series the rule lists as whole (`eligibility_rules.params` = `{"whole_series": ["14", "26", "27", "40"]}`, 0002/A14). A CIP confirmed as not on the list gives `confirmed_negative` (BR-02). Each result is stored in `program_eligibilities` with `result` (VerifiedValue) and `rule_version`. If the program claims STEM (`immigration.stem_opt_claimed_by_program`) and the CIP disagrees, the eligibility follows the CIP and `claim_mismatch = true` is set and shown (0002/A5, 0002/A8). Eligibilities in other countries follow the same pattern: a versioned rule, matched against the program's classification. |
| BR-04 | Elimination filter: the criteria come from the rules module of the program's country. In the `us` module: SEVP certification of the program's campus/institution, plus an I-20 issued for the program itself (`immigration.i20_issued_for_program`) — two separate checks at two levels (R11); modality compatible with F-1; institutional accreditation by a recognized accreditor (R10; "regional" is neither a criterion nor shown); English reachable by the profile, or conditional admission, or `pass_with_caveat` against the profile's target score (R14); accepts an undergraduate degree in another field; total cost ≤ the profile's budget, in the profile's currency and budget period. In the `ie` module: the programme is on the ILEP or TrustEd list (program-level authorization); English reachable (for a language course: `cefr_entry` ≤ the profile's band); total cost ≤ budget; and **family**: when the profile travels with family for that kind of program, Stamp 2 does not allow dependants, so the criterion fails with the rule cited, except NFQ 10 research programmes (`pass_with_caveat`: dependants on Stamp 2A, spouse cannot work) (0008/T2). In the US, dependants on F-2 are always allowed and the family criterion passes. |
| BR-05 | Score from 0 to 100, default weights: post-study work (STEM OPT, in the US) 20, cost 20, funding 15, admissibility 15, career and ROI 15, family 10, quality 5. Weights are configurable and must add up to 100. |
| BR-06 | Immigration risk is computed separately and does not enter the average; its criteria come from `docs/methodology/score-proposal.md` §4, pending author review (0002/A10). A program can be marked as a finalist only when SEVP, I-20 and STEM are all `confirmed_official` **and** true ("STEM confirmed" means confirmed and eligible, 0002/A5). For the I-20, `confirmed_official` comes from the international office (DSO), through its official page or a written reply; the department page alone gives only `reported_by_program` (R11). |
| BR-07 | Cost has four separate figures: tuition + fees; the visa financial requirement (the I-20 in the US; the €10,000-a-year rule in Ireland, €833 a month up to 8 months, with no amount per dependant, 0008/C2); living cost; period total net of funding. The net total subtracts guaranteed funding only; a second total with competitive funding subtracted is shown beside it (R15). Every value has a currency; conversion to the profile's currency uses a dated ECB exchange rate (cross through EUR, latest rate on or before the date), shown with the result (R8). |
| BR-08 | The profile states whether the spouse can work and who travels for each kind of program (`travelling_party`, 0008/T2); dependents who do not travel count in neither the family criterion nor the cost. On F-1/F-2 the default is that the spouse cannot work, and the cost model assumes a single income; the same holds for Irish Stamp 2A. Other routes (J-1/J-2 in the US; Hosting Agreement and Critical Skills in Ireland) are recorded as alternatives in `migration_rules`, with their own rule. |
| BR-09 | Source hierarchy: government agency > program website > aggregator. An aggregator never confirms a data point on its own. Exception for the I-20: the school's international office (the DSO) is the official source for whether a program gets an I-20, so its official page or written reply counts as `confirmed_official` (R11). |
| BR-10 | An LLM-extracted value enters as `extracted_unverified` and only becomes `reported_by_program` after curator review. |
| BR-11 | A **curation slice** (FR-34) is complete when every program in it has: classification, level and work eligibility verified, student authorization (and the I-20 in the US), costs, funding, admissions, estimated family cost, sources recorded, score and pending items listed (for a language course: CEFR levels, exam, weeks, hours, price and start dates instead of funding and admissions). Programs outside every slice are published as "official data only" and are never shown as complete (0008/T11). |
| BR-12 | Immigration rules that change (length-of-stay periods, fees on OPT and H-1B) live in their own table (`migration_rules`), with the date of the last check, and appear as a notice on the affected fields. The proposed OPT fee rule (Federal Register 2026-20660, 2026-10-08) is tracked there as a rule to check (0002/A16). |
| BR-13 | Graduate salaries from Scorecard are shown with the caveat that they measure graduates who received federal aid, not international students, and that they are measured at 4-digit CIP. Scorecard is enrichment only, never discovery (R3); a suppressed earnings value (`PS`) is `unknown`. |
| BR-14 | Online programs without F-1 can exist in the database, but are marked as outside the strategy and are not ranked. `in_strategy` is derived from the modality and F-1 compatibility, not stored as a free flag (0002/A11). |
| BR-15 | Every verifiable value records its `source_kind`: `page`, `official_list`, `correspondence` or `uploaded_file`. For `correspondence`, `source_url` may be empty; the message itself is stored privately (never in the repository, the public API or the dump), and the public view shows only "written reply from the international office, [date]". Names and email addresses are never stored in public fields (R13, NFR-10). |
| BR-16 | `admissions.deadlines` is a list in which each item (term, kind, date) is its own VerifiedValue, with its own status and source, because deadlines often come from different pages (graduate school vs department) (R18). |
| BR-17 | The STEM OPT extension applies only to bachelor's, master's and doctoral degrees (8 CFR 214.2(f)(10)(ii)(C)); certificates, associate's degrees and language courses get `us.stem_opt` `confirmed_negative` with the reason "level not eligible" and the flag `no_stem_opt_extension` (0008/T16). A degree whose primary CIP is 52.12xx stays in scope with the same flag, because no 52.12xx code is on the DHS STEM list (version 2024-07-22). The card says so, and `post_study_work` scores those programs on the 12-month OPT only (R1); English language study gives no OPT at all. The flag is recomputed when a new STEM list version is loaded. |

| BR-18 | **Absence from the Irish lists is not a "no".** A programme on ILEP or TrustEd is `confirmed_official` for Stamp 2. A programme found on neither stays `unknown` until every list row of its provider is linked (automatically or by reconciliation) and the curator confirms; only then can it become `confirmed_negative`, with both list versions as the source. A programme moving from ILEP to TrustEd never loses its status automatically (0008/T6, C1). |
| BR-19 | The placement result is an **estimate**, never an official score: it names the skills tested (grammar, vocabulary, reading, listening) and the ones not tested (writing, speaking), and is never stored on the server (0008/T18, NFR-10). |
| BR-20 | A CEFR band becomes a test score **only through the test owner's official table**, stored as typed boundaries with citation and check date; a range is shown, never a single number; per-skill ranges only where the owner publishes them. Program English minimums carry their scale (`toefl_ibt_scale` ∈ `ibt_0_120`, `ibt_1_6`) and are compared through ETS's concordance (0008/T17, T20). |
| BR-21 | A language course's eligibility for a student permission follows its country: in Ireland, 25+ weeks on the ILEP/TrustEd list, each course giving up to 8 months and three courses at most; in the US, F-1 with F-2 dependants, at most 24 months, no OPT or CPT. These limits are `migration_rules` rows with check date (0008/C2, T14). |

## 7. System modeling

### 7.1 Actors
- **Researcher:** searches, filters, compares, simulates.
- **English learner:** takes the placement test, sees the target score, searches English courses.
- **Curator:** edits, verifies, reviews extractions.
- **Administrator:** configures CIPs, weights and sources; triggers ingestions.
- **Scheduler** (system): runs periodic ingestions.
- **LLM service** (external): extracts fields from pages.
- **Official sources** (external): IPEDS, Scorecard, DHS, SEVP, DAPIP, HUD, ECB; ILEP, TrustEd Ireland, QQI register, CSO. Most reach the system as files uploaded by the administrator (FR-26).

### 7.2 Use cases
```
Researcher  ── UC01 Search and filter programs
            ── UC02 View detail with sources
            ── UC03 Compare programs
            ── UC04 Configure profile and simulate cost/score
            ── UC10 Export CSV
Learner     ── UC12 Take placement test and get the target score
            ── UC01 (English courses)
Curator     ── UC06 Curate program
            ── UC08 Review extraction
            ── UC09 Track state coverage
Admin       ── UC05 Import official sources
            ── UC07 Extract from program website
Scheduler   ── UC05
```

### 7.3 Main use cases

**UC05 — Import official sources**
- **Actor:** Administrator / Scheduler.
- **Precondition:** in-scope CIPs configured (11.xx, 52.12xx, 30.70xx, 30.71xx); the official files for the run uploaded (FR-26) or reachable by an optional downloader.
- **Main flow:** 1. Selects the state and the uploaded source files. 2. The system reads IPEDS (`C<year>_A`, `HD<year>`, `IC<year>_AY`) and creates or updates institutions, campuses (with locality) and master's programs by UNITID × 6-digit CIP. 3. Evaluates each program against the current DHS STEM rule (BR-03, BR-17). 4. Matches campuses against the SEVP list (by stored SEVP campus code, else by name + city, R5). 5. Reads institutional accreditation from DAPIP. 6. Enriches programs with Scorecard earnings and debt (UNITID + CIP4). 7. Loads HUD FMR rents per locality. 8. Inserts or updates records without overwriting fields already verified by a curator. 9. Records the run with its source file and counts.
- **Alternative flows:** 1a. An optional automatic download fails or is blocked → the run is recorded as failed and the administrator uploads the file by hand. 2a. UNITID × CIP6 with 0 completions in the latest year → program created as "to confirm" and not published. 4a. Campus with no exact name + city match in the SEVP list, or a previously matched institution missing from a new list → creates a reconciliation task for the curator, never "not certified" automatically.
- **Postcondition:** the state's programs are created with STEM and SEVP flagged according to BR-02, BR-03 and BR-17; unmatched SEVP cases are open reconciliation tasks; the run points to its source file.

**UC12 — Take placement test and get the target score**
- **Actor:** English learner.
- **Main flow:** 1. Starts the test (no account). 2. Answers the grammar, vocabulary, reading and listening sections; listening clips play from pre-generated audio. 3. The system computes the band per skill and overall (FR-29) and shows the seven test ranges with their citations and the estimate label (BR-19, BR-20). 4. The learner picks a degree program (or a test and score) as the goal; the system shows the gap as a target score (FR-35). 5. The learner opens the English-course search, already filtered by entry level ≤ their band and by the target.
- **Alternative flows:** 3a. A previous result exists in the browser → the change per skill is shown. 4a. No goal chosen → the course search filters by band only.
- **Postcondition:** the result is in the browser only (export as JSON available); nothing is stored on the server.

**UC08 — Review extraction**
- **Actor:** Curator.
- **Main flow:** 1. Opens the extraction queue. 2. Sees the extracted value and the page excerpt side by side. 3. Accepts, corrects or rejects each field. 4. The system stores the value with status `reported_by_program`, source and date, and records it in the history.
- **Alternative flow:** 3a. The page changed since extraction → the system offers to download it again before accepting.

**UC04 — Configure profile and simulate**
- **Actor:** Researcher.
- **Main flow:** 1. Enters budget (amount, currency, period), English score (or a target score), number of dependents, whether the spouse can work, undergraduate field. 2. The system recomputes filter, score and cost for all programs. 3. Shows pass, pass with caveat, undetermined and fail, with the reason for each, and the score with its range and certainty.
- **Alternative flow:** 1a. No English score → the profile may give `english.target` (test + overall); programs whose minimum the target reaches, and programs with conditional admission, appear as pass with caveat (R14).

## 8. Interface prototype
To be done after the UML model. Minimum screens: list with filters and a visual status per dimension; detail with sources; comparison; profile; curator login; program editing with source and history; state coverage dashboard; review queue; official file upload (FR-26); SEVP reconciliation tasks.

## 9. Validation and traceability

### 9.1 Validation log
| Date | Who (role) | What was reviewed | What changed |
|---|---|---|---|
| 2026-11-20 | sponsor | SRS v0.1 + decision questionnaire | curation in the database with login (A1), pilot in Texas (Q04), CIPs including 30.70 (Q05); FR-25, NFR-14 to NFR-16, C-07 to C-09 added |
| 2026-11-21 | sponsor | round-2 questionnaire | all 18 recommendations accepted (record 0002) |
| 2026-11-22 | sponsor | round-3 questionnaire (Q13–Q34) after spikes S-7 and S-8 | 17 recommendations accepted; every Irish register programme shown (Q15), every US level and field at once (Q20, Q21), F-1 4-year admission held until confirmed (Q26), seven tests in the placement result (Q27) (record 0008) |

### 9.2 Traceability (objective → requirement)
| Objective | Requirements |
|---|---|
| SO1 official discovery | FR-01–07, FR-26, BR-03, BR-13, BR-17 |
| SO2 source and verification | FR-08, FR-09, FR-17, FR-25, FR-26, NFR-01, NFR-10, NFR-16, BR-02, BR-09, BR-15, BR-16 |
| SO3 filter and score | FR-18, FR-19, FR-20, BR-04–06, BR-17 |
| SO4 family cost | FR-06, FR-21, BR-07, BR-08 |
| SO5 assisted extraction | FR-12–15, BR-10 |
| SO6 English placement | FR-28, FR-29, NFR-17–19, BR-19, BR-20 |
| SO7 Irish English courses | FR-30, FR-31, FR-33, BR-18, BR-21 |
| SO8 every level and field | FR-02, FR-03, FR-32, FR-34, FR-10, FR-11, NFR-02, BR-01, BR-11, BR-17 |
| SO9 target score | FR-35, FR-18, BR-20 |

## 10. Open issues, risks and out of scope

| Risk | Effect | Mitigation |
|---|---|---|
| Scorecard has master's data only at 4-digit CIP (confirmed by S-1) | ambiguous STEM check, no graduate tuition | IPEDS is the primary discovery source; Scorecard is enrichment only (Q09, R3) |
| Scorecard earnings suppressed in 70% of master's rows (all of 30.70 in Texas) | the career/ROI criterion is often unknown | suppressed values are `unknown` (neutral 50 with a range, R16); the BR-13 caveat stays; consider other official earnings sources after the pilot |
| SEVP list is a PDF only, with no UNITID/OPEID (confirmed by S-4) | about 15 of 110 Texas graduate institutions need a human | parser with row-count checks; exact name + city automatic, the rest as reconciliation tasks; confirmed SEVP campus code stored for later runs (Q10, R5) |
| Government sites block scripts (ice.gov, studyinthestates.dhs.gov and huduser.gov answer 403 or a WAF challenge; nces.ed.gov is unreliable) | scheduled ingestion cannot download the files | manual upload of official files in the curation screen, with hash and version (FR-26, R4); automatic download optional, never required |
| HUD fiscal-year lag (new FMRs take effect every October 1; the open ArcGIS layer still had FY2026 in November 2026) | rent from the wrong year | load only the huduser.gov county file of the year in force, uploaded once a year (R7); store and show the fiscal year with every rent |
| 52.12xx is not STEM (no 52.12xx code on the DHS list, 2024-07-22) | users expect the STEM OPT extension for information systems programs | flag `no_stem_opt_extension` on the card and score on 12-month OPT (BR-17, R1); `claim_mismatch` when the program advertises STEM (BR-03) |
| Institution names differ across sources | wrong matches | match by IPEDS ID (UNITID), OPEID and DAPIP ID, not by name; SEVP is the exception (name + city as a suggestion, then the stored campus code, R5) |
| LLM invents a value | false data published | mandatory literal evidence + human review (BR-10) |
| Immigration rules change in 2026–2027 | outdated conclusions | rules table with check date (BR-12) |
| Website terms of use | blocking or legal issues | official sites only, robots.txt, rate limit (NFR-04, C-05) |
| Scope grows to all states and fields before the pilot | the project never finishes | MVP = 1 state, the Q05 + R2 CIPs |
| Texas is large (many institutions × 4 CIP families) | the pilot and the BR-11 checklist take longer | manual pilot with a sample of ~20 programs; v0.1 may cover a slice of the state, as long as the slice satisfies BR-11 |
| Database loss (curated data exists only there) | curation work lost | daily backup with restore test (NFR-16) and a dump published with each release (FR-23) |
| Scope grows to every level and field in two countries (round 3) | curation never catches up; "complete" loses meaning | everything ingested is labelled "official data only"; completeness and coverage per curation slice (BR-11, FR-34); curation on demand |
| Irish list licences: TrustEd has no terms page; the register's NFQ codes are unlabelled | publishing data we may not re-use, or wrong levels | facts only, contact columns dropped; the author asks QQI (0008/T8); NFQ mapping marked provisional |
| ILEP ends at the end of 2026 and programmes move to TrustEd under new titles | a course shown as eligible loses eligibility, or the reverse | link by provider number + exact title, reconciliation otherwise, never negative automatically (BR-18); `ie.ilep_end` rule shown on the card |
| The placement estimate is read as an official score | users apply with a wrong expectation | estimate label, skills not tested named, ranges never single numbers (BR-19, NFR-17); calibration against real scores before release (SO6) |
| Fixed 4-year F-1 admission in the current 8 CFR 214.2(f)(5)(i) text | doctorates longer than 4 years need an extension | held until the effective date is confirmed (0008/T15) |
| Translation quality and upkeep across many languages | wrong or stale UI text | English is the source of truth; machine-translated drafts are marked and reviewed by native speakers through an open translation platform (Weblate or Crowdin, both free for open source); CI blocks releases with missing wave-1 keys |

**Out of scope:** see §1.4.

## 11. Glossary
| Term | Meaning |
|---|---|
| **F-1 / F-2** | student visa / dependent visa (a spouse on F-2 cannot work) |
| **I-20** | document issued by the school that allows applying for the F-1 |
| **SEVP** | government program that certifies schools authorized to enroll F-1 students |
| **CIP** | Classification of Instructional Programs, the official code for a program's field |
| **DHS STEM list** | CIPs that qualify for the STEM OPT extension |
| **OPT / STEM OPT** | post-study work authorization (12 months + 24-month STEM extension) |
| **CPT** | work/internship authorization during the program, tied to the curriculum |
| **TA / RA / GA** | teaching / research / graduate assistantship: university work that usually waives tuition and pays a stipend |
| **IPEDS / Scorecard** | official databases of the US Department of Education |
| **UNITID / OPEID** | official institution identifiers |
| **Award level** | degree level in IPEDS (master's has its own code) |
| **ISCED-F** | UNESCO international classification of fields of study (2013), used to compare programs across countries |
| **ROR** | Research Organization Registry, a global, open institution identifier |
| **Subdivision** | administrative division of a country (ISO 3166-2): the state in the US, the province in Canada |
| **Country rules module** | code that defines, for a country, the filter criteria, work eligibilities, immigration risk and household income |
| **i18n** | internationalization: building the UI so all text, dates, numbers and currency can be shown in the viewer's language and locale |
| **RTL** | right-to-left scripts, such as Arabic; the layout must mirror without a redesign |
| **hreflang** | HTML/sitemap attribute that tells search engines which language version of a page to show |
| **DSO** | Designated School Official: the international-office staff member who issues the I-20; the official source for whether a program gets an I-20 (BR-09) |
| **FMR (Fair Market Rent)** | HUD's yearly estimate of the 40th-percentile gross rent (rent + essential utilities) by area and bedroom count (0–4); new values take effect each October 1 |
| **ECB** | European Central Bank; its daily euro reference rates (EUR/xxx) are North's only exchange-rate source |
| **IPEDS files (C_A, HD, IC_AY)** | `C<year>_A`: completions by institution × 6-digit CIP × award level (includes `CNRALT`, graduates on temporary visas); `HD<year>`: institution directory (name, city, county, coordinates, identifiers); `IC<year>_AY`: charges by academic year (graduate tuition `TUITION7`, fees `FEE7`) |
| **Locality** | a sub-national area identified by a scheme and a code, e.g. scheme `us_county_fips`, code `48453` (Travis County, TX); rent benchmarks are stored per locality |
| **Stamp 2 / Stamp 2A / Stamp 1G** | Irish immigration permissions: full-time student (20 h/week work in term); non-working dependant of a PhD student; post-study stay for graduates (Third Level Graduate Programme) |
| **ILEP** | Interim List of Eligible Programmes: the Irish government list of programmes that give a student permission; being replaced by TrustEd Ireland |
| **TrustEd Ireland** | QQI's quality mark and eligible-programmes list that replaces ILEP |
| **QQI / NFQ** | Quality and Qualifications Ireland; National Framework of Qualifications, levels 1–10 (6 higher certificate, 7 ordinary bachelor's, 8 honours bachelor's, 9 master's, 10 doctorate) |
| **CEFR** | Common European Framework of Reference for Languages, bands A1–C2 |
| **ISCED level** | UNESCO's level of education (2011): 5 short-cycle tertiary, 6 bachelor's or equivalent, 7 master's or equivalent, 8 doctoral |
| **Curation slice** | a named group of programs (country + filter) whose coverage and completeness are tracked; programs outside every slice are "official data only" |
| **Language course** | a program of kind `language_course`: an English course with CEFR entry and exit levels, exam, weeks and weekly hours |
| **Campus** | a physical site of an institution (name, city, locality, coordinates, SEVP campus code); each program belongs to one campus; SEVP certification is checked per campus |

## References
- Source research reports and consolidated plan: kept outside the repository (A3).
- Execution plan: `execution-plan.md` · model: `uml-model.md`.
- Decision records: `decisions/0001-srs-baseline.md`, `decisions/0002-after-data-spikes.md` (R1–R18, A1–A16; wins over this SRS where they disagree).
- Spike results and source notes: `../spikes/*/RESULT.md`, `sources/*.md`.
- Deployment pattern: `k3s-gitops` repository, `docs/app-nova.md` and `docs/image-updater.md`.
