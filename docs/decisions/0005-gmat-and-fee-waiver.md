---
title: "Decision record 0005 — GMAT and application fee waiver"
status: accepted
date: 2026-11-21
---

# 0005 — GMAT and application fee waiver

The author asked to add two admissions fields that the pilot preparation found missing from the schema.

| # | Decision | Exact consequence |
|---|---|---|
| G1 | GMAT requirement | `admissions.gmat`: VerifiedValue with the same values as `admissions.gre` (`required`, `optional`, `not_required`, `waivable`). Common in analytics (30.71) and information systems (52.12) programs |
| G2 | Application fee waiver | `admissions.application_fee_waiver`: yes/no VerifiedValue. A confirmed "no" is `confirmed_negative` (0002/R12). Eligibility conditions go in `evidence` |

Both are site-only fields, collected in the manual pilot. Neither is a filter criterion (BR-04); the application fee waiver can feed the cost view later.
