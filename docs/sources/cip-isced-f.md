# Source: CIP 2020 → ISCED-F 2013 map

Open item 4 of the UML model. RP-09(c): course classification by scheme (CIP is one of them), mapped to ISCED-F. Tables `classifications` and `classification_maps`.

Date of the spike: 2026-11-20.

## Summary

- **No official US CIP 2020 → ISCED-F 2013 table was found.** Searches covered NCES, UNESCO UIS, OECD and Statistics Canada. NCES publishes CIP 2010↔2020 and CIP↔SOC crosswalks, not ISCED-F. UIS publishes ISCED *level* mappings per country (e.g. "United States ISCED 2011 Mapping"), not field mappings for CIP. Caveat: nces.ed.gov reset every connection during the spike, so the NCES check relies on web search results, not on the NCES resources page itself.
- **The closest official table is Statistics Canada's CIP Canada 2016 → ISCED-F 2013 concordance** (6-digit CIP, 4-digit ISCED-F). It is "the Canadian interpretation", built by mapping each CIP example programme to ISCED-F.
- The CIP Canada **2021** ↔ ISCED-F concordance is still listed as "forthcoming" on the StatCan CIP 2021 page (checked 2026-11-20).
- CIP Canada 2021 was harmonized with the US CIP 2020, and CIP Canada 2016 with the earlier US CIP. Codes in our scope that exist in both keep the same number.
- Result: `data/reference/cip-isced-f.csv`, 43 rows for 41 CIP codes. **36 rows `official`** (StatCan pairs copied verbatim), **7 rows `proposed`** (codes new in CIP 2020: 11.0105, 11.0204, 11.0205, 11.0902, 11.0999, 30.7001, 30.7099).

## Sources

| Source | URL | Format | Use |
|---|---|---|---|
| StatCan, CIP Canada 2016 – ISCED-F 2013 concordance | https://www.statcan.gc.ca/sites/default/files/documents/cip2016-isced-f-2013-eng.csv (page: https://www.statcan.gc.ca/eng/subjects/standard/cip/2016/cip2016-iscedf2013) | CSV, cp1252. Columns: `CIP Canada 2016 Code`, `CIP Canada 2016 Title`, `ISCED-F 2013 Code`, `ISCED-F 2013 Title`, `Explanatory Notes` | official pairs and ISCED-F titles |
| StatCan, how to read the concordance | https://www.statcan.gc.ca/en/subjects/standard/cip/2016/how-read-cip2016-iscedf2013 | HTML | `*` on the ISCED-F code = the CIP class is only a portion of that ISCED-F class; a CIP class equal to more than one ISCED-F class gets one row each with explanatory notes |
| StatCan, CIP Canada 2021 v1.0 structure | https://www.statcan.gc.ca/en/statistical-programs/document/cip-cpe-2021-structure-v1-eng.csv | CSV, UTF-8 BOM. Columns: `Level`, `Hierarchical structure`, `Code`, `Parent`, `Class title`, `Superscript`, `Class definition` | list of 6-digit codes in scope; `Superscript = CAN` marks 39 Canada-only classes (none in our scope) |
| DHS STEM list 2024-07-22 (from spike S-3) | `data/reference/dhs-stem-list-2024-07-22.csv` (source PDF: https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf) | CSV | US CIP 2020 titles for codes on the STEM list |
| NCES CIP 2020 | https://nces.ed.gov/ipeds/cipcode/ | — | **not reachable** during the spike (connection reset) |

## Output file

`data/reference/cip-isced-f.csv`, built by `spikes/isced/build_cip_isced.py`.

| Column | Content |
|---|---|
| `cip_code` | CIP 2020, `NN.NNNN` |
| `cip_title` | US CIP 2020 title from the DHS STEM list; if the code is not on it, the CIP Canada 2021 title (said so in `notes`) |
| `isced_f_code` | ISCED-F 2013, 4 digits, kept as text (leading zero) |
| `isced_f_title` | as written in the StatCan concordance |
| `origin` | `official` = pair copied from the StatCan concordance; `proposed` = our curation |
| `source` | URL of the concordance, or `north curation` |
| `partial` | `true` when StatCan marks the ISCED-F code with `*` (the CIP class is a portion of the ISCED-F class). Proposed rows use `true` |
| `notes` | justification per row, title differences between CIP Canada 2016 and 2021, StatCan explanatory notes |

Two columns (`partial`, `notes`) were added to the requested layout so each row carries its justification.

### What `official` means here

The pair is official for **CIP Canada 2016**, made by Statistics Canada. Reusing it for the **US CIP 2020** assumes the code means the same thing in both. That holds for the codes kept here (same number; titles equal or with small wording changes, which are listed in `notes`, e.g. 11.1003 gained "/auditing", 11.0901 gained ", general"). It is still an assumption a human should accept.

### Proposed rows

| CIP | Title | Proposed ISCED-F | Main reason |
|---|---|---|---|
| 11.0105 | Human-Centered Technology Design | 0613 | under 11.01; alternative 0688 (StatCan maps 30.3101 HCI to 0388) |
| 11.0204 | Computer game programming | 0613 | StatCan maps every other 11.02xx to 0613 |
| 11.0205 | Computer programming, specific platforms | 0613 | same as 11.0204 |
| 11.0902 | Cloud Computing | 0612 | like network/system administration (11.1001, 11.1002); alternative 0619 (parent 11.0901) |
| 11.0999 | Computer systems networking and telecommunications, other | 0619 | follows 11.0901 |
| 30.7001 | Data Science, General | 0688 | statistics + computing, no dominant field → x88; StatCan maps 30.3001 Computational science to 0688; alternatives 0542 Statistics, 0588 |
| 30.7099 | Data science, other | 0688 | follows 30.7001 |

The titles of 11.0204, 11.0205, 11.0999, 30.7099, 11.0601, 11.0602, 11.0699, 11.9999 and all 52.12xx come from CIP Canada 2021 because they are not on the DHS STEM list. **Their US CIP 2020 titles, and the existence of 11.0999 in the US CIP 2020, must be checked against NCES.**

## Findings worth knowing

- Several ISCED-F classes collect our scope: 0610 (ICT n.f.d.), 0611 (computer use), 0612 (database and network design and administration), 0613 (software and applications development and analysis), 0619 (ICT n.e.c.), 0688 (inter-disciplinary with ICT). **11.0401 Information science maps to 0322 (library and archival studies)** and **11.0803 Computer graphics to 0211 (audio-visual techniques)**, outside broad field 06. A "computing" filter on ISCED-F should be `06xx` and decide explicitly about those two.
- All 52.12xx (MIS) map to 0688, i.e. inside broad field 06, although MIS is not on the DHS STEM list (52.12 rows are absent from the 2024 list).
- Some CIP codes map to two ISCED-F classes (11.0301, 11.0601). `classification_maps` must allow many rows per `from_id`, and it may be worth adding `partial` (bool) and `origin` there.

## Limitations

- Canadian interpretation, CIP Canada 2016. When StatCan publishes the CIP Canada 2021 concordance, rebuild from it and re-check the proposed rows.
- ISCED-F titles come from the StatCan file, not from the UNESCO document. They match the ISCED-F 2013 names used by UIS, but were not compared line by line.

## Terms of use

Statistics Canada content is under the Statistics Canada Open Licence (per the site's general terms; not re-read in this spike). DHS list: US federal government work.

## Update frequency

CIP changes about every 10 years (2010, 2020); ISCED-F 2013 has no newer version. Rebuild when StatCan publishes the 2021 concordance or when NCES publishes CIP 2030.

## Needs a human decision

1. Accept StatCan CIP Canada 2016 pairs as `official` for the US CIP 2020 (or relabel them).
2. Review the 7 proposed rows, mainly 30.7001 Data Science (0688 vs 0542) and 11.0105.
3. Whether 11.0401 (→0322) and 11.0803 (→0211) count as "computing" in a cross-country filter.
4. Add `origin` and `partial` to `classification_maps` in the UML.

## Files

- Script: `spikes/isced/build_cip_isced.py` (run line in its docstring)
- Raw: `spikes/_raw/statcan_cip_isced/cip2016-isced-f-2013-eng.csv` (sha256 `eb49260926204c3d3bbf2e59fbc47ef1212b1c8dd1a439daebc2d57884236515`), `spikes/_raw/statcan_cip_isced/cip-cpe-2021-structure-v1-eng.csv` (sha256 `0022f848462ccd3b204737293f0c96d3582883b95789967d74044e2c71b4c9da`)
- Output: `data/reference/cip-isced-f.csv`
