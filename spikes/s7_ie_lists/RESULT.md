# S-7 Irish lists — result

Run on 2026-11-22. Files: ILEP of 2026-09-22, TrustEd list of August 2026 (Last-Modified 2026-08-18), EU QDR Ireland dump of 2026-11-22.

## In one sentence

Two official XLSX files with the same 15 columns tell North which programmes give a Stamp 2: ILEP (1,151 rows, mostly English schools) and TrustEd (6,784 rows, mostly HE), and they never share a programme. The only bulk list of **all** Irish programmes is QQI's register as republished by the EU (QDR: 11,705 released NFQ 6–10 programmes), which brings ISCED-F codes but shares no identifier with the immigration lists.

## How to reproduce

```sh
python3 -I spikes/s7_ie_lists/profile_ie_lists.py --download --raw-dir spikes/_raw --out-dir spikes/s7_ie_lists/out
uv run --with openpyxl python -I spikes/s7_ie_lists/profile_ie_lists.py --raw-dir spikes/_raw --out-dir spikes/s7_ie_lists/out
# QDR: download + unzip commands are in the docstring of profile_qdr_ie.py
uv run --with rdflib python -I spikes/s7_ie_lists/profile_qdr_ie.py --ttl-dir spikes/_raw/qdr_ie/extracted \
  --ie-csv spikes/_raw/ie_derived/ie_eligible_programmes.csv --out-dir spikes/s7_ie_lists/out
```

Outputs: `out/ie_lists_summary.json` and `out/qdr_ie_summary.json`. The row-level CSVs are written under `spikes/_raw/` because they are too large to commit. Contact name, email and phone columns are never written out.

## Numbers

### Immigration lists (Stamp 2 eligibility)

| | ILEP 2026-09-22 | TrustEd Aug 2026 |
|---|---|---|
| Rows | 1,151 | 6,784 |
| English language | 1,066 rows, 64 providers, Dublin 832 rows / 44 providers | 54 rows, 3 providers (university language centres in Cork and Limerick), Dublin 0 |
| HE major award | 78 rows, 12 providers | 6,658 rows (+53 non-major), 35 providers |
| Foundation / Professional | 3 / 4 | 19 / 0 |
| NFQ (HE) | 8: 33, 9: 31, 7: 9, 10: 4, 6: 1 | 9: 2,719, 8: 2,530, 10: 638, 7: 573, 6: 249 |
| HE in Dublin | 20 rows | 3,488 rows (9: 1,491, 8: 1,311, 10: 447) |
| Providers (names / codes) | 77 / 76 | 38 / 40 |
| Reference | `NNNN/NNNN`, 1 duplicate | `TENNNN/NNNN`, 5 duplicates |
| Field of study | none | none |

- **Overlap:** 0 programmes by provider + normalised title. 6 providers appear on both lists (Dorset, DBS, Galway Business School, Griffith Cork/Dublin/Limerick), each with **different programme types** on each list (for example English on ILEP, HE on TrustEd). Their provider number is the same on both lists (`0058` ↔ `TE0058`).
- **TrustEd provider pages:** 28 HE institutions and 5 English schools. None of the 5 English schools has a programme in the TrustEd file; 4 still have their programmes on ILEP (95 rows); Bridge Mills is on neither. Institute of Banking is authorised but has no programme rows.
- The ILEP sheet title says "with effect from 11 February 2026", while the file is dated 22 September 2026. The ISD page says the "final ILEP update was published on 20 June 2025", yet 5 later files exist.

### All programmes (QQI register via EU QDR)

- 25,705 learning opportunities, 15,072 `released`; 19,831 qualifications, all with EQF, NFQ and 4-digit ISCED-F (150 with 3 digits).
- Released NFQ 6–10: **11,705** (9: 4,881; 8: 2,799; 6: 2,218; 7: 1,310; 10: 497) from 152 providers. 859 of the NFQ 6 rows are ETB further-education courses.
- Title-only match: TrustEd HE 2,464 / 6,711 (37%), ILEP HE 15 / 78, English 0 / 1,120.

## Other Irish sources checked (desk check)

| Source | URL | Format / fields | Coverage | Terms | Scripts | Use for North |
|---|---|---|---|---|---|---|
| IRQ (QQI) | https://irq.ie/ | Angular app + API | All NFQ qualifications and programmes, plus TrustEd English providers' programmes | "free to use" | **robots.txt `Disallow: /`** | Manual check only. Bulk data through QDR (`docs/sources/qdr-ireland.md`) |
| EU QDR, Ireland | data.europa.eu `european-learning-data` | Turtle (JSON-LD empty on 2026-11-22), ELM | as IRQ, minus English programmes | COM_REUSE (2011/833/EU) | allowed | **Catalogue + ISCED-F**, see doc |
| HEA statistics via CSO PxStat | https://data.gov.ie (HEA01/02/03), e.g. `https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/HEA02/CSV/1.0/en` | CSV/JSON-stat. Enrolments by ISCED-F **broad field** (2-digit), by institution (2-letter HEA code, 18 HEIs) and by programme type (15 kinds, e.g. "Masters - Taught"), 2016/17–2022/23 | HEA-funded HEIs only ("not private colleges") | CC BY 4.0 | allowed (HTTP 200) | Context only (size of a field at an institution). No course list. The hea.ie dashboard exports CSV by hand only. |
| CAO | https://www.cao.ie/courses.php, handbook PDFs at `www2.cao.ie/handbook/handbook2027/` | Course search by 29 institutions (2-letter codes, e.g. `DN`, `TR`); level 8 and level 6/7 PDF lists | Undergraduate entry (NFQ 6–8) through CAO only | **"All rights reserved; no part ... may be reproduced ... without prior permission"** | robots.txt 404; site reachable | **Not used** (C-05 and copyright). Nothing was downloaded. |
| SUSI approved courses | https://www.susi.ie/eligibility-criteria/approved-courses/ | HTML pages of rules and institution codes | Grant eligibility for EU/EEA students | — | allowed | Not relevant to non-EEA discovery |
| Qualifax | https://www.qualifax.ie/ | Course search website, run by QQI (it uses QQI's privacy statement) | All levels, plus open days | not found | robots.txt default | No bulk download found. Not examined further; a lead at most. |

## Classifications

- **Level:** both immigration lists give the **NFQ level** (6–10, `n/a` for English and professional programmes) as free text. QDR gives the EQF level and an NFQ concept; in the data, NFQ 6→EQF 5, 7 and 8→EQF 6, 9→EQF 7, 10→EQF 8. For ISCED 2011, the usual mapping is Higher Certificate (NFQ 6, HE) → ISCED 5, Ordinary Bachelor (7) → 6, Honours Bachelor / Higher Diploma (8) → 6, Master's / Postgraduate Diploma (9) → 7, Doctorate (10) → 8; FET Advanced Certificate (NFQ 6) → ISCED 4. This spike did not fetch the official UIS mapping for Ireland, so verify it before seeding `classification_maps`.
- **Field of study:** **neither immigration list has one.** QDR has **ISCED-F 2013** (4-digit) for every qualification, the same scheme North already uses (`cip-isced-f.md`), so no crosswalk is needed. HEA statistics use ISCED-F broad fields. CAO categories were not examined (copyright).

## Recommendation

1. **English language schools (Stamp 2):** ILEP is the discovery source: 1,066 programmes from 64 providers, Dublin 832/44. Add the 54 English rows from the TrustEd file. Read both files at every run; a programme moving from ILEP to TrustEd shows up as "gone from ILEP, new on TrustEd" with the same provider number. Check the 5 TrustEd English schools by hand on irq.ie when their programmes leave ILEP.
2. **All HE programmes:** for **eligibility**, use TrustEd (6,711 HE rows) plus ILEP (78 HE rows), unioned on `(list, programme ref)`. For **field of study and a wider catalogue**, use QDR. Link a TrustEd/ILEP row to a QDR learning opportunity by provider + title. Accept exact matches; others become reconciliation tasks. Store the IRQ code as an identifier once confirmed.
3. **Identifiers:** `ie_ilep_ref` / `ie_trusted_ref` (programme), `ie_provider_no` (the 4 digits shared by both lists), `ie_irq` (QQI code + IRQ id). Never key on programme title alone: ILEP has 314 rows and TrustEd 827 rows whose provider + title is shared with another row.
4. **Ingestion:** both XLSX files download with a plain script (no blocking). Keep admin upload (FR-26) as the fallback. Drop the three contact columns while reading.

## Gaps (no official list has these)

Tuition fee (non-EU), intake / start dates, application deadlines, mode (except that TrustEd/ILEP imply full-time), programme URL, campus city for QDR, field of study for the immigration lists. All of these have to come from the programme's own site through manual curation, as in the US.

## Blocking and terms

| Site | robots.txt | curl with `north-research-spike` | Terms |
|---|---|---|---|
| irishimmigration.ie | Crawl-delay 10, nothing disallowed | 200 | PSI re-use, attribution |
| trustedireland.ie | Drupal default, files allowed | 200 | no terms page found (open question) |
| irq.ie | **Disallow: /** | not scripted | "free to use" |
| data.europa.eu / europa.eu (QDR) | paths allowed | 200 | COM_REUSE |
| ws.cso.ie / data.gov.ie (HEA) | — | 200 | CC BY 4.0 |
| cao.ie | 404 | 200 | all rights reserved; not used |

## Open questions for the author

1. **Scope:** the SRS covers US master's programmes. Ireland across NFQ 6–10 plus English schools is a scope change. Options: (a) Ireland, master's only (NFQ 9: 2,719 TrustEd + 31 ILEP rows); (b) all NFQ 6–10; (c) (b) plus English schools. *Recommendation:* (c) as the data contract, with the UI filtering by level. It needs a decision record (skill `decision-record`), because English schools are a new programme kind.
2. **What counts as "the programme universe" in Ireland:** (a) only Stamp 2-eligible programmes (TrustEd + ILEP); (b) every QDR programme, with eligibility as a flag. *Recommendation:* (a). North's users need the permission, and under BR-02 a QDR programme missing from both lists would be "unknown", which adds noise. Use QDR only for enrichment.
3. **TrustEd re-use terms:** (a) email QQI's International Education Division to confirm; (b) assume PSI terms like ISD's. *Recommendation:* (a), and publish with attribution in the meantime.
4. **NFQ concept labels in QDR:** (a) ask QQI or the QDR support for the vocabulary; (b) keep the inferred table. *Recommendation:* (a) before production, (b) for the pilot.
5. **ILEP disappearances during the TrustEd transition:** (a) reconciliation task (as for SEVP); (b) auto-match by provider number and title to the new TrustEd row. *Recommendation:* (b) when provider number + title match exactly, (a) otherwise. Never mark as negative automatically.
6. **CAO:** (a) ignore; (b) ask CAO for permission to use course codes. *Recommendation:* (a). TrustEd + QDR already cover undergraduate programmes. Whether non-EEA applicants go through CAO or apply to the institution directly varies by institution; this spike did not check it.
