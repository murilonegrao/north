---
title: "Decision record 0007 — Email from the admin area"
status: accepted
date: 2026-11-22
supersedes: "0006/X1 in part: password reset by email is now allowed (the second factor is still required)"
---

# 0007 — Email from the admin area

The author asked for the site to send email, admin email first, with a mailbox on the domain's
mail host, and possibly user notices later ("save a university"). This record fixes how email is
sent and what the admin area sends. Public accounts and their notices are not part of it.

## Decisions

| # | Decision | Exact consequence |
|---|---|---|
| E1 | **Outbox in Postgres, sent by the worker** | The web process only inserts into `email_outbox` in the same transaction as the event (a rolled back change sends nothing). A daemon thread of the worker (`north.mail.sender.MailSender`) claims due rows with `FOR UPDATE SKIP LOCKED` every 5 s and sends them over one SMTP connection, so a long job never delays a reset link. The web pod keeps its egress limited to DNS and Postgres (0006/X9) |
| E2 | **SMTP of the domain's mailbox** | Settings `NORTH_SMTP_HOST`, `NORTH_SMTP_PORT`, `NORTH_SMTP_SECURITY` (`ssl` 465, `starttls` 587, `none` local only), `NORTH_SMTP_USERNAME`, `NORTH_SMTP_PASSWORD` (sealed Secret `north-smtp`, worker only), `NORTH_MAIL_FROM`, `NORTH_MAIL_REPLY_TO`. TLS with certificate verification. Production: Hostinger, `smtp.hostinger.com:465`. Worker egress adds port 465. No third-party email API: one provider, no new account, enough for admin volume |
| E3 | **Delivery rules** | Retry after 1 min, 5 min, 30 min, 2 h; the fifth failure, or a 5xx refusal, ends as `failed`. An authentication failure waits 30 min (no lockout of the mailbox). A message not sent within 24 h becomes `expired` instead of arriving late. Without SMTP settings the rows wait with `last_error` saying why, shown on the admin overview with counts of the last 24 h |
| E4 | **Plain text, rendered when queued** | Templates in `backend/north/mail/locales/{en,pt-BR}.json` (the admin languages, 0006/X7), chosen by `users.locale`, which follows the admin language selector. No HTML, no remote images, no tracking. Headers: `Auto-Submitted: auto-generated`, a Message-ID on the sender's domain. Rows with a live link (`sensitive`) have their body blanked once sent; sent rows are deleted after 90 days |
| E5 | **Verified address per account** | `users.email` (lower-case, unique), `users.email_verified_at`. Setting an address sends a confirmation link; until it is opened, the address gets nothing but that link and test messages. The owner changes it on the account page with the current password; an admin can set it for another account. The previous verified address is told of a change |
| E6 | **Single-use links in the URL fragment** | `user_tokens` stores sha256 of a random 256-bit token, its `purpose` (`reset_password` 30 min, `verify_email` 24 h), `used_at`; a new link voids the older ones. Links are `<NORTH_PUBLIC_URL>/admin/reset#token=…`: the fragment never reaches a server log or a Referer. `NORTH_PUBLIC_URL` is configured, never read from the request (reset poisoning) |
| E7 | **Password reset by email** (supersedes part of 0006/X1) | `POST /api/admin/auth/forgot` with a username or address answers the same way whatever happens (no enumeration); a link goes only to an active account with a verified address, at most 3 per account per hour, 10 requests per address per hour. `POST /auth/reset` sets the password, ends every session and tells the owner. The TOTP code is still required at sign-in: a mailbox alone never opens the account. Losing the authenticator still needs another admin or the CLI |
| E8 | **What the admin area sends** | Security notices, always on: password changed or reset, authenticator replaced, account changed by an admin, address changed (to the old address), sign-in from an address not seen in the last 90 days (never on the first sign-in), sign-in paused after 5 failures (once per window). Job notices, on by default (`users.notify_jobs`): a job ending `failed` or `attention` goes to whoever started it, a scheduled one to every admin. A test message from the account page (5 per hour) |
| E9 | **Local runs use Mailpit** | `compose.yaml` adds `mailpit` (inbox at http://localhost:8025); nothing leaves the machine |

## Left out, and why

- **Public accounts and their notices** ("save a university", alerts on changes): they bring
  personal data of the public, consent, unsubscribe links and a privacy notice. A new record when
  that feature is designed; the outbox and templates are ready for it. Saving programs can start
  in the browser (local storage) without any account.
- **HTML email, a transactional email API, bounce processing**: not needed at admin volume.
- **Invitations by email** (an account created without a temporary password): small, next step.

## Open after this record

- DNS of the sending domain: SPF, DKIM and DMARC records for the mail host, set by the author.
- Public accounts and notices (above).
