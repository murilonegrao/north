# S-1 / S-2 result: Q09

Run on 2026-11-21. Sources: Scorecard FoS `Most-Recent-Cohorts-Field-of-Study_10152026`, IPEDS `C2024_A` / `HD2024` / `IC2023_AY`. Details: `docs/sources/scorecard.md` and `docs/sources/ipeds.md`.

## Answer in one sentence

**Yes. The College Scorecard still publishes master's data by field of study (`CREDLEV = 5`), and in Texas it covers all three CIP families with the same universe as IPEDS: 99 institution × CIP4 pairs at 48 institutions. But it only uses 4-digit CIP, has no graduate tuition, and suppresses earnings in 70% of the rows.**

## Numbers behind it

| Measure | Scorecard FoS | IPEDS C2024_A (AY2023-24) |
|---|---|---|
| TX master's, all CIPs | 2,319 rows / 105 inst. | 2,690 UNITID × CIP6 / 106 inst. |
| 11.xx computing | 83 programs / 46 inst. | 90 CIP6 (80 CIP4) / 46 inst. |
| 52.12 information systems | 9 / 9 | 10 CIP6 (8 CIP4) / 8 inst.; only 3 with completions > 0 |
| 30.70 data science | 7 / 7 | 7 / 7 |
| Total in target CIPs | **99 / 48** | **107 CIP6 (95 CIP4) / 48** |
| CIP granularity | 4 digits (100% of rows) | 6 digits |
| Graduate tuition | none (`TUITIONFEE_*` is undergraduate) | `TUITION7` (non-resident) for 47 of 48 inst. |
| Earnings (`EARN_MDN_1YR`) | 28 value / 69 `PS` / 2 `NA` (70% suppressed; 30.70: 7 of 7 suppressed) | none |
| International graduates | none | `CNRALT`: 6,778 of 8,636 completions (78%) |

Agreement between the two sources:
- all 95 UNITID × CIP4 pairs from IPEDS are in the Scorecard. The Scorecard has 4 extra pairs, all with no recent completions;
- `IPEDSCOUNT2` = C2024_A sum in 95 of 95 pairs;
- the Scorecard API (5 calls with DEMO_KEY) returned the same 99 programs / 48 institutions as the bulk file.

## Recommendation

**Q09 = (a) by the question's criterion (coverage). Even so, I recommend making RF-02 (IPEDS) a Must.** Not because of coverage: the Scorecard is missing three things North needs.
1. **6-digit CIP.** The STEM OPT rule (RF-03, RN-03) works on 6-digit CIP. In 10 TX pairs, one CIP4 holds 2–3 different CIP6 codes.
2. **Graduate tuition for non-residents** (`TUITION7`), as an institution reference value for the cost dimension.
3. **`CNRALT`** (temporary-visa graduates). This is the best official signal that a program actually takes international students.

Proposed split:
- **IPEDS = primary discovery source** (UNITID × CIP6 × AWLEVEL 7 + HD + IC_AY).
- **Scorecard FoS = enrichment** (earnings and debt by UNITID × CIP4, with the RN-13 caveat). Both are bulk files keyed by UNITID; the cost of the second source is small.

If the decision is to keep RF-01 as the only Must, the MVP works for discovery, but the STEM check stays ambiguous for every CIP4 with more than one CIP6 and will need curation.

## Changes to UML sequence 5.1

1. Add the participant `IPEDS (NCES, bulk files)` and make it the first source: download `C<year>_A`, `HD<year>`, `IC<year>_AY`, filter `STABBR = TX`, `AWLEVEL = 7`, CIP in the configured families. This creates `Institution` + `Program` candidates per UNITID × CIP6.
2. Swap `GET /schools?state=TX&fields=programs.cip_4_digit...` for **downloading the Scorecard FoS bulk file** (versioned file name = `ingestion_runs.file_version`; no API key, no paging, no 429). Join by `UNITID` + CIP prefix (the program's first 4 CIP6 digits) and write earnings/debt as values scoped to CIP4.
3. Write `TUITION7`/`FEE7` as `cost.tuition_reference_nonresident` with status "official reference (institution average)", never "verified".
4. Make the "429 or 5xx → backoff" note apply to every source: nces.ed.gov was down for ~20 min during the spike. Keep the zip and its hash.
5. A UNITID × CIP6 with 0 completions in the latest year → program created as "to confirm", not published.

Impact on the ER (§8): no new table. `program_classifications` gets the CIP6 as `is_primary`. Scorecard earnings go into `programs.career` along with the CIP4 they were measured at.

## For human decision

- Accept RF-02 as a Must even though Q09 came out (a) (see above).
- **52.12 is thin in Texas:** only 3 programs with completions in 2023-24 (48 graduates). CIP 30.71 (Data Analytics, incl. 30.7102 Business Analytics) has big master's programs. For example, UT Dallas 3071 shows 1,033 awards in `IPEDSCOUNT2`, and the Scorecard FoS has 182 master's rows in 3071 nationally. It is outside Q05; worth reconsidering after the pilot.
- The Urban Institute mirror (used as a backup while NCES was down) has terms that were not reviewed. As an official source, use only NCES.
