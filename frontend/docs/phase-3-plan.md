# Phase 3 — Flutter App i18n Plan

Date: 2026-04-22  
Status: PLANNING — ready for founder review  
Previous: Phase 3 Slice 0b merged (Bricolage → Manrope font swap)

---

## Document intent and constraints

This document defines implementation planning for Phase 3 Flutter i18n only.

- It is a planning artifact, not an implementation artifact.
- It intentionally avoids per-file hardcoded-string recon (that starts in Slice 3.3+).
- It does not create ARB files, dependency changes, or runtime wiring.
- It carries forward locked scope/policy from Phase 1 and the project-level i18n plan.

---

## 1. Inventory

### 1.1 Inputs reviewed

The following artifacts were reviewed before planning:

- `docs/i18n-glossary.md` (Phase 1 canonical term source)
- `docs/phase-3-slice-0-font-blocker-check.md` (font blocker check + resolution)
- `docs/i18n-developer-guide.md` (Phase 1 dev workflow/policy patterns)
- `docs/I18N_PLAN.md` (project-level scope and locked decisions)
- `SESSION_HANDOFF.md` (current state handoff)

### 1.2 Flutter app shape (high-level)

Current `frontend/lib/` top-level structure:

- `core/`
  - networking, routing, theme, shared infrastructure
- `dev/`
  - development helpers
- `features/`
  - domain feature modules
- `main.dart`

Current feature directories (`lib/features/*`) indicate the operational app has already expanded beyond the initial 3-screen memory:

- `queue/` — queue and triage
- `editor/` — brief editing
- `graphics/` — generation config + preview/polling
- `jobs/` — job monitoring dashboard
- `kpi/` — KPI monitoring
- `cubes/` — StatCan cube search + detail
- `data_preview/` — data inspection/preview

Total Dart files in `lib/`: **88** (snapshot at planning time).

### 1.3 Routing and navigation architecture

Observed routing stack:

- **Router library:** `go_router`
- **Router ownership:** `GoRouter` is provided via Riverpod provider (`routerProvider`)
- **Material app mode:** `MaterialApp.router`
- **Initial route:** `/queue`
- **Unknown-route handling:** redirect to `/queue`

Current route constants/surfaces:

- `/queue`
- `/editor/:briefId`
- `/preview/:taskId`
- `/cubes/search`
- `/cubes/:productId`
- `/data/preview`
- `/graphics/config`
- `/kpi`
- `/jobs`

Shared chrome:

- App drawer exists with visible nav labels (currently hardcoded EN):
  - Summa Vision
  - Brief Queue
  - Cubes
  - Jobs
  - KPI

### 1.4 State management and DI

- **State management:** `flutter_riverpod`
- Router injected via provider.
- Networking (`Dio`) injected via provider.
- Feature modules include application/provider layers in multiple modules.

This supports a clean locale-provider pattern for app-wide reactive locale switching.

### 1.5 Current localization baseline

Current state is pre-i18n:

- No `flutter_localizations` dependency present.
- No `intl` dependency present.
- No `lib/l10n/` directory present.
- No ARB files present.
- `MaterialApp.router` has no `locale`, `supportedLocales`, or localization delegates configured.
- UI labels in shell/router-adjacent code are currently literal EN strings.

### 1.6 API integration and backend-emitted strings

Networking stack:

- `dio` client with shared base options.
- Real backend path via auth interceptor.
- Mock mode via interceptor + fixtures.

Error-shape indicators from current code/model hints:

- Presence of fields such as `error_message`, `error_code`, and `detail` in various domains.
- Some fallback error text appears hardcoded in EN in generation-related logic.

Planning implication:

- Flutter phase should adopt same long-term direction as Phase 1: **map structured backend error codes to localized UI strings**.
- If backend still returns EN free-text in some endpoints, treat as tech debt with explicit boundary decision (now vs deferred).

### 1.7 Screen inventory against requested focus

Requested focus in prompt memory:

- Queue
- Editor
- Preview
- auth/settings (if present)

Observed implementation inventory (current codebase reality):

- Queue ✅
- Editor ✅
- Preview ✅ (under graphics feature)
- Jobs dashboard ✅
- KPI dashboard ✅
- Cube search/detail ✅
- Data preview ✅
- Auth/settings screens: not obvious in current route table

Planning consequence:

- Phase 3 should be framed as **core + already-live operational surfaces**, not only three historical screens.
- The first implementation slices can still prioritize Queue/Editor/Preview for continuity with initial roadmap.

---

## 2. Workflow mapping

This section maps existing Flutter surfaces to operator workflows, estimated string density, usage frequency, and dependency chain.

### 2.1 Operator context carried from Phase 1

From prior planning context:

- Two Russian-native operators are primary audience.
- Operational tasks include journalist review flow + data operations + job monitoring.
- High-frequency use should determine i18n ordering.

### 2.2 Surface-by-surface mapping

| Surface | Workflow role | String density | Daily-use frequency | Dependency chain |
|---|---|---:|---:|---|
| Queue (`/queue`) | Intake of LLM-proposed topics/briefs for review triage | High | Very high | Queue repo/API → brief card metadata → navigation to editor |
| Editor (`/editor/:briefId`) | Brief editing and refinement before generation | High | Very high | Brief model/state → validation/status messaging → transition to generation/preview |
| Preview (`/preview/:taskId`) | Polling + result review for generated graphics | Medium-High | High | Task polling/status API → transient states/errors → output-ready actions |
| Graphics Config (`/graphics/config`) | Configure chart/data source before generation | High | Medium-High | Data source selection/upload → configuration forms → generation trigger |
| Jobs (`/jobs`) | Operational monitoring of async jobs | Medium | High | Job list/status/error fields → filters and detail sheet |
| KPI (`/kpi`) | Quality and throughput observability | Medium | Medium | Aggregated metrics + chart legends/labels/status |
| Cube Search/Detail (`/cubes/search`, `/cubes/:productId`) | StatCan discovery and dataset inspection | High | Medium | Search filters/facets → cube metadata → downstream selection |
| Data Preview (`/data/preview`) | Inspect transformed data payloads before use | Medium | Medium | Data preview response shape → table/meta labels → validation hints |

### 2.3 Priority interpretation for Phase 3 slicing

Recommended operational priority for implementation slices:

1. Queue + shared shell/chrome (highest frequency, smallest dependency risk)
2. Editor (highest density + critical workflow)
3. Preview/Graphics config (polling/errors/plurals and state-heavy copy)
4. Jobs + KPI
5. Cubes + Data preview
6. Consolidation + test/coverage gates + docs updates

This preserves original roadmap intent while reflecting expanded app surface area.

---

## 3. Infrastructure plan

### 3a. Localization framework (recommendation + rationale)

#### Recommendation

Adopt **Flutter official localization stack**:

- `flutter_localizations`
- `intl`
- ARB catalogs (`app_en.arb`, `app_ru.arb`)
- Generated strongly typed localization class (`AppLocalizations`)

#### Why this option

1. **Alignment with locked project plan** (`docs/I18N_PLAN.md`).
2. **Strong typing** and compile-time breakage for missing keys reduces drift.
3. **ICU support** for plural/gender/placeholders matches Phase 1 patterns.
4. **Compatibility** with current app architecture (go_router + Riverpod).
5. **Lower long-term risk** vs extra abstraction package for a two-locale app.

#### Alternatives considered (not selected)

- `easy_localization`: runtime JSON convenience, but weaker compile-time guarantees.
- `slang`: strong typed alternative, but adds a second pattern not already signaled in project plan.

Decision default: **Stay with official ARB path unless founder explicitly overrides.**

### 3b. ARB file structure + key namespacing

Planned structure:

```text
lib/l10n/
  app_en.arb
  app_ru.arb
  l10n.yaml
```

#### Namespacing convention (Flutter-local)

Use screen/concern prefixes, matching Phase 1 conceptual grouping where possible:

- `common*` — generic reusable UI/chrome strings
- `queue*`
- `editor*`
- `preview*`
- `graphics*`
- `jobs*`
- `kpi*`
- `cubes*`
- `dataPreview*`
- `validation*`
- `status*`
- `errors*`
- `nav*`

#### Important Phase 1 → Flutter difference

- Phase 1 JSON keys used dotted namespaces (e.g., `queue.title`).
- Flutter ARB codegen produces Dart members, so keys should be Dart-friendly (camelCase), e.g.:
  - `queueTitle`
  - `queueEmptyState`
  - `validationRequiredField`

Policy for parity:

- Keep **semantic namespace concept** from Phase 1.
- Adapt to **ARB/Dart method naming** for generated API ergonomics.

### 3c. Locale persistence

Default plan:

1. Create locale state source in Riverpod (`localeProvider`).
2. Persist selected locale to SharedPreferences key:
   - `selected_locale`
3. Startup resolution order:
   1. persisted locale (`selected_locale`) if valid
   2. device locale if supported (`en`, `ru`)
   3. fallback to `en`
4. `MaterialApp.router` reads `locale` from provider.

Notes:

- SharedPreferences load is async: app bootstrap must account for preloaded locale state.
- Avoid frame-flash by resolving locale before first meaningful UI or using a controlled bootstrap placeholder.

### 3d. Language switcher UI

Equivalent to Next.js header switcher, adapted to Flutter shell.

Default UX recommendation:

- Compact EN/RU toggle visible in shared app chrome (preferred over settings-only for operators).

Interaction behavior:

- Tap language option.
- Update Riverpod locale state.
- Persist to SharedPreferences.
- App rebuilds in-place (no restart).

Placement options (founder decision, default in section 5):

- A) Drawer header action (quickest path)
- B) AppBar trailing action (best discoverability)
- C) Settings-only (lowest clutter, slower discoverability)

### 3e. Pluralization

Use ICU plural messages in ARB (official codegen-compatible).

Russian requirements (carryover from Phase 1):

- include `one`
- include `few`
- include `many`
- include `other`

Example shape (for planning only):

```text
"unresolvedComments": "{count, plural, one {...} few {...} many {...} other {...}}"
```

Guardrail:

- Translation QA checklist must explicitly check that RU plural messages include all required forms.

### 3f. Test strategy

Carry Phase 1 philosophy: tests assert stable identifiers/semantics, not fragile literal locale text.

Proposed Flutter testing tiers:

1. **Widget tests (default):**
   - Wrap widgets with test localization delegate.
   - Assert key-driven outputs/semantic labels.
2. **Locale-switch integration smoke:**
   - Verify toggle updates visible language and persistence path.
3. **Catalog health checks:**
   - Script/test ensures key parity between `app_en.arb` and `app_ru.arb`.
   - Optional check to detect unused keys (consolidation slice).

Explicit anti-pattern:

- Do not make most tests assert exact RU copy (too brittle for glossary iteration).

### 3g. Design system / font state

Font blocker resolution status carried from Slice 0b:

- Display font swapped from Bricolage Grotesque → Manrope (resolved)
- Body font remains DM Sans
- Data/mono font remains JetBrains Mono

Implication:

- Phase 3 i18n is **unblocked on font glyph coverage**.
- A targeted design QA pass in EN/RU remains necessary after strings land (planned in consolidation).

### 3h. Backend-emitted strings contract

Target contract (recommended):

- Backend returns machine-meaningful identifiers (`error_code`, structured validation keys/params).
- Flutter maps those identifiers to localized ARB messages.

Current risk indicators:

- Some fields/paths still expose text-like `detail`/`error_message` patterns.
- Some local fallback messages are currently hardcoded EN.

Decision boundary:

- If backend contracts are stable and code-based: localize now.
- If backend still emits raw EN text in key paths: choose between
  - tactical mapping in Flutter for known cases now, or
  - explicit debt item with timeline for backend contract cleanup.

Default: **prefer code-to-local-key mapping; minimize direct UI display of backend free-text.**

### 3i. Glossary reuse policy

Source of truth remains: `docs/i18n-glossary.md`.

Policy carryover:

- Reuse canonical terms for overlapping concepts (`status`, `workflow verbs`, `common nouns`).
- Respect EN-kept rules where applicable (technical tokens, abbreviations, etc.).
- Preserve register consistency (`Вы` form) and imperative button style.

Flutter-specific additions:

- New operational terms discovered in future slices are appended to glossary in focused follow-up PRs.
- Do not invent ad-hoc alternate translations when glossary has canonical mapping.

---

## 4. Slice decomposition (table)

The baseline decomposition is adjusted to reflect currently observed Flutter surfaces while preserving recon → implementation separation.

| Slice | Scope | Approx strings | Complexity | Notes |
|---|---|---:|---|---|
| 3.0 ✅ | Font blocker check + display font swap | — | Done | Completed 2026-04-22 |
| 3.1 ✅ | Detailed planning doc (`docs/phase-3-plan.md`) | — | Planning | This document |
| 3.2 | Infra scaffolding: localizations deps, `l10n.yaml`, empty ARBs, `MaterialApp` wiring, `localeProvider`, persistence, language switcher shell hook | 20-40 infra keys | Medium | No feature-local recon here |
| 3.3 | Recon: Queue + shared shell/chrome (drawer/header/common controls) | 80-140 | Low-Med | String inventory + key map only |
| 3.4 | Implementation: Queue + shared shell/chrome | 80-140 | Medium | Includes tests for queue/shell locale behavior |
| 3.5 | Recon: Editor (+ related validation/status touchpoints) | 90-170 | Medium | Highest density risk surface |
| 3.6 | Implementation: Editor | 90-170 | Medium-High | Includes plural/validation checks |
| 3.7 | Recon: Preview + Graphics Config (polling lifecycle + errors) | 70-130 | Medium | Include backend-message exposure map |
| 3.8 | Implementation: Preview + Graphics Config | 70-130 | Medium | Include async state copy + fallbacks |
| 3.9 | Recon+Impl: Jobs + KPI | 80-140 | Medium | May merge if low churn |
| 3.10 | Recon+Impl: Cubes + Data Preview | 100-180 | Medium-High | Data-heavy labels/filters |
| 3.11 | Consolidation: ARB parity checks, unused-key scan, switcher polish, EN/RU smoke tests, design QA checklist, docs update | — | Low | Final hardening |

If founder wants strict adherence to original 3-screen scope first, slices 3.9 and 3.10 can be explicitly deferred to “Phase 3b”.

---

## 5. Open decisions for founder (with defaults)

1. **Framework choice**  
   - Decision: official ARB stack vs alternative package.  
   - Default: **Official `flutter_localizations` + `intl` + ARB**.

2. **Locale toggle placement**  
   - Decision: app-wide visible toggle vs settings-only.  
   - Default: **App-wide visible toggle in shared chrome** (operator efficiency).

3. **Initial locale default policy**  
   - Decision: device locale fallback vs hardcoded EN fallback-first.  
   - Default: **Persisted → device-supported → EN**.

4. **Backend error string strategy timing**  
   - Decision: refactor to code-based messages in Phase 3 vs defer.  
   - Default: **Start mapping known code-based errors in Phase 3; log residual raw-text paths as explicit debt with owner/date.**

5. **Test assertion philosophy**  
   - Decision: key/semantic assertions vs literal EN assertions.  
   - Default: **Key/semantic-first assertions**, with minimal locale-literal smoke coverage.

6. **Scope handling for expanded Flutter surfaces**  
   - Decision: include Jobs/KPI/Cubes/Data Preview in Phase 3 now or defer after Queue/Editor/Preview.  
   - Default: **Implement Queue/Editor/Preview first, then continue in same phase for remaining already-present routes unless schedule pressure requires defer.**

7. **Glossary update cadence for Flutter-only terms**  
   - Decision: one bulk glossary update vs per-slice updates.  
   - Default: **Per-slice glossary updates** (lower review burden, better traceability).

---

## 6. Tech debt / risks

### 6.1 Technical risks

- `go_router` redirects may need minor locale-state awareness once localization is wired.
- Async locale bootstrap (SharedPreferences) can cause initial-frame mismatch if not handled intentionally.
- Locale switching triggers broad rebuilds; expected behavior, but must avoid accidental expensive side effects in providers.
- Hardcoded fallback EN strings in async/error flows can leak if not explicitly captured during recon slices.

### 6.2 Product/UX risks

- Language toggle placement can impact discoverability for Russian-native operators.
- Data-heavy screens (cubes/jobs/kpi) may expose mixed EN/RU if backend payload labels are inherently EN.
- Russian plural/inflection quality drift can reappear if glossary + ICU checks are not enforced in every slice.

### 6.3 Process risks

- Skipping recon/implementation split increases regression risk.
- Large-string slices can overload review context; keep slices narrow and mergeable.
- If backend error contract remains text-based, frontend localization completeness will plateau.

### 6.4 Risk mitigations

- Keep recon artifacts mandatory before each implementation slice.
- Add ARB parity and missing-key checks early (not only at final consolidation).
- Maintain glossary-first translation prompts for each slice.
- Track backend error-contract debt explicitly with owner and target date.

---

## 7. Timeline estimate

Baseline estimate updated for observed surface area expansion.

### 7.1 Core (Queue/Editor/Preview-first) estimate

- Slice 3.2 (infra scaffolding): **2-3h**
- Slice 3.3/3.4 (Queue + shell): **3-4h**
- Slice 3.5/3.6 (Editor): **3-5h**
- Slice 3.7/3.8 (Preview + Graphics Config): **3-5h**
- Core subtotal: **11-17 agent hours**

### 7.2 Expanded surfaces estimate (already present routes)

- Slice 3.9 (Jobs + KPI): **3-5h**
- Slice 3.10 (Cubes + Data Preview): **4-6h**
- Slice 3.11 (consolidation/polish/docs): **2-3h**
- Expanded subtotal: **9-14 agent hours**

### 7.3 Total scenarios

- **Scenario A (core only now):** ~11-17h, ~2-3 elapsed days
- **Scenario B (full current Flutter surface):** ~20-31h, ~4-6 elapsed days

Founder review load estimate:

- Scenario A: ~1-1.5h
- Scenario B: ~2-3h

---

## 8. Approvals

- [ ] Founder approves infrastructure choice (framework, ARB, provider pattern)
- [ ] Founder confirms Phase 3 scope boundary (core only vs all current routes)
- [ ] Founder resolves open decisions in Section 5
- [ ] Proceed to Slice 3.2 (scaffolding)

---

## Appendix A — Carryover policy checklist from Phase 1

Use this checklist in every Phase 3 implementation slice.

- [ ] No new hardcoded user-facing strings in touched scope
- [ ] EN/RU keys added in same PR
- [ ] ICU placeholders preserved unchanged
- [ ] RU plural blocks include one/few/many/other
- [ ] EN-kept policy respected where applicable
- [ ] Key naming follows Flutter ARB convention
- [ ] Tests assert stable semantics/keys, not brittle locale copy
- [ ] Glossary consulted for domain terms before adding translations

## Appendix B — Suggested key family starter set (for Slice 3.2 scaffolding)

Planning-only seed list (not implementation):

- `appTitle`
- `languageLabel`
- `languageEnglish`
- `languageRussian`
- `navQueue`
- `navCubes`
- `navJobs`
- `navKpi`
- `commonLoading`
- `commonRetry`
- `commonCancel`
- `statusLoading`
- `statusFailed`
- `errorsUnknown`

This starter set is intentionally minimal and shell-focused; feature keys are scoped to recon slices.

