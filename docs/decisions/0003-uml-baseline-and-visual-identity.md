---
title: "Decision record 0003 — UML baseline approved, visual identity"
status: accepted
date: 2026-11-21
---

# 0003 — UML baseline approved, visual identity

## Approvals

The author approved the UML model 1.0 and the items left open in record 0002:

| # | Item | Decision |
|---|---|---|
| P1 | UML model 1.0 | Approved as the baseline for Phase 3 |
| P2 | The 7 proposed CIP → ISCED-F rows (`data/reference/cip-isced-f.csv`) | Approved. They keep `origin = proposed` so readers know they are not official, and are marked as reviewed by the author |
| P3 | Immigration risk criteria (`docs/methodology/score-proposal.md` §4) | Approved, to be calibrated with pilot data |
| P4 | GPA and GRE in the profile | Added as optional profile fields |
| P5 | Non-housing family costs | Added as a cost-model parameter per country module, sourced and dated like any other value |
| P6 | Public repository `murilonegrao/north` | Approved. Created after a scan for personal data and secrets |

The manual check of the 8 Texas institutions with no SEVP match stays as a task for the pilot.

## Visual identity

North follows **A Forja**, the author's visual identity for personal projects (North lives under harpia.info, which is in scope of A Forja). Summary of the rules that apply to the UI:

- One accent only: ember `#D96C2C` (ember-dim `#8C5A32` for hover and muted borders). Everything else is neutral: charcoal `#0E0E10`, soot `#17171B`, iron `#26262C`, forge-gray `#8A857E`, parchment `#EDE6DB`; light side linen `#F5F0E7`, sand `#DBD3C4`, graphite `#57534C`. Never pure black or pure white.
- Dark theme by default; light theme on user preference or toggle.
- Fixed type roles: JetBrains Mono for titles, labels and code; Inter for body text; Spectral italic for at most one short epigraph per page. Fonts are self-hosted.
- The sigil is a signature, never a hero: ring (r=42, stroke 3) plus a glyph in ember. North's glyph is a needle pointing north. Used as favicon, header mark, footer seal and at the top of the README.

Constraint C-10 in the SRS points here.
