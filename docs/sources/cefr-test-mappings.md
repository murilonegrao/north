# Source: official CEFR ↔ English test score tables

Input to the English placement test (`docs/design/english-placement-v0.md`, objective SO6 in `docs/elicitation/round-3-scope.md`). The test estimates a CEFR band; this file lists the tables **published by each test owner** that let North show the matching IELTS / TOEFL / other ranges.

Date of the spike (every "checked" date below): 2026-11-22.

## Summary

- **IELTS** (overall band only): C2 8.5–9, C1 7–8, B2 5.5–6.5, B1 4–5. Band 8 is borderline C1/C2, 6.5 borderline B2/C1, 5 borderline B1/B2. Nothing is published below band 4 or per skill.
- **TOEFL iBT changed scale on 2026-01-21.** Tests taken from that date are reported on a **1–6 band scale** in half bands, the same for each section and the total (the total is the average of the four sections rounded to the nearest half band). The CEFR mapping is the same number for every section: 1–1.5 A1, 2–2.5 A2, 3–3.5 B1, 4–4.5 B2, 5–5.5 C1, 6 C2. ETS publishes a concordance to the old 0–120 total and 0–30 sections. Until January 2028 score reports also carry the CEFR level and a "comparable" 0–120 total (midpoint of the range).
- **Cambridge English Scale** (B2 First, C1 Advanced): one scale for every skill and the overall score; B1 140–159, B2 160–179, C1 180–199, C2 200+, within the range each exam reports.
- **Duolingo, PTE Academic, LanguageCert Academic, Trinity ISE**: each owner publishes an overall CEFR table (below). Per-skill tables: only TOEFL and Cambridge publish them in the documents checked.
- **CEFR Companion Volume (2020)** is the reference for writing items per band. Its copyright notice requires written permission to reproduce; the general Council of Europe rule for its publications allows non-commercial extracts up to 500 words with attribution. coe.int blocked automated access during the spike, so the notice in the 2020 PDF itself was **not read directly** (see section 5).
- Every owner warns that score comparisons are approximate. ETS: tables "cannot predict the exact score each individual test taker would receive"; IELTS: no "strong claims about exact equivalence"; Pearson: "always an approximation". The UI must say "estimate, not an official score" and never present a single number.

## 1. IELTS ↔ CEFR

| CEFR | IELTS overall band | Notes from the owner |
|---|---|---|
| C2 | 8.5–9 | "Band scores of 8.5 and higher are recognised as C2. Band 8 is borderline." |
| C1 | 7–8 (6.5 borderline) | "a C1 minimum threshold would fall between the 6.5 and 7 bands"; for high confidence in C1 "set a requirement of 7, rather than 6.5" |
| B2 | 5.5–6.5 (5 borderline) | quick guide: "an IELTS score of 5.5–6.5 … is equivalent to CEFR level B2" |
| B1 | 4–5 | "it is not clear whether band 5 is B1 or B2" |
| A2 | not published | the diagram stops at band 4 |
| A1 | not published | |

Per skill (Listening, Reading, Writing, Speaking): **not published**. The owner says the figure "refers to overall band scores, not the individual band scores".

Sources:

| Document | URL | Published | Checked |
|---|---|---|---|
| IELTS, "IELTS and the CEFR" (text + diagram "CEFR to IELTS band score comparison chart"; caveats and borderline bands) | https://ielts.org/organisations/ielts-for-organisations/compare-ielts/ielts-and-the-cefr | no date on page | 2026-11-22 |
| IELTS, "Your guide to understanding and using IELTS scores", p. 12 diagram "CEFR levels and IELTS overall band scores" | https://ielts.org/cdn/ielts-downloadable-assets/ielts-guidance-and-support/ielts-guides/ielts-scores-guide.pdf | PDF modified 2026-09-08 | 2026-11-22 |
| IELTS, "Everything you need to know about IELTS and the CEFR" (quick guide 5.5–6.5 = B2, 7–8 = C1) | https://ielts.org/news-and-insights/everything-you-need-to-know-about-ielts-and-the-cefr | 2023-11-17 | 2026-11-22 |

The diagram is an image. The ranges above are read from it and agree with the text statements on the same pages.

## 2. TOEFL iBT ↔ CEFR

### 2a. Tests taken on or after 2026-01-21 (1–6 scale)

| CEFR | Total (1–6) | Reading | Listening | Writing | Speaking |
|---|---|---|---|---|---|
| C2 | 6 | 6 | 6 | 6 | 6 |
| C1 | 5–5.5 | 5–5.5 | 5–5.5 | 5–5.5 | 5–5.5 |
| B2 | 4–4.5 | 4–4.5 | 4–4.5 | 4–4.5 | 4–4.5 |
| B1 | 3–3.5 | 3–3.5 | 3–3.5 | 3–3.5 | 3–3.5 |
| A2 | 2–2.5 | 2–2.5 | 2–2.5 | 2–2.5 | 2–2.5 |
| A1 | 1–1.5 | 1–1.5 | 1–1.5 | 1–1.5 | 1–1.5 |

Rules stated by ETS:

- Total = average of the four section scores, rounded to the nearest half band (5.125 → 5; 5.25 → 5.5).
- "From January 2026 to January 2028" each score report shows (1) the CEFR level, (2) the 1–6 overall and section scores, (3) a comparable 0–120 overall score, which is "the midpoint value of the equivalent range" (e.g. 4.5 → 90).
- How the CEFR mapping was made: vertical linking with the previous test for Reading and Listening; for Writing and Speaking, a content review against CEFR scales and an ETS-internal standard setting (performance profile method).

### 2b. ETS concordance between the 1–6 scale and the 0–120 scale

Published by ETS "to help you interpret scores from TOEFL exams taken before January 21, 2026".

| 1–6 (total and sections) | Reading 0–30 | Listening 0–30 | Writing 0–30 | Speaking 0–30 | Total 0–120 |
|---|---|---|---|---|---|
| 6 | 29–30 | 28–30 | 29–30 | 28–30 | 114+ |
| 5.5 | 27–28 | 26–27 | 27–28 | 27 | 107+ |
| 5 | 24–26 | 22–25 | 24–26 | 25–26 | 95+ |
| 4.5 | 22–23 | 20–21 | 21–23 | 23–24 | 86+ |
| 4 | 18–21 | 17–19 | 17–20 | 20–22 | 72+ |
| 3.5 | 12–17 | 13–16 | 15–16 | 18–19 | 58+ |
| 3 | 6–11 | 9–12 | 13–14 | 16–17 | 44+ |
| 2.5 | 4–5 | 6–8 | 11–12 | 13–15 | 34+ |
| 2 | 3 | 4–5 | 7–10 | 10–12 | 24+ |
| 1.5 | 2 | 2–3 | 3–6 | 5–9 | 12+ |
| 1 | 0–1 | 0–1 | 0–2 | 0–4 | 0+ |

ETS note: "Estimated total scores under the 0 – 120 scale are the sum of the section scores and can be obtained with different section score combinations." ETS's recommended new requirements for common old ones: 100 → 5, 90 → 4.5, 80 → 4, 70 → 3.5, and "the same requirement is also established for the section scores".

ETS also publishes a TOEFL (1–6) ↔ IELTS table on the same page, built from a TOEFL–IELTS concordance study and vertical linking. North does not need it if both are derived from CEFR, and should not chain the two tables (see "How North may use this").

### 2c. Tests taken before 2026-01-21 (0–120 scale, legacy)

ETS CEFR cut scores (minimum score for each level), revised in 2015:

| CEFR | Reading 0–30 | Listening 0–30 | Speaking 0–30 | Writing 0–30 | Total 0–120 |
|---|---|---|---|---|---|
| C2 | 25 | not published | not published | not published | 114–120 (2022 flyer) |
| C1 | 24 | 22 | 25 | 24 | 95 (95–113) |
| B2 | 18 | 17 | 20 | 17 | 72 (72–94) |
| B1 | 4 | 9 | 16 | 13 | 42 (42–71) |
| A2 | not published | not published | 10 | 7 | not published |
| A1 | not published | not published | 5 | not published | not published |

Note the difference between 2b and 2c at B1: the 2026 concordance puts band 3 (B1) at 44+ on the old total, the 2015 cut score is 42. They come from different studies; North uses 2a for new scores and does not mix them.

Sources:

| Document | URL | Published | Checked |
|---|---|---|---|
| ETS, "TOEFL® Score Scale Update: A Guide for Institutions" (page title "TOEFL iBT Score Scale 1 to 6: CEFR & IELTS Comparison"): tables 2a, 2b, TOEFL–IELTS, FAQ | https://www.ets.org/toefl/institutions/ibt/score-scale-update.html | no date on page | 2026-11-22 |
| ETS, Papageorgiou, Li, Gu & Barton, "A banded score scale for the TOEFL iBT test: Rationale, development, and score linking" | https://www.ets.org/content/dam/ets-org/pdfs/toefl/score-scale-update-2026.pdf (also on in.ets.org) | April 2026 | 2026-11-22 |
| ETS Research Memorandum RM-15-06, Papageorgiou et al., "The Association Between TOEFL iBT® Test Scores and the Common European Framework of Reference (CEFR) Levels", Table 1 | https://www.ets.org/Media/Research/pdf/RM-15-06.pdf | 2015 | 2026-11-22 |
| ETS flyer "Compare TOEFL® iBT Scores" (CEFR total ranges, legacy) | https://www.ets.org/content/dam/ets-org/de/pdfs/toeic/mapping-cefr-toefl-ibt-test.pdf | © 2022 (PDF 2022-03-18) | 2026-11-22 |

Note on the April 2026 PDF: every page footer says it "contains privileged and confidential information intended solely for the designated recipient(s)", although ETS links it publicly from the institutions page. Cite the web page for the numbers; do not quote the PDF.

## 3. Cambridge English Scale ↔ CEFR

The scale is the same for every skill (Reading, Writing, Listening, Speaking, Use of English) and for the overall score, which is the average of the skill scores. "scores are given on the same scale for each skill and for overall exam performance."

Levels on the scale: Pre-A1 80–99, A1 100–119, A2 120–139, B1 140–159, B2 160–179, C1 180–199, C2 200–230.

| Exam | Scale score | Grade | CEFR |
|---|---|---|---|
| B2 First | 180–190 | A | C1 |
| B2 First | 173–179 | B | B2 |
| B2 First | 160–172 | C | B2 |
| B2 First | 140–159 | Level B1 | B1 |
| B2 First | 122–139 | none (reported, no certificate) | — |
| C1 Advanced | 200–210 | A | C2 |
| C1 Advanced | 193–199 | B | C1 |
| C1 Advanced | 180–192 | C | C1 |
| C1 Advanced | 160–179 | Level B2 | B2 |
| C1 Advanced | 142–159 | none (reported, no certificate) | — |

Cambridge also publishes an IELTS ↔ scale table (IELTS 7.5 = 191, 7.0 = 185, 6.5 = 176, 6.0 = 169, 5.5 = 162, 5.0 = 154). Not needed by North.

Sources:

| Document | URL | Published | Checked |
|---|---|---|---|
| Cambridge English, "Results for Cambridge English Qualifications" | https://www.cambridgeenglish.org/exams-and-tests/qualifications/results/ | no date on page | 2026-11-22 |
| Cambridge English, "The Cambridge English Scale – information for institutions" | https://www.cambridgeenglish.org/exams-and-tests/cambridge-english-scale/institutions/ | no date on page | 2026-11-22 |
| Cambridge English, "The Cambridge English Scale explained" (diagram of levels and grades) | https://www.cambridgeenglish.org/images/210434-converting-practice-test-scores-to-cambridge-english-scale-scores.pdf | PDF 2023-11 / 2024-01 | 2026-11-22 |
| Cambridge English, "Comparing scores to IELTS – B2 First and C1 Advanced" | https://www.cambridgeenglish.org/images/461626-cambridge-english-qualifications-comparing-scores-to-ielts.pdf | PDF 2019, modified 2021-04 | 2026-11-22 |

## 4. Other tests

Overall score only unless stated. "Per skill" means a CEFR table for section scores.

### Duolingo English Test (DET), scale 10–160

| CEFR | DET |
|---|---|
| C2 | 155–160 |
| C1 | 130–150 |
| B2 | 100–125 |
| B1 | 60–95 |
| A1–A2 | 10–55 (not split) |

Per skill: not published in the guide checked. Duolingo's research page lists a 2025 technical report on aligning subscores to the CEFR; not reviewed here. ETS states it has "not conducted a score concordance study with the Duolingo English Test".

Source: Duolingo, "Scoring Guide for Teachers, 2026", section 2.4 "Score Comparison", https://englishtest-static.duolingo.com/media/resources/DET_Scoring%20Guide%20for%20Teachers%20(2026).pdf (PDF modified 2026-07-12; checked 2026-11-22). The same table also lists IELTS and TOEFL columns; those are Duolingo's claims about other owners' tests and North must not use them.

### PTE Academic, scale 10–90

| CEFR | PTE Academic |
|---|---|
| C2 | 85–90 |
| C1 | 76–84 |
| B2 | 59–75 |
| B1 | 43–58 |
| A2 | 30–42 |
| A1 or below | 10–29 |

Pearson adds that a score below a level's range predicts success on that level's easiest tasks (e.g. 51 → easiest B2 tasks) and that "This alignment is unchanged from the previous version of this Score Guide." Per skill: not published.

Source: Pearson, "PTE Academic Institution Score Guide", July 2025, Appendix, https://www.pearsonpte.com/content/dam/ELL/pte/pearsonpte/pdfs/Score-Guide-Institution-PTE-Academic-July-2025-web.pdf (checked 2026-11-22).

### LanguageCert Academic, LanguageCert Global Scale 0–100

| CEFR | LanguageCert Academic |
|---|---|
| C2 | 90–100 |
| C1 | 75–89 |
| B2 | 60–74 |
| B1 | 40–59 |
| A2 | 20–39 |
| A1 | 10–19 |
| below A1 | 0–9 |

Certificates only for 40–100 (B1–C2). The overall is the average of the four equally weighted skills. Per skill: not published in the guide checked.

Source: LanguageCert, "LANGUAGECERT Academic Summary Guide" (file dated 2026-06-19), https://www.languagecert.org/-/media/feature/documents/lc-redesign/languagecert-academic-summary-guide.ashx (checked 2026-11-22).

### Trinity ISE (Integrated Skills in English)

| CEFR | Level | ISE minimum scaled score (ISE Digital) |
|---|---|---|
| C2 | ISE IV | 130 (different format, "not covered" by the figure) |
| C1 | ISE III | 105 |
| B2 | ISE II | 80 |
| B1 | ISE I | 55 |
| A2 | ISE Foundation | 30 |
| A1 | ISE A1 | 5 |

ISE paper edition reports Pass/Fail per level, not a scaled score. Per skill: not published in the figure (it states "overall scores, not individual module scores").

Source: Trinity College London, "CEFR, ISE (paper edition), ISE Digital, TOEFL iBT and IELTS", https://www.trinitycollege.com/resource?id=7680 (PDF 2026-02-26; checked 2026-11-22). Level names: https://trinitycollege.com/qualifications/english-language/ISE/ISE-levels. The figure also shows TOEFL and IELTS columns copied from ETS and IELTS; use the owners' own tables instead.

## 5. CEFR descriptors for writing items

| Document | URL | Published | Checked |
|---|---|---|---|
| Council of Europe, *Common European Framework of Reference for Languages: Learning, teaching, assessment – Companion volume*, Council of Europe Publishing, Strasbourg | https://rm.coe.int/common-european-framework-of-reference-for-languages-learning-teaching/16809ea0d4 ; portal https://www.coe.int/lang-cefr | 2020 | 2026-11-22 (blocked, see below) |
| Council of Europe, CEFR descriptors page (descriptor collection) | https://www.coe.int/en/web/common-european-framework-reference-languages/cefr-descriptors | — | 2026-11-22 (blocked) |

- The Companion Volume replaces the 2001 descriptors and adds mediation and online interaction; the 2001 conceptual framework stays valid.
- Use for North: the scales for reading (e.g. "Overall reading comprehension", "Reading for information and argument"), listening ("Overall oral comprehension", "Understanding audio media and recordings"), and "Grammatical accuracy" / "Vocabulary range" to decide what an item at A2…C1 asks. ETS did the same for the TOEFL 1–6 descriptors ("selected from the CEFR with minor modifications").
- **Licence, not confirmed first-hand.** Search results show the 2020 volume's imprint saying no part may be reproduced "without prior permission in writing from the Directorate of Communication" (contact publishing@coe.int). Other Council of Europe publications, including *The CEFR Companion volume in practice* (2022), carry a general rule: "Reproduction of extracts (up to 500 words) is authorised, except for commercial purposes, as long as the integrity of the text is preserved, the excerpt is not used out of context, does not provide incomplete information or does not otherwise mislead the reader … The source text must always be acknowledged as follows '© Council of Europe, <year>'." coe.int and rm.coe.int returned Cloudflare challenge / HTTP 403 to scripts during the spike, so a human must open the PDF and read its imprint page before any descriptor is copied into the repo.

## 6. Owner guidance on equivalence claims

What the UI wording must respect:

- **ETS**: "score comparison tables are useful as general guiding tools, but they cannot predict the exact score each individual test taker would receive on two different language tests"; recommends choosing a TOEFL score "based on your desired CEFR level, rather than a direct comparison to DET"; the 2022 flyer adds "ETS does not endorse using the tables to calculate cut scores."
- **IELTS**: the CEFR "was not designed to provide the basis for precise equating"; the figure "should not be interpreted as reflecting strong claims about exact equivalence between assessment products"; concordance tables published by other providers "should be treated with caution", especially when a test does not cover writing and speaking in depth.
- **Pearson**: "score relationships between tests are always an approximation … can only provide estimates".
- **Cambridge**: its practice-test conversion tables "only apply when using official Cambridge English practice tests" and "may not always reflect the results the students may achieve". By the same logic no owner's conversion applies to a North quiz.
- **Trademarks**: IELTS, TOEFL, TOEFL iBT, PTE, Duolingo English Test, LanguageCert and Cambridge names are trademarks of their owners. Use the names in plain text to identify the tests; no logos, no wording that suggests endorsement.

## 7. Licence for reproducing the tables

What the documents say (facts, not legal advice):

| Owner | Notice seen |
|---|---|
| ETS | page © ETS; April 2026 PDF footer claims "privileged and confidential … Any unauthorized review, use, or disclosure is strictly prohibited"; 2022 flyer "All rights reserved" |
| IELTS | "©2026. IELTS is jointly owned by the British Council; IDP IELTS; and Cambridge University Press & Assessment"; trademarks "enforced by the IELTS Partners" |
| Cambridge | © UCLES on the PDFs |
| Pearson | "All rights reserved; no part of this publication may be reproduced without the prior written permission of Pearson Education Ltd." |
| Duolingo | "© Duolingo, Inc. All rights reserved." |
| LanguageCert, Trinity | copyright of the owner; no reuse licence found |
| Council of Europe | see section 5 |

None of the test owners grants an open licence. The numbers themselves (score X ↔ level Y) are short factual statements; the documents, diagrams, descriptor texts and layouts are protected. The prudent line for North, consistent with the facts-only rule used for the Irish lists (round-3 scope):

- Store **only the numeric boundaries** in the repo (one row per test, level, section, min, max), each with owner, document title, URL, publication date and check date. Write the table ourselves; do not copy images, PDFs or prose.
- Quote at most one short sentence from an owner's caveat, attributed, where the UI needs it.
- Link to the owner's page next to each range so the user reads the original.
- Do not commit the downloaded PDFs (they are in the spike scratchpad only).

## How North may use this

1. **Direction.** The quiz estimates a CEFR band. North then shows, for that band, the range each owner publishes for the same CEFR level. This is "the owner says level B2 corresponds to IELTS 5.5–6.5", not "your IELTS would be 5.5–6.5". Never chain two tables (CEFR → TOEFL → IELTS, or Duolingo's IELTS column).
2. **What to show per band** (from the tables above):

   | North band | IELTS overall | TOEFL iBT (from 2026-01-21) | Cambridge Scale | DET | PTE Academic |
   |---|---|---|---|---|---|
   | C1 | 7–8 (6.5 borderline) | 5–5.5 | 180–199 | 130–150 | 76–84 |
   | B2 | 5.5–6.5 (5 borderline) | 4–4.5 | 160–179 | 100–125 | 59–75 |
   | B1 | 4–5 | 3–3.5 | 140–159 | 60–95 | 43–58 |
   | A2 | not published | 2–2.5 | 120–139 | 10–55 (A1–A2) | 30–42 |

   A borderline band is shown as such ("6.5 may be B2 or C1"), not hidden.
3. **Sections.** Only TOEFL (1–6) and Cambridge publish per-section CEFR values. North measures Reading and Listening only, so it may show TOEFL Reading/Listening and Cambridge Reading/Listening per skill. For IELTS, PTE, DET, LanguageCert and ISE only the overall exists, and North's overall covers no Writing or Speaking: label it "Reading and Listening only; the official overall includes Writing and Speaking".
4. **TOEFL scale.** Show the 1–6 scale as primary. Show the legacy 0–120 value only as the ETS concordance range (e.g. B2 → 72–94), marked "scale used before 21 January 2026", until scores taken before that date expire (late 2027 / January 2028). The comparable 0–120 on new score reports is the range midpoint.
5. **Wording.** Always "estimate, not an official score", plus a line like "Test owners publish these CEFR tables for their own tests; they do not convert scores from other tests." Show ranges, never one number (BR-02 spirit: an estimate is not a confirmed value).
6. **Versioning.** Store the mapping as data with `owner`, `document`, `url`, `published`, `checked`; re-check every 6 months and whenever an owner announces a scale change (TOEFL 2026 is the precedent). A result stored in the browser records the mapping version it used.
7. **Impact outside the quiz (not edited here).** Program minimums are stored as `admissions.english.toefl_ibt_min` on the 0–120 scale (pilot guide, requirements FR acceptance criteria, score proposal thresholds 79/89/99). Programs are moving to 1–6 requirements from 2026, so the field needs a scale marker or a separate field; this needs a decision record.

## Needs a human decision

1. Which tests appear in the result (IELTS + TOEFL only, as in the spec, or also Cambridge, DET, PTE).
2. Whether to show per-skill ranges (TOEFL/Cambridge only) or only the overall.
3. How to label the overall when Writing and Speaking are not measured.
4. Legacy TOEFL 0–120 display and when to drop it.
5. Scale marker for `toefl_ibt_min` (decision record).
6. Read the Companion Volume imprint page by hand and decide whether descriptor text may be quoted in the repo, or only referenced by scale name and page.
