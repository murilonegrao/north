# Source: DAPIP (Database of Accredited Postsecondary Institutions and Programs)

Spike S-5, run on 2026-11-21. Script: `spikes/s5_dapip/analyze_dapip.py`.

## What it is

The U.S. Department of Education's database of institutions and programs accredited by recognized agencies. It feeds RF-05 and `institutions.accreditation`.

## Download

- Page: https://ope.ed.gov/dapip/#/download-data-files ("Download Accreditation Data Files", CSV or Excel).
- The page is an Angular app. The button calls an API that works with plain `curl`, needs no key, and accepts our generic user-agent:

  ```
  curl -A north-research-spike -X POST -H 'Content-Type: application/json' \
    --data-raw '{"CSVChecked":true,"ExcelChecked":false}' \
    -o DAPIPData.zip https://ope.ed.gov/dapip/api/downloadFiles/accreditationDataFiles
  ```

  We found this endpoint by reading the site's JavaScript bundle. It is not documented, so it can change.
- Answer on 2026-11-21:
  - `DAPIPData.zip`, 3,738,869 bytes, sha256 `2d2bef85…cfd22521a`.
  - Files inside are dated 2026-11-20, which suggests the zip is built daily or on request.

| File | Rows | Columns |
|---|---|---|
| InstitutionCampus.csv | 45,826 (10,376 Institution, 33,786 Additional Location, 1,664 Site) | DapipId, OpeId, IpedsUnitIds, LocationName, ParentName, ParentDapipId, LocationType, Address, GeneralPhone, AdminName, AdminPhone, AdminEmail, Fax, UpdateDate |
| AccreditationRecords.csv | 65,682 | DapipId, AgencyId, AgencyName, ProgramId, ProgramName, SequentialId, InitialDateFlag, AccreditationDate, AccreditationStatus, ReviewDate, DepartmentDescription, AccreditationEndDate, EndingActionId |
| AccreditationActions.csv | (26 MB) | DapipId, AgencyId, AgencyName, ProgramId, ProgramName, SequentialId, ActionDescription, ActionDate, JustificationDescription, JustificationOther, EndDate |

**Personal data:** InstitutionCampus.csv has administrator names, phones and e-mails (AdminName, AdminPhone, AdminEmail). North doesn't need them. Drop these columns at ingestion and never store or serve them.

## Join keys

- **Yes**, it has both `OpeId` (8 digits) and `IpedsUnitIds`. The UNITID field can hold a list ("133881, 480569"); 15 institutions have more than one.
- Of 10,376 `Institution` rows, 7,441 have a UNITID and 7,127 have an OPEID. Additional locations usually have neither.
- **Texas** (110 IPEDS graduate institutions, the same universe as S-4):

  | Join | Institutions |
  |---|---|
  | By UNITID | 100 |
  | Parent's 6-digit OPEID (branch campuses of multi-state chains) | 4 |
  | No join | 6 |

  The 6 without a join:
  - Strayer-Texas, DeVry-Texas and University of Phoenix-Texas: chain campuses. The parent row exists, but for Strayer and Phoenix it has a different OPEID, and for DeVry no OPEID or UNITID at all.
  - TTUHSC El Paso and Redeemers University: they exist in DAPIP, but with no OPEID or UNITID.
  - Southwestern Baptist Theological Seminary: DAPIP has UNITID 228477, while IPEDS 2024 uses 494603.

  So the join covers about 95%. The rest need a curated link (a `ReconciliationTask`).

## How to tell institutional ("regional") accreditation

- Institutional accreditation: `AccreditationRecords.ProgramName == "Institutional Accreditation"`. Everything else is programmatic accreditation (nursing, music, theology and so on).
- Current: empty `AccreditationEndDate`. `AccreditationStatus` is one of Accredited (62,581), Preaccredited (3,041) or Denied Accreditation (60).
- **"Regional" is not a field.**
  - Since July 2020, Department of Education rules no longer distinguish regional from national accreditors, and DAPIP has no flag for it.
  - To show "regional", keep a list of the 7 former regional commissions, matched by `AgencyName` (better: by `AgencyId`, still to be mapped). The 7 are: MSCHE, NECHE, HLC, NWCCU, SACSCOC (in DAPIP: "Southern Association of Colleges and Schools Commission on Colleges d.b.a. Commission on Colleges and Universities"), WSCUC and ACCJC.
  - Recommendation: store the institutional accreditor's name and status, and treat "former regional" as a derived label, not as a quality filter.
- Texas:
  - 103 of 110 have a current institutional accreditation.
  - 90 have one from a former regional commission, almost all SACSCOC.
  - The other 13 have national or faith-based accreditors (ABHE, TRACS, ACCSC, ABHES, ATS, ACAHM).
  - Examples without a former regional accreditor: Arlington Baptist University (ABHE), Paul Quinn College (TRACS), Southwest University at El Paso (ABHES).
  - AOMA's SACSCOC record ended on 2024-04-06.

Output: `spikes/s5_dapip/out/tx_ipeds_grad_accreditation.csv`, `spikes/s5_dapip/out/dapip_summary.json`.

## Mapping to our model

| DAPIP | North |
|---|---|
| IpedsUnitIds / OpeId | join with `institution_identifiers` (`unitid`, `opeid`) |
| DapipId | new identifier `institution_identifiers(scheme='dapip')`, so a confirmed match can be reused |
| AgencyName + AccreditationStatus (current institutional record) | `institutions.accreditation` (VerifiedValue, `confirmado_oficial`, source URL = DAPIP, date = download date) |
| ReviewDate | next review (useful for RF-24-style warnings) |
| ProgramName ≠ institutional | programmatic accreditation (ABET, AACSB, etc.). Out of scope for the MVP, but useful later per program. AACSB and ABET are not recognized by ED, so they don't appear here. |

## Coverage

National: all institutions and programs accredited by ED-recognized agencies. It doesn't cover agencies outside ED recognition.

## Limitations

- About 30% of `Institution` rows have no UNITID.
- Some codes are out of date compared with IPEDS (SWBTS).
- Some `InitialDateFlag` values are "Estimated" (15,612 records), meaning the start date is approximate.
- `UpdateDate` is filled for only 9,271 location rows (newest 2026-11-06).

## Terms of use

U.S. federal government data, public domain. No specific terms page was found.

## Update frequency

- Continuous: accreditors report actions to ED, and the zip seemed to be generated on 2026-11-20.
- Suggested cadence: monthly. The ingestion is idempotent on the zip's sha256.
