---
title: "Decision record 0001 — SRS baseline questionnaire"
status: accepted
date: 2026-11-20
inputs: [docs/requirements.md §3.4]
---

# 0001 — SRS baseline questionnaire

The author answered the first decision questionnaire on 2026-11-20. These answers took the SRS from draft 0.1 to baseline 1.0. Later changes are in [0002](0002-after-data-spikes.md).

## SRS adjustments

| # | Question | Decision |
|---|---|---|
| A1 | Where curated data lives | In the database, edited in a curation screen with login; per-field history in a table |
| A2 | Other countries | In the structure only: the model is country-neutral, only the US module is built (detailed in C-09) |
| A3 | Original research files | Kept outside the repository: they contain personal data |

## Questionnaire

| # | Question | Decision |
|---|---|---|
| Q01 | Is the data public? | Yes: a public search app |
| Q02 | Curators | One curator, one account; outside contributions through issues |
| Q03 | Researcher profile | Browser only, shareable by link; nothing stored on the server |
| Q04 | Pilot state | Texas |
| Q05 | Initial CIPs | 11.xx, 52.12, 30.70 (30.71 added in 0002) |
| Q06 | UI language | English first, i18n from day one; later made multilingual in waves (Q06b) |
| Q07 | LLM provider | Configurable by environment variable |
| Q08 | Raw scraped pages | Internal use only; the API serves only the evidence snippet |
| Q11 | License | AGPL-3.0 for code, CC BY 4.0 for data |
| Q12 | Hosting | Own k3s cluster, `k3s-gitops` pattern |

## Deployment

| # | Question | Decision |
|---|---|---|
| D1 | App name | Repo `murilonegrao/north`, image `ghcr.io/murilonegrao/north`, namespace `north`, host `north.harpia.info` |
| D2 | Images | One image: the Vue build served by FastAPI |
| D3 | Database | Declared through Crossplane on the existing Postgres server |
| D4 | GHCR image visibility | Public |
| D5 | Search indexing | Indexable, with a sitemap |
| D6 | First deployment | Early, with `/health` only; then every push to `main` goes live |
| D7 | Periodic ingestion | A CronJob in the cluster, same image, another command |

## Added later the same day

- **Country-neutral model** (C-09): identifiers, field classification, international-student authorization, work eligibilities and money are generic; visa rules live in a per-country module.
- **Q06b, multilingual UI**: wave 1 en, es, pt-BR, zh-Hans; wave 2 hi, fr, ar, vi, ko, ja.
