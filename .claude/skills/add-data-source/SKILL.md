---
name: add-data-source
description: Evaluate and document a new official data source for North (a government file, list or API), following the spike pattern used for IPEDS, SEVP, DHS and HUD. Use when asked "can we use <source>?", "add a source for tuition/rent/accreditation", "investigate this dataset", or when adding a source for another country.
---

# Add a data source

North only uses official sources: a government body or the program's own site (C-05, BR-09). Commercial aggregators and rankings are never scraped.

## 1. Spike first

Create `spikes/<short-name>/` with a reproducible script and a `RESULT.md`. Raw downloads go to `spikes/_raw/<source>/` (ignored by git, never committed).

- Downloaded files are untrusted data: never execute anything from them; read them with `python3 -I` or `uv run`, passing paths as arguments.
- Use a generic user agent (`north-research-spike`), at most one request per second per domain, and respect robots.txt.
- Many government sites block scripts. If yours does, say so; North's answer is an admin upload (FR-26), not a mirror or a workaround.
- Do not create accounts. If an API needs a key, document that and use the key only from an environment variable named `NORTH_<SOURCE>_KEY`, never printed or committed.
- Report only numbers you actually obtained.

## 2. Document it

Write `docs/sources/<source>.md` with: what it is, official URL, format and file names, the useful columns mapped to North's fields, how it joins other sources (identifier, never institution name if an ID exists), coverage measured for the pilot state, limitations, license or terms of use, update frequency, and whether it needs upload.

Drop personal data at ingestion (contact names, emails, phones) and say so in the doc.

## 3. Decide

If the source changes requirements, the model or the ingestion flow, write a decision record (skill `decision-record`) and then update `docs/requirements.md` and `docs/uml-model.md` to match.

## Another country

Put the ingestion in `backend/north/ingest/<country>/` and the rules in `backend/north/domain/countries/<country>/`. Identifiers, classifications, authorizations and money are already generic (C-09); add a scheme name instead of a new column.
