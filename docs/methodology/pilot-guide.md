# Manual pilot: filling guide

For whoever fills in `pilot-template.csv` during Phase 4 (about 20 Texas master's programs). Goal: real data for each program, plus a record of where each item was found and how long it took.

Names and rules follow decision record 0002 (`docs/decisions/0002-after-data-spikes.md`) and UML model 1.0.

**Scope: four CIP families** (R1, R2):

| CIP family | What it is | STEM OPT |
|---|---|---|
| 11.xx | Computer and information sciences | on the DHS STEM list (check the 6-digit code) |
| 52.12xx | Management information systems | **no** 52.12xx code is on the DHS STEM list. In scope, but flagged `no_stem_opt_extension` (12-month OPT only). The system sets the flag; you only record the CIP and the STEM result |
| 30.70xx | Data science | check the 6-digit code |
| 30.71xx | Data analytics (incl. 30.7102 Business Analytics) | every 30.71xx code is on the list |

## 1. Before you start

- Copy `pilot-template.csv` and open it in a spreadsheet tool. Do not edit the header row. The header is generated from the schema:
  `uv run --with jsonschema python3 -I schema/csv_to_json.py --print-header > docs/methodology/pilot-template.csv`
- Use one row per program and one program per row.
- Freeze the first columns (`id`, `institution.name`, `name`). Hide the `.evidence` columns while you search if that helps, but fill them in before you finish.
- A complete, fictitious filled-in program is in `schema/examples/program.example.json`.
- Export as CSV (UTF-8, comma separator).
- `in_strategy` and `flags` are not columns: the system derives them (0002/A11, R1).

## 2. How the columns work

Each verifiable field has six groups of columns:

| Column | What goes in it |
|---|---|
| `<field>.value` (or `<field>.value.<part>`) | the value. Money has `.amount`, `.currency` (`USD`) and `.per` |
| `<field>.status` | one of the 5 statuses (section 3) |
| `<field>.source_kind` | the kind of source (section 3.1). Empty = `page` |
| `<field>.source_url` | the exact page or file URL where you saw it (`https://...`). May be empty only for `correspondence` |
| `<field>.evidence` | the literal sentence from the source, copied in English (short, at most about 300 characters). **Never** a name or an email address |
| `<field>.verified_at` | the date you saw it (`YYYY-MM-DD`). If you leave it empty, `collected_on` is used |

Formats:
- Numbers: digits only, with a dot for decimals. No `$` and no thousands separators (`1800`, not `$1,800`).
- Booleans: `true` or `false`.
- Simple lists (e.g. `academic.start_terms.value`): items separated by `;` (e.g. `fall;spring`). For a list you confirmed is empty, write `[]`.
- Dates: `YYYY-MM-DD`.
- Columns with `.0.`, `.1.`, `.2.` are slots of a list (identifiers, funding opportunities, deadlines). Fill them in order and leave unused slots empty; empty slots are dropped.

## 3. Choosing the status

| Situation | Status | Fill in |
|---|---|---|
| A government source shows it: DHS STEM list, SEVP school list, IPEDS/Scorecard, HUD, DAPIP | `confirmed_official` | value, source_kind, source_url, evidence |
| The international office (DSO) confirms the **I-20** for the program, on its official page or in a written reply (R11) | `confirmed_official` | value, source_kind (`page` or `correspondence`), evidence |
| The university or program shows it: program page, graduate catalog, bursar, or a written reply from them | `reported_by_program` | value, source_kind, source_url, evidence |
| A source says **no** to a yes/no question (e.g. "PTE is not accepted", "no child care center", "no assistantships for master's students") | `confirmed_negative` | value = `false`, source_kind, source_url, evidence |
| You did not find it | leave all of the field's cells **empty** | nothing (the converter records `unknown`) |
| `extracted_unverified` | do not use | reserved for the LLM extractor (BR-10) |

**Polarity rule (R12):**
- A "no" to a yes/no field is **always** `confirmed_negative` with value `false`. Never write `confirmed_official` or `reported_by_program` with `false`: the converter rejects it.
- Numeric and text fields **never** use `confirmed_negative`. "Test not accepted" is not a minimum score: write it in `admissions.english.<test>_accepted` (`false` + `confirmed_negative`) and leave `<test>_min` empty.
- SEVP and accreditation count as yes/no: a campus confirmed as not certified is `campus.intl_authorization.value.authorized = false` + `confirmed_negative`.
- Enum fields (e.g. `admissions.gre.value = not_required`, `...tuition_coverage.value = none`) are text: use `reported_by_program` or `confirmed_official`, never `confirmed_negative`.

Rules:
- **Never guess.** "Probably 80" counts as not found. Unknown is not the same as no (BR-02).
- **Aggregators never confirm** (U.S. News, Peterson's, forums, rankings). Use them only as leads to find the official page (BR-09). If only an aggregator has the information, leave the field empty and say so in `remarks`.
- If two official pages disagree, record the more specific one (program page over the university's general page) and describe the conflict in `remarks`.
- If a value depends on the track (thesis or non-thesis, on campus or online), record the on-campus, full-time value and note the difference in `remarks`.

### 3.1 Choosing the source kind (R13)

| `source_kind` | When | `source_url` |
|---|---|---|
| `page` (default if empty) | a web page: program, department, graduate school, international office, bursar | required |
| `official_list` | an official list or dataset you looked up online: DHS STEM list, SEVP school search, IPEDS, Scorecard, DAPIP, HUD | required (the list or dataset URL) |
| `uploaded_file` | an official file that was downloaded and kept as a file (e.g. the SEVP PDF, the HUD county file) | required (the official download URL) |
| `correspondence` | a written reply (email or form answer) from the international office or the program | may be empty; put the office's official page if there is one |

## 4. Fields that need care

- **Institution identifiers**: slot 0 = `unitid`, slot 1 = `opeid`, slot 2 = `dapip` if you looked it up. Do **not** put any SEVP code here (the schema rejects `sevp_campus`).
- **Accreditation (`institution.accreditation`)** (R10): the criterion is "institutional accreditation by a recognized accreditor". Look the institution up in DAPIP. `value.accreditor` = the agency name, `value.scheme` = `us_ed_recognized`, `value.institutional` = `true`. Never write "regional". (The converter cannot record a confirmed absence of accreditation; if you find one, leave the field empty and write it in `remarks`.)
- **Carnegie (`institution.carnegie_classification`)** (0002/A12): the research classification as the Carnegie site writes it (e.g. `R1`, `R2`); `confirmed_official` with `official_list`. It moved here from `academic.research_classification`.
- **Campus and locality (`campus.*`)** (R17): `campus.name` (e.g. `Main Campus`) and `campus.city`. `campus.locality.country` = `US`, `campus.locality.scheme` = `us_county_fips`, `campus.locality.code` = the 5-digit county FIPS of the campus (e.g. `48453` for Travis County), `campus.locality.name` = the county name. Latitude and longitude are optional (IPEDS HD has them). Leave `campus.id` empty.
- **SEVP (`campus.intl_authorization`)** (R5, R11): SEVP certification lives on the campus. `value.scheme` = `sevp`, `value.authorized` = the F-1 flag of the SEVP list. Write the 15-character SEVP **campus** code (e.g. `DAL214F00932000`) in `campus.sevp_campus_code`. Do not use the 12-character school code: it is shared by several institutions.
- **STEM (`eligibilities.0`)**: write `us.stem_opt` in `rule_key` and the list date (`2024-07-22`) in `rule_version`. Look up the program's primary 6-digit CIP (`classifications.0.code`) on the DHS STEM list:
  - on the list (or in a whole 2-digit series: 14, 26, 27, 40): `true` + `confirmed_official`, `source_kind` = `official_list`;
  - CIP known and not on the list (every 52.12xx): `false` + `confirmed_negative`;
  - CIP unknown but the program says it is STEM: `true` + `reported_by_program` (BR-03).
  In every case, also fill in `immigration.stem_opt_claimed_by_program` with what the program itself says, and set `eligibilities.0.claim_mismatch` = `true` if the program claims STEM but the CIP is not on the list.
- **I-20 for this program (`immigration.i20_issued_for_program`)** (R11): the international office (DSO) is the official source. Its official page (lists of eligible programs, or "online programs are not eligible for I-20") or its written reply = `confirmed_official`. The department page alone = `reported_by_program`. A confirmed "no" = `false` + `confirmed_negative`.
- **Day-1 CPT (`immigration.cpt_from_first_term`)**: `true` only if the program allows CPT from the first term. This raises the immigration risk. A confirmed "no" = `false` + `confirmed_negative`.
- **English (`admissions.english.*`)**: for each test (TOEFL iBT, IELTS Academic, Duolingo, PTE Academic) there is `<test>_accepted` (yes/no) and `<test>_min` (number). Accepted with a minimum: `<test>_accepted = true` and `<test>_min` = the number, both `reported_by_program`. Not accepted: `<test>_accepted = false` + `confirmed_negative`, `<test>_min` empty.
- **Tuition**: use the non-resident or international rate. Record what the page shows (`per` = `credit_hour`, `term`, `academic_year`...). Fill in `cost.tuition_fees_program_total` only if the program publishes a total.
- **I-20 amounts**: `cost.i20_requirement_student` and `cost.i20_requirement_per_dependent`, usually on the international office's "estimated expenses" or "financial requirements" page.
- **Funding**: first answer `funding.available_to_masters`. If the program says master's students do not get funding: `false` + `confirmed_negative`, and leave the slots empty. Otherwise use one slot per kind (TA, RA, GA...). Inside each slot, leave empty anything the page does not say (for example "open to international").
- **Deadlines (`admissions.deadlines.N`)** (R18): up to 3 slots, **each with its own status and source**, because deadlines often come from different pages (graduate school vs department). Fill them in this order of priority: fall final deadline for international applicants, funding deadline, spring final deadline. Each slot: `value.term`, `value.term_year`, `value.applicant`, `value.kind`, `value.date`, plus `status`, `source_url`, `evidence`. A slot with a value but no source is rejected. A deadline you did not find is simply left out (there is no "unknown" deadline).
- **Earnings (`career.median_earnings`)**: from the Scorecard, field of study (4-digit CIP) + master's level. Use `population` = `federal_aid_recipients` (BR-13).
- **HUD rent (`cost.rent_reference_monthly`)**: monthly Fair Market Rent for the campus county, `br0`..`br4`. HUD publishes it per FMR area; use the area that contains the county in `campus.locality.code` (K5). In the database it is stored once per county.

### Allowed values (enums)

| Field | Values |
|---|---|
| `modality.value` | `in_person`, `hybrid`, `online` |
| `institution.control` | `public`, `private_nonprofit`, `private_for_profit` |
| `...source_kind` | `page`, `official_list`, `correspondence`, `uploaded_file` |
| `immigration.internship.value` | `required`, `optional`, `not_offered` |
| `academic.thesis_option.value` | `thesis_only`, `non_thesis_only`, `both` |
| `academic.start_terms.value` | `fall`, `winter`, `spring`, `summer` |
| `academic.credits_required.value.unit` | `us_semester_credit_hour`, `us_quarter_credit_hour`, `ects` |
| `...per` (money) | `credit_hour`, `term`, `academic_year`, `calendar_year`, `month`, `program_total`, `one_time` |
| `funding.opportunities.N.type` | `TA`, `RA`, `GA`, `fellowship`, `scholarship`, `tuition_waiver`, `other` |
| `...tuition_coverage.value` | `full`, `partial`, `none` |
| `...availability.value` | `guaranteed`, `competitive`, `rare` |
| `admissions.gre.value` | `required`, `optional`, `not_required`, `waivable` |
| `admissions.deadlines.N.value.term` | `fall`, `winter`, `spring`, `summer` |
| `admissions.deadlines.N.value.applicant` | `international`, `domestic`, `all` |
| `admissions.deadlines.N.value.kind` | `priority`, `final`, `funding_consideration`, `rolling` |
| `career.median_earnings.value.population` | `federal_aid_recipients`, `all_graduates`, `program_reported` |

## 5. When you cannot find something

1. Spend at most about 5 minutes per field. After that, leave it empty and add a line to `remarks`: `not found: <field>`.
2. Try, in order: the program page, the graduate catalog, the graduate school (admissions, assistantships), the international office (ISSS/OISS), the bursar (tuition and fees), then a `site:` search on the university domain.
3. Do not email anyone during the first pass. Finish every program first.

## 6. When to email the international office or the program

After the first pass, email only about fields that block the filter or the finalist list:
- whether the school issues an I-20 for this program (and for the hybrid format, if there is one);
- conditional admission without an English score;
- whether assistantships are open to **master's** and **international** students;
- the I-20 amount per dependent, if it is not published.

Send one email per university, with all your questions in a list.

**Recording a written reply (R13), without names or emails:**
- `source_kind` = `correspondence`.
- `status`: a reply from the **international office about the I-20** = `confirmed_official` (R11). Any other reply = `reported_by_program`. A "no" to a yes/no question = `false` + `confirmed_negative`.
- `source_url`: the office's official page if the answer refers to one; otherwise leave it empty.
- `verified_at`: the date of the reply (required).
- `evidence`: `Written reply from the <office>, YYYY-MM-DD: "<the one sentence that answers the question>"`. Write the office (e.g. "international office", "graduate program office"), **never** the name, signature or email address of the person. The schema rejects any email address in `evidence`.
- Keep the full message privately, outside the repository (the data and this repository are public). It is never published.
- Start the `remarks` line with `EMAIL:` and list the fields that only came by email. That list is one of the pilot's deliverables.

## 7. Tracking time and method

| Column | How to fill it in |
|---|---|
| `collected_on` | the date you filled in the row (the default for `verified_at`) |
| `where_found` | the kinds of pages you used, separated by `;` (e.g. `program page; grad catalog; bursar; ISSS; DHS list`) |
| `minutes_spent` | total minutes of active work on the row: start the timer when you open the first page, pause it when you stop. Include time spent writing emails, not time spent waiting for replies |
| `remarks` | what was hard, `not found: ...`, `EMAIL: ...`, conflicts between pages, and fields that an LLM could easily extract from the page |

These columns do not go into the JSON. They feed `pilot-report.md`.

## 8. Converting and validating

```
uv run --with jsonschema python3 -I schema/csv_to_json.py my-pilot.csv --out data/pilot/
```

Each valid row becomes `data/pilot/<id>.json`. Invalid rows are listed with the field and the reason (for example `confirmed_official` without `source_url`, or `reported_by_program` + `false`). Fix them and run the command again.

## 9. Mapping: spreadsheet to schema

| Spreadsheet | Schema (`schema/program.schema.json`) |
|---|---|
| column name `a.b.c` | JSON path `a → b → c` |
| `<field>.value`, `.status`, `.source_kind`, `.source_url`, `.evidence`, `.verified_at` | a `VerifiedValue` object |
| `<field>.value.<part>` | part of an object value (e.g. `Money.amount`) |
| `<list>.N.<field>` | item N of a list (`institution.identifiers`, `classifications`, `eligibilities`, `funding.opportunities`); empty slots are dropped |
| `admissions.deadlines.N.value.<part>`, `admissions.deadlines.N.status`... | item N of `admissions.deadlines`, itself a `VerifiedValue` (R18) |
| `campus.*`, `campus.locality.*` | the program's campus and its locality (R17) |
| all cells of a field empty | `{"value": null, "status": "unknown", ...}` |
| `.verified_at` empty and status filled in | `collected_on` |
| `.source_kind` empty and status filled in | `page` |
| value or source filled in without a status | error: choose a status |
| `schema_version` | added automatically (`0`) |
| `in_strategy`, `flags` | not columns: derived by the system |
| `collected_on`, `where_found`, `minutes_spent`, `remarks` | not written to the JSON (method only) |
| `immigration.*` | `$defs.immigration_us` (the `country` = `US` module) |
