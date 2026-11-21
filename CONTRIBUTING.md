# Contributing to North

Thank you for helping. North is maintained by one part-time developer, so small, focused contributions work best.

## Report a data error

Open an issue with:

- the program and the field that is wrong;
- the correct value;
- **the source**: a link to the official page or document (program website, IPEDS, SEVP, DHS, HUD...) and the date you checked it.

Data without a source cannot be accepted. Commercial aggregators and rankings are fine as leads, but not as sources.

## Pull requests

1. Open an issue first for anything larger than a typo, so we agree on the approach.
2. Fork, create a branch, keep the change small.
3. Run the checks before pushing:
   - `cd backend && uv run ruff check . && uv run pytest`
   - `cd web && npm run test -- --run && npm run build`
   - `uv run --with jsonschema python -I schema/validate.py`
4. Open the pull request against `main` and describe what changed and why.

## Rules

- **English only** in code, comments, docs, issues and commit messages. UI translations live in `web/src/locales/` and every UI string goes through i18n.
- **No personal data.** Do not commit names, emails, phone numbers or private correspondence, including contact data from official files.
- Code is AGPL-3.0 and data is CC BY 4.0; by contributing you agree to license your contribution under them.
