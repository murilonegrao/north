---
name: decision-record
description: Write a new decision record in docs/decisions/ and propagate it to the SRS, the UML and the plan. Use when a choice changes requirements, the data model, a source or the scope, or when asked to "record this decision", "write an ADR", "log what we decided".
---

# Write a decision record

Records live in `docs/decisions/NNNN-short-title.md`, numbered in order. A newer record wins over older records and over the SRS and UML until those are updated.

## Format

```markdown
---
title: "Decision record NNNN — short title"
status: accepted        # or proposed
date: YYYY-MM-DD
supersedes: none        # or the record/items it replaces
---

# NNNN — Short title

One paragraph: what was decided and who decided it (the author, or "proposed").

## Findings that drove the decision      (optional: facts with their source)

## Decisions

| # | Decision | Exact consequence |
|---|---|---|
| X1 | … | names of fields, tables, requirements affected |

## Open after this record
```

Give each item an ID unique inside the record and cite it from other docs as `NNNN/X1`. Use the exact field, table and requirement names; vague records cause drift.

## Propagate

1. Update `docs/requirements.md`: the decision table in §3.4, the affected FR/NFR/BR/C, and a new row in the version table.
2. Update `docs/uml-model.md` diagrams and notes; keep Mermaid valid.
3. Update `docs/execution-plan.md` if phases or next steps change.
4. If the schema changes, update `schema/` and run the `run-checks` skill.

A clarification that does not change a decision goes in a "Clarifications" table of the same record.
