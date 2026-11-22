---
title: "API contract v0 — programs (official-data slice)"
version: 0.4
status: accepted
date: 2026-11-22
---

# API contract v0 — programs

The first slice of Phase 5: programs discovered from official files only (IPEDS, DHS STEM list, SEVP, DAPIP). Backend and frontend both build against this contract. Field names follow the UML (§2, §8) and decision records 0002–0003.

## Shared types

**VerifiedValue** (BR-02, record 0002/A1, R13):

```json
{ "value": 48210, "status": "confirmed_official", "source_kind": "uploaded_file",
  "source_url": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx",
  "evidence": "IC2023_AY TUITION7", "verified_at": "2026-11-21" }
```

- `status` ∈ `confirmed_official`, `reported_by_program`, `extracted_unverified`, `unknown`, `confirmed_negative`.
- `source_kind` ∈ `page`, `official_list`, `correspondence`, `uploaded_file`.
- `unknown` has `value: null` and may have no source.

**Money**: `{ "amount": 48210, "currency": "USD" }`.

## Program id

`<unitid>-<cip6 without dot>`, for example `228778-110701`. Stable across re-ingestion.

## `GET /api/programs`

Query parameters (all optional): `state` (USPS code; absent = every state, since v0.3), `cip_family` (`11`, `30.70`, `30.71`, `52.12`; repeatable), `stem` (`eligible`, `not_eligible`, `unknown`), `q` (text search over institution name, city and CIP title), `limit` (default 50, max 200), `offset` (default 0).

```json
{
  "total": 107,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": "228778-110701",
      "title": "Computer Science",
      "title_source": "cip_title",
      "degree": "Master's",
      "cip": { "code": "11.0701", "title": "Computer Science.", "family": "11" },
      "institution": { "id": "228778", "name": "The University of Texas at Austin", "control": "public" },
      "campus": { "city": "Austin", "state": "TX" },
      "stem_opt": { "eligible": true, "status": "confirmed_official", "rule_version": "2024-07-22" },
      "flags": [],
      "completions": { "total": 312, "nonresident": 240, "year": "2023-24" },
      "sevp_status": "confirmed_official",
      "accreditation_status": "confirmed_official"
    }
  ]
}
```

- `title` is the CIP title until the program's real name is collected from its site; `title_source` says which (`cip_title` or `program_page`).
- `flags` may contain `no_stem_opt_extension` (52.12xx, record 0002/R1).
- `stem_opt.eligible` is `null` when the status is `unknown`.

## `GET /api/programs/{id}`

```json
{
  "id": "228778-110701",
  "title": "Computer Science",
  "title_source": "cip_title",
  "degree": "Master's",
  "cip": { "code": "11.0701", "title": "Computer Science.", "family": "11", "isced_f": "0613" },
  "institution": {
    "id": "228778", "name": "The University of Texas at Austin", "control": "public",
    "website": "https://www.utexas.edu/",
    "identifiers": { "unitid": "228778", "opeid": "00365800" },
    "accreditation": { "value": { "accreditor": "SACSCOC", "scheme": "us_ed_recognized", "institutional": true }, "status": "confirmed_official", "...": "VerifiedValue fields" },
    "carnegie_classification": { "value": null, "status": "unknown" }
  },
  "campus": {
    "city": "Austin", "state": "TX",
    "locality": { "country": "US", "scheme": "us_county_fips", "code": "48453", "name": "Travis County" },
    "sevp_campus_code": null,
    "intl_authorization": { "value": { "scheme": "sevp", "authorized": true }, "status": "confirmed_official", "...": "VerifiedValue fields" }
  },
  "stem_opt": { "eligible": true, "status": "confirmed_official", "rule_version": "2024-07-22", "claim_mismatch": false, "source_url": "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf" },
  "flags": [],
  "completions": { "total": 312, "nonresident": 240, "year": "2023-24", "source_url": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx" },
  "graduate_tuition_nonresident": {
    "value": { "amount": 48210, "currency": "USD" }, "status": "confirmed_official",
    "note": "institution-wide average for graduate students, not this program's price"
  },
  "not_yet_collected": [
    "admissions.english", "admissions.deadlines", "admissions.other_field_accepted",
    "funding", "cost.program_tuition", "immigration.i20_issued_for_program"
  ],
  "sources": [
    { "source": "ipeds_hd", "file_version": "HD2024", "sha256": "…", "ingested_at": "2026-11-21T03:30:00Z" }
  ]
}
```

- `not_yet_collected` lists the site-only fields (FR-12/13, manual pilot) so the UI can say what is missing instead of hiding it.
- Every value that is shown carries a status; values without a source are never `confirmed_*` (NFR-01).

## `GET /api/sources`

The source files behind the data: `[{ "source", "file_version", "sha256", "uploaded_at", "rows" }]`.

## Errors

`404 {"detail": "program not found"}`; `422` for invalid query parameters (FastAPI default).

## Changes in v0.1 (2026-11-21)

Fixes found while building the UI. They override the examples above where they differ.

1. **`completions`** is a VerifiedValue whose value is `{ "total": 312, "nonresident": 240, "year": "2023-24" }`, with status, source_kind, source_url and verified_at. The same in list items (the list may omit `evidence`).
2. **`stem_opt`** carries every VerifiedValue field: `{ "value": { "eligible": true, "rule_version": "2024-07-22", "claim_mismatch": false }, "status", "source_kind": "official_list", "source_url", "evidence", "verified_at" }`. In list items it is the same object.
3. Plain facts stay plain: `cip`, `identifiers`, `website`, `locality` and `sevp_campus_code` come straight from the uploaded official files and are not VerifiedValues. The detail response lists the file they came from in `sources`.
4. **No UI text in data.** `graduate_tuition_nonresident.note` becomes a code: `"note_code": "institution_wide_average"`. The UI translates codes.
5. **Source ids** are fixed: `ipeds_hd`, `ipeds_c_a`, `ipeds_ic_ay`, `dhs_stem_list`, `sevp_csl`, `dapip`, `scorecard_fos`, `hud_fmr`.
6. **One name for one idea:** both `GET /api/sources` and `sources[]` in the detail use `{ "source", "file_version", "sha256", "uploaded_at", "rows" }`.
7. **`institution.control`** ∈ `public`, `private_nonprofit`, `private_for_profit` (IPEDS `CONTROL` 1/2/3).
8. **`stem=unknown`** matches programs whose `stem_opt.status` is `unknown` (value null), whatever else is true. `eligible` matches `value.eligible = true` with a non-unknown status; `not_eligible` matches `false`.
9. List items carry `sevp` and `accreditation` as **status strings** (`sevp_status`, `accreditation_status`) as before; the detail carries the full VerifiedValues.

## Changes in v0.2 (2026-11-21): price in the list, more filters, sorting

1. **List items** gain `graduate_tuition_nonresident`: the same VerifiedValue as in the detail (`value` is Money or null, `note_code: "institution_wide_average"`), without `evidence`.
2. **New query parameters** on `GET /api/programs` (all optional, combinable with the v0 ones):
   - `control` — repeatable: `public`, `private_nonprofit`, `private_for_profit`.
   - `city` — repeatable, exact city name as served in `campus.city`.
   - `min_tuition`, `max_tuition` — numbers in USD, applied to `graduate_tuition_nonresident.value.amount`. Programs with unknown tuition are excluded when either bound is set.
   - `sevp` — `confirmed` (status `confirmed_official` and authorized) or `unknown`.
   - `accredited` — `true` (institutional accreditation confirmed) or `unknown`.
   - `has_graduates` — `true` (completions total > 0 in the latest year) or `false`.
   - `sort` — `title` (default), `institution`, `city`, `tuition`, `graduates`, `nonresident_graduates`, `nonresident_share` (nonresident ÷ total).
   - `order` — `asc` (default) or `desc`. Unknown values always sort **last**, in both orders. Ties break by institution name, then program id, so pages are stable.
3. **`GET /api/facets`** — counts for building the filter UI, for the current `state` (other filters ignored):

```json
{
  "state": "TX",
  "total": 132,
  "cip_family": { "11": 90, "30.70": 7, "30.71": 25, "52.12": 10 },
  "control": { "public": 80, "private_nonprofit": 45, "private_for_profit": 7 },
  "cities": [ { "city": "Austin", "count": 9 } ],
  "stem": { "eligible": 121, "not_eligible": 11, "unknown": 0 },
  "sevp": { "confirmed": 110, "unknown": 22 },
  "accredited": { "true": 128, "unknown": 4 },
  "has_graduates": { "true": 112, "false": 20 },
  "tuition": { "min": 5000, "max": 60000, "known": 125, "unknown": 7, "currency": "USD" }
}
```

(Numbers above are illustrative.) Cities are sorted by count desc, then name.

### v0.2 clarifications

- `has_graduates=true` means a known total > 0; `false` means a known total of 0. Programs with unknown completions match neither (BR-02), so the two facet counts may not add up to `total`.
- `sevp=confirmed` means `confirmed_official` and authorized; `accredited=true` means `confirmed_official` with `institutional: true`. A `confirmed_negative` matches neither value; a filter for it can be added when such data exists.
- Text sorts use the database collation (case-insensitive), not byte order.
- With `sort=institution` the tie-break is the program id.
- Facet counts use the same predicates as the list filters, so a facet count always equals the list total for that single filter.

## Changes in v0.3 (2026-11-22): every state

- `state` is optional on `GET /api/programs` and `GET /api/facets`. Absent, the list and the
  counts cover every state of the country (the default was `TX` during the Texas pilot).
- `GET /api/facets` returns `state: null` for the whole country, and a new
  `states: [{state, name, count}]` (programs per state, ordered by name, always over the whole
  country, whatever `state` is), for the state picker.
- `cities` is empty when `state` is absent: the same city name in two states is two places.
  The `city` filter still matches by name, so clients send it together with `state`.

## Changes in v0.4 (2026-11-22): Ireland English courses (record 0008, slice E2)

A program has a **kind**: `degree` (every US program) or `language_course` (the English courses
of the Irish ILEP and TrustEd Ireland lists). Everything above still holds for degrees.

1. **Program id** is now any lower-case slug of 2–6 dash-separated parts (`^[a-z0-9]{1,12}(-[a-z0-9]{1,12}){1,5}$`): US `228778-110701`, Ireland `ie-ilep-0018-0001` or `ie-trusted-0058-0012` (the list that first carried the programme; the id does not change when it moves).
2. **Every list item and detail** gains:
   - `kind` (`degree` | `language_course`) and `country` (ISO 3166-1, `US` | `IE`).
   - `language_course`: `null` for a degree; for a course, `{ cefr_entry, cefr_exit, exam, weeks, hours_per_week, price, start_dates }`. Each is a VerifiedValue (`start_dates` a list of them, empty = none collected). `cefr_*` values are CEFR bands `A0`–`C2` (`A0` = pre-A1, as the lists write it); `exam` ∈ `ielts`, `cambridge`, `trinity`, `languagecert`, `toefl`, `pte`, `duolingo`, `tie`, `other`; `weeks` an integer (the minimum written); `hours_per_week` a number (the lowest number written). List values are `confirmed_official` with `source_kind: "uploaded_file"`; text the parser cannot read plainly is `unknown` and the detail keeps the raw text in `evidence`. `price` and `start_dates` are not on the lists: `unknown` / `[]`.
   - `intl_authorization`: the authorization held by the program itself (record 0008/T5): `{ value: { scheme: "ie_ilep" | "ie_trusted", authorized: true }, status, source_kind, source_url, verified_at, evidence (detail only), notes: [...] }`, or `null` for a US degree (SEVP stays on the campus). `notes` lists migration rules attached to the scheme as `{ code, params, source_url, checked_on }`; ILEP courses carry `ie.ilep_end` ("ILEP ends after the second TrustEd round, scheduled for the end of 2026"). The UI translates `code`.
   - List items omit `evidence` in `language_course` and `intl_authorization`, as for tuition.
3. For a course, `cip` is `null`, `stem_opt`, `completions` and `graduate_tuition_nonresident` are `unknown` (tuition with `note_code: null`), `sevp_status` and `accreditation_status` are `unknown`. `campus.state` is the local subdivision code (an Irish county, e.g. `D`, `CO`) and may be `null` (a provider listed at sites in several counties); `campus.city` is `null` when the address names several towns or none North knows (never guessed).
4. **Detail** gains `identifiers: [{ scheme, value }]` (`ie_ilep_ref`, `ie_trusted_ref`); the institution's `identifiers` carry `ie_provider_no` for Irish providers. `not_yet_collected` depends on the kind (courses: `language_course.price`, `language_course.start_dates`). `sources` lists `ie_ilep` and `ie_trusted` for Irish programs (new source ids).
5. **New query parameters** on `GET /api/programs`:
   - `country` — `US` or `IE` (default: the country of `state`, else `US`; unknown country = 422). `state` accepts 1–3 letters (Irish counties); with both, `state` is a subdivision of `country`.
   - `kind` — `degree` or `language_course`.
   - `exam` — repeatable, the codes above.
   - `cefr_entry_max` — a band: courses whose entry level is at or below it. Courses with an unknown entry level are kept, so the card can show them as unknown (BR-02); the facet counts them.
   - `hours_min` — number 0–80: `hours_per_week.value ≥ hours_min` (unknown excluded).
   - `city` works as before (exact name).
6. **`GET /api/facets`** takes `country` and `kind` as scope (like `state`) and returns, in addition: `country`, `kind_scope` (the `kind` asked, or null), `kind: { degree, language_course }`, `exam: { <code>…, unknown }`, `cefr_entry: { A0…C2, unknown }` (exact entry band; the filter is cumulative), `hours_per_week: { min, max, known, unknown }`. `cities` is filled without a `state` when the country's city names are unique (Ireland). `tuition.currency` is the country's (`EUR` for Ireland).

Contacts printed in the official files (record 0009) are never served by this API; they are read only through the admin area.
