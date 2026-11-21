# Source: IPEDS (NCES, U.S. Department of Education)

Spike S-2, run on 2026-11-21. Scripts: `spikes/s2_ipeds/`. Summary: `spikes/s2_ipeds/out/summary_ipeds.json`.

## What it is

The Integrated Postsecondary Education Data System. It is a mandatory annual survey for every institution in the federal student aid programs (Title IV). For North, three components matter:

- **Completions (C<year>_A):** awards by UNITID × **6-digit CIP (CIP 2020)** × award level × first/second major, with breakdowns by race/ethnicity and sex. This includes **"U.S. Nonresident"** (`CNRALT`), the IPEDS category for students on temporary visas.
- **Directory (HD<year>):** name, city, control, size, OPEID, website, coordinates.
- **Institutional Characteristics, academic year charges (IC<year>_AY):** average graduate tuition and fees, in-state and out-of-state.

The Scorecard FoS file uses IPEDS completions (its `IPEDSCOUNT1/2`) but rolls them up to 4-digit CIP.

## Access

| File | URL | Contents (measured) |
|---|---|---|
| C2024_A | https://nces.ed.gov/ipeds/datacenter/data/C2024_A.zip | `C2024_a.csv`, 62.8 MB, 307,707 rows; AY2023-24 completions |
| C2024_A_Dict | https://nces.ed.gov/ipeds/datacenter/data/C2024_A_Dict.zip | xlsx: Varlist, Description, Frequencies |
| HD2024 | https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip | `HD2024.csv`, 4.5 MB |
| HD2024_Dict | https://nces.ed.gov/ipeds/datacenter/data/HD2024_Dict.zip | xlsx |
| IC2023_AY | https://nces.ed.gov/ipeds/datacenter/data/IC2023_AY.zip | `ic2023_ay.csv`; charges for 2023-24 |
| IC2023_AY_Dict | https://nces.ed.gov/ipeds/datacenter/data/IC2023_AY_Dict.zip | xlsx (sheet `varlist`, lowercase) |
| Listing page | https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx | **did not load** during the spike (connection reset) |

Notes from the spike:
- `C2025_A`, `HD2025`, `IC2025_AY` and `IC2024_AY` returned **404** on 2026-11-20. So the most recent files available were completions 2023-24 (C2024_A) and graduate tuition 2023-24 (IC2023_AY). The 2024 charges file may use another name or may not be out yet. That was not confirmed because the listing page did not load.
- **nces.ed.gov was unstable:** for about 20 minutes, every connection was reset or timed out, including the home page. Then it came back, and the files were downloaded with retries (`download_ipeds.sh`). The ingestor needs retry/backoff, and it should keep a local copy of the zip with a hash.
- Columns are uppercase, the CSV starts with a UTF-8 BOM, and fields have padding spaces. The parser uses `utf-8-sig` and strips values.

### Fallback: Urban Institute Education Data Portal (third-party mirror)

`spikes/s2_ipeds/fetch_urban_ipeds.py` pulls the same data through the JSON API at https://educationdata.urban.org/api/v1/college-university/ipeds/ (`completions-cip-6`, `academic-year-tuition`, `directory`). Differences from NCES:
- `year` = fall of the academic year (2023 = AY2023-24 = C2024_A).
- `award_level` is recoded: **9 = Master's degree** (in NCES `AWLEVEL` it is 7). 7 = bachelor's, 8 = postbaccalaureate/post-master's certificate.
- CIP is an integer without the dot (`110701`).
- Completions only cover up to 2023 (the endpoint lists "1983–2023").

Cross-check: for the 107 TX master's UNITID × CIP6 pairs in the target CIPs, Urban and NCES match exactly (sum 8,636 = 8,636). It works as a backup, but the official source for `source_url` is NCES.

## Useful columns → North model

| File.column | Meaning (dictionary) | North field |
|---|---|---|
| `C_A.UNITID` | institution ID | `institution_identifiers(scheme='unitid')` |
| `C_A.CIPCODE` | **6-digit CIP 2020**, format `xx.xxxx` (`99` = grand total) | `program_classifications` (cip2020, `is_primary`) |
| `C_A.AWLEVEL` | **7 = Master's degree** (confirmed in the `Frequencies` sheet of C2024_A_Dict) | filter; `programs.degree` |
| `C_A.MAJORNUM` | 1 = first major, 2 = second | sum both, or use only 1 |
| `C_A.CTOTALT` | grand total of awards | size indicator (`programs.academic`) |
| `C_A.CNRALT` | "U.S. Nonresident total" | signal of how international the program is (`programs.career` or `admissions`) |
| `HD.INSTNM`, `HD.CITY`, `HD.STABBR` | name, city, state | `institutions.name`, `city`, `subdivision_id` |
| `HD.CONTROL` | 1 public, 2 private nonprofit, 3 private for-profit | `institutions.control` |
| `HD.OPEID` | 8-digit OPEID | `institution_identifiers(scheme='opeid')` |
| `HD.INSTSIZE` | size category 1–5 | helper |
| `HD.WEBADDR` | website | starting point for the crawler |
| `HD.LATITUDE`, `HD.LONGITUD` | coordinates | map |
| `HD.CYACTIVE` | active in the current year | filter |
| `IC_AY.TUITION6` / `FEE6` | in-state average tuition / fees, full-time graduate | `programs.cost` (institution-level reference) |
| `IC_AY.TUITION7` / `FEE7` | **out-of-state** average tuition / fees, full-time graduate | `programs.cost.tuition_reference_nonresident` |
| `IC_AY.HRCHG7` | out-of-state credit hour charge, part-time graduate | helper |

`TUITION7` is an **institution-wide average for graduate study**, not the price of the program. It is a starting value with status "official reference", not "verified". In every private institution of the TX target list, `TUITION6` = `TUITION7`.

## Coverage measured in Texas (master's, AWLEVEL 7, AY2023-24)

- TX master's, all CIPs: 2,690 UNITID × CIP6 rows at 106 institutions.
- Target CIPs (`spikes/s2_ipeds/out/tx_masters_target_ipeds.csv`):

| Family | UNITID × CIP6 | with completions > 0 | UNITID × CIP4 | Institutions | Completions | Nonresident |
|---|---|---|---|---|---|---|
| 11.xx computing | 90 | 82 | 80 | 46 | 7,814 | 6,311 (81%) |
| 30.70 data science | 7 | 6 | 7 | 7 | 774 | 460 (59%) |
| 52.12 information systems | 10 | 3 | 8 | 8 | 48 | 7 (15%) |
| **Total** | **107** | **91** | **95** | **48** | **8,636** | **6,778 (78%)** |

Institutions by control (target CIPs): 32 public, 12 private nonprofit, 4 for-profit.

Most common 6-digit CIPs: 11.0401 (22), 11.0101 (20), 11.1003 (17), 11.0701 (12), 52.1201 (8), 30.7001 (7), 11.0103 and 11.0102 (5 each). In 10 UNITID × CIP4 pairs there is more than one CIP6 (up to 3). The Scorecard merges these.

Graduate tuition (`TUITION7`, IC2023_AY): has a value for **47 of the 48** target institutions. The one missing is Hallmark University.

## Comparison with the Scorecard (UNITID × CIP4, master's)

- All 95 IPEDS pairs are in the Scorecard. The Scorecard has 4 more pairs with no AY2023-24 completions row (TAMU-Victoria 1103, TAMU 5212, UTSA 1104, Texas Tech 1104; `IPEDSCOUNT2 = NA` in all of them).
- `IPEDSCOUNT2` in the Scorecard equals the sum from C2024_A in **95 of the 95** comparable pairs.
- Same set of 48 institutions.
- Name drift: UNITID 225502 is "University of Houston-Victoria" in HD2024 and "Texas A&M University-Victoria" in the Scorecard 2026. This confirms the rule of matching by UNITID, never by name.

## Limitations

1. Completions show what was **awarded** in a past year (two years behind), not what is open for admission now. A program with 0 completions may be new or closed.
2. A UNITID × CIP6 pair is not a named program: an institution can have two master's programs under the same CIP6. The program name, concentration and delivery mode come from the website (curation/extraction).
3. Graduate tuition is an institution-wide average. It does not cover differential tuition by program (common in engineering/business).
4. A missing column, an empty cell or `.` is "not reported", never 0 (BR-02): if any `CTOTALT` of a program is missing its completions are `unknown`; if only `CNRALT` is missing the value keeps the total with `nonresident: null` and the evidence says so. A changed `WEBADDR` host opens a `website_changed` reconciliation task (the new value is still applied and logged).
5. `CNRALT` counts temporary-visa graduates. It is a good signal of an international pipeline, but it does not say whether the program issues an I-20 (SEVP, RF-04) or whether it is online.
6. The site was unstable. The ingestor needs retries and must save the original zip.

## License and terms

U.S. federal government data (NCES). Generally in the public domain (17 U.S.C. §105). No explicit license was checked on the site. Cite "U.S. Department of Education, NCES, IPEDS, <component> <year>". The Urban mirror has its own terms of use; they were not checked. Do not rely on it as the official source without reading those terms.

## Update frequency

Annual. Each component comes out as a provisional version and is later revised (some zips bring an `_rv` file; the script prefers it). Files seen: C2024_A, dated 2025-09-21 inside the zip; IC2023_AY, dated 2024-07-05. For `ingestion_runs.file_version`, use the file name plus the zip hash.

## Local sample

`scripts/load_local_sample.sh` reads `spikes/_raw/ipeds/` (git-ignored). Download in a browser (or with `bash spikes/s2_ipeds/download_ipeds.sh spikes/_raw/ipeds`, which retries) and keep the zips as they are:

| File | Saved as |
|---|---|
| https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip | `spikes/_raw/ipeds/HD2024.zip` |
| https://nces.ed.gov/ipeds/datacenter/data/C2024_A.zip | `spikes/_raw/ipeds/C2024_A.zip` |
| https://nces.ed.gov/ipeds/datacenter/data/C2024_A_Dict.zip | `spikes/_raw/ipeds/C2024_A_Dict.zip` (CIP titles; the loader checks that `AWLEVEL` 7 is "Master's degree") |
| https://nces.ed.gov/ipeds/datacenter/data/IC2023_AY.zip | `spikes/_raw/ipeds/IC2023_AY.zip` |

The loader (`backend/north/ingest/us/ipeds.py`) picks the newest year of each file in the directory, so newer files can be dropped next to the old ones. It reads only the HD columns it needs; `CHFNM` (the chief administrator's name) is never read.
