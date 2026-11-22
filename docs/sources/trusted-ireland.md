# Source: TrustEd Ireland list of eligible programmes (QQI)

Spike S-7, run on 2026-11-22. Script: `spikes/s7_ie_lists/profile_ie_lists.py`. Result: `spikes/s7_ie_lists/RESULT.md`.

## What it is

TrustEd Ireland is QQI's statutory quality mark for providers that recruit international learners. It replaces the ILEP (see `ilep.md`) for study visas and Stamp 2 permissions. The ISD policy statement (Feb 2026) says: "Visas ... and Stamp 2 immigration permissions will only be granted in respect of an eligible programme offered by a provider with authorisation to use the TrustEd Ireland mark." It also says the mark "does not guarantee that every course you offer is eligible". Eligibility is decided per programme, so the programme list is what counts, not the provider list.

## Where and in what format

| Item | Value |
|---|---|
| Page | https://www.trustedireland.ie/check-eligible-courses-for-study-visas |
| File | https://www.trustedireland.ie/sites/default/files/2026-02/trusted-ireland-he-list-of-eligible-programmes.xlsx |
| Format | XLSX, one sheet `in`. Row 1 is the title, row 2 the header, 6,784 data rows. **Same 15 columns as ILEP**; only the first header differs (`Programme Ref:`). |
| Sheet title | "TrustEd Ireland Authorised Providers: List of Eligible Programmes (Higher Education, Foundation and Quality Assured English Language Programmes) **August 2026**" |
| Size / hash | 530,654 bytes, sha256 `70db0c12053042b23a82f26d77a95ec8a411c22a60bc2544fc66b1145288f6b1`, Last-Modified 2026-08-18 15:10 GMT |
| Version | The URL is **stable**: the `2026-02` folder stayed while the content was replaced in August. Detect changes by hash or Last-Modified, never by URL. |
| Provider pages (HTML) | https://www.trustedireland.ie/trusted-providers/higher-education-institutions (3 pages, `?page=1`, `?page=2`: **28** institutions) and https://www.trustedireland.ie/trusted-providers/english-language-education-institutions (**5** schools). These list providers only, with no programmes. |

Despite the file name ("he-list"), the file also has English language and foundation programmes.

## Fields

As in `ilep.md`. Differences:

| Column | Notes |
|---|---|
| Programme Ref: | `TE` + 4-digit provider number + `/` + 4-digit programme number. All 6,784 rows match. 5 references are duplicated (10 rows), e.g. `TE0133/0267` is used for two different MTU programmes. Unique in 6,779 of 6,784 rows. |
| Provider code | 40 codes. `TE0063` covers "University of Galway" and "University of Galway English Language Centre"; `TE0101` covers SETU Carlow and Wexford campuses; TUS has 5 codes (`TE0376`–`TE0380`). So the code points to a provider entity, sometimes split by campus. Not a campus identifier. |
| Provider | 38 names, often a campus (e.g. "Munster Technological University - Kerry Campus"). |
| **Contact Email, Telephone, Name** | **Dropped at ingestion** (personal data). Filled in 6,784 / 6,783 / 6,784 rows. |
| Programme Type | 8 spellings, which normalise to: HE major award 6,658, English Language 54, HE non-major award 53, Foundation 19 |
| NFQ Level | 9: 2,719; 8: 2,533; 10: 638; 7: 575; 6: 259; n/a 54; 5: 4. Two broken cells: one Excel date (`2026-09-08`, Pharmacy BSc/MPharm) and one empty. |
| Duration | ECTS in 5,714 rows (240: 1,812; 90: 1,636; 60: 815; 180: 787; 120: 418), "Research" 197, none / "Not applicable" 748, weeks 54 (English) |
| Awarding Body | 32 values, e.g. "The University of Dublin" 1,647, NUI 623, MTU 452, ATU 434 |

There is **no field of study**, no price, no start date, no mode of study (full-/part-time) and no URL.

## Numbers (August 2026 file)

- 6,784 rows, 38 provider names, 40 provider codes.
- Higher education (major + non-major), 6,711 rows: NFQ 9: 2,719; 8: 2,530; 10: 638; 7: 573; 6: 249.
  - Dublin: 3,488 rows (9: 1,491, 8: 1,311, 10: 447, 7: 188, 6: 51).
  - NFQ 9 is offered by 33 provider names.
- Award kind, read from the titles: master's 2,333, doctorate 626, postgraduate diploma 515, higher certificate 227, bachelor about 2,880. Most bachelor's at NFQ 8 are honours by definition, so use the NFQ level, not the title.
- Largest providers: TCD 1,655, UCD 564, University of Galway 425, TUS 425, Maynooth 411, UCC 388, TU Dublin 353, UL 351, DCU 253.
- **English language: 54 rows from 3 providers**, all university language centres (UCC Language Centre 48, UL Language Centre 4, Mary Immaculate College 2). None is in Dublin. All 54 are 25 weeks.

## Provider pages vs the file

- **English schools page (5):** Bridge Mills Galway Language Centre, Emerald Cultural Institute, International House Dublin, Liffey College, Patrick's English Academy. **None** of them has a programme in the TrustEd file. Four still have their programmes on ILEP (37, 39, 12 and 7 rows); Bridge Mills is on neither list. Going by QQI's IRQ page, their TrustEd programmes are published only in the Irish Register of Qualifications (irq.ie). That site disallows all robots (`qdr-ireland.md`).
- The 3 English providers in the file (university language centres) are not on the English schools page.
- **HE page (28):** 17 match a file provider by exact name. 10 more are naming variants (ATU vs "Atlantic Technological University Sligo", TU Dublin, RCSI, IADT…). **Institute of Banking** is authorised but has no programme in the file.

## Is this the list of all HE programmes open to non-EEA students?

Only together with ILEP, and only for the eligibility question:

- It lists programmes eligible for a **Stamp 2** (full-time). It is not a catalogue: it doesn't show part-time programmes, and some institutions are missing entirely or have few rows.
- Compared with QQI's own register (EU QDR file, `qdr-ireland.md`): QDR has 4,881 released NFQ 9 programmes against TrustEd's 2,719, and UCD has 695 released QDR entries against 564 in TrustEd. For TCD it is the other way round (QDR 758, TrustEd 1,655, where TrustEd counts research degrees by school). Neither is a superset of the other.

## Joins

- To ILEP: provider number (`TE0058` = ILEP `0058`). No shared programmes (0 provider + title matches).
- To QDR/IRQ: no shared identifier. Title-only match: 2,464 of 6,711 HE rows (37%).
- To HEA/CSO statistics: by institution name only (HEA uses 2-letter codes, e.g. `TR`, `DN`).

## Terms of use

No copyright or re-use page was found on trustedireland.ie or qqi.ie; the footer only says "© 2021 Quality and Qualifications Ireland". QQI is a public body under the Open Data Directive (S.I. 376/2021), and the list is published so the public can check eligibility. **Open question:** ask QQI to confirm re-use terms, or treat it like ISD's PSI terms (attribution, accurate reproduction).

## Access and update frequency

- robots.txt (Drupal default) allows `/sites/default/files/` and the provider pages. `curl` with `north-research-spike` got everything (HTTP 200). **No blocking.**
- Update frequency is unknown. One version is known: August 2026, replacing an earlier file at the same URL (folder `2026-02`).
- Suggested: a weekly HEAD request comparing `ETag`/`Last-Modified`, a hash of the file in `ingestion_runs.file_version`, and admin upload (FR-26) as the fallback.
