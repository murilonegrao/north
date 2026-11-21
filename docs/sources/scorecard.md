# Source: College Scorecard (U.S. Department of Education)

Spike S-1, run on 2026-11-21. Scripts: `spikes/s1_scorecard/`. Result: `spikes/s1_scorecard/RESULT.md`.

## What it is

The Department of Education's public dataset about institutions that take part in federal student aid (Title IV). It has an institution-level file and a **Field of Study (FoS)** file. One FoS row is one combination of institution (UNITID) + **4-digit CIP** + credential level. Completion counts come from IPEDS; earnings come from Treasury (IRS) and debt comes from NSLDS (federal loans).

## Access

| Channel | URL | Notes |
|---|---|---|
| Bulk download page | https://collegescorecard.ed.gov/data/ | links change with each release (date in the file name) |
| FoS file (used) | https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_10152026.zip | zip, 33.9 MB; one CSV of 197.7 MB, 223,587 rows, 230 columns |
| Institution file (used) | https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_11022026.zip | zip, 24.2 MB; has STABBR, CITY, LATITUDE/LONGITUDE (the FoS file has no state column) |
| Full history | https://ed-public-download.scorecard.network/downloads/College_Scorecard_Raw_Data_11022026.zip | not downloaded |
| Data dictionary | https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx | sheets `FieldOfStudy_Data_Dictionary` and `FieldOfStudy_Cohort_Map` |
| FoS technical docs | https://collegescorecard.ed.gov/files/FieldOfStudyDataDocumentation.pdf | "Version: October 2026" |
| API | https://api.data.gov/ed/collegescorecard/v1/schools | needs an api.data.gov key; FoS data is nested under `latest.programs.cip_4_digit` |

API notes: the spike used `DEMO_KEY` (5 calls, `school.state=TX`, `per_page=100`, `all_programs_nested=true`). The ingestor should read the key from the `NORTH_API_DATA_GOV_KEY` environment variable (the probe script already does this and falls back to `DEMO_KEY`). The API returned 411 TX schools and the same 99 master's programs / 48 institutions in the target CIPs as the bulk file, so both channels hold the same data. For ingestion, the bulk file is simpler: one download, no key, a versioned file name (good for `ingestion_runs.file_version`, RNF-03).

## Useful columns (FoS file) → North model

| Column (exact) | Meaning (dictionary) | North field |
|---|---|---|
| `UNITID` | IPEDS ID | `institution_identifiers(scheme='unitid')` |
| `OPEID6` | 6-digit OPE ID (main campus) | `institution_identifiers(scheme='opeid')` (6-digit; SEVP/DAPIP may use 8 digits) |
| `INSTNM` | institution name | `institutions.name` (seed only; matching never uses the name) |
| `CONTROL` | in the 2026 CSV it is a text label: `Public`, `Private, nonprofit`, `Private, for-profit` (the dictionary lists 1–4) | `institutions.control` |
| `MAIN` | main-campus flag | helper |
| `CIPCODE` | **4-digit CIP, no dot** (e.g. `1107`); 100% of rows have 4 characters | `program_classifications` (cip2020, 4-digit only) |
| `CIPDESC` | CIP title | `classifications.title` |
| `CREDLEV` | credential level; **5 = Master's Degree** | filter; `programs.degree` |
| `IPEDSCOUNT1`, `IPEDSCOUNT2` | awards in AY2022-23 and AY2023-24 (IPEDS) | `programs.career` / size indicator |
| `EARN_MDN_1YR` | median earnings 1 year after completion, pooled AY2020-21 + AY2021-22, 2024 dollars | `programs.career.median_earnings_1yr` (with the RN-13 caveat) |
| `EARN_MDN_4YR`, `EARN_MDN_5YR` | 4 and 5 years after completion | `programs.career` |
| `EARN_COUNT_WNE_1YR` | earnings cohort size | helper |
| `DEBT_ALL_STGP_EVAL_MDN` | median Stafford + Grad PLUS debt | `programs.funding` (helper) |
| `DISTANCE` | 0 not reported, 1 no credential fully online, 2 some, 3 all can be fully online | helps RN-14 (online without F-1), as a hint only |
| `CITY`, `STABBR`, `LATITUDE`, `LONGITUDE` (institution file) | location | `institutions.city`, `subdivision_id` |

**No graduate tuition.** `TUITIONFEE_IN` / `TUITIONFEE_OUT` in the institution file are undergraduate tuition and fees. Graduate tuition has to come from IPEDS (IC_AY) or from the program page.

## Coverage measured in Texas (master's, CREDLEV = 5)

Script `spikes/s1_scorecard/analyze_fos_tx.py`, output `spikes/s1_scorecard/out/summary_scorecard.json`.

- Master's in TX, all CIPs: 2,319 rows at 105 institutions.
- Target CIPs:

| Family | Programs (UNITID × CIP4) | Institutions | Public / Nonprofit / For-profit |
|---|---|---|---|
| 11.xx computing | 83 | 46 | 59 / 20 / 4 |
| 52.12 information systems | 9 | 9 | 4 / 4 / 1 |
| 30.70 data science | 7 | 7 | 5 / 2 / 0 |
| **Total** | **99** | **48** | 68 / 26 / 5 |

CIP4 breakdown: 1101 (25), 1104 (24), 1110 (17), 1107 (12), 5212 (9), 3070 (7), 1108 (2), 1102, 1103, 1105 (1 each).

Fill rate for the 99 target programs (`PS` = privacy-suppressed, `NA` = null):

| Column | Value | PS | NA |
|---|---|---|---|
| `EARN_MDN_1YR` | 28 (28%) | 69 (70%) | 2 |
| `EARN_MDN_4YR` | 22 | 75 | 2 |
| `EARN_MDN_5YR` | 16 | 81 | 2 |
| `DEBT_ALL_STGP_EVAL_MDN` | 22 | 77 | 0 |
| `IPEDSCOUNT2` | 95 | 0 | 4 |

All 7 data-science (30.70) programs have suppressed earnings. Nationally, in the same CIP families, `EARN_MDN_1YR` has a value in 427 of 1,729 master's programs (25%), so the Texas rate is not unusual.

Several rows have `IPEDSCOUNT2 = 0` or `NA` (for example SMU 1104/1105/1108, all of 52.12 at Dallas Baptist, DeVry, LeTourneau, SMU and University of Dallas). The FoS row can exist because of past NSLDS/earnings data even when the program had no graduates recently. Do not read a FoS row as proof that the program is currently offered.

## Limitations

1. **4-digit CIP only.** The DHS STEM list (RF-03) is keyed by 6-digit CIP, so a 4-digit code cannot decide STEM eligibility by itself (RN-03). Which 6-digit codes under 11.xx, 52.12 and 30.70 are on the list is for spike S-3 to confirm; it was not checked here.
2. **Unit = institution × CIP4 × level, not a named program.** A school with "MS Computer Science" and "MS Software Engineering" under the same CIP4 shows up as one row.
3. **Earnings cover only federally aided graduates** (RN-13). F-1 students are generally not eligible for Title IV aid, so this does not describe them. Also 70% of target rows are suppressed.
4. **No graduate tuition, no deadlines, no admission requirements.** Those come from curation or extraction.
5. Debt and earnings are computed at the OPEID6 level and repeated across branches.
6. The format changes between releases: missing codes moved from `NULL`/`PrivacySuppressed` to `NA`/`PS`; `CONTROL` is text in the CSV. The parser has to be tolerant and the ingestion has to record the file version.
7. CIP 30.70 (data science) only exists in CIP 2020. Programs that report data science under 11.07, 27.05, 52.13 etc. do not show up as 30.70.

## License and terms

U.S. federal government data. Works of the U.S. government are generally not covered by copyright (17 U.S.C. §105). The site does not show an explicit license on the data page; that was not checked further. The API goes through api.data.gov, which needs a key and applies rate limits (DEMO_KEY is very limited). Cite "U.S. Department of Education, College Scorecard" and the file version.

## Update frequency

Several releases a year. The changelog shows releases on 2026-10-15 (new FSA/Treasury data, IPEDS Winter 2025-26) and 2026-11-02 (IPEDS revisions). The file name carries the release date (`_MMDDYYYY`), which works as `file_version`.
