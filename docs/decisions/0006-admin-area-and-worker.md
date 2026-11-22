---
title: "Decision record 0006 — Admin area, worker and job queue"
status: accepted
date: 2026-11-22
supersedes: "the GitHub OIDC recommendation of docs/design/admin-and-sync.md (O1); UML `accounts` is named `users`"
---

# 0006 — Admin area, worker and job queue

The author asked for an admin area with username and password so that data can be fetched,
uploaded and loaded without touching the server: "the best design, the most secure, without
waste". This record fixes the choices made when building it. The design it implements is
[docs/design/admin-and-sync.md](../design/admin-and-sync.md), steps 1 to 3 of its section 13,
except the diff and publish policy (section 6) and the review queue (step 4).

## Decisions

| # | Decision | Exact consequence |
|---|---|---|
| X1 | **Username and password, plus TOTP**, implemented in the app | `users.password_hash` is Argon2id (argon2-cffi defaults); policy: 12 to 256 characters, not containing the username (NIST SP 800-63B, no composition rules). TOTP (RFC 6238, 6 digits, 30 s, ±1 step, a step is never accepted twice: `users.totp_last_step`) is required for every account when `NORTH_ADMIN_REQUIRE_TOTP` is true (default). The first sign-in forces a new password and TOTP enrolment. No self sign-up; no password reset by e-mail (an admin or the operator CLI resets; superseded by 0007/E7: reset by email, TOTP still required). Replaces the GitHub OIDC recommendation (design O1) |
| X2 | **Server-side sessions** | `admin_sessions` stores sha256 of a random 256-bit token; cookie `__Host-north_admin`, `Secure; HttpOnly; SameSite=Strict; Path=/`; 2 h idle, 12 h absolute. After the password, a TOTP account gets a 5-minute pending session that can only submit a code; a valid code replaces it with a new token. Password change, TOTP change, role change, disable and reset end the account's other sessions |
| X3 | **CSRF and cross-site defence** | a per-session CSRF token in `X-CSRF-Token` on every state-changing `/api/admin` request, plus an Origin / Sec-Fetch-Site check in middleware, plus SameSite=Strict. JSON bodies only (no forms) |
| X4 | **Throttling** | `login_attempts`: 5 failures per account or 20 per address in 15 minutes give HTTP 429. Errors never say whether the account exists; an unknown user is checked against a dummy hash. The client address comes from `NORTH_CLIENT_IP_HEADER` (`cf-connecting-ip` in production) |
| X5 | **Roles** | `viewer` (reads), `curator` (also uploads and runs jobs), `admin` (also users, schedules, audit log, recompute). Checked server-side on every call. The last active admin cannot be demoted or disabled; nobody edits their own access in the users screen |
| X6 | **Audit log** | `audit_log` is append-only: a trigger refuses UPDATE and DELETE. Every sign-in, failure, password or TOTP change, user change, job, cancel, schedule change and upload is written in the same transaction as the change |
| X7 | **Admin UI languages** | the admin is an internal tool: English and Brazilian Portuguese only, in `web/src/admin/locales/`, outside the public wave-1 locale files (NFR-14 applies to the public site). Lazy chunk under `/admin`, `noindex` (header and meta), `Cache-Control: no-store` on `/api/admin` |
| X8 | **Worker and queue in Postgres** | table `jobs` claimed with `FOR UPDATE SKIP LOCKED`, `job_logs` for live progress (polled every 2 s), one active job per kind, cooperative cancel, heartbeat every 15 s, stale running jobs reaped as failed. `python -m north.jobs.worker`, same image, one replica. SIGTERM cancels at the next checkpoint. No broker |
| X9 | **Schedules in code, state in the database** | `schedules` rows keep only `paused` and `next_run_at`; kind, parameters and interval come from `north.jobs.registry` (first: `us-sync-weekly`, Mondays 06:00 UTC, every 168 h). Admins pause, resume or run now |
| X10 | **Job kinds come from country modules** | `north.ingest.us.jobs` declares `us.fetch`, `us.sync`, `us.recompute` and `us.accept_upload`; the core never names a country (P8) |
| X11 | **Uploads** | raw body (no multipart), streamed to `NORTH_INCOMING_DIR` with a size cap (`NORTH_UPLOAD_MAX_MIB`, 95), hashed on the way; the web process never parses it. The worker recognises the file by name and magic bytes and moves it into `NORTH_RAW_DIR` with the download's rules (same bytes = unchanged; different bytes keep the old file). Only the worker writes the raw store; in Kubernetes the web pod mounts only the `incoming` subPath |
| X12 | **Fetcher host allowlist** | `north.ingest.us.fetch.ALLOWED_HOSTS`, checked on every request and every redirect (https only), because NetworkPolicy cannot filter by host name |
| X13 | **First account by CLI** | `python -m north.auth.cli create-user`: password typed twice or generated and shown once, never an argument. Also `reset-password`, `reset-totp`, `enable`, `disable`, `list-users` for recovery |
| X14 | **Reference files in the image** | the Dockerfile copies `data/reference/`, so the worker loads without files copied by hand |

## Clarifications

| # | Point |
|---|---|
| C1 | The database role split of the design (section 9: `north_web` vs `north_worker`) is not done yet: both processes use `north_app`. It needs a third role in the `Banco` composition of `k3s-gitops` |
| C2 | Diffs held for review (design section 6) are not built: a load publishes as before (idempotent, one transaction per step) |
| C3 | Cloudflare Access in front of `/admin` and `/api/admin` stays recommended as a second layer |

## Open after this record

- Database roles (C1), held diffs (C2), the review queue for SEVP reconciliation.
- API snapshot sources (Scorecard fallback, HUD with token, ECB, Federal Register) as new job kinds.
