---
title: "Elicitation round 3 — English placement, Ireland and every degree level"
type: elicitation
status: answered (record 0008, SRS 2.0); validation of the baseline pending
level: M
created: 2026-11-22
---

# Elicitation round 3 — English placement, Ireland and every degree level

This file follows the author's requirements-engineering framework (phases 0–7 with exit gates). It frames the scope change before any code: the problem, the sources, the plan, what the sources say, and the closed questions only the sponsor can answer. When the questions are answered, a decision record (0008) is written and `requirements.md` moves to version 2.0.

## 1. Framing (phase 0)

**Request as it came** (translated from Portuguese), sponsor, 2026-11-22, chat:
> "Yes: placement test and Ireland. If possible, also include Irish universities, for all courses, and other kinds of course in the US, such as doctorate and undergraduate, whatever official sources have."

**Why / what for**

- Why is it needed? → The persona's route changed. Before a US master's, they need to raise their English (no official score yet, listening is the weak skill). The cheapest legal route that combines study and part-time work is an English course in Ireland on a Stamp 2 permission. The US master's stays as plan B, a few years later.
- What happens today without it? → The persona picks a language school from 832 Dublin courses on a government spreadsheet with no price, compares nothing with the target score the master's programs ask for, and has no idea of their own level except a guess.
- Who suffers? → International students who need English before a degree abroad, and especially those who want to bring their family, because the family rules differ by country and by type of course.

**Problem** (one sentence, no technology): someone planning to study abroad cannot see, with official sources, which English course and which degree they are eligible for now, which score they need to reach, and what that path costs their family.

**Measurable objectives** (new specific objectives, numbering continues the SRS):

- SO6: give a user an estimated CEFR band per skill in at most 25 minutes, and the matching IELTS/TOEFL range taken only from the test owners' official tables. Verified when the band of at least 5 people with a recent official score lands within one half-band of it.
- SO7: list every Stamp 2 eligible English course in Ireland from the official lists (ILEP and TrustEd Ireland), filterable by city, exam, entry/exit CEFR level and weekly hours, with the risk of losing eligibility when ILEP ends shown per course.
- SO8: extend program discovery to every degree level and field that official sources list, in the US and Ireland, without breaking BR-02 (unknown ≠ negative) and without asking the curator to verify what nobody will look at.
- SO9 (the bridge): for a chosen degree program, show the gap between the user's estimated band and the program's minimum English score as a **target score**, which then filters the English courses.

**Expected benefits:** one tool for the whole path (English → degree → work), instead of a degree search that starts after the hardest step; the dated "this list is being replaced" risk that no school will tell you; the same source-per-value guarantee across countries.

**Project context:** own product, new market need (the team reads the market) **and** normative imposition (immigration permissions, official eligibility lists). The normative part raises the rigor: interpretation of rules must cite the rule.

**Rigor level:** M (own product, MVP), with the F-level practice of citing every rule, because a regulator is involved (Irish immigration, DHS).

**Initial scope** (slices in proposed order; the sponsor confirms the order in the round-3 questionnaire):

| Slice | In | Out (this round) |
|---|---|---|
| E1 English placement v0 | grammar, vocabulary, reading, listening (TTS); band per skill; official score ranges; result in the browser; monthly retake | speaking and writing; adaptive testing; accounts; any claim of official equivalence |
| E2 Ireland English courses | ILEP + TrustEd English lists; city, exam, levels, hours, duration; price and start dates by assisted extraction; eligibility risk | schools outside the official lists; booking or payment |
| E3 Ireland higher education | every NFQ level and field on the official eligibility lists; permission, family and post-study rules of the Irish module | courses not open to non-EEA students |
| E4 US every degree level | associate's to doctoral, every CIP, from IPEDS; STEM OPT rule per level; ESL programs if an official source lists them | curation of every program (only the ones a user follows, see §5) |

**Known constraints**

| ID | Type | Constraint | Origin |
|---|---|---|---|
| C-06 | project | one developer, part time | SRS |
| C-05 | project | official sources or the institution's own site only | SRS |
| C-09 | project | country model already generic; Ireland enters as a scheme, not as new columns | SRS, decision A2 |
| new | project | the placement test bank is original and publishable under the repo licence; nothing copied from test owners | sponsor spec |
| new | normative | score equivalences only from the test owners' official tables | sponsor spec |

**Gate 0:** problem written without a solution ✅ · objectives verifiable ✅ (SO6–SO9) · rigor chosen ✅.

## 2. Information sources (phase 1)

### 2.1 Stakeholders and user classes

| Stakeholder (role) | Representative | User class | Involvement | Interest |
|---|---|---|---|---|
| Sponsor | project author | — | controls the result | ships the path they need |
| Researcher planning a degree | author (persona below) | favored | controls (first user) | eligibility, cost, family |
| **English learner** (new) | author (persona below) | favored | controls (first user) | level, target, course, cost |
| Curator / admin | author | favored | controls | workload proportional to use |
| Irish Immigration Service Delivery, QQI | official pages | indirect (source) | informed | licence of the lists (open question) |
| Language schools, universities | official sites | ignored (data subject) | informed (correction channel) | correct data |
| Score-gaming user | — | not favored | — | must not get an "official score" claim out of the test |

**Who validates the baseline:** the sponsor. **Class without a real representative:** students other than the author (risk carried from the SRS; feedback by issues after release).

**Persona update.** Working professional with a family (SRS §2.4), now **before** the degree: no official English score, listening weaker than reading, plans to spend 6–8 months on an English course abroad while working part time, then to apply for a master's that accepts their undergraduate field. The family's place in each step depends on the country's rules, which is exactly what North must make visible.

### 2.2 Documents and systems

Measured in the round-3 spikes (section 4): ILEP and TrustEd Ireland lists, Irish immigration rules, rent and fee sources for Ireland, IPEDS and Scorecard at every award level, SEVP and ESL, official CEFR tables of each English test.

**Gate 1:** every user class has a representative or persona ✅ (the author for all three favored classes; risk recorded) · sources listed ✅ · baseline validator defined ✅.

## 3. Elicitation plan (phase 2)

| # | Technique | Why | Output |
|---|---|---|---|
| S07 | Document analysis: official lists and rules (spikes `s7`, `s8` and desk research) | normative context; vocabulary and limits before deciding | `docs/sources/*.md`, `spikes/*/RESULT.md` |
| S08 | Closed-question questionnaire, round 3 | only the sponsor can decide scope order, levels and family policy; the decisions must stay written | section 5, then record 0008 |
| S09 | Prototype of the placement test, validated by tasks with the sponsor | the sponsor recognizes a good test when they take it; calibration needs real scores | `docs/design/english-placement-v0.md` |
| — | Interviews with other students | deferred, as in the SRS (§3.5) | — |

**Elicitation risks:** scope grows to "everything" before one slice is complete (the SRS already lists it) → slices with their own completeness rule, and curation only on demand; official tables change (TOEFL 2026) → mapping versioned with a check date; licence of the Irish lists unknown → facts only, contact columns dropped, ask the publisher.

**Gate 2:** ≥ 2 techniques with a reason ✅ · order defined ✅ · risks listed ✅.

## 4. What the sources say (phase 4–5)

Session S07, 2026-11-22. Details and citations in the files named in each line; numbers are the ones measured, not estimates.

**English placement** (`sources/cefr-test-mappings.md`)
- Official CEFR tables exist for IELTS (overall only, nothing below band 4), Cambridge English Scale (per skill), TOEFL iBT (per section), Duolingo, PTE Academic, LanguageCert and Trinity ISE.
- TOEFL iBT is scored 1–6 in half bands for tests taken from 2026-01-21; ETS publishes a concordance to the old 0–120 scale, and score reports show a "comparable" 0–120 score until January 2028. Program minimums in North are stored on 0–120 today.
- No test owner grants an open licence; Pearson forbids reproduction. Safe use: our own typed numeric boundaries with a citation, no copied documents or logos. The CEFR Companion Volume licence must be read by hand (coe.int blocks scripts) before any descriptor is quoted.
- Official overall scores include writing and speaking; the v0 test has neither, so its result cannot be presented as an overall equivalent.

**Ireland: lists** (`spikes/s7_ie_lists/RESULT.md`, `sources/ilep.md`, `sources/trusted-ireland.md`, `sources/qdr-ireland.md`)
- ILEP (file of 2026-09-22): 1,151 programmes, 77 providers; **1,066 English language from 64 providers (Dublin 832 / 44)**, 78 higher education. Free re-use with attribution. Contact columns (personal data) dropped at read time.
- TrustEd Ireland (file of August 2026): **6,711 higher-education programmes** (NFQ 6: 249, 7: 573, 8: 2,530, 9: 2,719, 10: 638; Dublin 3,488) and 54 English programmes, all from university language centres. The 5 TrustEd-approved English schools have no rows in it; 4 of them still list 95 rows on ILEP. No terms page.
- No programme is on both lists. Provider numbers carry over (`0058` → `TE0058`). Neither list has field of study, fees, start dates, programme URL or mode of study.
- QQI's Irish Register of Qualifications (EU open-data copy, Commission re-use licence): 11,705 active programmes at NFQ 6–10, 152 providers, ISCED-F 4-digit field. No shared identifier with the immigration lists; title matching links 37% of TrustEd rows. NFQ codes in the copy are unlabelled (mapping inferred). irq.ie forbids robots; CAO is "all rights reserved" (not used).

**Ireland: rules and cost** (`sources/ireland-immigration-rules.md`, `sources/rtb-rent-index.md`)
- **Family: students cannot bring dependants**, by the Family Reunification Policy of 2026-06-12 (§5.4), except PhD students and certain recognised scholarship holders (spouse and children on Stamp 2A, **spouse cannot work**; state school only with a levy and written approval). Researchers on a Hosting Agreement and Critical Skills permit holders can bring a family whose spouse can work.
- English course: each 25-week course gives up to 8 months; at most three, so 2 years. Student time cap 7 years (8 at NFQ 9+). Work 20 h/week in term, 40 h/week in June–September and 15 December–15 January.
- Money: €10,000 a year (€833/month for ≤ 8 months), **no amount per dependant**; fees fully paid if under €6,000, otherwise at least €6,000 upfront; private medical insurance; €300 registration fee. Brazil is visa-exempt: the money is checked at registration.
- Post-study: Stamp 1G 12 months after NFQ 8, 12 + 12 after NFQ 9+. Critical Skills: €40,904 salary (€36,848 for recent graduates).
- Rent: CSO table RIQ02 (RTB data), 446 locations × 1/2/3/4+ bedrooms, quarterly (latest 2025Q4), no key, no bot block. No official fee list.

**US: every award level** (`spikes/s8_us_levels/RESULT.md`, appendices in `sources/ipeds.md`, `scorecard.md`, `sevp.md`)
- IPEDS 2023-24, Texas: 14,828 programs at all levels and CIPs (846 in the tech CIPs); master's tech 132. Nationally: **267,595 programs**, 5,869 institutions; 65,499 in a DHS STEM CIP. Nonresident share of graduates: bachelor's 2.5%, master's 25.5%, doctor's research 29.8%.
- Tuition differs by level: undergraduate `TUITION3`/`CHG3AY3`, graduate `TUITION7`, professional doctorates `OSPROF1..9`. Scorecard earnings suppressed (Texas, 1 year): bachelor's 55%, master's 67%, doctoral 87%.
- STEM OPT extension (8 CFR 214.2(f)(10)(ii)(C)): bachelor's, master's and doctoral degrees only; a prior US STEM degree within 10 years can be used; at most two extensions in a lifetime, the second at a higher level. Regular 12-month OPT at any level except English language study.
- **F-1 admission is a fixed period of up to 4 years** in the current eCFR text of 8 CFR 214.2(f)(5)(i), no longer "duration of status" (checked in the downloaded text on 2026-11-22; effective date still to be confirmed). Programs longer than 4 years, most doctorates, need an extension.
- English language (ESL) programs: no structured official list. IPEDS does not collect ESL codes; the SEVP PDF flags F/M per campus, not per program. Language study gives F-1 with F-2 dependants, capped at 24 months, no OPT or CPT.

**Consequences for the model** (to be confirmed by the questionnaire): an English course is a new kind of program (CEFR entry/exit, exam, weeks, hours) with the same source and status envelope; Ireland's authorization is "on the ILEP or TrustEd list" at program level (two schemes, ILEP with an end date); the family criterion now really differs by country and by route, so it must come from the country module; the degree level must become generic (the US award level and the Irish NFQ level become classifications); 267k US programs cannot all be curated, so completeness (BR-11) must apply to what is curated, not to everything ingested.

## 5. Questions for the sponsor (phase 4–5)

Session S08. Closed questions, answered in the round-3 questionnaire (artifact); the answers become decision record 0008. Numbering continues the SRS (Q01–Q12). The recommendation is marked ★.

| # | Question | Options (★ recommended) |
|---|---|---|
| Q13 | Order of the slices | ★ E1 placement → E2 Ireland English → E3 Ireland HE → E4 US levels · E2 first · E4 first |
| Q14 | Family in a path where the family joins later | ★ the profile says who travels in each step; Stamp 2 dependants are `confirmed_negative`; PhD / Hosting Agreement as separate routes · family always travels (Ireland fails almost always) · ignore family for Ireland |
| Q15 | Which Irish programmes appear | ★ only Stamp 2-eligible ones (ILEP + TrustEd), the QQI register used to add the field · every register programme with eligibility as a flag |
| Q16 | Irish HE levels | ★ NFQ 6–10, all fields (6.7k rows) · NFQ 9 (master's) only |
| Q17 | ILEP → TrustEd transition | ★ automatic link on provider number + exact title, otherwise reconciliation task; never negative automatically; ILEP end date in `migration_rules` · treat the lists separately |
| Q18 | Irish rent benchmark | ★ CSO RIQ02 by location and bedrooms, county fallback · RTB standardised index by area, no bedroom split |
| Q19 | Letters to publishers | ★ the author emails QQI (TrustEd terms, NFQ codes) and SEVP (English-training flag) · assume and do not ask |
| Q20 | US levels after master's | ★ doctorates + graduate certificates, then bachelor's · all levels at once · bachelor's next |
| Q21 | US fields | ★ every CIP on the DHS STEM list · tech CIPs only · all fields |
| Q22 | Curation at this scale | ★ ingest the whole scope as "official data only"; curate and extract on demand (programs a user shortlists or a slice the author picks); BR-11 completeness per curated slice · curate a whole state · ingest only what is curated |
| Q23 | Degree level in the model | ★ generic level (ISCED 2011) plus the source code kept as a classification (IPEDS award level, NFQ) · store each country's code only |
| Q24 | English courses in the model | ★ a program of kind `language_course`, with its own fields, same envelope · a separate entity |
| Q25 | US ESL programs | ★ ask SEVP; meanwhile curate leads from the SEVP list by hand for one city · skip until an official list exists |
| Q26 | F-1 fixed 4-year admission | ★ dated rule in `migration_rules`, caveat on programs longer than 4 years · ignore until confirmed |
| Q27 | Tests shown in the placement result | ★ IELTS, TOEFL, Cambridge · IELTS and TOEFL · all seven |
| Q28 | Label of the result | ★ "grammar, vocabulary, reading and listening; writing and speaking not tested", per-skill ranges where official · one overall equivalent |
| Q29 | TOEFL 0–120 scale | ★ secondary until January 2028 · hide it |
| Q30 | Program English minimums | ★ a scale marker on the TOEFL minimum (`ibt_0_120`, `ibt_1_6`) · a new field per scale |
| Q31 | Item bank storage (Q-N1) | ★ versioned YAML in the repo, reviewed in pull requests · database with a curation screen |
| Q32 | Listening audio (Q-N2) | ★ pre-generated audio files, versioned with the item · browser speech synthesis |
| Q33 | Placement result → course filter (Q-N3) | ★ now: course entry level ≤ estimated band, target from SO9 · later |
| Q34 | CEFR descriptors | ★ write our own band guidelines; quote no descriptor until the licence is read by hand · quote descriptors with attribution |

**Gate 4:** every session has a record (S07 in the source files, S08 in the questionnaire) · every finding has a source · gaps became questions ✅.

**Next (phases 5–7):** with the answers, write record 0008, update `requirements.md` to 2.0 (new SO6–SO9, FRs for placement, Irish ingestion and language courses, BR changes for family, level and completeness, NFRs for the test), then `uml-model.md`; validation by the sponsor closes the baseline.
