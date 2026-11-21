# Score formula: proposal

> **Proposal for the author's review. Not a decision.** Every band below is a first guess. The bands will be calibrated with the pilot data (Phase 4) before they go into `domain/`. Each criterion uses only fields that exist in `schema/program.schema.json` (v0), plus the profile (FR-20) and the cost estimate (`CostEstimate`, BR-07).
>
> **Naming:** status values (`confirmed_official`, `reported_by_program`, `extracted_unverified`, `unknown`, `confirmed_negative`), risk levels (`low`/`medium`/`high`) and requirement IDs (FR, NFR, BR, C) follow SRS 1.3 (`docs/requirements.md`) and decision record 0002 (`docs/decisions/0002-after-data-spikes.md`), which wins where they differ.
>
> **Decided since the first draft (record 0002, 2026-11-21):** the neutral value for unknowns is a fixed 50, and every evaluation shows `score`, `score_range` and `certainty` (**R16**); the main cost total subtracts guaranteed funding only, with `period_total_with_competitive_funding` beside it (**R15**); 52.12xx programs score on the 12-month OPT only (**R1**). The bands themselves are still a proposal. In this file, "A1"–"A16" always mean the items of record 0002.

## 1. Overview

- Score = Σ (criterion weight × criterion score) / 100. The default weights come from BR-05: post_study_work 20, cost 20, funding 15, admissibility 15, career_roi 15, family 10, quality 5. The weights are configurable and must add up to 100.
- Each criterion is scored from 0 to 100 and is built from **sub-items** with internal weights that add up to 100%. Each sub-item reads one schema field (or one number derived from the schema) and turns it into 0–100 with a small table.
- The score is always shown with a **range** and a **certainty** figure (section 2). For example: `76 · range 75–76 · certainty 99%`.
- The immigration risk (section 4) is separate and is never averaged in (BR-06).
- The filter (BR-04) and the score are separate. A program that fails the filter still gets a score, but it is not ranked among the approved programs.

## 2. Unknown data (BR-02)

### Rule

Each sub-item falls into one of three cases, depending on the status of the field it reads:

| Field status | Point score | Range | Counts toward certainty? |
|---|---|---|---|
| `confirmed_official`, `reported_by_program`, `confirmed_negative` | value from the table | the same value | yes |
| `extracted_unverified` | value from the table (using the extracted value) | 0 to 100 | no |
| `unknown` | **50 (neutral)** | 0 to 100 | no |

- **Point score** = the sum with unknowns at 50. This is the number used for sorting.
- **Range** = the same sum with every uncertain sub-item at 0 (minimum) and at 100 (maximum). It answers the question "how far could this score move once we know the missing data?"
- **Certainty** = the share of total weight (criterion weight × sub-item weight) whose data is known. Labels: high ≥ 80%, medium 50–79%, low < 50%.
- In the UI, a sub-item with an unknown value shows "?" instead of a number (NFR-05).

### Why this rule

- **50 is neither good nor bad.** A known good value scores up to 100 and a known bad value scores close to 0. An unknown scores 50, and its range is visible.
- **The score is the midpoint of what is possible.** When every uncertain item is `unknown`, the point score is exactly the middle of the range. This is easy to explain: "we don't know, so we put it halfway, and we show you how far it could go."
- **The score does not move when other programs change.** Filling unknowns with the average of known programs (imputation) would make a program's score depend on the rest of the database. That is harder to explain and to test.
- **Rejected alternatives:**
  - *0 for unknowns:* this treats unknown as negative, which contradicts BR-02 and penalizes programs that are only badly documented.
  - *Dropping the criterion and reweighting the rest:* this hides the gap and rewards opacity. A program that publishes only its good data would score as if everything else were also good.
  - *A fixed penalty (e.g. 40 instead of 50):* this is defensible ("programs that hide information tend to be worse"), but it mixes an opinion with the data.
- **Decided (R16, record 0002):** the neutral value is a **fixed 50**, not configurable. `Evaluation` carries `score`, `score_range` (min–max) and `certainty` (0–100%), plus the per-criterion breakdown (A9).
- `extracted_unverified` uses the extracted value for the point score but stays outside the certainty figure. This is consistent with the filter, which treats it as undetermined (UML §4).
- A sorting option "by worst case" (sort by the minimum of the range) suits cautious users.

## 3. Criteria

Notation: `field` = path in the schema. "Unknown" means the rule in section 2 applies.

### 3.1 Post-study work (`post_study_work`, 20)

Field: `eligibilities[rule_key = us.stem_opt].result`. Rule: **months of post-study work ÷ 36 × 100**, capped at 100. The 36-month reference and the month count come from the country module. In the US, STEM = 12 months of OPT + 24 months of STEM extension = 36 months, and non-STEM = 12 months.

| Situation | Score |
|---|---|
| STEM `confirmed_official` (true) | 100 |
| CIP confirmed as not on the list (`confirmed_negative`; by R12 a confirmed "no" is never `confirmed_official` + false) | 33 |
| Primary CIP 52.12xx (flag `no_stem_opt_extension`, BR-17): no 52.12xx code is on the DHS list, so the program gets the 12-month OPT only (**R1**) | 33 (known; counts toward certainty) |
| STEM only `reported_by_program` (the program says so, but the CIP does not confirm it, BR-03) | 67, range 33–100, does not count toward certainty |
| `unknown` | 50, range 0–100 |

A single sub-item. For 52.12xx the score comes from the CIP, not from what the program advertises: a 52.12xx program that claims STEM still scores 33, and the claim raises `claim_mismatch` (A8) and the immigration risk (§4). `in_strategy = false` (derived from modality and F-1 compatibility, A11) or a modality that does not allow F-1 takes the program out of the ranking before the score is computed (BR-14, filter).

### 3.2 Cost (`cost`, 20)

Input: `CostEstimate.period_total_net` (the 4th number in BR-07), converted to the profile currency. It is calculated from `cost.*`, `academic.duration_months`, `family.family_housing_rent` / the HUD FMR of the campus locality (`rent_benchmarks`, bedrooms = ceil((1 + dependents) / 2), max 4, **R6**) and `family.dependent_insurance_cost`. **It only subtracts funding that is guaranteed** (`availability = guaranteed`). Otherwise the cost and funding criteria would count the same assistantship twice. **Decided (R15):** `CostEstimate` also shows `period_total_with_competitive_funding` beside it, for information; the score uses `period_total_net` only. The ratio `r = period_total_net ÷ profile budget`:

| r | Score |
|---|---|
| ≤ 0.50 | 100 |
| ≤ 0.70 | 80 |
| ≤ 0.85 | 60 |
| ≤ 1.00 | 40 |
| ≤ 1.15 | 15 |
| > 1.15 | 0 |

- r > 1 already fails the filter (BR-04). The score is shown for comparison only.
- Profile without a budget: use the annual total in USD instead: ≤ 40k → 100; ≤ 55k → 80; ≤ 70k → 60; ≤ 85k → 40; ≤ 100k → 20; > 100k → 0.
- If any part of the total is unknown, the criterion is unknown (50, range 0–100). Possible improvement: compute a partial minimum with the parts that are known.

### 3.3 Funding (`funding`, 15)

1. If `funding.available_to_masters` is false (`confirmed_negative`), the score is **0** (known).
2. Otherwise, score each item in `funding.opportunities`:

   | Sub-item | Value |
   |---|---|
   | `tuition_coverage` | full 50 · partial 25 · none 0 |
   | `stipend` | any amount > 0: 25 · none 0 |
   | `availability` | guaranteed 25 · competitive 15 · rare 5 |

   That gives a base from 0 to 100. Then multiply by the two gates, `open_to_masters` and `open_to_international`: true ×1 · unknown ×0.5 (range ×0 to ×1) · false ×0. Unknown sub-items use half of their maximum (25, 12.5, 12.5).
3. Criterion score = the best opportunity's score (highest point score).
4. No opportunities listed and `available_to_masters` true: one opportunity with every field unknown (50, range 0–100). No opportunities and `available_to_masters` unknown: criterion unknown (50, range 0–100).

### 3.4 Admissibility (`admissibility`, 15)

| Sub-item (weight) | Rule |
|---|---|
| English (50%) | **Profile has a score** in a test the program accepts: score ≥ minimum → 100; below the minimum with `conditional_admission` true → 60; below the minimum otherwise → 0. **Profile without a score**: use how hard the minimum is: TOEFL `admissions.english.toefl_ibt_min` ≤ 79 → 100; 80–89 → 80; 90–99 → 55; ≥ 100 → 30 (if TOEFL is unknown, IELTS `ielts_academic_min` ≤ 6.0 → 100; 6.5 → 80; 7.0 → 55; ≥ 7.5 → 30); if `conditional_admission` is true, the score is at least 70. Every minimum unknown → unknown |
| Other field accepted (35%) | `admissions.accepts_other_undergrad_area`: true 100 · false 0 |
| GRE (15%) | `admissions.gre`: not_required / optional 100 · waivable 80 · required 40 |

### 3.5 Career and ROI (`career_roi`, 15)

| Sub-item (weight) | Rule |
|---|---|
| Earnings (60%) | `career.median_earnings.value.amount` (annual, in USD): ≥ 110k → 100; 90–110k → 80; 70–90k → 60; 50–70k → 35; < 50k → 15 |
| Payback (40%) | tuition + fees for the whole program (the 1st number in BR-07, without living costs, which the family would pay anyway) ÷ median earnings: ≤ 0.25 → 100; ≤ 0.50 → 80; ≤ 0.75 → 60; ≤ 1.00 → 40; ≤ 1.50 → 20; > 1.50 → 0 |

- Earnings unknown → both sub-items are unknown.
- The BR-13 caveat (Scorecard covers graduates with federal aid, not international students) is always shown. It does not change the score.
- Scorecard suppresses earnings (`PS`) in about 70% of master's rows (all 30.70 rows in Texas). A suppressed value is `unknown` (50, range 0–100), so this criterion will often be uncertain.
- `career.placement_rate_pct` is shown but **does not** enter the score. It is self-reported by the program, with no standard window, and is not comparable across programs. Reconsider after the pilot.
- The bands are in USD. Bands live in the country module, weights stay global (A13); another country brings its own bands.

### 3.6 Family (`family`, 10)

What matters to a family *besides* money. Costs (family housing, dependent insurance) are already counted in the cost criterion, so they are not counted again here.

| Sub-item (weight) | Field | true / false |
|---|---|---|
| Family housing on campus (40%) | `family.family_housing_on_campus` | 100 / 0 |
| School health plan covers dependents (30%) | `family.dependent_insurance_available` | 100 / 0 |
| Childcare on campus (20%) | `family.childcare_on_campus` | 100 / 0 |
| Support for spouses (10%) | `family.spouse_support_programs` | 100 / 0 |

### 3.7 Quality (`quality`, 5)

Low weight on purpose. Rankings are not used (C-05). Institutional accreditation is part of the filter, not the score.

| Sub-item (weight) | Rule |
|---|---|
| Research classification (60%) | `institution.carnegie_classification` (institution level: `institutions.carnegie_classification`, A12): R1 → 100 · R2 → 75 · any other known value → 40 |
| Specialized accreditation (40%) | `academic.specialized_accreditation`: non-empty list → 100 · empty list (known) → 40 |

## 4. Immigration risk (BR-06, separate)

The risk is never averaged into the score. It is shown next to the score, with its reasons. The rules come from the country module. Record 0002 adopts this section as the source of the criteria (A10), **pending author review**. The `us` module:

| Level | Any of these conditions |
|---|---|
| **high** | SEVP (`campus.intl_authorization`) or `immigration.i20_issued_for_program` false; `modality` = online, or `immigration.f1_compatible_modality` false; `immigration.cpt_from_first_term` true (Day-1 CPT), **even if only extracted**; the program claims STEM (`stem_opt_claimed_by_program` true) but the CIP is confirmed as not on the list (`claim_mismatch`, A8); institutional accreditation by a recognized accreditor (R10) `confirmed_negative` |
| **medium** | none of the above, but SEVP, I-20 or `us.stem_opt` is not `confirmed_official`; `modality` = hybrid; `f1_compatible_modality` unknown |
| **low** | none of the above |

- Signs of risk count even when they are only `extracted_unverified` (better a false alarm than missing one), and they are labeled "to verify".
- **Finalist eligible** (BR-06): SEVP, I-20 and `us.stem_opt` all `confirmed_official` **with the value true** (A5). The I-20 is `confirmed_official` when the international office (DSO) confirms it, by official page or written reply; the department page alone is `reported_by_program` (R11). SEVP is checked on the campus/institution, the I-20 on the program.

## 5. Worked examples (fictitious)

> **All three programs are fictitious.** Names and numbers are made up to show the calculation. They are not real programs.

Shared profile: budget USD 150,000 for the whole program; **no English score yet**; 4 dependents; spouse cannot work (F-2); undergraduate degree in another field.

### Example A: "Example State University, MS Data Science" (well documented)

Data: STEM `confirmed_official`. `period_total_net` = 42,000 (tuition + fees: 36 credits × 1,000 + 4 terms × 1,500) + 6,000 (student insurance) + 18,000 (dependent insurance, 2 × 9,000) + 27,300 (family housing, 21 × 1,300) + 42,000 (other expenses for a family of six, 21 × 2,000, a cost-model parameter) − 0 (the TA is competitive, not guaranteed) = **135,300**. TA: full tuition, stipend 1,800/month, competitive, open to master's and international students (all `reported_by_program`). TOEFL minimum 80, conditional admission unknown, other field accepted, GRE not required. Earnings 85,000 (Scorecard). Family housing yes, dependent plan yes, childcare **no** (`confirmed_negative`), spouse support unknown. R2, no specialized accreditation.

| Criterion | Calculation | Score | × weight |
|---|---|---|---|
| post_study_work | STEM confirmed | 100 | 20 × 100 = 2000 |
| cost | r = 135,300 / 150,000 = 0.90 → band ≤ 1.00 | 40 | 20 × 40 = 800 |
| funding | TA: 50 + 25 + 15 = 90; gates 1 × 1 | 90 | 15 × 90 = 1350 |
| admissibility | 0.5 × 80 (TOEFL 80, no score) + 0.35 × 100 + 0.15 × 100 | 90 | 15 × 90 = 1350 |
| career_roi | 0.6 × 60 (85k) + 0.4 × 80 (42,000 / 85,000 = 0.49) | 68 | 15 × 68 = 1020 |
| family | 0.4 × 100 + 0.3 × 100 + 0.2 × 0 + 0.1 × **50** (?) | 75 (70–80) | 10 × 75 = 750 |
| quality | 0.6 × 75 + 0.4 × 40 | 61 | 5 × 61 = 305 |
| **Total** | 7575 / 100 | **75.8** | |

Range: only spouse support is unknown (weight 10 × 10% = 1 point of weight): 75.3–76.3. Certainty: 99%. Risk: **medium**, because the I-20 for the program is only `reported_by_program` (the department page). Not finalist eligible until the international office confirms the I-20 (R11).

### Example B: "Example Tech Institute, MS Computer Science" (good on paper, outside the profile)

Data: STEM confirmed. `period_total_net` = **210,000**. `funding.available_to_masters` = `confirmed_negative`. TOEFL minimum 100, conditional admission `confirmed_negative`, does **not** accept another field (`confirmed_negative`), GRE required. Earnings 120,000; tuition + fees 90,000. Family housing no, dependent plan yes, childcare yes, spouse support yes. R1, with ABET.

| Criterion | Calculation | Score | × weight |
|---|---|---|---|
| post_study_work | STEM confirmed | 100 | 2000 |
| cost | r = 1.40 → > 1.15 | 0 | 0 |
| funding | no funding for master's (known) | 0 | 0 |
| admissibility | 0.5 × 30 (TOEFL 100) + 0.35 × 0 + 0.15 × 40 | 21 | 315 |
| career_roi | 0.6 × 100 (120k) + 0.4 × 60 (90 / 120 = 0.75) | 84 | 1260 |
| family | 0 + 30 + 20 + 10 | 60 | 600 |
| quality | 0.6 × 100 + 0.4 × 100 | 100 | 500 |
| **Total** | 4675 / 100 | **46.8** | |

Certainty: 100%. Filter: **fail** (cost above budget; does not accept another field; English without a score and without conditional admission). Risk: **low**, assuming the international office lists the program as I-20 eligible, which counts as `confirmed_official` (R11). This shows that score and filter are independent: the program is good on paper, but it is out of reach for this profile.

### Example C: "Example Valley University, MS Information Systems" (poorly documented)

Data: CIP unknown; the program says it is STEM (`reported_by_program`). Living cost unknown, so `period_total_net` is unknown. Funding unknown. TOEFL minimum 79 **extracted** by the LLM (`extracted_unverified`). Other field unknown. GRE not required (`reported_by_program`). Earnings unknown. Dependent plan yes; the other family fields unknown. Research classification known (neither R1 nor R2); specialized accreditation unknown. The page mentions **CPT from the first term** (`extracted_unverified`).

| Criterion | Calculation | Point | Min–max | × weight (point) |
|---|---|---|---|---|
| post_study_work | STEM reported_by_program | 67 | 33–100 | 1340 |
| cost | total unknown | 50 | 0–100 | 1000 |
| funding | unknown | 50 | 0–100 | 750 |
| admissibility | 0.5 × 100 (79, extracted) + 0.35 × 50 (?) + 0.15 × 100 | 82.5 | 15–100 | 1237.5 |
| career_roi | unknown | 50 | 0–100 | 750 |
| family | 0.4 × 50 (?) + 0.3 × 100 + 0.2 × 50 (?) + 0.1 × 50 (?) | 65 | 30–100 | 650 |
| quality | 0.6 × 40 + 0.4 × 50 (?) | 44 | 24–64 | 220 |
| **Total** | 5947.5 / 100 | **59.5** | **13.1–98.2** | |

Minimum: (20 × 33 + 0 + 0 + 15 × 15 + 0 + 10 × 30 + 5 × 24) / 100 = 1305 / 100 = 13.1. Maximum: (2000 + 2000 + 1500 + 1500 + 1500 + 1000 + 5 × 64) / 100 = 9820 / 100 = 98.2. Certainty: GRE (15 × 15% = 2.25) + dependent plan (10 × 30% = 3) + research classification (5 × 60% = 3) = **8%** (low). Filter: **undetermined**. Risk: **high** (Day-1 CPT, to verify), plus medium-level reasons (I-20 unknown, STEM not confirmed).

How the list would look: A 75.8 (certainty 99%) · C 59.5 (range 13–98, certainty 8%) · B 46.8 (fails the filter). C sits in the middle of the list, but its low certainty and wide range warn the user not to treat it as good or bad until the curator fills in the data.

## 6. Gaps found in the model

Contradictions and gaps found in the SRS (v1.1), the UML (v0.2) and the execution plan while writing the schema and this proposal. None of those files was changed at the time.

**Status after record 0002 (2026-11-21):** each gap below is marked **Resolved** with the decision that closed it (R* or A* from `docs/decisions/0002-after-data-spikes.md`), **Partly resolved**, or **Still open**. The text of each gap is kept as it was found.

1. **Envelope field names.** NFR-01 uses `last_verified_at` and `verification_status`; the UML (`VerifiedValue`) uses `verified_at` and `status`. The schema follows the UML. — **Resolved (A1).** NFR-01 now uses the UML names.
2. **Field path.** FR-13 uses `english_proficiency.toefl_ibt_min`; the UML (FieldChange, ER index) uses `admissions.english.toefl_ibt_min`. The schema follows the UML. — **Resolved (A2).** FR-13 now uses `admissions.english.*`.
3. **"Only `confirmed_negative` fails the filter" (BR-02) vs FR-18.** In FR-18 and in the UML activity diagram, a program fails on English when the profile score is below a minimum whose status is `reported_by_program`, not `confirmed_negative`. Suggested wording: "only `confirmed_negative` fails *by itself*; comparing a known value against the profile can also fail." — **Resolved (A3).** BR-02 uses the suggested wording.
4. **The status mixes origin and polarity.** `confirmed_negative` does not say whether the "no" came from an official source or from the program. For booleans there are also two ways to record a confirmed "no" (`confirmed_official` + false, or `confirmed_negative`). For numeric fields, "negative" has no clear meaning (the schema uses it for "test not accepted"). Suggestion: for booleans, a confirmed false is always `confirmed_negative`; or split the status into `source_level` + `polarity`. — **Resolved (R12).** The 5 statuses stay; a confirmed "no" on a yes/no field is always `confirmed_negative`; numeric and text fields never use it; "test not accepted" is a yes/no field.
5. **Source for `confirmed_negative` and extractions.** NFR-01 requires a source for 100% of displayed values, but the requested rule only covered `confirmed_official`/`reported_by_program`. The schema also requires `source_url` + `verified_at` for `confirmed_negative` (it fails the filter, so it cannot be unsourced) and `source_url` + `evidence` for `extracted_unverified` (FR-13). The author should confirm this. — **Resolved (A4).** Confirmed as written here.
6. **The I-20 for a program has no "official" source.** BR-06 requires I-20 = `confirmed_official` for a finalist, but the only source is the school itself. As written, almost no program could become a finalist. Proposal: the international office (DSO) counts as the official source for the I-20, and the department page counts as `reported_by_program`. Related: BR-04 says "SEVP + I-20 *for the program*", but in the UML SEVP lives on the institution (`Institution.intl_authorization`). — **Resolved (R11).** The DSO counts as `confirmed_official` for the I-20; SEVP lives on the campus/institution, the I-20 on the program (BR-04).
7. **"STEM confirmed_official" in BR-06 is ambiguous.** A CIP that is confirmed *not* to be on the list is also confirmed. The schema and this proposal read the rule as "confirmed **and true**". — **Resolved (A5).** "Confirmed" means confirmed **and** eligible.
8. **Correspondence as a source.** Replies from the international office arrive by email, but `source_url` only accepts URLs, and the repo is public (no names or emails can be published). The pilot uses the office's official page + a quote in `evidence`. It may be worth adding a `source_kind` field (page, official_list, correspondence). — **Resolved (R13).** `source_kind` ∈ {`page`, `official_list`, `correspondence`, `uploaded_file`}; correspondence is stored privately (BR-15).
9. **Funding as a list (UML/ER) cannot tell "no funding" from "unknown".** That breaks BR-02. The schema uses an object: `available_to_masters` (VerifiedValue) + `opportunities`. The UML/ER need updating (`funding: list` → object). — **Resolved (A6).** `funding` is an object in the UML too.
10. **The 4th cost number (BR-07) cannot be stored on the program.** It depends on the profile (dependents) and on which funding is subtracted. BR-07 does not say whether to subtract *guaranteed* or *possible* funding. This proposal uses guaranteed only. FR-21 also lacks a rule for mapping dependents to bedrooms (4 dependents → 3 bedrooms is an example, not a rule) and a parameter for non-housing family expenses (food, transport). Neither exists in the schema or in the domain. — **Partly resolved (R15, R6).** Guaranteed funding only, with `period_total_with_competitive_funding` beside it (R15); bedrooms = ceil((1 + dependents) / 2), max 4 (R6). **Still open:** the parameter for non-housing family expenses (food, transport).
11. **HUD needs a county; the model has no locality.** `Institution` only has `city`, and the program only has `campus`. The schema adds `campus_location` (city + `locality_scheme`/`locality_code`, e.g. county FIPS). The HUD rent is per county but is repeated on each program; a `localities` table might be better. — **Resolved (R17, R6).** New `localities`, `campuses` and `rent_benchmarks` tables; rent stored once per locality.
12. **CIP without verification.** BR-11 requires a "verified CIP", but `program_classifications` has no status or source. In the schema, the code is a VerifiedValue. — **Resolved (A7).** The primary classification is a VerifiedValue (`program_classifications.verified`).
13. **`ProgramEligibility` has no source, version or flag.** It has `status` but no `source_url` (needed in the manual pilot), and it has no field for the BR-03 "flag" (the program claims STEM but the CIP does not match). The schema has `eligibilities[].rule_version`, `result` (VerifiedValue) and `immigration.stem_opt_claimed_by_program`. — **Resolved (A8).** `program_eligibilities` gets `result`, `rule_version` and `claim_mismatch`.
14. **Incomplete profile.** `Profile.english: EnglishScore` is not defined (which test? overall and section scores?). There is no GPA, no GRE and no "planned score". The budget has no period (total or annual?). Also, by UML §4, a profile without a score **fails English** in every program without conditional admission. That is too harsh for the persona (who has no score yet); UC04 1a only covers programs with conditional admission. Suggestion: allow a "target score". — **Partly resolved (R14).** The profile accepts `english.target`, which passes with `pass_with_caveat`; SRS 1.3 FR-20 gives the budget a currency and a period. **Still open:** GPA and GRE in the profile.
15. **`Evaluation` has no breakdown or uncertainty.** It has only `score: 0..100`. It needs `score_range`, `certainty` and the per-criterion breakdown (FR-19, NFR-05). — **Resolved (A9, R16).** `score_range`, `certainty` and the per-criterion breakdown.
16. **Risk without criteria.** `migration_risk: low/medium/high` exists in the UML, but BR-06 only defines the finalist gate. Section 4 above proposes the criteria. — **Partly resolved (A10).** The criteria in §4 are adopted. **Still open:** author review with pilot data.
17. **"Regional accreditation" (BR-04).** In US federal regulations, the distinction between regional and national accreditors was removed some years ago. The criterion should probably say "institutional accreditation by a recognized accreditor"; check this. `Institution.accreditation` is a `VerifiedValue<str>` with no scheme or accreditor type. — **Resolved (R10).** "Institutional accreditation by a recognized accreditor"; the value is `{accreditor, scheme: "us_ed_recognized", institutional: true}`.
18. **Overlap among `in_strategy`, `modality` and `f1_compatible_modality`.** These are three places for related information. `in_strategy` is a plain bool (not verifiable), but it determines exclusion from the ranking. Suggestion: derive `in_strategy` from the other two. — **Resolved (A11).** `in_strategy` is derived.
19. **Institution-level data with no column.** The Carnegie classification (used in quality) is institution-level, but the ER `institutions` table has no column for it. The schema keeps it in `academic.research_classification`. — **Resolved (A12).** `institutions.carnegie_classification` column.
20. **Bands per country.** `post_study_work` (36-month reference) and the USD earnings and cost bands depend on the country. The weights are global (BR-05), but the tables should live in the country module (C-09g). — **Resolved (A13).** Bands in the country module, weights global. **Still open:** calibrating the bands with pilot data.
21. **Plan and UML numbering.** The plan (Phase 2, S-3) mentions `stem_list_versions`, but the UML uses `eligibility_rules`. SRS D6 says the first deploy happens in "Phase 2", while the plan puts it in Phase 3 (the plan's summary table also says "on air since Phase 3"). UML §7 says the database and CronJob come in "Phase 4", but the plan puts the backend in Phase 5. The plan says it covers "SRS 1.0", but its front matter says v1.1. — **Resolved editorially (no R/A number).** Plan v4 uses `eligibility_rules` and cites SRS 1.3; the UML phase numbers are fixed in UML 1.0.
22. **Deadlines.** The SRS says "deadlines as a list" but does not say whether each deadline has its own source. The schema uses a single VerifiedValue for the whole list. If deadlines come from different pages (graduate school vs department), each item needs its own envelope. — **Resolved (R18).** Each deadline item is its own VerifiedValue (BR-16).
