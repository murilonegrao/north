---
title: "Design — English placement test v0"
status: accepted (record 0008)
date: 2026-11-22
---

# English placement test v0 — spec

Scope of v0: small, original, retaken monthly.

## Goal

Give the user an **estimated CEFR band** and the matching ranges of seven English tests, so the North can (a) pick which ILEP courses fit (entry level) and (b) compare with the target score of the programs (eligibility, see `docs/elicitation/round-3-scope.md`). Always labelled **"estimate, not an official score"**.

## Out of scope (v0)

Speaking and writing (need human or LLM grading, later); adaptive testing; accounts (result stays in the browser, like the profile in FR-20); any claim of equivalence to an official exam.

## Test shape

| Section | Items | Format | Notes |
|---|---|---|---|
| Grammar | 20 | multiple choice, 4 options | 5 per band A2→C1 (+ C2 bonus later) |
| Vocabulary | 16 | multiple choice / gap fill | 4 per band; word frequency bands as the level guide |
| Reading | 3 texts × 4 items | multiple choice | B1, B2, C1 texts, written by us |
| Listening | 3 clips × 4 items | multiple choice | **TTS** (the clip is generated from our own script; voice + speed stored with the item). Normal speed for B2+: listening at native speed is the usual bottleneck |

~20–25 minutes. Item bank v0 ≈ 60–70 items; each item has `id`, `skill`, `band` (A2…C1), `prompt`, `options`, `answer`, `explanation`, `author`, `version`. Items are **original** (written by us, never copied from Cambridge/ETS materials, so the bank can be public under the repo license).

## Scoring

- Per skill: percentage correct per band; the skill band is the **highest band with ≥ 70% correct and all lower bands ≥ 70%**.
- Overall: the median of the four skill bands (with an even count, the lower of the two middle bands), shown with the per-skill bars (listening may sit below the others, and that is the useful signal).
- Output: `{band: "B2", skills: {...}, ielts_range, toefl_range, taken_at, bank_version}`.

## Equivalence

Map the CEFR band to IELTS and TOEFL ranges **only from the official tables** (IELTS/Cambridge CEFR mapping; ETS TOEFL iBT CEFR mapping). Pending: download and cite both tables, check whether ETS's TOEFL score scale change (reported for 2026) alters the mapping. Show a range, never a single number.

## Monthly retake

Stored in the browser (localStorage, with export as JSON). Retake shows the delta per skill. Later (step 5, public diary) the user can choose to publish their own series.

## Validation before shipping

- Calibrate the bank on a few people with a **real recent score** (IELTS/TOEFL/Cambridge) and check the band lands within ±1 half-band. The author is the first data point, after an official test.
- An item that ≥ 90% or ≤ 10% of takers get right moves band or leaves the bank.

## Decided (record 0008)

- Tests shown: IELTS Academic, TOEFL iBT, Cambridge English Scale, Duolingo, PTE Academic, LanguageCert Academic, Trinity ISE, from `data/reference/cefr_test_mappings.csv` (T17); label "Grammar, vocabulary, reading and listening. Writing and speaking were not tested." (T18); TOEFL 0–120 secondary until 2028-01-31 (T19).
- Q-N1: versioned YAML in `data/placement/items/`, validated by `schema/placement-item.schema.json` (T21).
- Q-N2: pre-generated audio files stored with the item, script available after answering (T22, NFR-19).
- Q-N3: linked now: language courses filter on `cefr_entry` ≤ overall band, and the chosen degree's minimum gives the target score (T23, FR-35).
- No CEFR descriptor is quoted until the Companion Volume licence is read by hand (T24).
