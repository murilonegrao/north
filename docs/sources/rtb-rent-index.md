# Source: RTB rent data (Ireland)

Spike for the Irish living-cost figure (BR-07): a reference rent per locality and bedroom count, the Irish counterpart of HUD FMR ([`hud-fmr.md`](hud-fmr.md)).

Date of the spike: **2026-11-22**. User agent `north-research-spike`, one request per file, with pauses between requests. Raw files are in `spikes/_raw/rtb/` (git-ignored, never committed).

## Summary

- **Publisher:** Residential Tenancies Board (RTB), the state body where every private tenancy is registered. The **RTB Rent Index** is produced with the ESRI and comes out quarterly. The latest edition is **Q1 2026**, published 2026-09-03.
- **Two products, and neither covers locality × bedrooms at the finest level:**
  1. **RTB/ESRI Rent Index** (standardised, i.e. mix-adjusted; new and existing tenancies). It gives **166 LEAs** (local electoral areas), counties, cities and selected local authorities, but at those levels only for **all bedrooms together**. Bedroom splits (1, 2, 3, 4+ for houses; 1, 2, 3+ for apartments) exist only at **national and regional** level (National, Dublin, Non-Dublin, GDA, …). The full tables are in the **PDF**. Figure data come as small **XLSX** files.
  2. **RTB Average Monthly Rent Report**, hosted by the **CSO on PxStat**: tables **RIQ02** (quarterly), **RIH02** (half-yearly) and **RIA02** (annual). These are plain averages, not standardised. They cover **446 locations** (counties, cities, towns and Dublin postal districts) × **bedrooms** (1, 2, 3, 4+, plus groupings) × **property type**, from 2007Q4. The data come through an **open API** (JSON-stat, CSV, XLSX, PX) with no key.
- **Scripts are not blocked:** rtb.ie, its `wp-content` files and `ws.cso.ie` all answered plain `curl` with HTTP 200 (one wrong guessed URL gave a 404). This is unlike huduser.gov.
- **Recommendation:** use **CSO RIQ02**, by county or city × bedrooms, as the per-locality rent, with the quarter stored. Use the RTB standardised county figure only as a fallback or cross-check. Details below.

## Access options

| Option | URL | Format | Auth | Result |
|---|---|---|---|---|
| RTB/ESRI Rent Index data page | https://rtb.ie/data-insights/rtb-data-hub/rtb-esri-rent-index-data-set/ | HTML with 13 XLSX links (`RTBRIQ126-Figure-N.xlsx`, Q1 2026) and links to the CSO tables | none | HTTP 200 |
| RTB Rent Index reports | https://rtb.ie/data-insights/rtb-research-reports/rtb-esri-rent-index/ (also on esri.ie, e.g. https://www.esri.ie/system/files/publications/RI2026Q1.pdf) | PDF, about 70 pages | none | Q4 2025 PDF downloaded (https://rtb.ie/wp-content/uploads/2026/05/RTB-Rent-Index-Q4-2025.pdf, 5.2 MB, HTTP 200) |
| Figure XLSX (sample) | https://rtb.ie/wp-content/uploads/2026/09/RTBRIQ126-Figure-12.xlsx, `…-13.xlsx` | XLSX, sheets "New" and "Existing" | none | downloaded. Fig. 12 = houses, Fig. 13 = apartments; standardised rent by bedrooms for National, Dublin, Non-Dublin, GDA and regions, Q1 2026 |
| CSO PxStat RIQ02 (used) | https://data.cso.ie/table/RIQ02 · API `https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/RIQ02/JSON-stat/2.0/en` (also `/CSV/1.0/en`, XLSX, PX) | JSON-stat 2.0 (7.7 MB, whole cube) | none | HTTP 200. Updated 2026-05-14 ("Planned release"); latest quarter **2025Q4** |
| CSO RIH02 / RIA02 | https://data.cso.ie/table/RIH02, https://data.cso.ie/table/RIA02 | same | none | not downloaded |
| Profile of the Register | https://rtb.ie/data-insights/rtb-data-hub/profile-of-the-register/ | — | — | not read. Tenancy counts by LEA and dwelling size, no rents (according to the RTB September 2026 quarterly update) |

## RIQ02 structure (read from the JSON-stat file)

| Dimension | Code | Values |
|---|---|---|
| Statistic | `RIQ02` | "RTB Average Monthly Rent Report", unit **Euro**, 2 decimals |
| Quarter | `TLIST(Q1)` | 73 quarters, 2007Q4 … 2025Q4 (codes like `20254`) |
| Number of Bedrooms | `C02970V03592` | All bedrooms, One bed, Two bed, Three bed, 1 to 2 bed, 1 to 3 bed, Four plus bed |
| Property Type | `C02969V03591` | All property types, Detached house, Semi detached house, Terrace house, Apartment, Other flats |
| Location | `C03004V03625` | 446 labels: 26 counties, cities ("Cork City", "Galway City", "Limerick City", "Waterford City"), county towns, towns written "Maynooth, Kildare", Dublin postal districts ("Dublin 2") and sub-areas ("Grand Canal Dock, Dublin 2"). **Labels only; no LEA or county codes** |

- Missing cells are `null`. 990,448 of 1,367,436 cells are null. RTB says: "A nil return (0.00) indicates insufficient data for that location."
- Coverage in 2025Q4, all property types: One bed 108/446 locations, **Two bed 186**, Three bed 156, Four plus 82. Counties and the main cities are complete for 2 and 3 bedrooms. Small towns and postal districts are often missing; for example "Dublin 2" was null for every bedroom count in 2025Q4.
- Contact field in the metadata: a generic RTB research mailbox (not personal).
- `official: true`. Copyright: Residential Tenancies Board.

Sample, 2025Q4, all property types, € per month (RIQ02):

| Location | 1 bed | 2 bed | 3 bed | 4+ bed |
|---|---|---|---|---|
| Dublin (county) | 1,740.68 | 2,253.28 | 2,585.87 | 3,319.36 |
| Cork City | 1,235.26 | 1,623.69 | 1,841.79 | 2,552.88 |
| Galway City | 1,215.02 | 1,665.37 | 1,939.60 | 2,457.25 |
| Limerick City | 1,289.04 | 1,584.98 | 1,738.10 | 2,301.21 |
| Maynooth, Kildare | 1,259.19 | 1,732.67 | 2,166.03 | 2,669.81 |
| Leitrim | null | 944.69 | 1,034.03 | 1,183.81 |

Compare the standardised Rent Index for Q1 2026, new tenancies, houses, Dublin: 1 bed 1,706 · 2 bed 2,195 · 3 bed 2,584 · 4+ 3,315 (Figure 12 XLSX).

## RTB/ESRI Rent Index structure (Q4 2025 PDF, Q1 2026 XLSX)

- Measure: **standardised average rent** (hedonic regression, mix-adjusted), separately for **new** and **existing** tenancies. Q4 2025 sample: 11,593 new and 42,914 existing tenancy registrations.
- Geography: national, regions, 26 counties (Table 5), cities (Table 6), selected local authorities (Table 7), **166 LEAs** (Table 8). Table 8 has the new-tenancy rent, the existing-tenancy rent, and a comparison with a reference average. **All bedrooms only.**
- Bedrooms: Tables 1 to 4 and Figures 12 and 13. National and regional only. Houses 1/2/3/4+, apartments 1/2/3+.
- Release lag: Q4 2025 published around May 2026, Q1 2026 on 2026-09-03. So **about 5 to 8 months** after the quarter. The CSO RIQ02 table follows the same cycle: 2025Q4 was published 2026-05-14.

## Licence

- CSO PxStat data: the data.gov.ie listing for RIA02 says **Creative Commons Attribution 4.0**. The JSON-stat file names RTB as copyright holder. **Not checked on the CSO site itself.** Before ingesting, confirm on the dataset page and cite "Residential Tenancies Board (RTB), via CSO PxStat".
- RTB PDFs and XLSX: no licence statement was found on the data page. Treat them as "official, attribution required" until confirmed.

## Campus → rent locality

There are no codes in RIQ02, so the join is by label:

1. **By county or city (recommended).** Store `rent_locality` on the Irish campus as an RIQ02 location label: the city where there is one (Dublin county, Cork City, Galway City, Limerick City, Waterford City), otherwise the county. All 26 counties have 2 and 3 bed values.
2. **By town** (e.g. "Maynooth, Kildare" for Maynooth University). More precise, but often null. Fall back to the county when the cell is null.
3. **By LEA:** only possible with the standardised Rent Index, and only for all bedrooms. To use it, scale the LEA all-bedroom figure by the regional bedroom ratio from Figures 12 and 13. That is an estimate of ours, not an official value, so it would be `reported_by_program`-grade or lower, not `confirmed_official`.

## Proposed mapping (proposal, not in the UML)

The US proposal in `hud-fmr.md` already defines `rent_benchmarks`. The Irish rows would fit it:

- `scheme` = `ie.rtb_avg_rent` (RIQ02) or `ie.rtb_rent_index` (standardised)
- `area_code` = the RIQ02 location label (no code exists); `period` = `2025Q4`
- `bedrooms` = 1, 2, 3, 4 (4 = "Four plus bed"); `property_type` = "All property types"
- `amount` in EUR, `source_url` = the CSO API URL, `file_hash`, `ingestion_run_id`

The bedroom rule `ceil((1 + dependents) / 2)`, max 4 (R6) maps directly onto RIQ02's 1, 2, 3, 4+. But **in Ireland a Stamp 2 student has no dependants** (see [`ireland-immigration-rules.md`](ireland-immigration-rules.md)). Family-size rents matter only for the PhD and researcher routes.

## Open points

- RIQ02 is "average monthly rent". RTB does not say on the page whether it is new tenancies only or all registrations. Check the CSO table notes or ask the RTB research mailbox.
- Rents are **rent only**: no utilities, unlike HUD FMR, which is gross rent. A utilities figure would need another official source; none was looked at here.
- Whole-cube JSON-stat is 7.7 MB. The PxStat API can filter by dimension; use a filtered query in production.
