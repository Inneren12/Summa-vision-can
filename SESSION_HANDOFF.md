## i18n effort — Phase 1 COMPLETE

Phase 1 (Next.js admin + editor) closed 2026-04-22.

**Merged:**
- Slice 1 — editor core + admin layout + publications list
- Slice 2a — Inspector + RightRail
- Slice 2b — validation architecture refactor
- Slice 2c — ReviewPanel + TopBar + QAPanel
- Slice 3 — block editors + registry + LeftPanel + template picker
- Slice 5 — consolidation (ESLint rule, integration test, coverage test, developer guide)

**Deferred:**
- Slice 4 — non-editor admin routes (routes don't exist yet; policy documented in developer guide for when they're built)

**Phase 3 (Flutter operational i18n)** — next in roadmap. Blocker check: Cyrillic font coverage.

**i18n developer guide:** `docs/i18n-developer-guide.md`
**Policy reference:** `docs/i18n-recon-slice2-inspector-validation.md` → "Consolidated EN-kept policy"


### Tests and guardrails
- `tests/i18n/catalog-coverage.test.ts` — BREG-catalog coverage gate
- `tests/integration/i18n-ru-mode.test.tsx` — real `NextIntlClientProvider` smoke test + DOM
  scan for EN leaks (first version was mock-backed; re-written in Slice 5 follow-up to use
  real provider)
- `npm run lint:i18n` — ESLint `no-literal-string` rule (heuristic, not proof; see
  `docs/i18n-developer-guide.md`)
