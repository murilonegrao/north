---
name: add-translation
description: Add a new UI language to North or review an existing translation. Use when asked to "add French/Arabic/Hindi...", "translate the interface", "review the Spanish strings", or when a new English UI string needs translating in every locale.
---

# Add or review a UI language

English (`web/src/locales/en.json`) is the source. Translations cover UI strings and help text only; program data stays in English (NFR-14). Wave order: wave 1 `en`, `es`, `pt-BR`, `zh-Hans`; wave 2 `hi`, `fr`, `ar`, `vi`, `ko`, `ja`.

## Add a language

1. Copy `web/src/locales/en.json` to `web/src/locales/<code>.json` (BCP 47 code, e.g. `fr`, `ar`, `zh-Hant`).
2. Translate every value. Keep the keys and the placeholders (`{version}`) exactly as they are. Keep the disclaimer meaning intact: it is a legal notice.
3. Add at the top: `"_meta": { "machine_translated": true }` if a machine or a non-native speaker translated it.
4. Register it in `web/src/locales.ts`: `{ code, prefix (lowercase URL segment), dir: 'ltr' | 'rtl', name (endonym) }`. If the browser tag needs mapping (like `pt` → `pt-BR`), extend `matchBrowserLanguage`.
5. Right-to-left languages (`ar`, `he`, `fa`, `ur`): set `dir: 'rtl'`, then check the page in the browser. Layout must use logical CSS properties; fix any `left`/`right` you find instead of adding RTL overrides.
6. Run `cd web && npm run test -- --run && npm run build`. The test fails on missing, empty or extra keys.

## Native review

A native speaker reads every string in context (run the app, switch language). When done, set `"_meta": { "machine_translated": false, "native_review_on": "YYYY-MM-DD" }`. Never record the reviewer's name in the repo.

## New English string

Add it to `en.json` first, then to every other locale (machine translation is fine, keep the file's `_meta` honest). The test blocks the change until every locale has it.
