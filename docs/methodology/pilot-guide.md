# Manual pilot: filling guide (site-only fields)

For whoever fills in `pilot-site-template.csv` (20 Texas master's programs, one row per program and field). Decision record 0004 (`docs/decisions/0004-official-data-first.md`, O2) reduced the pilot: official files now discover the programs and fill everything a government source publishes, so the pilot collects **only what exists on each program's own website**. It has two goals:

1. real site data for each program, plus a record of where each item was found and how long it took;
2. a gold set to measure LLM-assisted extraction later (0004/O3, O4).

Names and rules follow decision record 0002 (`docs/decisions/0002-after-data-spikes.md`), UML model 1.0 and `schema/program.schema.json`.

## 1. What is already automatic (do not collect)

Ingestion of the official files (IPEDS, DHS STEM list, SEVP, DAPIP, Scorecard, HUD) already fills these for every program. They are **not columns** of the site template:

- institution (name, control, identifiers UNITID/OPEID), campus, city and county (locality);
- CIP code and title (6-digit), completions;
- STEM OPT eligibility (DHS list) and the `no_stem_opt_extension` flag for 52.12xx;
- SEVP authorization of the campus;
- institutional accreditation (DAPIP);
- institution-wide graduate tuition (IPEDS, an average, not the program's price);
- Scorecard earnings and debt, HUD rent for the county.

If the site contradicts one of these (for example the program page says "STEM" but the CIP is 52.12xx, or the city is different), do not change anything: write it in `remarks`.

## 2. What to collect (site only)

| Group | Rows (`field`) |
|---|---|
| Program | `program_page` (the program's page URL), `program_name` (its real name, e.g. "Master of Science in Computer Science"), `collected_on` (the date) |
| Modality and F-1 | `modality`, `immigration.f1_compatible_modality` |
| I-20 for this program | `immigration.i20_issued_for_program` (DSO rule R11, section 7) |
| English | `admissions.english.*`: each test accepted (yes/no) and its minimum, TOEFL section minimums, IELTS band minimum, waiver and its criteria, conditional admission and its details |
| Background | `admissions.accepts_other_undergrad_area`, `admissions.prerequisites` |
| STEM claim | `immigration.stem_opt_claimed_by_program` (what the program says; the official STEM result is ingested) |
| Tests and grades | `admissions.gre`, `admissions.gmat`, `admissions.min_gpa_4scale` |
| Application | `admissions.application_fee`, `admissions.application_fee_waiver`, `admissions.deadlines[0]`, `[1]` (each with its own source, R18) |
| Academic | `academic.credits_required`, `academic.duration_months`, `academic.start_terms`, `academic.thesis_option` |
| Cost | `cost.tuition_international`, `cost.fees`, `cost.tuition_fees_program_total`, `cost.student_health_insurance` (each with its basis: per credit, term, year...) |
| I-20 financial requirement | `cost.i20_requirement_student`, `cost.i20_requirement_per_dependent` |
| Funding | `funding.available_to_masters` and `funding.opportunities[0]`, `[1]` (type TA/RA/GA..., tuition coverage, stipend, hours per week, open to international, open to master's, availability) |
| Work during the program | `immigration.cpt_available`, `immigration.cpt_from_first_term` (Day-1 CPT), `immigration.internship` |
| Family | `family.family_housing_on_campus`, `family.family_housing_rent`, `family.dependent_insurance_available`, `family.dependent_insurance_cost` |

The site template has **12 columns** and **62 rows per program** (3 program rows, 43 single fields, 2 deadline rows, 2 funding opportunities of 7 rows each): **1,240 rows** for the 20 programs. The full template, by comparison, has 561 columns in one row per program.

**Time:** expect roughly **30 to 45 minutes per program** on the first pass (about 10 to 15 hours for all 20), plus emails. This is an estimate; measuring it is part of the pilot (`minutes_spent`).

## 3. Which programs

The 20 rows of `pilot-site-template.csv` are pre-filled with `program_id` = `<unitid>-<cip6 without dot>` (the API id, `docs/api/programs-v0.md`). Details of each candidate are in `pilot-candidates.csv`.

| Candidate | `program_id` | Institution | City | CIP |
|---|---|---|---|---|
| TX-01 | `228787-110101` | The University of Texas at Dallas | Richardson | 11.0101 Computer and Information Sciences, General |
| TX-02 | `228769-110101` | The University of Texas at Arlington | Arlington | 11.0101 Computer and Information Sciences, General |
| TX-03 | `227216-110103` | University of North Texas | Denton | 11.0103 Information Technology |
| TX-04 | `228778-110101` | The University of Texas at Austin | Austin | 11.0101 Computer and Information Sciences, General |
| TX-05 | `227757-110101` | Rice University | Houston | 11.0101 Computer and Information Sciences, General |
| TX-06 | `223232-110701` | Baylor University | Waco | 11.0701 Computer Science |
| TX-07 | `224226-110401` | Dallas Baptist University | Dallas | 11.0401 Information Science/Studies |
| TX-08 | `226091-110701` | Lamar University | Beaumont | 11.0701 Computer Science |
| TX-09 | `224147-110101` | Texas A & M University-Corpus Christi | Corpus Christi | 11.0101 Computer and Information Sciences, General |
| TX-10 | `461795-110701` | North American University | Stafford | 11.0701 Computer Science |
| TX-11 | `225511-111003` | University of Houston | Houston | 11.1003 Computer and Information Systems Security/Auditing/Information Assurance |
| TX-12 | `226833-110101` | Midwestern State University | Wichita Falls | 11.0101 Computer and Information Sciences, General |
| TX-13 | `228149-110701` | St. Mary's University | San Antonio | 11.0701 Computer Science |
| TX-14 | `229115-307001` | Texas Tech University | Lubbock | 30.7001 Data Science, General |
| TX-15 | `228723-307001` | Texas A&M University-College Station | College Station | 30.7001 Data Science, General |
| TX-16 | `228246-307001` | Southern Methodist University | Dallas | 30.7001 Data Science, General |
| TX-17 | `227216-307001` | University of North Texas | Denton | 30.7001 Data Science, General |
| TX-18 | `229814-521201` | West Texas A & M University | Canyon | 52.1201 Management Information Systems, General |
| TX-19 | `229063-521201` | Texas Southern University | Houston | 52.1201 Management Information Systems, General |
| TX-20 | `229027-521207` | The University of Texas at San Antonio | San Antonio | 52.1207 Knowledge Management |

One `program_id` is one institution + 6-digit CIP. If the site has more than one master's program under the same CIP (for example an MS and a professional master's), fill in the on-campus, full-time MS and list the others in `remarks`. If you find no master's program for the CIP at all, leave the row empty and write `no program found` in `remarks`.

## 4. Before you start

- Copy `pilot-site-template.csv` and open it in a spreadsheet tool. Do not edit the header row or the `program_id`, `field`, `field_label` and `hint` columns. Filter by `program_id` to work on one program at a time. The template is generated from the schema and the candidates:
  `uv run --with jsonschema python3 -I schema/csv_to_json.py --site-template docs/methodology/pilot-candidates.csv > docs/methodology/pilot-site-template.csv`
- Keep `pilot-candidates.csv` open beside it for the institution names.
- A fictitious filled program is `SITE_TEST_VALUES` in `schema/csv_to_json.py`; a complete fictitious program document is `schema/examples/program.example.json`.
- Export as CSV (UTF-8, comma separator).

## 5. How the rows and columns work

One row per program and field. Pre-filled: `program_id`, `field` (the schema path), `field_label` (plain English) and `hint` (what to look for and the format). You fill in:

| Column | What goes in it | If left empty |
|---|---|---|
| `value` | the value in the format of the `hint` (see "Compact values" below) | with `status` also empty: the field is left out (stays "not yet collected") |
| `status` | one of the statuses (section 6) | `reported_by_program`; for a yes/no field answered `no`: `confirmed_negative` |
| `source_kind` | the kind of source (section 6.1) | `page` |
| `source_url` | the exact page URL where you saw it, if it is not the program page | the URL of the program's `program_page` row (not used for `correspondence` or `unknown`) |
| `evidence` | the literal sentence from the source, copied in English (short, at most about 300 characters). **Never** a name or an email address | nothing |
| `verified_at` | the date you saw it (`YYYY-MM-DD`), only if it differs from `collected_on` (e.g. the date of an email reply) | the program's `collected_on` row |
| `minutes_spent`, `remarks` | method only (section 10) | — |

The first three rows of each program are plain rows (only `value` counts): `program_page` (the program page URL; it becomes `official_url` and the default `source_url`), `program_name` (it becomes the program's name in the app) and `collected_on` (the date; **required** once anything is filled in for that program).

**"Searched and not found"**: write `unknown` in `status` and leave `value` empty. It is recorded as unknown with the date you searched. An empty row means "not looked at" and is simply left out; never write `false` or `0` for something you did not find. Deadlines are never `unknown`: leave a deadline row empty if you did not find one.

**Compact values:**

| Kind | Format | Examples |
|---|---|---|
| yes/no | `yes`/`no` (or `true`/`false`) | `yes` |
| number | digits, dot for decimals | `80`, `6.5`, `3.0` |
| choice | one of the values in the `hint` | `in_person`, `waivable`, `partial` |
| list | values separated by `;` | `fall;spring` |
| money | `amount [currency]`, USD if no currency; `$` and thousands commas are tolerated | `75`, `75 USD` |
| rate | `amount [currency] per`; per = `credit_hour`, `term`, `academic_year`, `calendar_year`, `month`, `program_total`, `one_time` | `1450 credit_hour`, `42000 USD academic_year`, `1800 month` |
| credits | `amount [unit]`, semester credit hours if no unit | `30`, `45 us_quarter_credit_hour` |
| TOEFL sections | `section=score` separated by `;`, only the published ones | `reading=20;writing=22` |
| deadline | `term|year|applicant|kind|date` (date empty for `rolling`) | `fall|2027|international|final|2027-02-01` |

**Lists**: each deadline is one row `admissions.deadlines[i]`, with its own status and source (R18). Each funding opportunity is a group of rows `funding.opportunities[i].type`, `...tuition_coverage`, `...stipend` and so on; `type` is a plain row (no status) and is required for a filled opportunity. Two slots of each are pre-filled; if you need a third, copy the rows and change `[1]` to `[2]` (at most 3). Empty slots are dropped.

## 6. Choosing the status

| Situation | Status | Fill in |
|---|---|---|
| The international office (DSO) confirms the **I-20** for the program, on its official page or in a written reply (R11) | `confirmed_official` | value, source_kind (`page` or `correspondence`), evidence |
| The university or program shows it: program page, graduate catalog, graduate school, bursar, housing, or a written reply from them | `reported_by_program` | value, source_kind, source_url, evidence |
| A source says **no** to a yes/no question (e.g. "PTE is not accepted", "no family housing", "no assistantships for master's students") | `confirmed_negative` (the default for `no`) | value = `no`, plus source if not the program page, evidence |
| You searched and did not find it | `unknown` | nothing else (value empty) |
| You did not look | leave the row **empty** | nothing |
| `extracted_unverified` | do not use | reserved for the LLM extractor (BR-10) |

In the site pilot, `confirmed_official` is used almost only for the I-20 (R11). Everything else a program or university publishes is `reported_by_program`.

**Polarity rule (R12):**
- A "no" to a yes/no field is **always** `confirmed_negative` with value `false`. Never write `confirmed_official` or `reported_by_program` with `false`: the converter rejects it.
- Numeric and text fields **never** use `confirmed_negative`. "Test not accepted" is not a minimum score: write it in `admissions.english.<test>_accepted` (`false` + `confirmed_negative`) and leave `<test>_min` empty.
- Enum fields (e.g. `admissions.gre.value = not_required`, `...tuition_coverage.value = none`, `immigration.internship.value = not_offered`) are text: use `reported_by_program` or `confirmed_official`, never `confirmed_negative`.

Rules:
- **Never guess.** "Probably 80" counts as not found. Unknown is not the same as no (BR-02).
- **Aggregators never confirm** (U.S. News, Peterson's, forums, rankings). Use them only as leads to find the official page (BR-09). If only an aggregator has the information, leave the field empty and say so in `remarks`.
- If two official pages disagree, record the more specific one (program page over the university's general page) and describe the conflict in `remarks`.
- If a value depends on the track (thesis or non-thesis, on campus or online), record the on-campus, full-time value and note the difference in `remarks`.

### 6.1 Choosing the source kind (R13)

| `source_kind` | When | `source_url` |
|---|---|---|
| `page` (default if empty) | a web page: program, department, graduate school, international office, bursar, housing, health insurance | required |
| `correspondence` | a written reply (email or form answer) from the international office or the program | may be empty; put the office's official page if there is one |
| `official_list`, `uploaded_file` | government lists and files: normally not needed here, ingestion records them | required |

## 7. Fields that need care

- **Name and page (`program_name`, `program_page`)**: the name exactly as the program page writes it, with the degree (e.g. "Master of Science in Data Science"). It replaces the CIP title in the app. `program_page` is the program's own page, not the department home page; it is also the default source of every other row of the program, so fill in `source_url` only when a value comes from another page.
- **Modality (`modality`, `immigration.f1_compatible_modality`)**: `in_person`, `hybrid` or `online`. `f1_compatible_modality` = `true` when the format lets an F-1 student keep status (in person, or hybrid with an in-person option); `false` + `confirmed_negative` when the site says the program is fully online or not available to F-1 students.
- **I-20 for this program (`immigration.i20_issued_for_program`)** (R11): the international office (DSO) is the official source. Its official page (lists of eligible programs, or "online programs are not eligible for I-20") or its written reply = `confirmed_official`. The department page alone = `reported_by_program`. A confirmed "no" = `false` + `confirmed_negative`.
- **STEM claim (`immigration.stem_opt_claimed_by_program`)**: `yes` if the program advertises itself as STEM or STEM OPT eligible. The official STEM result comes from the DHS list; the system flags a mismatch.
- **English (`admissions.english.*`)**: for each test (TOEFL iBT, IELTS Academic, Duolingo, PTE Academic) there is `<test>_accepted` (yes/no) and `<test>_min` (number). Accepted with a minimum: `<test>_accepted = yes` and `<test>_min` = the number. Not accepted: `<test>_accepted = no` (becomes `confirmed_negative`), `<test>_min` empty. Section minimums: `toefl_ibt_section_min` as `reading=20;...`; `ielts_band_min` = the minimum on each IELTS band. Waivers: `waiver_available` and `waiver_criteria` (e.g. "degree from a country where English is the official language"). Conditional admission: `conditional_admission` and `conditional_admission_details` (e.g. "through the university's intensive English program").
- **Another undergraduate field (`admissions.accepts_other_undergrad_area`, `admissions.prerequisites`)**: `true` if applicants from another field are accepted (often with leveling courses); write the required courses or knowledge in `prerequisites`. A clear "a bachelor's in computer science is required" = `false` + `confirmed_negative`.
- **GRE and GMAT (`admissions.gre`, `admissions.gmat`)**: each `required`, `optional`, `not_required` or `waivable` (record 0005). These are choices, not yes/no: never `confirmed_negative`.
- **GPA (`admissions.min_gpa_4scale`)**: the minimum on a 4.0 scale. If it applies only to the last 60 hours or similar, put that in `evidence`.
- **Application fee (`admissions.application_fee`, `admissions.application_fee_waiver`)**: the international fee if it differs. The waiver is yes/no (record 0005): `yes` if the program or graduate school offers a fee waiver to international applicants (conditions in `evidence`); a clear "no waivers" = `no` (`confirmed_negative`, R12).
- **Deadlines (`admissions.deadlines[i]`)** (R18): one row per deadline, **each with its own status and source**, because deadlines often come from different pages (graduate school vs department). Fill them in this order of priority: fall final deadline for international applicants, funding deadline, then (in a third row you add) the spring final deadline. Value: `term|year|applicant|kind|date`. A deadline you did not find is simply left out (there is no "unknown" deadline).
- **Tuition and fees (`cost.*`)**: use the non-resident or international rate for this program (a program-specific rate beats the university table). Record what the page shows with its basis (`per` = `credit_hour`, `term`, `academic_year`...). Fill in `cost.tuition_fees_program_total` (no `per`) only if the program publishes a total. Do not copy the IPEDS average: it is already ingested.
- **Academic (`academic.*`)**: credits with their unit (semester credit hours by default); typical full-time duration in months (e.g. "2 years" = `24`); start terms (`fall;spring`); thesis option (`thesis_only`, `non_thesis_only` or `both`).
- **Student health insurance (`cost.student_health_insurance`)**: the mandatory student plan if billed separately, with its basis (e.g. `3200 academic_year`).
- **I-20 amounts (`cost.i20_requirement_student`, `cost.i20_requirement_per_dependent`)**: usually on the international office's "estimated expenses" or "financial requirements" page; record the basis (`academic_year`, `calendar_year`...).
- **Funding**: first answer `funding.available_to_masters`. If the program says master's students do not get funding: `no`, and leave the opportunity rows empty. Otherwise use one slot per kind (TA, RA, GA...). Inside each slot, leave empty anything the page does not say (for example "open to international"); `type` is required for a filled slot.
- **CPT and internship (`immigration.cpt_available`, `immigration.cpt_from_first_term`, `immigration.internship`)**: `cpt_from_first_term` (Day-1 CPT) is `true` only if the program allows CPT from the first term; this raises the immigration risk. A confirmed "no" = `false` + `confirmed_negative`. `internship` = `required`, `optional` or `not_offered`.
- **Family (`family.*`)**: only what the university publishes: on-campus family housing (yes/no and its monthly rent, `per` = `month`) and whether the student health plan covers a spouse and children (yes/no and the cost of the family tier, with its basis). Leave the rest empty.

### Allowed values (enums)

| Field | Values |
|---|---|
| `modality` | `in_person`, `hybrid`, `online` |
| `source_kind` | `page`, `official_list`, `correspondence`, `uploaded_file` |
| `immigration.internship` | `required`, `optional`, `not_offered` |
| credits unit | `us_semester_credit_hour`, `us_quarter_credit_hour`, `ects` |
| rate basis (`per`) | `credit_hour`, `term`, `academic_year`, `calendar_year`, `month`, `program_total`, `one_time` |
| `funding.opportunities[i].type` | `TA`, `RA`, `GA`, `fellowship`, `scholarship`, `tuition_waiver`, `other` |
| `...tuition_coverage` | `full`, `partial`, `none` |
| `...availability` | `guaranteed`, `competitive`, `rare` |
| `admissions.gre`, `admissions.gmat` | `required`, `optional`, `not_required`, `waivable` |
| `academic.thesis_option` | `thesis_only`, `non_thesis_only`, `both` |
| `academic.start_terms` | `fall`, `winter`, `spring`, `summer` |
| deadline term / applicant / kind | `fall`, `winter`, `spring`, `summer` / `international`, `domestic`, `all` / `priority`, `final`, `funding_consideration`, `rolling` |

## 8. Workflow

1. Pick the next row. Start the timer when you open the first page.
2. Filter the sheet to the program. Find the program page; fill in `program_page`, `program_name` and `collected_on`.
3. Work through the groups of section 2 in order. Try, in order: the program page, the graduate catalog, the graduate school (admissions, deadlines, assistantships), the international office (ISSS/OISS: I-20, financial requirement, CPT), the bursar (tuition and fees), housing and student health insurance, then a `site:` search on the university domain.
4. Spend at most about 5 minutes per field. After that, write `unknown` in `status` (searched, not found).
5. Stop the timer, fill in `minutes_spent` on the program's `collected_on` row (section 10), go to the next program.
6. Do not email anyone during the first pass. Finish every program first, then email (section 9).
7. Convert and fix (section 11).

## 9. When to email, and how to record a reply without personal data

After the first pass, email only about fields that block the filter or the finalist list:
- whether the school issues an I-20 for this program (and for the hybrid format, if there is one);
- conditional admission without an English score;
- whether assistantships are open to **master's** and **international** students;
- the I-20 amount per dependent, if it is not published.

Send one email per university, with all your questions in a list.

**Recording a written reply (R13, 0002/K9):**
- `source_kind` = `correspondence`.
- `status`: a reply from the **international office about the I-20** = `confirmed_official` (R11). Any other reply = `reported_by_program`. A "no" to a yes/no question = `false` + `confirmed_negative`.
- `source_url`: the office's official page if the answer refers to one; otherwise leave it empty.
- `verified_at`: the date of the reply (required).
- `evidence`: `Written reply from the <office>, YYYY-MM-DD: "<the one sentence that answers the question>"`. Write the office (e.g. "international office", "graduate program office"), **never** the name, signature or email address of the person. The schema rejects any email address in `evidence`.
- Keep the full message privately, outside the repository (the data and this repository are public). It is never published.
- Write `EMAIL` in the `remarks` of each row whose value only came by email. That list is one of the pilot's deliverables.

## 10. Tracking time and method

| Where | How to fill it in |
|---|---|
| `collected_on` row, `value` | the date you collected the program (the default for `verified_at`) |
| `collected_on` row, `minutes_spent` | total minutes of active work on the program: start the timer when you open the first page, pause it when you stop. Include time spent writing emails, not time spent waiting for replies. Optionally also put minutes on single rows that took long |
| any row, `remarks` | what was hard, `EMAIL`, conflicts between pages or with the official data, `easy for an LLM` when the value was plainly on the page |
| `collected_on` row, `remarks` | general notes on the program (several master's under the same CIP, no program found...) |

`minutes_spent` and `remarks` do not go into the JSON. Where each value was found is the `source_url` itself. They feed `pilot-report.md`.

## 11. Converting, validating and merging

```
uv run --with jsonschema python3 -I schema/csv_to_json.py my-pilot-site.csv --site-only --out data/pilot-site/
```

Each program with anything filled in becomes `data/pilot-site/<program_id>.json`, a **site patch**. Programs with nothing filled in are skipped. Errors are listed per program with the row or field and the reason (for example a rate without its basis, a missing `collected_on` row, or `reported_by_program` + `no`). Fix them and run the command again.

A site patch looks like this (full format and merge rules in the docstring of `schema/csv_to_json.py`):

```json
{
  "format": "north.site_patch.v0",
  "schema_version": 0,
  "program_id": "228778-110101",
  "fields": {
    "name": "Master of Science in Computer Science",
    "admissions.english.toefl_ibt_min": { "value": 79, "status": "reported_by_program", "...": "VerifiedValue fields" },
    "admissions.deadlines": [ { "value": { "term": "fall", "...": "..." }, "status": "reported_by_program", "...": "..." } ]
  }
}
```

The backend merges it onto the program ingested from official files with the same id: each key is a path in `schema/program.schema.json` and replaces the whole value at that path (lists are replaced, not appended); keys that are absent stay as they are; an explicit `unknown` is stored as "searched, not found" with its date; keys outside the site-only fields are rejected; no patch is applied to a program id that was not ingested.

## 12. Texas institutions with no SEVP match (check by hand)

Separate from the 20 rows: the SEVP spike (`spikes/s4_sevp/RESULT.md`) left 8 Texas graduate institutions with no match in the SEVP list, plus one with the right name in another city. None of them is a pilot candidate. Look each one up on the SEVP school search page (Study in the States) in a browser and write the result (found as / not found, campus code if found, date) in the SEVP section of `pilot-report.md`. Do not add rows to the site template for them; the curation screen will turn these into reconciliation tasks.

| UNITID | Institution | City | What the spike found |
|---|---|---|---|
| 224554 | East Texas A&M University | Commerce | renamed in 2024; SEVP probably still lists "Texas A&M University-Commerce" (false negative) |
| 477039 | West Coast University-Texas | Richardson | school listed, but every campus has city "Irvine, CA" |
| 429094 | AOMA Graduate School of Integrative Medicine | Austin | not found under any name tried |
| 420705 | Bakke Graduate University | Dallas | not found |
| 224712 | Episcopal Theological Seminary of the Southwest | Austin | not found |
| 481401 | Grace School of Theology | Conroe | not found |
| 497462 | Redeemers University North America | Greenville | not found |
| 484756 | University of Phoenix-Texas | Dallas | not found |
| 458973 | Strayer University-Texas | Farmers Branch | same name, but no SEVP campus in Farmers Branch (closest: Cedar Hill) |

"Not found" means probably not certified, but only a human check on the school search page can say so; never record `false` from the spike alone.

## 13. Mapping: site spreadsheet to schema

| Spreadsheet | Schema (`schema/program.schema.json`) |
|---|---|
| `program_id` | the id of the ingested program (`<unitid>-<cip6>`), not a schema field |
| `program_page`, `program_name` rows | `official_url`, `name` |
| `collected_on` row | not written; default `verified_at` |
| `field` = `a.b.c` | the `VerifiedValue` at JSON path `a → b → c` (`immigration.*` = `$defs.immigration_us`) |
| `value`, `status`, `source_kind`, `source_url`, `evidence`, `verified_at` | the fields of that `VerifiedValue`; a compact `value` is split into its parts (e.g. `MoneyRate.amount/currency/per`) |
| `admissions.deadlines[i]` | item i of `admissions.deadlines`, itself a `VerifiedValue` (R18) |
| `funding.opportunities[i].<field>` | `<field>` of item i of `funding.opportunities`; empty slots are dropped |
| value and status empty | left out of the patch (not looked at) |
| status `unknown`, value empty | `{"value": null, "status": "unknown", "verified_at": ...}` (searched, not found) |
| `minutes_spent`, `remarks` | not written to the JSON (method only) |

## Appendix: the full template (programs not covered by official files)

`pilot-template.csv` (561 columns, one complete program document per row, wide format) stays for programs that official files do not cover, for example programs in other countries, or a US program missing from IPEDS. It is converted without `--site-only`:

```
uv run --with jsonschema python3 -I schema/csv_to_json.py --print-header > docs/methodology/pilot-template.csv
uv run --with jsonschema python3 -I schema/csv_to_json.py my-pilot.csv --out data/pilot/
```

It uses the same statuses as above but a wide layout: each field has six columns `<field>.value` (or `<field>.value.<part>`), `.status`, `.source_kind`, `.source_url`, `.evidence`, `.verified_at`; lists use slots `.0.`, `.1.`, `.2.`; all cells of a field empty = `unknown`; booleans `true`/`false`; method columns `collected_on`, `where_found`, `minutes_spent`, `remarks`. There is no default `source_url` and no default status: write the status for every field you fill. Notes for the fields ingestion fills for Texas:

- Use the `id` slug (institution + degree + field + campus). `in_strategy` and `flags` are not columns: the system derives them (0002/A11, R1).
- **Official sources** (a government list, file or dataset) = `confirmed_official` with `source_kind` = `official_list` (looked up online) or `uploaded_file` (a kept download; `source_url` = the official download page, 0002/K10).
- **Institution identifiers**: slot 0 = `unitid`, slot 1 = `opeid`, slot 2 = `dapip` if you looked it up. Never an SEVP code (the schema rejects `sevp_campus`).
- **Accreditation** (R10): institutional accreditation by a recognized accreditor (US: DAPIP). `value.accreditor` = the agency, `value.scheme` = `us_ed_recognized`, `value.institutional` = `true`. Never "regional". The converter cannot record a confirmed absence; write it in `remarks`.
- **Carnegie** (0002/A12): `institution.carnegie_classification` as the Carnegie site writes it (`R1`, `R2`).
- **Campus and locality** (R17): `campus.name`, `campus.city`; `campus.locality` = country, scheme (`us_county_fips` in the US), code, name. Leave `campus.id` empty.
- **International authorization** (R5, R11): `campus.intl_authorization` with `value.scheme` (`sevp` in the US) and `value.authorized`; in the US the 15-character SEVP campus code goes in `campus.sevp_campus_code`. A campus confirmed as not authorized = `authorized = false` + `confirmed_negative`.
- **Classification and eligibility**: `classifications.0.code` (US: `cip2020`, 6 digits). `eligibilities.0` with `rule_key` (`us.stem_opt`), `rule_version` (list date, `2024-07-22`) and `result`: on the list = `true` + `confirmed_official`; code known and not on the list = `false` + `confirmed_negative`; code unknown but the program claims it = `true` + `reported_by_program` (BR-03). Also fill in `immigration.stem_opt_claimed_by_program` and set `eligibilities.0.claim_mismatch` = `true` on a mismatch.
- **Earnings** (`career.median_earnings`): US Scorecard, field of study (4-digit CIP) + master's level, `population` = `federal_aid_recipients` (BR-13).
- **Reference rent** (`cost.rent_reference_monthly`): US HUD Fair Market Rent for the campus county, `br0`..`br4` (K5).
- Other enums of the full template: `institution.control` = `public`, `private_nonprofit`, `private_for_profit`; `academic.thesis_option.value` = `thesis_only`, `non_thesis_only`, `both`; `academic.start_terms.value` = `fall`, `winter`, `spring`, `summer` (a `;`-separated list, `[]` = confirmed empty); `career.median_earnings.value.population` = `federal_aid_recipients`, `all_graduates`, `program_reported`.
