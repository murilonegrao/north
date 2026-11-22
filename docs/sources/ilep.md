# Source: ILEP, Interim List of Eligible Programmes (Ireland)

Spike S-7, run on 2026-11-22. Script: `spikes/s7_ie_lists/profile_ie_lists.py`. Result: `spikes/s7_ie_lists/RESULT.md`.

## What it is

The Irish immigration service's list of programmes for which a non-EEA student can get a study visa and a **Stamp 2** permission. It is published by Immigration Service Delivery (ISD), Department of Justice, Home Affairs and Migration. Four programme types: English language (at least 25 weeks), higher education major awards at NFQ 6–10, professional awards and foundation programmes.

The ILEP is being replaced by **TrustEd Ireland** (QQI, see `trusted-ireland.md`):

- "The ILEP is closed." Providers not already listed must get TrustEd authorisation before they can recruit non-EEA students.
- Providers already listed keep recruiting "until the ILEP ceases operation". No end date is published.
- "Eligible programmes will not appear on both lists, please check BOTH" (ISD and TrustEd pages). North has to read both.
- The ISD page says "the final ILEP update was published on 20 June 2025". Even so, the media library has files dated 2026-02-11, 2026-07-09, 2026-09-17 and 2026-09-22, and the sheet title says "with effect from 11 February 2026". So the content still changes, probably through removals and corrections.

## Where and in what format

| Item | Value |
|---|---|
| Page that links the file | https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-options/a-third-level-course-or-a-language-course/ (the same page also shows the list as a searchable HTML table) |
| Info page (criteria, status) | https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-options/interim-list-of-eligible-programmes-ilep/ (it **does not** link the XLSX) |
| File used | https://www.irishimmigration.ie/wp-content/uploads/2026/09/Interim-List-of-Eligible-Programmes-updated-22-September-2026.xlsx |
| Format | XLSX, sheets `ILEP` (data) and `Sheet1` (empty). Row 1 is the title, row 2 the header, data from row 3. The sheet reaches row 1,899, but only 1,151 rows are filled. |
| Size / hash | 133,232 bytes, sha256 `b6f4be81df990a4a8e6adae6aab993924666770865fafdc904ec75dc2ea9eda2`, Last-Modified 2026-09-22 12:51 GMT |
| Newer version? | None. The WordPress media API (`/wp-json/wp/v2/media?search=Interim List` and `?search=ILEP`) lists, newest first: 22-Sep-2026 xlsx, 18-Sep-2026 csv, 17-Sep-2026 xlsx/csv, Jul-2026 xlsx/csv, 11-Feb-2026 xlsx, 20-Jun-2025 xlsx. A CSV exists for some versions, but the page links only the XLSX. |
| Criteria PDFs | `EL-Prog-Criteria-21-March-2025.pdf`, `HE-Prog-Criteria-21-March-2025.pdf`, `Foundation-Criteria-21-March-2025.pdf` (linked from the info page) |

The file name changes with every update (`...updated-DD-Month-YYYY.xlsx` under `/wp-content/uploads/YYYY/MM/`), so a fetcher has to read the link from the page. The media API is a second way to find it.

## Fields

| Column (header as written) | North | Notes |
|---|---|---|
| Programme Reference No | `program_identifiers(scheme='ie_ilep_ref')` | `NNNN/NNNN`: provider number / programme number. 1,141 rows match `9999/9999`, 10 rows `9999/999`. One reference is duplicated (`0372/0005`, 2 rows). |
| (derived) provider code | `institution_identifiers(scheme='ie_ilep_provider')` | First 4 digits. 76 codes for 77 provider names, one-to-one. **TrustEd keeps the same number with a `TE` prefix** for the 6 providers found on both lists (0058→TE0058, 0041→TE0041…). |
| Programme Type | program kind | `English Language` 1,066, `Higher education - Major award` 78, `Professional` 4, `Foundation` 3 |
| Provider | matching / display | 77 providers |
| Addresss (sic) | campus city / county | Institutional postal address. The county is derived from the text and the Eircode routing key. |
| **Contact Email, Contact Telephone, Contact Name** | `institution_contacts` (private, record 0009) | Named staff. Filled in all 1,151 rows. Stored only in the private contacts table, latest file only; never served publicly, never in values, evidence or logs. Read in the admin area (admin role, audited). |
| Programme Title | program name | Not unique per provider: 314 rows share provider + title with another row (variants by hours, level or exam). |
| Awarding Body | awarding body | 97 distinct values, written freely (`IELT`, `IELTS`, `Cambridge`, `Cambridge ESOL`…) |
| Award Title | award | |
| Duration (ECTS /Weeks per year) | duration | Free text, 28 distinct values. Weeks for English (25 weeks: 1,029 rows), ECTS for HE (60/90/120/180/240). |
| Hours per week | contact hours (English) | Free text: `15 hours`, `15`, `15 Hours`… |
| NFQ Level | level (`nfq_ie`) | `n/a` 1,070 (English and professional), 8: 34, 9: 31, 7: 9, 10: 4, 6: 2, 5: 1 |
| Entry Level / Exit Level | CEFR range (English) | Free text: `B1`, `A2+`, `A1 / A2 / B1 / B2 / C1`… |

There is **no field of study** (no ISCED-F, no CAO category), no price, no start date, no campus URL and no programme URL.

## Numbers (file of 2026-09-22)

| Type | Rows | Providers | Dublin rows | Dublin providers |
|---|---|---|---|---|
| English Language | 1,066 | 64 | 832 | 44 |
| Higher education - Major award | 78 | 12 | 20 | 9 |
| Professional | 4 | 4 | 2 | 2 |
| Foundation | 3 | 2 | 1 | 1 |
| **Total** | **1,151** | **77** | 855 | 53 |

- Providers by county (main county of each provider): Dublin 53, Cork 9, Limerick 3, Kildare 3, Kerry 3, Galway 2, Carlow 1, Sligo 1. Rows: Dublin 855, Cork 138, Kildare 49, Limerick 39, Galway 27, Kerry 26, Carlow 7, Wexford 6, Sligo 3, Donegal 1.
- English language: 1,029 rows at 25 weeks, 25 at 26 weeks, 8 at 28, 3 at 27. The most common hours are 15 h/week (about 660 rows written in three ways), then 20 h/week.
- HE on ILEP covers small and private providers only, for example St Patrick's Pontifical University (37), ICHAS (14), Carlow College (7). The big public HEIs are on TrustEd.

## Joins

- Within Ireland: provider number = TrustEd provider number without `TE`, checked for 6 of 6 shared providers. No shared programme: provider + normalised title gave **0** matches between ILEP and TrustEd, as the "not on both lists" rule says.
- To the EU QDR / IRQ (see `qdr-ireland.md`): no common identifier. A title-only match found 15 of 78 ILEP HE rows.
- The 4 TrustEd-authorised English schools that have programmes (Emerald Cultural Institute 37, International House Dublin 39, Liffey College 12, Patrick's English Academy 7) still list them **on ILEP**, not on the TrustEd file.

## Limitations

- Free text everywhere (duration, hours, levels, awarding body). The parser needs normalisation rules and must keep the raw value.
- The sheet title date ("with effect from 11 February 2026") does not match the file date (22 September 2026). Use the file name date and Last-Modified as the version, and record the hash.
- Rows can disappear when a provider is removed for non-compliance or moves to TrustEd. A programme that disappears becomes a reconciliation task. It is never marked "not eligible" automatically: under BR-02, a missing value is unknown, not negative.

## Terms of use

ISD terms ("Copyright and re-use of public sector information"): content is © Department of Justice and may be re-used free of charge in any format. Conditions: acknowledge the source and copyright, reproduce accurately, do not mislead, do not use mainly for advertising. Compatible with North if every value cites the source.

## Access and update frequency

- robots.txt: `Crawl-delay: 10`, nothing disallowed. `curl` with user agent `north-research-spike` got the pages, the media API and the XLSX (HTTP 200). **No blocking.**
- Updates are irregular, each one a new dated file: 2025-06, 2026-02, 2026-07, 2026-09 (twice).
- Suggested: check the page or the media API weekly, wait 10 s between requests, and keep admin upload (FR-26) as the fallback.

## Ingestion (slice E2)

`backend/north/ingest/ie/` reads the uploaded XLSX (admin upload, country Ireland, job `ie.accept_upload`; `ie.load` reloads the newest stored files). English rows become `language_course` programs; HE, foundation and professional rows are counted and skipped until slice E3. Free text is parsed conservatively (`ingest/ie/parse.py`): weeks and hours take the lowest number written, CEFR entry/exit the lowest/highest band written (an IELTS score is never converted), the exam comes from `Awarding Body` through `data/reference/ie_exam_names.csv` (a spelling not in the map stays unknown and is reported in the run errors), and the town is matched at the end of an address part (several towns = no city). A programme that leaves the list keeps its values and opens a reconciliation task (`ie_list_move`); a TrustEd row with the same provider number and normalized title is linked to the ILEP programme automatically.
