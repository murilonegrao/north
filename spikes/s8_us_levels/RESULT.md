# S-8 Every award level and every field (US): result

Run on 2026-11-22. Script: `analyze_levels.py`. Output: `out/` (`summary_levels.json` and one CSV per table). The national program list it derives (`ipeds_programs_all_levels.csv.gz`, 267,595 rows) goes to `spikes/_raw/ipeds/derived/`, which is git-ignored.

```
uv run --with pandas,openpyxl python -I spikes/s8_us_levels/analyze_levels.py spikes/_raw spikes/s8_us_levels/out
```

Inputs were already downloaded by S-1, S-2 and S-4: IPEDS C2024_A (AY2023-24 completions) with its dictionary, HD2024 and IC2023_AY with its dictionary; Scorecard FoS `_10152026` and Institution `_11022026`; the parsed SEVP list dated 2026-11-18. The regulation text is new for this spike: 8 CFR 214.2 and 214.3 from the eCFR versioner API (snapshot 2026-11-01). It is saved in `spikes/_raw/ecfr/`. sha256 for 214.2 is `673bc972…3097b8`; for 214.3 it is `fcb52cd3…7f39`. The API needs `--compressed`. The HTML eCFR page redirects scripts to an "unblock" page.

Definitions:
- **Program:** UNITID × CIP6 × AWLEVEL, with first and second majors summed. The CIP `99` total row is excluded.
- **Tech CIPs:** 11.xx, 52.12xx, 30.70xx and 30.71xx. The last one (30.71 Data Analytics) is new compared with S-2, and it adds 25 TX master's rows: 107 + 25 = 132.

## 1. IPEDS award levels (C2024_A dictionary, Frequencies sheet)

| AWLEVEL | Label | Rows in C2024_A data |
|---|---|---|
| 20 | Certificates of less than 12 weeks | 4,543 |
| 21 | Certificates of at least 12 weeks but less than 1 year | 35,358 |
| 2 | Certificates of at least 1 but less than 2 years | 29,688 |
| 3 | Associate's degree | 48,741 |
| 4 | Certificates of at least 2 but less than 4 years | 2,445 |
| 5 | Bachelor's degree | 104,090 |
| 6 | Postbaccalaureate certificate | 14,936 |
| 7 | Master's degree | 45,516 |
| 8 | Post-master's certificate | 5,378 |
| 17 | Doctor's degree, research/scholarship | 13,469 |
| 18 | Doctor's degree, professional practice | 3,171 |
| 19 | Doctor's degree, other | 372 |

The dictionary also lists code 1 ("less than 1 year", split into 20 and 21) and the totals 12, 13, 14 and 15. None of these appear as rows in the data file, so the ingestor must not expect them. Code 1 means something else in older years, so check it against each year's dictionary.

## 2. Texas programs by level (IPEDS AY2023-24)

| Level (AWLEVEL) | Tech: programs | Tech: >0 / =0 | Tech: nonres. | All CIPs: programs | All: >0 / =0 | All: nonres. % |
|---|---|---|---|---|---|---|
| Cert < 12 weeks (20) | 4 | 0 / 4 | 0 | 80 | 39 / 41 | 0.2% |
| Cert 12 wk–1 yr (21) | 167 | 133 / 34 | 107 (2.3%) | 1,843 | 1,436 / 407 | 1.4% |
| Cert 1–2 yr (2) | 94 | 70 / 24 | 24 (1.9%) | 1,490 | 1,151 / 339 | 0.8% |
| Associate's (3) | 189 | 152 / 37 | 124 (3.9%) | 2,911 | 2,264 / 647 | 1.8% |
| Cert 2–4 yr (4) | 1 | 0 / 1 | 0 | 27 | 13 / 14 | 0.2% |
| Bachelor's (5) | 200 | 170 / 30 | 595 (6.2%) | 4,067 | 3,472 / 595 | 2.5% |
| Postbacc cert (6) | 38 | 19 / 19 | 362 (63.3%) | 687 | 320 / 367 | 17.8% |
| Master's (7) | 132 | 112 / 20 | 8,511 (76.8%) | 2,690 | 2,247 / 443 | 25.5% |
| Post-master's cert (8) | 0 | – | – | 120 | 66 / 54 | 24.6% |
| Doctor's research (17) | 21 | 18 / 3 | 153 (75.0%) | 806 | 706 / 100 | 29.8% |
| Doctor's professional (18) | 0 | – | – | 100 | 88 / 12 | 1.0% |
| Doctor's other (19) | 0 | – | – | 7 | 5 / 2 | 23.7% |
| **Total** | **846** | 674 / 172 | | **14,828** | 11,807 / 3,021 | |

Coverage:
- Tech CIPs: 148 TX institutions.
- All CIPs: 387 TX institutions.
- No program had a missing `CTOTALT`. All "unknown" counts are 0.

Nonresident completions in TX, all CIPs:
- Master's: 15,968 of 62,662.
- Research doctorate: 1,922 of 6,457.
- Bachelor's: 3,595 of 146,522.
- Associate's: 1,796 of 97,647.

International graduates cluster in master's, research doctorates and postbacc/post-master's certificates. Undergraduate and sub-baccalaureate awards are 0.2–6% nonresident. Professional doctorates are 1.0% in TX and 2.5% nationally.

## 3. National scale

| Scope | Programs (UNITID × CIP6 × level) | with completions > 0 | Institutions |
|---|---|---|---|
| US, tech CIPs, all levels | 15,567 | 11,317 | 2,676 |
| **US, all CIPs, all levels** | **267,595** | **200,947** | **5,869** |
| US master's only, all CIPs | 42,946 | 34,121 | 2,003 |

There are 1,607 distinct CIP6 codes. Programs whose CIP6 is on the DHS STEM list (`data/reference/dhs-stem-list-2024-07-22.csv`, 466 codes): 65,499 nationally, 3,780 in TX. Per level, nationally: bachelor's 81,872; associate's 45,907; master's 42,946; certificates below the bachelor's (20, 21, 2, 4) 63,501; postbacc and post-master's certificates 18,322; doctorates (17, 18, 19) 15,047.

Today North covers 132 TX tech master's programs. "Everything" is about 2,000× that by row count. Storage is trivial: about 270k small rows, around 10 MB compressed. Curation is not: a curator cannot visit 200k program pages, so most rows would carry only the official IPEDS/Scorecard values with no program page verified.

## 4. Tuition fields by level (IC2023_AY dictionary)

| Level | IC_AY variables | TX fill (202 IC_AY rows) |
|---|---|---|
| Undergraduate (certificate, associate's, bachelor's) | `TUITION1/2/3` + `FEE1/2/3`: in-district/in-state/out-of-state average tuition, full-time undergraduates. `CHG1/2/3AT3`/`AY3`: published tuition (and fees) 2023-24 | `TUITION3` 189; `CHG3AY3` 179 |
| Graduate (master's, research doctorate, postbacc/post-master's certificates) | `TUITION5/6/7` + `FEE5/6/7`; `HRCHG5/6/7` part-time per credit | `TUITION7` 103 |
| Professional practice doctorates, 9 fields | `ISPROF1..9` / `OSPROF1..9` (+ `ISPFEE`/`OSPFEE`): chiropractic, dentistry, medicine, optometry, osteopathic medicine, pharmacy, podiatry, veterinary medicine, law | `OSPROF3` (medicine) 13; `OSPROF6` (pharmacy) 9; `OSPROF9` (law) 10 |
| Living costs (all levels, undergraduate-oriented) | `CHG4AY3` books; `CHG5–9AY3` food, housing and other, on/off campus | not counted |

How this maps to North's fields:
- For a nonresident, the relevant value is out-of-state: `TUITION3`/`CHG3*` for undergraduate, `TUITION7` for graduate, `OSPROFn` for the 9 professional fields.
- Professional doctorates outside those 9 fields (for example DNP, DPT, OTD, AuD, PsyD) have no specific variable. They fall back to `TUITION7`.

Only 202 of 401 active TX institutions have an IC_AY row. Our reading, not checked in this spike: the rest are program/clock-hour reporters, whose charges are in a separate IPEDS file (IC<year>_PY). We did not download that file. Many sub-baccalaureate certificate schools would need it.

## 5. Scorecard Field of Study by credential level (UNITID × CIP4 × CREDLEV)

`EARN_MDN_1YR`: % with a value / % privacy-suppressed (`PS`).

| CREDLEV | Label (CREDDESC) | TX rows | TX value / PS | TX tech rows | Tech value / PS | US rows | US value / PS |
|---|---|---|---|---|---|---|---|
| 1 | Undergraduate Certificate or Diploma | 2,151 | 25.0 / 71.8 | 184 | 10.9 / 84.8 | 42,739 | 16.1 / 80.4 |
| 2 | Associate's Degree | 2,456 | 19.1 / 79.6 | 187 | 9.6 / 90.4 | 40,471 | 17.0 / 81.1 |
| 3 | Bachelor's Degree | 3,464 | 43.6 / 54.6 | 192 | 42.2 / 54.7 | 70,944 | 35.8 / 62.9 |
| 4 | Post-baccalaureate Certificate | 63 | 1.6 / 98.4 | 3 | 0 / 100 | 1,864 | 7.1 / 92.9 |
| 5 | Master's Degree | 2,319 | 30.5 / 66.9 | 119 | 24.4 / 72.3 | 38,199 | 28.7 / 69.6 |
| 6 | Doctoral Degree | 729 | 11.0 / 87.0 | 22 | 0 / 95.5 | 12,494 | 10.3 / 88.0 |
| 7 | First Professional Degree | 86 | 45.3 / 54.7 | 0 | – | 2,364 | 32.2 / 63.8 |
| 8 | Graduate/Professional Certificate | 682 | 3.5 / 85.9 | 36 | 5.6 / 72.2 | 14,512 | 3.8 / 89.6 |

The Scorecard levels do not line up 1:1 with IPEDS:
- CREDLEV 1 lumps all sub-baccalaureate certificates (IPEDS 20, 21, 2, 4).
- CREDLEV 6 is research/other doctorates.
- CREDLEV 7 "First Professional" corresponds to IPEDS 18.
- CREDLEV 8 merges post-master's certificates with graduate certificates.

Earnings are most usable for bachelor's (36–44% have a value) and first-professional degrees. They are mostly suppressed for doctorates and graduate certificates (≤ 11%). The RN-13 caveat still applies: earnings cover only federally aided graduates.

## 6. STEM OPT extension by level (8 CFR 214.2, eCFR 2026-11-01)

Source: https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.2. This is the browser URL. The text was read through the versioner API.

- **(f)(10)(ii)(C)(2), level:** "The degree that is the basis for the 24-month OPT extension is a bachelor's, master's, or doctoral degree in a field determined by the Secretary … to qualify within a science, technology, engineering, or mathematics field."
  - Associate's degrees and certificates (undergraduate or graduate) **do not qualify** for the STEM extension.
  - The degree must also be on the STEM list at the time of the DSO recommendation, (C)(2)(iii).
- **(f)(10)(ii)(C)(1):** the degree must be from a US institution accredited by an ED-recognized accreditor at the time of application.
- **(f)(10)(ii)(C)(3), previously obtained degree:** the STEM extension may rest on an earlier degree instead of the one that gave the current post-completion OPT. It must meet three conditions:
  - It was conferred by a US institution that is accredited and SEVP-certified at the time of the DSO recommendation.
  - It is on the current STEM list.
  - It was conferred within the preceding 10 years.

  Example: a STEM bachelor's from a US school followed by a non-STEM MBA can still give the extension.
- **Lifetime limit:** "In no event may a student be authorized for more than two lifetime STEM OPT extensions." A second extension needs a degree "at a higher degree level than the first".
- **Regular OPT, (f)(10):** 12 months, "and becomes eligible for another 12 months of practical training when they change to a higher educational level". It is not limited to bachelor's and above, so an F-1 associate's or certificate student gets 12 months of OPT, just not the STEM extension.
  - "Students in English language training programs are ineligible for practical training."
- **M-1 students (vocational):** practical training only after completion, under (m)(14). No OPT or STEM extension.

The Study in the States CIP-list page (https://studyinthestates.dhs.gov/stem-opt-hub/additional-resources/eligible-cip-codes-for-the-stem-opt-extension) talks about fields only, not degree levels. The regulation is the citable source for the level rule.

Not asked, but relevant to doctorates and families. In this eCFR snapshot, (f)(5)(i) admits an F-1 student "for a fixed period of time … not to exceed a period of 4 years". Longer programs need an extension of stay under (f)(7). (f)(7)(iv) says F-2 dependents must be included in, or file, that extension. This replaces duration of status. It affects 5–7-year PhDs and should go to `migration_rules`. We did not check the effective date or the Federal Register history of this change.

## 7. English language (ESL / intensive English) programs

**IPEDS.**
- CIP 32.0108 (Developmental/Remedial English) and 32.0109 (Second Language Learning, example "English as a Second Language") are defined in CIP 2020 as "**not valid for IPEDS reporting**". C2024_A has **0 rows** in 32.xx.
- The ESL code that is reportable is **16.1701 English as a Second Language**, new in CIP 2020. Its definition covers ESL "for academic credit towards a postsecondary credential"; non-credit ESL goes to 32.0109.
- C2024_A has only **22 programs nationally** under 16.1701 (levels 2, 20, 21, 4, 6, 7), with 230 completions and 81 nonresident. **TX has 2, both with 0 completions.**
- Stand-alone language schools are mostly not in IPEDS at all: they are not Title IV. In HD2024, a name search for English/language/ESL/intensive finds exactly one: "M-DCPS The English Center" (FL).
- **IPEDS cannot list intensive English programs.**

**SEVP Certified School List (the S-4 parse).**
- It has an F flag and an M flag per campus. National split: Y/N 11,880, Y/Y 1,365, N/Y 562.
- There is **no school-type or "language training" column**. 8 CFR 214.3 shows that SEVIS holds this on Form I-17 ("If the school is engaged in English language training", 214.3(h)(3)(i)(P)), but the public PDF does not.
- A name-keyword heuristic (english, language, ESL, ELS, intensive, linguistic, TOEFL) finds:
  - 273 campuses / 176 school codes nationally;
  - **11 TX campuses**, all F-1 only (Y/N), in `out/sevp_tx_language_name_hits.csv`. They include Austin ESL School, ELS Language Center/Houston, Excel English Institute (2), Shepherd School of Language (2), The Language Company-Dallas/Fort Worth, UTRGV Language Institute (Brownsville, Edinburg) and the U. of Houston Language & Culture Center.
- The heuristic misses university intensive English programs whose campus row doesn't carry such a name, and it can produce false positives. It is a lead list, not a classification.

**Visa rules (8 CFR 214.2 / 214.3).**
- Language training is F, not M.
  - 214.3(a)(2)(i)(G): F-1 schools include "An institution which provides language training".
  - 214.3(a)(2)(ii)(C): M-1 covers vocational training "other than language training".
  - Paragraph (m) is titled "… other than in language training programs".
  - The exception is 214.3(a)(2)(iv): English taken only to follow a vocational course at the same school is M-1.
- **F-2 dependents can come.** (f)(3): "The spouse and minor children accompanying an F-1 student are eligible for admission in F-2 status if the student is admitted in F-1 status." Each needs their own I-20. No exception is made for language students.
- Limits specific to ESL:
  - (f)(5)(i)(A) caps admission at **24 months** plus 30 days.
  - (f)(10) gives **no practical training** (no CPT, no OPT).
  - F-2 may not work, (f)(15)(i).
- Accreditation of English language training programs is required by statute, the Accreditation of English Language Training Programs Act (2010). We did not trace where it sits in the CFR in this spike.

## 8. What is feasible from official data alone

| Level | Program list | Size and nonres. signal | Tuition reference | Earnings | STEM OPT | SEVP/F-1 |
|---|---|---|---|---|---|---|
| Master's, research doctorate, grad certificates | IPEDS | yes | `TUITION7` (inst.-wide) | Scorecard, mostly PS beyond master's | master's and doctorate yes (CIP list); certificates **no** | campus-level |
| Professional doctorate | IPEDS | yes | `OSPROFn` for 9 fields, else `TUITION7` | Scorecard CREDLEV 7, 32–45% value | yes if CIP on list (rare: 50 of 2,298 US level-18 programs; no law code is on the list) | campus-level |
| Bachelor's | IPEDS | yes (2–9% nonres.) | `TUITION3`/`CHG3AY3` | best coverage (36–44%) | yes | campus-level |
| Associate's, sub-bacc. certificates | IPEDS | yes (≤ 4% nonres.) | `TUITION3`, or IC_PY (not checked) | 10–25% value | **no**; 12-month OPT only (F-1) | campus-level; F vs M per campus, not per program |
| ESL / intensive English | **none** (IPEDS excludes it) | – | – | – | no OPT at all | SEVP campus list + name heuristic, manual |

Program-level F vs M is not in any public file. A campus flagged Y/Y can issue either, and which one applies to a given vocational certificate is decided by the school (214.3(a)(2)(iii)). M-1 has very different family and work rules: M-2, no OPT, (m)(14).

## Open questions (for the author)

1. **Which levels first.**
   - (a) Add research doctorates and grad certificates: same tuition field, high nonresident share.
   - (b) Also bachelor's.
   - (c) Everything at once.

   Recommendation: (a) then (b). They reuse `TUITION7`, the STEM rule and the SEVP logic, and that is where international graduates are. Associate's and sub-bacc certificates are ≤ 4% nonresident and bring the M-1 question.
2. **Which fields.**
   - (a) Keep tech.
   - (b) Expand to the full DHS STEM list.
   - (c) All CIPs.

   Recommendation: (b). It keeps a clear family-relevant reason (12 + 24 months of work). Programs whose CIP6 is on the 2024 list: 65,499 of 267,595 nationally (24%), 3,780 of 14,828 in TX. Show non-STEM rows as "official data only, not curated" only if (c) is chosen.
3. **ESL source.**
   - (a) Skip ESL.
   - (b) A curated list seeded from the SEVP name heuristic and verified on each school site.
   - (c) Ask SEVP or ICE whether the I-17 "English language training" flag is published anywhere.

   Recommendation: (c) as a question, plus (b) for TX only. Present ESL as its own entity, not a "program level". It has no CIP, no OPT, and a 24-month cap.
4. **The level model.**
   - (a) Store IPEDS AWLEVEL as is.
   - (b) Map it to a generic degree level (ISCED) with the IPEDS code as a classification.

   Recommendation: (b), consistent with C-09. This needs a decision record.
5. **Fixed 4-year F-1 admission (f)(5)(i).** Confirm it is in force and model it in `migration_rules` before showing doctorates.
