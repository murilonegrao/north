# Source: HUD Fair Market Rents (FMR)

Spike S-6. Requirement RF-06 (Could): import HUD reference rent by county and number of bedrooms, as input to the family living cost (RN-07).

Date of the spike: 2026-11-20.

## Summary

- **What it is:** HUD's estimate of the 40th percentile *gross* rent (base rent plus essential utilities) for a standard-quality unit. HUD publishes it for every metro area and every non-metro county, for 0 to 4 bedrooms.
- **Current year:** FY2027, in force since 2026-10-01 (Federal Register doc. 2026-17891, docket FR-6553-N-03). FMRs change every year on October 1.
- **What we actually downloaded:** HUD's own ArcGIS FeatureServer. It has **no fiscal year field**. Its data were last edited on 2025-09-30, so it is almost certainly **FY2026**, not FY2027 (see "Vintage" below).
- **Blocker:** huduser.gov (the canonical download) answers scripts with an AWS WAF JavaScript challenge. The HUD User API needs a token, which needs a free account. We did not create one.
- **Recommendation:** use the county file `FY27_FMRs.xlsx` from huduser.gov as the source of truth, downloaded once a year (by a person in a browser, or through the API with a token). Use the ArcGIS layer only for point-in-polygon lookups and for prototyping.

## Access options

| Option | URL | Format | Auth | Result in this spike |
|---|---|---|---|---|
| HUD User dataset page | https://www.huduser.gov/portal/datasets/fmr.html | HTML with links to XLSX | none for browsers | HTTP 202, empty body, header `x-amzn-waf-action: challenge` |
| County file FY2027 | https://www.huduser.gov/portal/datasets/fmr/fmr2027/FY27_FMRs.xlsx | XLSX | none for browsers | same WAF challenge. The Internet Archive has a capture dated 2026-09-22 (HTTP 200); we did not download it |
| Small Area FMR FY2027 | https://www.huduser.gov/portal/datasets/fmr/fmr2027/FY27_safmrs.xlsx | XLSX, by ZIP code | none for browsers | same WAF challenge (Internet Archive capture dated 2026-10-02) |
| HUD User API | `https://www.huduser.gov/hudapi/public/fmr/...` (`/fmr/listStates`, `/fmr/statedata/{state}`, `/fmr/data/{entityid}`) | JSON | Bearer token from a free HUD User account | `/fmr/listStates` without a token gives HTTP 403. Per third-party summaries of the OpenAPI spec, the limit is 60 queries per minute and apps must show a non-endorsement notice. **Not verified on HUD's site** |
| HUD ArcGIS FeatureServer (used) | https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/Fair_Market_Rents/FeatureServer/0 | ArcGIS REST, JSON/GeoJSON; CSV/XLSX through the Hub (`hudgis-hud.opendata.arcgis.com`, item `12d2516901f947b5bb4da4e780e35f07`) | none | works. 2,622 areas in total, 215 in Texas, `maxRecordCount` 1000 |
| HUD ArcGIS Small Area FMR | https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/HUD_PDR_Small_Area_Fair_Market_Rents/FeatureServer/0 | ArcGIS REST, ZCTA polygons; values come through a relationship class | none | metadata read. Data last edited 2025-09-30 too. Values not extracted |

## Fields

ArcGIS layer `FAIR_MARKET_RENTS` (fields read from the layer metadata):

| Field | Meaning | Our model |
|---|---|---|
| `FMR_CODE` | HUD FMR area code, e.g. `METRO12420M12420` (metro area, CBSA 12420), `METRO26420N48015` (a county split off as its own HUD Metro FMR Area: county FIPS 48015), `NCNTY48001N48001` (non-metro county, FIPS 48001) | `area_code` |
| `FMR_AREANAME` | e.g. `Austin-Round Rock-San Marcos, TX MSA` | `area_name` |
| `FMR_0BDR` ... `FMR_4BDR` | monthly FMR in USD, integer, 0 to 4 bedrooms | `Money(amount, "USD")` per bedroom count |
| geometry | area polygon | used for the point lookup, not stored |

HUD's description says rent for 5+ bedrooms = 4-bedroom FMR × 1.15 per extra bedroom. Those values are not in the service.

The county file `FY27_FMRs.xlsx` should also carry the county FIPS of each row and the HUD area code, which makes the county join direct. **We could not open it, so we have not confirmed its column names.** Check this on the first manual download.

### Proposed mapping to our model (proposal, not in the UML yet)

The UML has no place for reference rents. Proposal:

- New reference table `rent_benchmarks`: `country_code`, `scheme` (`us.hud_fmr`), `area_code`, `area_name`, `period` (`FY2027`), `bedrooms` (0–4), `amount`, `currency` (`USD`), `source_url`, `file_hash`, `ingestion_run_id`.
- New table `rent_benchmark_areas`: (`scheme`, `period`, `area_code`) → county FIPS list (or ZIP list for SAFMR).
- `Institution` (or the campus) needs `county_fips` and lat/long, filled from IPEDS HD.
- `CostEstimate.living_cost` uses the FMR for `bedrooms = f(dependents)` as a `VerifiedValue` with status `confirmado_oficial`, `source_url` = the HUD file, plus the fiscal year. The rule "how many bedrooms for N dependents" is a product decision.

## Campus → FMR area

Two official ways, both tested or confirmed in part:

1. **By county FIPS (preferred, needs the HUD county file).** IPEDS HD has `COUNTYCD` ("Fips County code", 5 digits) and `COUNTYNM` ("County name"). Source for the names: the CRAN `IPEDS` package documentation of the HD 2020 file (https://rdrr.io/cran/IPEDS/man/dir_info2020.html). **We could not open the NCES dictionary**: nces.ed.gov reset every connection during the spike. Confirm on the HD dictionary of the year used. Then join `COUNTYCD` to the county FIPS in `FY27_FMRs.xlsx`.
   - For non-metro counties and split counties the ArcGIS `FMR_CODE` already contains the county FIPS (`N48001`). For metro areas (`M12420`) you need the county list of the area, which is in the HUD file. Do not use the OMB CBSA list alone: HUD splits some counties out of their MSA (e.g. `Austin County, TX HUD Metro FMR Area`, `METRO26420N48015`, is outside the Houston area).
2. **By point-in-polygon (works today, no token).** IPEDS HD has `LATITUDE` and `LONGITUD`. The ArcGIS layer accepts a point query (`geometry=lon,lat`, `geometryType=esriGeometryPoint`, `inSR=4326`, `spatialRel=esriSpatialRelIntersects`). The spike tested this with the Census 2024 Gazetteer internal point of each city, because IPEDS was not reachable.

## Texas sample (3 bedrooms and others)

From `spikes/_raw/hud_fmr/tx_city_points.json`, produced by `spikes/s6_hud/fmr_tx.py`. Monthly USD. **Probable vintage FY2026** (see below), not the current FY2027.

| City (Census place, Gazetteer 2024) | FMR area | FMR_CODE | 0BR | 1BR | 2BR | **3BR** | 4BR |
|---|---|---|---|---|---|---|---|
| Austin city | Austin-Round Rock-San Marcos, TX MSA | METRO12420M12420 | 1474 | 1562 | 1852 | **2347** | 2760 |
| Houston city | Houston-The Woodlands-Sugar Land, TX HUD Metro FMR Area | METRO26420M26420 | 1280 | 1323 | 1573 | **2116** | 2639 |
| Dallas city | Dallas, TX HUD Metro FMR Area | METRO19100M19100 | 1582 | 1648 | 1931 | **2431** | 3091 |
| San Antonio city | San Antonio-New Braunfels, TX HUD Metro FMR Area | METRO41700M41700 | 1077 | 1177 | 1426 | **1830** | 2132 |
| College Station city | College Station-Bryan, TX MSA | METRO17780M17780 | 1025 | 1082 | 1186 | **1649** | 1928 |

## Vintage

- The layer has no year field. The ArcGIS item description still says "Date of Coverage: FY2024", which is stale text.
- `editingInfo.dataLastEditDate` of the layer = 2025-09-30, the day before FY2026 took effect. The item itself was modified on 2026-04-20 (metadata only; HUD published revised FY2026 FMRs in the Federal Register on 2026-04-21, and we cannot tell if the layer has them).
- The layer's Phoenix-Mesa-Chandler 2BR is 1839. A secondary summary (Novogradac, via web search) gives Phoenix 2BR as 1839 in FY2026 and 1734 in FY2027. That points to FY2026.
- Conclusion: treat the numbers above as **FY2026, unconfirmed**. Do not load them as current.

## Limitations

- FMR is a 40th percentile gross rent used to set voucher payment standards. It is not the median or the rent near campus. Small Area FMR (by ZIP) is closer to the campus neighbourhood. Both are fine as an official, comparable baseline. Show the label "HUD FMR FYxxxx, 40th percentile, includes utilities".
- One value per metro area: Austin and Round Rock get the same FMR.
- huduser.gov blocks scripted downloads (WAF). Annual ingestion needs either a manual browser download committed to `spikes/_raw`/ingestion storage, or a HUD User API token.
- The ArcGIS layer lags behind huduser.gov (FY2027 was not there on 2026-11-20).

## Terms of use

- US federal government data. The ArcGIS item license text is a disclaimer ("HUD ... assume no responsibility for the use or misuse of the dataset. No warranty ..."), with no reuse restriction.
- The HUD User API terms (per a secondary summary) set 60 queries per minute and a non-endorsement notice. Check the official text when a token is requested.

## Update frequency

Once a year. FMRs must be posted at least 30 days before October 1 (42 USC 1437f) and take effect on October 1. HUD can revise areas later (reevaluation requests), as it did for FY2026 in April 2026.

## Needs a human decision

1. Who gets the FY2027 file: a person downloads `FY27_FMRs.xlsx` (and `FY27_safmrs.xlsx`) in a browser each year, or someone creates a free HUD User account for an API token. The agent did not create an account.
2. FMR (metro) or Small Area FMR (ZIP) for the living cost.
3. Bedrooms per household size (e.g. couple + 1 child = 2BR?).
4. Adding `rent_benchmarks` and campus `county_fips`/lat-long to the UML (proposal above).

## Files

- Script: `spikes/s6_hud/fmr_tx.py` (`python3 -I spikes/s6_hud/fmr_tx.py spikes/_raw/hud_fmr`)
- Raw: `spikes/_raw/hud_fmr/layer_meta.json`, `tx_areas.json` (215 Texas areas), `tx_city_points.json`; `spikes/_raw/census_gazetteer/2024_gaz_place_48.txt` (https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_gaz_place_48.txt)
