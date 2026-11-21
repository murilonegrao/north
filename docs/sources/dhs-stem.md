# Source: DHS STEM Designated Degree Program List

Spike S-3, run on 2026-11-21. Scripts are in `spikes/s3_dhs_stem/`.

## What it is

The list of CIP codes that DHS treats as STEM for the 24-month STEM OPT extension (8 CFR 214.2(f)(10)(ii)(C)(2)). It feeds rule `us.stem_opt` (RF-03, RN-03).

## Current version

| Item | Value |
|---|---|
| Title (PDF metadata) | 2024 DHS STEM Designated Degree Program List |
| "Last Updated" printed in the PDF | July 22, 2024 |
| Adopted as of | July 23, 2024 (Federal Register 2024-16127, "DATES" section) |
| URL | https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf |
| Format | PDF, 16 pages, a 3-column table (2-digit series, 2020 CIP code, title) |
| SHA-256 | `b8346f30cd6ab7702510f4837b339438323a96adfbd8133b6cb9d565e90b4336` (428,790 bytes) |
| CIP edition | CIP 2020 |

How we know it is current: a Federal Register API search on 2026-11-21 for "STEM Designated Degree Program List" returns no update notice after 2024-07-23. The newest related items are an OPT fees proposed rule (2026-10-08, document 2026-20660) and others that don't change the list. We didn't read the OPT fees rule because it is out of scope, but someone should check it for the immigration rules (`migration_rules`).

## Version history (from the Federal Register)

| Date | FR document | Change |
|---|---|---|
| 2016-03-11 | 2016-04828 (final rule) | Current list format: 4 whole 2-digit series plus 6-digit codes in related fields |
| 2022-01-21 | 2022-01188 | Adds 22 CIP codes |
| 2023-07-12 | 2023-14807 | Adds 8 CIP codes, removes none (file `stemList2023.pdf`) |
| 2024-07-23 | 2024-16127 | Adds 1 CIP code, 03.0204 Environmental/Natural Resource Economics (file `stemList2024.pdf`) |

Older PDFs found by search: `stemList2016.pdf`, `stemList2020.pdf`, `stemList2023.pdf` under `ice.gov/doclib/sevis/pdf/`, plus `ice.gov/sites/default/files/documents/stem-list.pdf`. We didn't download them.

## Generated files

- `data/reference/dhs-stem-list-2024-07-22.csv`, with columns:
  - `cip_code`: NN.NNNN
  - `title`
  - `version`
  - `level`: 2 = whole-series heading, 4 = 4-digit group heading, 6 = code
- `data/reference/dhs-stem-list-2024-07-22.meta.json`: URL, date, sha256, totals and the cross-check result.

Commands to reproduce:

```
uv run --with pdfplumber python -I spikes/s3_dhs_stem/parse_stem_list.py \
  spikes/_raw/dhs_stem/stemList2024.pdf \
  --source-url https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf --out-dir data/reference
python3 -I spikes/s3_dhs_stem/check_against_cip2020.py \
  data/reference/dhs-stem-list-2024-07-22.csv spikes/_raw/nces_cip/CIPCode2020.csv
```

## Validation

- **540 rows:** 466 six-digit codes, 4 whole-series headings (14.0000, 26.0000, 27.0000, 40.0000) and 70 four-digit group headings inside those series. 15.0000 and 41.0000 are real 6-digit codes, not headings.
- **Two independent extractors agree:**
  - pdfplumber assigns each title line to the nearest code.
  - A regex over `pdftotext -layout` output finds the same set of 540 codes.
  - The parser stops with an error if they disagree or if a title line is ambiguous.
- **Checked against the official CIP 2020 table** (NCES `CIPCode2020.csv`, sha256 `6cf0882c…6b2657`):
  - All 466 six-digit codes exist.
  - Titles match, with 4 small differences: 3 are spacing, and the PDF calls 45.0102 "Social Sciences, Research Methodology and Quantitative Methods" where CIP has "Research Methodology and Quantitative Methods".
  - Series 14, 26, 27 and 40 are printed in full (60, 92, 18 and 45 codes, the same as CIP 2020).
- **Codes the task asked about:**
  - **11.0701 Computer Science:** on the list.
  - **30.7001 Data Science, General:** on the list. It is the only 30.70xx code.
  - **52.1201 Management Information Systems, General:** **not** on the list, and no 52.12xx code is. The only 52.xx codes are 52.1301, 52.1302, 52.1304 and 52.1399.
  - **11.xx:** 28 codes on the list: 11.0101, 0102, 0103, 0104, 0105, 0199, 0201, 0202, 0203, 0299, 0301, 0401, 0501, 0701, 0801, 0802, 0803, 0804, 0899, 0901, 0902, 1001, 1002, 1003, 1004, 1005, 1006, 1099.

Consequence for RN-03: an MIS program reported under 52.1201 is not STEM-eligible. If the university advertises it as STEM, the status is `informado_pelo_programa` and the case is flagged. This will be common.

## Mapping to our model

| Source | North |
|---|---|
| version (2024-07-22) | `eligibility_rules.version`, `published_on` |
| PDF URL | `eligibility_rules.source_url` |
| PDF SHA-256 | `eligibility_rules.file_hash` |
| each 6-digit code (466) | `eligibility_rule_codes` → `classifications(scheme='cip2020', code)` |
| whole series 14, 26, 27, 40 | **not in the ER model today** (see below) |

**Suggested ER change.** The PDF says new CIP codes in series 14, 26, 27 and 40 are STEM automatically. Today the expanded list is identical to CIP 2020, so listing the codes is enough. But a future CIP edition (CIP 2030) would add codes that are not on the printed list. Proposal:
- Add `eligibility_rules.params jsonb` holding `{"whole_series": ["14","26","27","40"]}`.
- Expand the series against the `classifications` table at import time.

Ignore the heading rows (level 2 and 4) when filling `eligibility_rule_codes`.

## Coverage, limits, terms, updates

- **Coverage:** national, the complete list for STEM OPT.
- **Limits:**
  - The list says which CIP is STEM, not which program uses which CIP. The CIP of each program comes from IPEDS/Scorecard or from the school (see RN-03).
  - The parser depends on the 2024 table layout (column x positions). A new layout will fail loudly in the cross-check, not silently.
- **Access:** ice.gov and studyinthestates.dhs.gov return HTTP 403 (Akamai "Access Denied") to `curl` with user-agent `north-research-spike`. The PDF was obtained with a web fetch tool that uses a different client. For automation, either a human downloads the PDF when a new FR notice comes out, or we watch the Federal Register API (which works with curl) and alert. Updates are rare (about once a year), so manual is fine.
- **Terms:** a U.S. federal government work, public domain (17 U.S.C. 105).
- **Update frequency:** irregular, by Federal Register notice (2022, 2023, 2024; none in 2025–2026 so far). Monitor `federalregister.gov/api/v1/documents.json?conditions[term]="STEM Designated Degree Program List"`.

## Local sample

The loader reads the versioned CSV and meta JSON in `data/reference/` (in the repository), so no download is needed. To rebuild them from a new PDF, download it in a browser from https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf into `spikes/_raw/dhs_stem/` and run the parser command above. Ingestion: `backend/north/ingest/us/dhs_stem.py` (source id `dhs_stem_list`).
