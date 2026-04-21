# Summa Vision — i18n Plan (EN + RU)

> Status: **Phase 0 in flight** (glossary prompt ready for dispatch).
> Last updated: 2026-04-21.

## Goal

Bilingual (English + Russian) runtime-switchable UI for admin and editor. Public site stays English-only. Two Russian-native operators joining the team make i18n a pre-launch priority, not post-launch polish.

## Users

| User | Native language | Primary codebase | Priority |
|---|---|---|---|
| Founder (Oleksii) | Russian | All (but prefers EN for code) | Medium — speed |
| Designer (outsource) | Russian | Next.js editor | **Critical** — daily creative work |
| Data worker (outsource) | Russian | Flutter operational + Next.js admin | High — daily data work |

## Scope decisions (locked)

- **In scope:**
  - Next.js admin routes (`/admin/*` including editor) — full UI chrome
  - Flutter operational app — full UI chrome
  - Language switcher (runtime toggle) in both apps
- **Out of scope:**
  - Public site (`summa.vision` home, gallery, METR, partner-with-us) — stays English
  - Backend API error messages — stays English for now, frontend displays as-is (DEBT entry to be added for error-code mapping later)
  - Infographic content (titles, descriptions, data labels entered by operators) — stays English (public site target audience is English)
  - Email templates (magic link, lead notifications, Slack alerts) — stays English

## Strategy decisions (locked)

- **Execution order: sequential** — Next.js editor first, Flutter second. Avoids parallel context switching between two i18n stacks.
- **Translation method: LLM + founder spot-check** — not pure LLM (quality matters for two outsource operators), not hired translator (cost).
- **URL strategy for future public Russian site (if ever):** `/ru/...` subpath (Next.js App Router native support, SEO-friendly). Not relevant for current admin-only scope but noted for consistency.
- **Language persistence: cookie + optional backend profile** — cookie initially, backend user-profile-based persistence can be added later without redesign.
- **Font Cyrillic coverage:** to be verified in Flutter Phase 3 recon (potential blocker if fonts load subset=latin only).

## Tech stack decisions

| Concern | Next.js admin | Flutter operational |
|---|---|---|
| i18n library | `next-intl` (App Router native, ~2M weekly downloads) | `flutter_localizations` + `intl` (stdlib) |
| String catalog | `messages/en.json` + `messages/ru.json` | `lib/l10n/app_en.arb` + `lib/l10n/app_ru.arb` |
| Language switcher | Dropdown in admin header, persisted to cookie | Toggle in app header, persisted to SharedPreferences |
| Pluralization | ICU MessageFormat via next-intl | ICU via Flutter codegen |
| Missing-key handling | Dev warning + fallback to EN | Dev warning + compile-error if key missing from ARB |

## Phased roadmap

### Phase 0 — Foundation

**Goal:** Unblock all subsequent work with consistent terminology baseline.

**Deliverables:**
- `docs/i18n-glossary.md` — 9-section bilingual glossary (product, editor, data, workflow, status, validation, technical-kept-EN, Canadian-domain, plural forms). 150-200 terms total.
- Operator onboarding notes — which screens are daily-use for each operator (2× 10 min conversations).
- Decision doc (this file).

**Process:**
- LLM generates glossary draft via `phase-0-glossary-prompt.md`.
- Founder reviews draft (30-45 min spot-check).
- Committed to `docs/i18n-glossary.md`.
- Glossary is included as context in every subsequent LLM translation prompt.

**Estimate:** 1-2 days elapsed, ~1 hour founder time.

**Status: prompt ready in `/mnt/user-data/outputs/phase-0-glossary-prompt.md`. Awaiting dispatch.**

### Phase 1 — Next.js editor MVP i18n

**Goal:** Designer can work in editor fully in Russian.

**Sub-slices (separate recon PRs to avoid prompt timeouts):**
- Slice 1: Editor core (canvas, toolbar, shell pages) — `frontend-public/src/components/editor/index.tsx`, `/admin/editor/[id]/*`, top-level editor files.
- Slice 2: Inspector + validation — `components/editor/components/Inspector.tsx`, `RightRail.tsx`, `validation/*`.
- Slice 3: Block editors — per-block-type inspector forms, block creation menu.
- Slice 4: Admin shell + publications (moved here instead of separate Phase 2) — covers all non-editor `/admin/*` pages.
- Slice 5: Consolidation — cross-cutting concerns, implementation PR shape.

**Deliverables:**
- `next-intl` scaffolding, locale detection middleware, cookie persistence.
- Language switcher component in admin header.
- `messages/en.json` + `messages/ru.json` with full editor + admin coverage.
- ESLint rule for hardcoded-string detection (prevents regression).
- Tests: language switch re-renders, no English leakage in RU mode.

**Estimate:** 3-5 days elapsed, ~8-12 agent hours, ~2-3 hours founder review time.

**Status: waiting on Phase 0 glossary.**

### Phase 2 — MERGED INTO Phase 1

Admin shell + publications originally planned as standalone Phase 2 but consolidated into Phase 1 Slice 4 — avoids duplicate scaffolding work.

### Phase 3 — Flutter operational app i18n

**Goal:** Data worker can use operational tools in Russian.

**Sub-slices (following Phase 1 pattern):**
- Slice 1: Font Cyrillic coverage check (BLOCKER check — must complete first).
- Slice 2: Jobs dashboard feature.
- Slice 3: KPI monitoring feature.
- Slice 4: StatCan cube catalog search.
- Slice 5: CMHC data views.
- Slice 6: Shared widgets + app shell + main scaffold.
- Slice 7: Consolidation.

**Deliverables:**
- `flutter_localizations` + `intl` setup, `l10n.yaml` codegen config.
- `app_en.arb` + `app_ru.arb` with full coverage.
- Cyrillic-safe font loading (may require adding font subsets or fallback).
- Language switcher toggle in app header, SharedPreferences persistence.
- Riverpod `localeProvider` feeding MaterialApp.
- Tests: locale switch triggers rebuild, compile fails on missing RU key.

**Estimate:** 5-7 days elapsed, ~10-15 agent hours, ~3-4 hours founder review time.

**Status: blocked on Phase 1 completion.**

### Phase 4 — Polish + onboarding

**Goal:** Operators smoothly begin work; feedback loop established.

**Deliverables:**
- 2-min Loom/screencast: "How to switch language" (EN + RU versions).
- Document any per-locale keyboard shortcut differences.
- Operator feedback channel — GitHub issue template for i18n bugs.
- Any operator-reported first-day issues fixed.

**Estimate:** 1-2 days elapsed, ~2-3 hours founder time.

## Budget

| Category | Amount |
|---|---|
| Agent time (Claude/Cursor) | $600-900 total across all phases |
| Translation cost | $0 (LLM-generated, founder review) |
| Time saved — operator onboarding efficiency | ~$400/month ongoing (breaks even in 2-3 months) |

## Translation workflow (applies to all phases)

1. Agent extracts all hardcoded strings from scope into `en.json` / `app_en.arb`.
2. Translation prompt to LLM includes:
   - Full EN catalog as input
   - `docs/i18n-glossary.md` as context
   - Instructions to preserve ICU structure, placeholders, plural forms
   - Output format identical to input
3. LLM produces `ru.json` / `app_ru.arb`.
4. Founder 30-min spot-check: scan for obvious wrongness, domain-term mistranslations, register inconsistency.
5. Commit.
6. Operators report issues via feedback channel → fixes in next translation iteration.

## Critical quality checks (per phase)

- **Pluralization** — Russian has 3 forms (one / few / many). LLM sometimes produces only 2 forms. Validate ICU `plural` blocks have all three.
- **Placeholder preservation** — `{count}`, `{name}`, `{total}` must survive translation unchanged.
- **Register consistency** — "Вы"-form throughout. No slips to "ты" (informal).
- **Imperative infinitive for buttons** — "Сохранить" not "Сохраните".
- **No calques** — "Опубликовать" not "запаблишить".
- **Glossary adherence** — every term in glossary is used as glossary specifies.

## Edge cases to handle in implementation

- **Backend error messages in admin UI.** Errors from FastAPI are English. Frontend displays them as-is initially. Post-launch: add error-code mapping to translation keys. DEBT entry to be created in Phase 1.
- **Cube names from StatCan.** 7000+ cubes have English titles from StatCan (no Russian source). Displayed in admin as-is. Not translatable per-cube.
- **User-entered content.** Operators type content in English (public site stays EN). Admin UI chrome around the input is Russian. Clear workflow expectation for operators.
- **Keyboard shortcuts.** Ctrl+S, Escape, etc. — symbols universal, labels translated. "Ctrl+S to save" → "Ctrl+S для сохранения".
- **Date/number formatting.** Russian decimal separator is `,` (comma), English is `.`. Use locale-aware formatters (`Intl.NumberFormat`, `intl` package) not hardcoded.
- **Toast notifications.** In-scope for admin. Displayed via whatever toast library is in use.

## Known risks

| Risk | Mitigation |
|---|---|
| Flutter fonts lack Cyrillic → Russian text = boxes | Phase 3 Slice 1 blocker check |
| LLM translation drift — different translations for same term in different files | Glossary as single source of truth; all translation prompts reference it |
| Hardcoded strings missed by recon, leak through to Russian UI | ESLint rule + operator feedback loop |
| Partial prior i18n infrastructure exists and creates conflicts | Recon Slice 1 explicitly checks for this |
| Language switch doesn't persist across sessions | Cookie-based persistence + tests |
| Post-launch: backend error codes needed for UI consistency | DEBT entry, addressed Stage 5 |

## Out-of-scope items (for future consideration)

- Public site Russian translation (not currently planned)
- RTL language support (not planned — Russian is LTR)
- More than 2 languages (architecture supports but not yet needed)
- Automated translation quality validation (e.g. CI checks for missing keys)
- Per-user locale preference backed by database (currently cookie-only)

## Open questions (resolve before proceeding)

- [ ] Operators' daily-screens list (Phase 0 deliverable)
- [ ] Does admin have any React components shared with public site where Russian would leak? (To check in Phase 1 Slice 1)
- [ ] Are there any admin routes that receive Russian content from backend (e.g. Cyrillic lead name)? (Affects validation logic — handled per-case)

## References

- `docs/deployment.md` — production deployment (Stage 4 Task 10a output)
- `docs/modules/production-hardening.md` — console stripping, error boundaries (Stage 4 Task 10b output)
- `phase-0-glossary-prompt.md` — current in-flight artifact
- Project memory: glossary philosophy, operator context, current status
