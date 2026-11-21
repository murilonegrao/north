# Source: SEVP Certified School List

Spike S-4, run on 2026-11-21. Scripts are in `spikes/s4_sevp/`. The result and the answer to Q10 are in `spikes/s4_sevp/RESULT.md`.

## What it is

The list of schools certified by the Student and Exchange Visitor Program to enroll F-1 and/or M-1 students. It feeds RF-04 and `campuses.intl_authorization` (scheme `sevp`).

## Where and in what format

| Item | Value |
|---|---|
| Search page | https://studyinthestates.dhs.gov/school-search (a web search with filters and a "Download Certified School List" link) |
| Bulk file | https://studyinthestates.dhs.gov/assets/certified-school-list-11-18-26.pdf |
| Format | **PDF only** (252 pages, letter size). Metadata: Title "sevp-certified-school-list.xlsx", Producer "Microsoft: Print To PDF". In other words, an Excel sheet printed to PDF. |
| Date | "Updated November 18, 2026" (page header), which matches the file name |
| SHA-256 | `b10468f35001bec6d3066ee66b5edd4d43ecbf765c20ae7d51fd27bd9f1a5f8a` (3,589,078 bytes) |
| CSV/XLSX | **Not found.** No structured download was linked on the search page or turned up by web search. ice.gov pages could not be read (403). |

## Fields (PDF columns)

| PDF | Parsed CSV | North |
|---|---|---|
| SCHOOL NAME | `school_name` | matching only |
| CAMPUS NAME | `campus_name` | matching only |
| F | `f_1` (Y/N) | `intl_authorization.authorized` (F-1 is what matters for a master's) |
| M | `m_1` (Y/N) | not used |
| CITY | `city` | matching only |
| ST | `state` | `subdivisions` (US-XX) |
| CAMPUS CODE | `campus_code` (e.g. DAL214F00932000) | `institution_identifiers(scheme='sevp_campus')` |
| (derived) | `school_code` = first 12 chars | stored as an attribute only, **not unique per institution** |

There is **no UNITID or OPEID**. Matching to IPEDS has to go through name + city + state (see RESULT.md).

Parsed output (`spikes/_raw/sevp/derived/sevp-certified-schools-2026-11-18.csv`):
- 13,807 campuses and 6,579 school codes.
- F/M split: Y/N 11,880; Y/Y 1,365; N/Y 562.
- 55 state/territory codes. Texas has 842 campuses and 418 school codes.

Command to reproduce:

```
uv run --with pdfplumber python -I spikes/s4_sevp/parse_sevp_pdf.py \
  spikes/_raw/sevp/certified-school-list-11-18-26.pdf \
  spikes/_raw/sevp/derived/sevp-certified-schools-2026-11-18.csv
uv run --with rapidfuzz python -I spikes/s4_sevp/match_ipeds.py \
  --sevp spikes/_raw/sevp/derived/sevp-certified-schools-2026-11-18.csv \
  --hd spikes/_raw/ipeds/extracted/HD2024.csv --state TX --out-dir spikes/s4_sevp/out
```

How the parser works:
- Excel prints long text over the next column, so columns are split by content-stream order, not by x position:
  - school run, then campus run, then F, M, city;
  - the state is the 2 characters before the 15-character code.
- Overflow is clipped at the next column, the same way the page shows it.

Checks:
- Row count equals the codes found by `pdftotext` (13,807).
- No row is missing F/M flags.
- Every state has 2 letters.
- Campus codes are unique.

## IPEDS used for matching

- File: `HD2024.zip` from https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip
  - sha256 `d98425c1…1f28345`
  - 6,072 institutions; 403 in TX, 401 of them active
- `HD2025.zip` returned 404 on 2026-11-21, so HD2024 is the newest.
- Access: nces.ed.gov resets the TLS connection for `curl` from this machine (`Connection reset by peer` at Client Hello). The zip came through a web fetch tool. This affects RF-02 (IPEDS ingestion) too.

## Coverage

- National: all 50 states plus territories, including K-12, language and flight schools.
- In Texas, 101 of 110 graduate institutions in IPEDS were matched (exact or approximate). See RESULT.md.

## Limitations

- Names are cut at the printed cell width.
- The city is sometimes the school's main city, not the campus city.
- The school code is shared by several IPEDS units (UNT and UNT Dallas/HSC; UH and UH-Victoria).
- A renamed school keeps its old name in SEVP for a while (East Texas A&M is still "Texas A&M University-Commerce").
- The site showed "13808 results found"; the PDF has 13,807 rows.

## Terms of use

U.S. federal government data, public domain (17 U.S.C. 105). No license or terms page was found for the file itself.

## Update frequency

Unknown. The file name carries the date (`certified-school-list-MM-DD-YY.pdf`), so the URL changes with each release and the link has to be taken from the search page.

- studyinthestates.dhs.gov and ice.gov return 403 (Akamai) to `curl` with user-agent `north-research-spike`, so automated download is not reliable.
- Plan for manual upload of the PDF by the admin, with the hash recorded in `ingestion_runs.file_version`.
- Suggested cadence: monthly, and before marking a state "done".
