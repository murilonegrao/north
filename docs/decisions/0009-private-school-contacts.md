---
title: "Decision record 0009 — School contacts kept privately for the admin"
status: accepted
date: 2026-11-22
supersedes: "NFR-10, FR-05 and FR-30 in part; 0002/A16 (DAPIP contacts dropped): contact columns of official lists are no longer dropped at ingestion; they are stored privately"
---

# 0009 — School contacts kept privately for the admin

The ILEP and TrustEd Ireland files list a contact person per provider (name, email, phone); DAPIP lists an administrator per institution and campus; the IPEDS directory file (HD) has the chief administrator's name and title and a general phone. Until now North dropped those columns at ingestion (0002/A16). The author wants to keep all of them so the admin can contact any institution when needed. This record allows that, under rules that keep them out of every public surface.

## Decisions

| # | Decision | Exact consequence |
|---|---|---|
| P1 | **Stored in a private table** | `institution_contacts` (institution_id, source, source_file_id, name, title, email, phone, seen_at); `source` ∈ `ie_ilep`, `ie_trusted`, `dapip`, `ipeds_hd`; a row may hold only a general phone. Contacts never go into `programs`, any VerifiedValue or `evidence`, `field_changes`, run summaries, logs or error messages |
| P2 | **Admin only** | Read through the admin API (`GET /api/admin/institutions/{id}/contacts`), role `admin`; `curator` and `viewer` get 403. Each read writes an `audit_log` entry (account, institution, time), never the values |
| P3 | **Never public** | Not served by the public API, not in CSV exports or the CC BY data dump (FR-23), never in the repository; test fixtures use made-up names, `example.com` addresses and fake numbers |
| P4 | **Only the latest list** | Each new run of a source replaces that source's contacts for the institutions in the file; nothing older is kept (data minimization) |
| P5 | **Scope** | Every official source that lists contacts: ILEP and TrustEd Ireland (contact person), DAPIP (AdminName, AdminPhone, AdminEmail; supersedes 0002/A16), IPEDS HD (CHFNM, CHFTITLE, GENTELE). The SEVP list and the Scorecard have no contacts. Institutional URLs (website, admissions, financial aid) are not personal data and are outside this record |

## Why this is acceptable

The contacts were published by government bodies (the Irish immigration service, the US Department of Education) so that people can reach the institutions; using them to contact an institution about its own programmes is the same purpose. Keeping them private, limited to one role, audited and replaced on each new list keeps the use narrow. The repository rule stands: no personal data in the repo.

## Propagation

- SRS 2.1: NFR-10, FR-05 and FR-30 updated.
- `CLAUDE.md`: the ground rule names this exception.
- UML: `institution_contacts` in the physical model.
