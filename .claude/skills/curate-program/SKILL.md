---
name: curate-program
description: Record or correct the data of one master's program in North's format, with a source, status and date for every value, and validate it against the schema. Use when asked to "add a program", "fill in the data for <university> MS in ...", "fix this program's tuition/deadline/English minimum", or to turn a pilot spreadsheet row into JSON.
---

# Curate one program

The contract is `schema/program.schema.json`; start from `schema/examples/program.example.json` (it is fictitious, keep it that way). The collection method is in `docs/methodology/pilot-guide.md` — read it before the first program.

## Every value is a VerifiedValue

```json
{ "value": 80, "status": "reported_by_program", "source_kind": "page",
  "source_url": "https://grad.example.edu/admissions/international",
  "evidence": "minimum TOEFL iBT score of 80", "verified_at": "2026-11-21" }
```

Pick the status honestly:

| Status | When |
|---|---|
| `confirmed_official` | a government source says so (DHS STEM list, SEVP list, IPEDS, DAPIP), or the international office (DSO) confirms the I-20 for the program (record 0002/R11) |
| `reported_by_program` | the program's or university's own official page says so |
| `extracted_unverified` | an LLM extracted it and no human checked yet (needs `source_url` and `evidence`) |
| `unknown` | you could not find it. No `value`. **Never guess and never write `false` or `0` for unknown** |
| `confirmed_negative` | a source confirms a "no". Only for yes/no fields; numbers and text never use it (R12) |

`source_kind` is one of `page`, `official_list`, `correspondence`, `uploaded_file`. Only `correspondence` may have no URL. For an email reply: do **not** store the message, names, signatures or addresses; set `source_kind: correspondence`, the reply date in `verified_at`, and at most one quoted sentence in `evidence` (K9).

## Field rules that trip people up

- English minimums live under `admissions.english.*`; "test not accepted" is the yes/no field `<test>_accepted`, not a number.
- Each application deadline is its own VerifiedValue item with term, kind and date (R18).
- `funding.available_to_masters` (yes/no) is separate from the list of opportunities, so "no funding" differs from "nobody checked".
- SEVP authorization belongs to the **campus**; the I-20 belongs to the **program**.
- `in_strategy` and `flags` are derived; do not fill them by hand.
- 52.12xx (Information Systems) is not on the DHS STEM list: the program stays, flagged `no_stem_opt_extension` (R1).

## Validate

```sh
uv run --with jsonschema python -I schema/validate.py path/to/program.json
```

From the pilot spreadsheet: `uv run --with jsonschema python -I schema/csv_to_json.py <filled.csv> --out <out-dir>` (empty cells become `unknown`).

## Before saving

Re-read every value against its evidence. If a value has no source, it is `unknown`. Never put personal data in any field.
