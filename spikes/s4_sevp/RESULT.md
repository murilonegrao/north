# S-4 SEVP — result (answers Q10)

Run on 2026-11-21 with the SEVP list dated 2026-11-18 and IPEDS HD2024.

## Q10 in one sentence

There is no CSV/XLSX: the only bulk download is a 252-page PDF printed from Excel (13,807 campuses, no UNITID/OPEID, names truncated), which we can parse reliably and match by name + city for 92% of Texas graduate institutions automatically (86.4% exact + 5.5% approximate), leaving about 8% for a human.

## Numbers (Texas)

| Universe | Total | exact | approximate | exact name, other city | no match |
|---|---|---|---|---|---|
| IPEDS active, highest offer master's or above, not admin units | 110 | 95 (86.4%) | 6 (5.5%) | 1 (0.9%) | 8 (7.3%) |
| SEVP school codes with a campus in TX (context only) | 418 | 163 (39.0%) | 11 (2.6%) | 6 (1.4%) | 238 (56.9%) |

Manual review of the 110 graduate institutions:

- **exact (95):** all 95 point to the right school. Precision looks like 100%, judged by eye; there is no gold standard.
- **approximate (6):** all 6 are right (for example, "The Univ of Tx M.D. Anderson Cancer" and the El Paso entry under "Texas Tech University System").
- **exact name, other city (1):** Strayer University-Texas. The school is right, but no SEVP campus is in Farmers Branch.
- **no match (8):**
  - East Texas A&M University is a false negative. It was renamed in 2024, and SEVP still lists "Texas A&M University-Commerce".
  - West Coast University-Texas: SEVP lists the school, but every campus has city "Irvine, CA", so the Texas campus can't be identified.
  - Six were not found in the SEVP list under any name we tried: AOMA Graduate School of Integrative Medicine, Bakke Graduate University, Episcopal Theological Seminary of the Southwest, Grace School of Theology, Redeemers University North America, University of Phoenix-Texas. They are probably not certified, but a human must confirm on the school search page.

In the SEVP→IPEDS direction, most unmatched schools are K-12, religious or language schools. That is expected: they aren't in IPEDS, and North doesn't care about them. This direction also shows why matching by name alone is risky. "Texas A&M University-Commerce" matched "Texas A & M University-Corpus Christi" on name only, and "Radford School" matched "Vet Tech Institute of Houston" through an IPEDS alias.

Files: `out/tx_match_summary.json`, `out/tx_ipeds_grad_to_sevp.csv`, `out/tx_sevp_schools_to_ipeds.csv`.

## Recommendation: (b) RF-04 becomes curation with reconciliation tasks, heavily assisted

Q10's precondition for (a), a structured download, is false. But the PDF still gives most of the value automatically:

1. **Import:** the parser (`parse_sevp_pdf.py`) turns the PDF into CSV. Its checks: row count equals the codes found by `pdftotext` (13,807), every row has F/M flags and a 2-letter state, and campus codes are unique.
2. **First match:** by normalized name + city + state against IPEDS. Accept `exact` automatically. Open a `ReconciliationTask` for `approximate`, `exact_name_only` and `none`. In Texas that is about 15 of 110 institutions.
3. **Store the link:** once confirmed, save the SEVP **campus code** as an identifier (`institution_identifiers.scheme = 'sevp_campus'`). Later runs match by that code, not by name.
   - Don't use the 12-character SEVP school code as a unique identifier. It is shared by several IPEDS units: UNT, UNT Dallas and UNT Health Science Center share DAL214F00610; UH and UH-Victoria share HOU214F00110.
4. **Disappearances:** an institution that matched before but is gone from a new list version becomes a `ReconciliationTask`. It is not marked "not certified" automatically. Name changes, as with East Texas A&M, will cause this.
5. **What to record:** `intl_authorization = {scheme: 'sevp', authorized: F-1 flag == 'Y'}`, with source URL, list date and file hash. M-1 doesn't matter for master's programs.

## Does UML sequence 5.1 need to change? Yes.

- The step that matches SEVP "by InstitutionIdentifier (unitid, opeid), never by name" can't be done, because the list has neither key. Replace it with two steps:
  - Match by `sevp_campus` identifier when the link already exists.
  - Otherwise, match by name + city as a *suggestion*: exact goes in automatically, the rest go to `ReconciliationTask`.
- **Get the file:** the `SEVP` participant gets the file from a dated PDF URL (`/assets/certified-school-list-MM-DD-YY.pdf`). The link has to be scraped from the school-search page.
- **Access is blocked:** studyinthestates.dhs.gov and ice.gov answer 403 (Akamai "Access Denied") to `curl` with our generic user-agent. A fetch tool with a different client did get through. The CronJob may therefore not be able to download it. Plan for a manual upload path: the admin downloads the PDF and the ingestor takes it as input, with the hash recorded in `ingestion_runs.file_version`.
- **ER change:** add `sevp_campus` to the list of identifier schemes. The name-to-name rule is a US-specific exception; keep it inside `ingest/us`.

## Limitations

- Names in the PDF are cut at the cell width (about 38–55 characters). The parser drops the text that overflows into the next column, the same way the printed page does.
- The "city" is sometimes the school's main address, not the campus city. Examples: Lamar State College-Orange shows "Beaumont"; West Coast University shows "Irvine" for every campus.
- The site showed "13808 results found". The PDF has 13,807 rows, which we didn't reconcile.
- How often it is updated is unknown. The PDF file name carries the date (11-18-26), so expect irregular, dated releases.
