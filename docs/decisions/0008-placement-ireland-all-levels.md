---
title: "Decision record 0008 — English placement, Ireland and every degree level"
status: accepted
date: 2026-11-22
supersedes: "SRS §1.4 scope (master's only, tech CIPs only, US only); Q05 and R2 (scope CIPs); BR-11 as a per-state rule; BR-17 as a 52.12-only rule; NFR-02 volume"
inputs: [docs/elicitation/round-3-scope.md, spikes/s7_ie_lists/RESULT.md, spikes/s8_us_levels/RESULT.md, docs/sources/ilep.md, docs/sources/trusted-ireland.md, docs/sources/qdr-ireland.md, docs/sources/ireland-immigration-rules.md, docs/sources/rtb-rent-index.md, docs/sources/cefr-test-mappings.md]
---

# 0008 — English placement, Ireland and every degree level

The author answered the round-3 questionnaire (Q13–Q34, session S08, 2026-11-22). They accepted 17 recommendations and chose differently on five: every Irish register programme is shown, not only the visa-eligible ones (Q15); every US award level and every field, at once (Q20, Q21); the fixed 4-year F-1 admission stays out until its effective date is confirmed (Q26); the placement result shows all seven tests (Q27). This record fixes the names. Where the SRS or the UML disagree, this record wins.

## Findings that drove the decisions

Summarized in `docs/elicitation/round-3-scope.md` §4, with the sources listed above. The ones that shape the model:

- Irish students on Stamp 2 cannot bring dependants (Family Reunification Policy, 2026-06-12, §5.4), except PhD students and some recognised scholarship holders (Stamp 2A, spouse cannot work).
- ILEP (1,066 English programmes, 78 HE) and TrustEd Ireland (6,711 HE, 54 English) are programme-level lists with no programme on both; provider numbers carry over (`0058` → `TE0058`). QQI's register (11,705 programmes at NFQ 6–10, ISCED-F field) shares no identifier with them.
- IPEDS lists 267,595 US programs at every award level; STEM OPT extension only for bachelor's, master's and doctoral degrees.
- Official CEFR tables exist for seven tests; TOEFL iBT moved to a 1–6 scale on 2026-01-21.

## Decisions

| # | Decision | Exact consequence |
|---|---|---|
| T1 | **Slice order** (Q13 a) | E1 English placement → E2 Ireland English courses → E3 Ireland higher education → E4 US every level and field. `execution-plan.md` gets these as phases after the current slice |
| T2 | **Who travels, per program kind** (Q14 a) | `Profile.travelling_party` = `{language_course: alone \| with_family, degree: alone \| with_family}`, default `{language_course: alone, degree: with_family}`. The family criterion and the family cost use the dependents only when the party for that program's kind is `with_family`. The family criterion comes from the country module (new `CountryRules.family(program, profile)`). Ireland: on Stamp 2 dependants are not allowed → criterion `family` is `fail` with the reason and the rule cited; NFQ 10 research programmes give `pass_with_caveat` (dependants on Stamp 2A, spouse cannot work, schooling needs approval). The Hosting Agreement and Critical Skills routes are `MigrationRule` rows shown as notes, not evaluated per program (they depend on a job, not on the programme) |
| T3 | **Irish universe = the QQI register plus the immigration lists** (Q15 b) | Every active register programme at NFQ 6–10 becomes a `Program` (identifier scheme `ie_irq`), plus every ILEP/TrustEd row; a list row is linked to a register programme when provider and title match exactly, otherwise it stays its own programme until reconciled. Eligibility is the program-level authorization in T5. A register programme that matches no list row is `unknown` for Stamp 2, never `confirmed_negative` automatically (see C1) |
| T4 | **NFQ 6–10, every field** (Q16 a) | Irish HE scope: NFQ levels 6, 7, 8, 9, 10; field from the register's ISCED-F code (`classification scheme = isced_f_2013`) |
| T5 | **Authorization can sit on the program** | `Authorization` gains a level: campus (`sevp`) or program (`ie_ilep`, `ie_trusted`). New `Program.intl_authorization: VerifiedValue<Authorization>` used by the `ie` module; the `us` module keeps `Campus.intl_authorization`. List rows give `confirmed_official` with `source_kind = uploaded_file` |
| T6 | **ILEP → TrustEd transition** (Q17 a) | Identifier schemes `ie_ilep_ref` (e.g. `0018/0001`), `ie_trusted_ref`, and institution scheme `ie_provider_no` (the number without the `TE` prefix). A programme leaving ILEP links automatically to a TrustEd row when `ie_provider_no` and the normalized title match exactly; anything else opens a `ReconciliationTask` (reason `ie_list_move`). Never `confirmed_negative` automatically. `MigrationRule` `ie.ilep_end` records the announced end (after the second TrustEd round, end of 2026) and the card shows "eligible through ILEP, which ends …" |
| T7 | **Irish rent: CSO RIQ02** (Q18 a) | `Locality` scheme `ie_cso_riq02` (446 locations) with `ie_county` as fallback; `RentBenchmark.source = cso_riq02`, period = quarter (`2025Q4`), bedrooms 1, 2, 3, 4+ (4 = "4+"). Bedrooms rule unchanged: ceil((1 + travelling dependents) / 2), max 4. One-bedroom minimum in Ireland (RIQ02 has no studio column) |
| T8 | **Ask the publishers** (Q19 a) | The author emails QQI (TrustEd re-use terms; meaning of the NFQ codes in the register copy) and SEVP (whether an English-language-training flag per school is published). Until a reply, the inferred NFQ mapping and the ILEP terms are used, marked provisional in the source notes. Replies stored privately (BR-15) |
| T9 | **US: every award level at once** (Q20 b) | FR-02 ingests every IPEDS award level (certificates below bachelor's, associate's, bachelor's, postbaccalaureate certificate, master's, post-master's certificate, doctor's research/scholarship, professional practice, other). Tuition by level: undergraduate `TUITION3`/`FEE3` (out of state), graduate `TUITION7`/`FEE7`, professional doctorates `OSPROF1..9`. Certificate-only institutions report charges in `IC<year>_PY`, which is added to the upload list |
| T10 | **US: every field** (Q21 c) | No scope CIP list: every CIP is ingested. The tech CIPs (11.xx, 52.12xx, 30.70xx, 30.71xx) stay as the first curated slice (T11). Supersedes Q05 and R2 as scope rules |
| T11 | **Ingest everything, curate on demand** (Q22 a) | Every ingested program is published with the label "official data only" until a curator works on it. New table `curation_slices` (name, country, filter as JSON, created_by, created_at); coverage (FR-10) and completeness (BR-11, FR-11) are computed per slice, not per state. Curation and extraction start from a slice or from a program a user shortlists. The first slices: Texas tech master's (the existing 132), Dublin English courses |
| T12 | **Generic level** (Q23 a) | `Program.level: VerifiedValue<Level>` with `Level` = ISCED 2011 level (`5` short-cycle, `6` bachelor's or equivalent, `7` master's or equivalent, `8` doctoral) plus `credential` (`certificate`, `associate`, `bachelor`, `postgraduate_certificate`, `master`, `doctorate_research`, `doctorate_professional`, `language_course`). The source codes stay as classifications: scheme `us_ipeds_awlevel`, scheme `ie_nfq`. The map from source code to `Level` lives in `classification_maps` (`origin = proposed` until the author reviews it). Language courses have no ISCED level |
| T13 | **English course = a program of kind `language_course`** (Q24 a) | `Program.kind` ∈ `degree`, `language_course`. A language course has `language_course.cefr_entry`, `cefr_exit` (CEFR band, e.g. `B1`), `exam` (normalized: `ielts`, `cambridge`, `trinity`, `languagecert`, `toefl`, `pte`, `duolingo`, `tie`, `other`, raw text kept in `evidence`), `weeks`, `hours_per_week`, `price` (Money), `start_dates` (list, each a VerifiedValue). All are VerifiedValues; list fields are `confirmed_official` from ILEP/TrustEd; price and start dates come from the school site (FR-13). The ILEP `Awarding Body` spellings are normalized through a map in `data/reference/ie_exam_names.csv` |
| T14 | **US ESL programs** (Q25 a) | Ask SEVP (T8). Meanwhile the curator records ESL leads from the SEVP list by hand for one city, as `language_course` programs with `source_kind = page` (the school's own site); no automatic ingestion. Rule in the `us` module: F-1 with F-2 dependants, at most 24 months, no OPT or CPT |
| T15 | **F-1 fixed 4-year admission not recorded yet** (Q26 b) | Not a `MigrationRule` and no caveat until the effective date of the current 8 CFR 214.2(f)(5)(i) text is confirmed. Open item C3 |
| T16 | **STEM OPT extension by level** | Rule `us.stem_opt` evaluates only bachelor's, master's and doctoral degrees (`Level` 6–8 with a degree credential); certificates, associate's degrees and language courses get `confirmed_negative` with the reason "level not eligible" and the flag `no_stem_opt_extension`. Supersedes BR-17 as a 52.12-only rule: 52.12xx still carries the flag because of its CIP |
| T17 | **Placement result shows seven tests** (Q27 c) | IELTS Academic, TOEFL iBT, Cambridge English Scale, Duolingo English Test, PTE Academic, LanguageCert Academic, Trinity ISE. Boundaries typed by us from each owner's official table, with citation and check date, in `data/reference/cefr_test_mappings.csv`; no document, prose or logo copied (Pearson forbids reproduction) |
| T18 | **Result label** (Q28 a) | "Grammar, vocabulary, reading and listening. Writing and speaking were not tested." Per-skill ranges only where the owner publishes them (TOEFL, Cambridge); otherwise an overall range labelled "reading and listening only"; always "estimate, not an official score" |
| T19 | **Old TOEFL scale** (Q29 a) | The 0–120 range shown as secondary, from ETS's concordance, until 2028-01-31; then hidden (a `MigrationRule` `toefl.legacy_scale_end`) |
| T20 | **Scale marker on TOEFL minimums** (Q30 a) | New field `admissions.english.toefl_ibt_scale` ∈ `ibt_0_120`, `ibt_1_6` beside `toefl_ibt_min` and `toefl_ibt_section_min`; existing values are `ibt_0_120`. The filter converts through the concordance table before comparing |
| T21 | **Item bank in the repo** (Q31 a) | `data/placement/items/*.yaml`, one file per skill, each item with `id`, `skill`, `band`, `prompt`, `options`, `answer`, `explanation`, `author`, `version`; the bank has a `bank_version`. Reviewed in pull requests; validated by a JSON Schema in `schema/placement-item.schema.json` |
| T22 | **Pre-generated audio** (Q32 a) | Listening clips are generated once from our own scripts and stored with the item (`audio_file`, `voice`, `speed`), served as static files; the script text ships too, for accessibility |
| T23 | **Placement feeds the course filter now** (Q33 a) | `Profile.english.estimated` = `{band per skill, overall band, taken_at, bank_version}`; language courses filter on `cefr_entry ≤ overall band`; the degree program the user chose gives the target (`english.target`, R14), and the gap is shown as "target score" |
| T24 | **No CEFR descriptor quoted** (Q34 a) | Items are written from our own band guidelines (`docs/design/english-placement-v0.md`); no Council of Europe descriptor is copied until someone reads the Companion Volume licence by hand |

## Clarifications

| # | Clarification |
|---|---|
| C1 | **Absence from the Irish lists.** A register programme can be set to `confirmed_negative` for Stamp 2 only after every ILEP and TrustEd row of its provider is linked (automatically or by reconciliation) and the curator confirms; the source is both list versions. Until then it is `unknown`. Same spirit as R5 for SEVP: a matching failure never reads as "not eligible". *Applied without asking; say so if you disagree.* |
| C2 | **Irish money and post-study rules** go to the `ie` module as `MigrationRule` rows with check date: €10,000 a year (€833 a month up to 8 months), fees paid in full under €6,000 or at least €6,000, private medical insurance, €300 registration, 8 months per 25-week English course and three courses at most, the 7-year student cap (8 at NFQ 9+), work 20 h / 40 h, Stamp 1G 12 months (NFQ 8) and 12 + 12 (NFQ 9+). The visa financial requirement figure of BR-07 is the €10,000 rule for Ireland; there is no per-dependant amount |
| C3 | Volume: about 280,000 programs (US 267,595, Ireland about 12,000 plus list rows). NFR-02 moves to p95 < 500 ms on filtered listings over that table |

## Open after this record

- C3 / T15: effective date of the fixed 4-year F-1 admission in 8 CFR 214.2(f)(5)(i).
- Replies from QQI and SEVP (T8).
- Author review of the source code → ISCED level map (T12), as with R9.
- The city for the first US ESL leads (T14).
- The PhD dependant school levy in Ireland (no current figure found).
