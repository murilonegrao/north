---
title: "Decision record 0004 — official data first, smaller pilot"
status: accepted
date: 2026-11-21
supersedes: execution plan v4 phase order (Phases 4, 5 and 8)
---

# 0004 — Official data first, smaller pilot

The author accepted this change of order on 2026-11-21, after seeing the local skeleton with no data.

## Why

The data spikes already downloaded the official files for Texas (IPEDS, DHS STEM list, SEVP, DAPIP, Scorecard, HUD). Together they cover program discovery, the 6-digit CIP, STEM OPT eligibility, SEVP authorization, accreditation, completions and institution-wide graduate tuition. Collecting those by hand would repeat work a script does better.

They do not cover the fields that decide the filter and the cost: English minimums and conditional admission, whether another undergraduate field is accepted, funding for master's students, the program's own tuition and fees, the I-20 financial requirement, the I-20 for the program and deadlines. Those exist only on each program's site.

## Decisions

| # | Decision | Consequence |
|---|---|---|
| O1 | Build the official-data slice of Phase 5 now | Database (core ER tables), ingestion of the official files, `GET /api/programs` and `GET /api/programs/{id}` ([API contract v0](../api/programs-v0.md)), and list and detail screens. Site-only fields show as "not yet collected" |
| O2 | The manual pilot collects site-only fields only | `docs/methodology/pilot-site-template.csv`, keyed by program id (`<unitid>-<cip6>`), on top of the ingested programs. The full template stays for sources not covered by official files |
| O3 | The pilot is still required | It shows which fields sites actually publish and becomes the gold set to measure LLM extraction accuracy |
| O4 | LLM-assisted extraction moves up | Right after the pilot and before the rest of the backend MVP (profile filter, score, cost, curation login), because it automates the site-only fields for every other program |

## New order

1. Official-data slice (O1) — in progress.
2. Manual pilot, site fields only (O2), 10–20 Texas programs.
3. LLM-assisted extraction with review, measured against the pilot.
4. Rest of the backend MVP: profile filter, score, family cost, curation with login, uploads screen.
5. Rest of the frontend MVP, then release v0.1 "Texas".
