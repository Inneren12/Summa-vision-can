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

#### ARB parity must-have checks

Enforced in CI via a health-check test in Slice 3.11 (can land earlier):

- Every non-metadata key in `app_en.arb` exists in `app_ru.arb`
- Placeholder names match exactly between locales for each key
- Placeholder types match exactly between locales for each key
- Pluralized messages preserve all required RU forms (`one`/`few`/`many`/`other`)
- `@@locale` and ARB metadata entries (any key prefixed with `@`) are excluded from
  parity check
- Orphan keys in RU absent from EN are flagged as error unless explicitly allowlisted

Placeholder parity is particularly important: ARB codegen derives Dart method signatures
from placeholder declarations. Mismatched types between locales either break codegen or
cause runtime errors on locale switch.

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

#### Bootstrap ownership

Locale bootstrap logic must have a **single ownership point** in the app.

**Preferred ownership:** a dedicated bootstrap provider (e.g., `appBootstrapProvider`
returning an `AsyncValue<AppBootstrapState>` that includes resolved locale) OR an app
settings controller that owns locale alongside other app-level preferences.

**Anti-pattern — do NOT:**
- Duplicate locale resolution logic across `main.dart`, router redirects, and shell
  widgets
- Resolve locale in multiple providers that read SharedPreferences independently
- Mix async locale loading with router-level async redirect logic (creates race
  conditions)

**Implementation guidance for Slice 3.2b:**
- One provider owns the locale bootstrap and reads SharedPreferences
- `MaterialApp.router` reads from that provider only
- Language switcher writes to that provider only (which persists to SharedPreferences)
- Router and other consumers READ the resolved locale, never resolve it themselves

This prevents first-frame EN flash, avoids double-reads of SharedPreferences, and
centralizes rollback/debug if locale bootstrap misbehaves.

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

Carry Phase 1 philosophy: tests assert stable identifiers/semantics, not fragile literal
locale text. Flutter-specific strategy is more explicit about what categories must exist.

#### Tier 1 — Widget tests (default, per-screen)

- Wrap widgets with test `AppLocalizations` delegate.
- Assert expected localized output for the active locale. Prefer assertions against
  `AppLocalizations.of(context)!....` derived values where practical (e.g.,
  `expect(find.text(appLoc.queueTitle), findsOneWidget)`).
- Widget runtime tests can verify rendered output matches the expected localized value,
  but cannot definitively prove the source of a string is `AppLocalizations` vs a
  coincidentally-equal hardcoded literal. Catching literal leakage is the job of Tier 2b
  denied-EN smoke tests, not Tier 1.
- Do NOT assert exact RU copy in widget tests — copy iterates during glossary refinement
  and tests become brittle. Assert keys/method-derived values instead.

#### Tier 2 — Mandatory smoke tests (three categories)

**2a. Locale-switch smoke**
- Pump app in EN, capture several visible shell strings
- Switch locale via provider / switcher
- Assert at least 3 visible strings changed to a non-EN variant
- Verifies end-to-end locale wiring (provider → MaterialApp → rebuild)

**2b. Denied-EN phrase shell smoke**
- Pump app in RU mode
- Assert that specific EN strings are NOT present in rendered DOM of shared chrome
  (drawer, app bar, common buttons). Example denied list: `"Brief Queue"`, `"Cubes"`,
  `"Jobs"` — whichever translations exist per policy.
- Allowlist for documented EN-kept exceptions (KPI, JSON, IDs)
- The specific denied list must be generated per recon-approved translation policy for
  that surface; do not hardcode a global denied list that conflicts with EN-kept
  exceptions defined in §3k.
- Catches hardcoded literals that slipped through widget tests

**2c. Missing-localization fail-fast policy**

Policy for this project: **missing localizations fail in development and CI. Production
must never rely on silent raw-key fallback in UI.**

- Incomplete ARB is considered a build/test failure, not a runtime fallback feature
- ARB parity check (Tier 3) catches missing keys before build
- AppLocalizations codegen enforces compile-time method existence (can't reference a
  missing key without Dart analyzer error)
- Any runtime AppLocalizations lookup returning null is a bug to fix, not to tolerate

Rationale: raw keys in production UI ("queueTitle" displayed as-is) are worse than a
clean build failure. Failing fast forces translation gap to be addressed, not
papered over.

#### Tier 3 — Catalog health checks (CI gate)

- **ARB parity**: every non-metadata key in `app_en.arb` exists in `app_ru.arb`
  (`@@locale` and ARB metadata entries, any key prefixed with `@`, are excluded)
- **Placeholder parity**: placeholder names AND types match between EN and RU for each key
- **Plural form completeness**: every RU plural has `one`, `few`, `many`, `other`
- **Orphan key detection** (optional consolidation check): warn on keys in RU not in EN

#### Explicit anti-pattern

- Do not make most tests assert exact RU copy. One or two smoke assertions per critical
  shell element are enough; broader coverage comes from Tier 1 (source-of-string check)
  plus Tier 3 (catalog health).

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

### 3j. Localization boundary: UI chrome vs backend/content payload

Explicit policy on what gets localized and what stays as-is. This boundary prevents
recon debates on data-heavy screens (Cubes, Data Preview, Jobs).

#### Localize (frontend responsibility)

- UI chrome: app bar, drawer, tabs, buttons, menus
- Widget labels, field labels, placeholders, hint text
- Empty states, loading states, skeleton text
- Validation messages (including locally-derived ones)
- Client-side error messages and fallbacks
- Confirmation dialogs and prompts
- Locally-formatted status / badge / chip text

#### Do NOT localize (display as-is)

- Backend content payload: dataset names, cube names/IDs, source titles,
  metadata field labels coming from StatCan/CMHC/etc.
- User-generated content: brief text, operator comments, document titles
- Raw metric codes, product IDs (`36100434`), task IDs, job IDs
- Technical identifiers: `taskId`, `briefId`, `jobId`, URLs
- Timestamps (format for locale, but don't translate the underlying values)

#### Structured backend codes (map to localized wrappers)

- `error_code`, structured validation keys from backend → Flutter maps to ARB keys
- Example: backend returns `{"error_code": "brief_not_found"}` → Flutter renders
  `AppLocalizations.errorBriefNotFound` localized value
- Mapping lives in `lib/l10n/backend_errors.dart` (see §3h)

#### Raw backend free-text (edge case)

- If backend emits raw EN text as `detail` or `error_message` and no code is available,
  display under a localized wrapper phrase. Example:
  `AppLocalizations.errorWithBackendDetail(detail)` renders as
  `"Ошибка: {detail}"` where `{detail}` stays EN.
- Log these cases as explicit tech debt for backend contract cleanup.
- Do NOT attempt to translate backend free-text heuristically.

### 3k. EN-kept policy (Flutter-specific)

Carries forward Phase 1's 4-category EN-kept policy (see
`docs/i18n-recon-slice2-inspector-validation.md` → "Consolidated EN-kept policy") and
adds Flutter-specific cases.

#### Category A — Technical abbreviations kept EN (Phase 1 carryover)

- `QA`, `JSON`, `ID`, `API`
- `KPI` (industry-standard financial/operational term)
- Short toolbar chrome tokens (if introduced): `SAVE`, `IMPORT`, `EXPORT`
- Tab short labels if used: `Tpl`, `Blk`, `Thm` (not expected in Flutter shell; listed for
  consistency)

#### Category B — Dev / debug / diagnostic labels kept EN

- Development overlays, debug panels, console / log labels
- Performance monitor labels
- Feature flag names if surfaced

#### Category C — Machine identifiers (NEVER translate)

- `taskId`, `briefId`, `jobId`, `productId`, `userId`
- Cube product IDs (`36100434`)
- Metric codes, column codes, series codes from backend
- URL paths, endpoint names

#### Category D — Data-viz terminology (Phase 1 carryover)

- `Small Multiples`
- Visualization family names if introduced in Flutter (Single Stat Hero, Insight Card,
  Ranked Bars, Line Editorial, Comparison, Visual Table)

#### Ambiguous cases (flag for explicit decision in recon slice)

- Navigation labels that are also product concepts (e.g., "Jobs", "Cubes"): **default
  is to translate**. Keep EN only if one of the following is true:
  1. Glossary or policy already locks EN for that term
  2. Operators explicitly use EN in day-to-day workflow (confirmed by founder, not
     assumed by agent)
  3. Translation reduces clarity (e.g., technical term with no good RU equivalent)
  4. Translation conflicts with backend naming in a way that would create mixed-signal
     UX
  If none of the above applies, translate. Resolve specific cases in Slice 3.3 recon
  with founder input on each ambiguous label; do NOT silently default to EN.
- Status badge labels (e.g., `DRAFT`, `READY`, `FAILED`) — Phase 1 translated these;
  default is to translate unless operator convention says otherwise.

#### Decision rule

When recon encounters a candidate for EN-kept, classify into A/B/C/D/ambiguous and
document in the recon doc. Do not silently decide to keep EN without a category.

### 3l. Migration rule for implementation slices

Each implementation slice touches a bounded scope (Queue screen, Editor screen, etc.).
When an implementation slice touches a widget, the following rule applies:

#### Localize the whole visible surface in touched scope

- Do not leave half-localized widgets after merge.
- If a widget contains 10 strings and the slice migrates 7, the remaining 3 must either:
  (a) be migrated in the same PR, OR
  (b) be explicitly deferred with a `// TODO(i18n-slice-X)` comment and a line in the
      recon doc explaining why it was deferred.

#### No mixed-mode zebra widgets

- A widget rendering "Sources: источник:" (EN label + RU value) is forbidden unless
  documented as an intentional backend-payload boundary (see §3j).
- Reviewer must reject PRs that introduce EN/RU zebra within a single widget without
  explicit justification.

#### Bounded partial rewrites

- If a deeply-nested component tree can't be fully localized in one PR, define the
  boundary by widget file or logical subtree and document it in the recon doc.
- Deferred subtrees must be listed with ownership and target slice.

#### Recon artifact obligation

- Every recon slice outputs a list of deferred literals (if any)
- Every implementation slice verifies its touched scope has no remaining deferred
  literals unless explicitly carried forward

---

## 4. Slice decomposition (table)

The baseline decomposition is adjusted to reflect currently observed Flutter surfaces while preserving recon → implementation separation.

| Slice | Scope | Approx strings | Complexity | Notes |
|---|---|---:|---|---|
| 3.0 ✅ | Font blocker check + display font swap | — | Done | Completed 2026-04-22 |
| 3.1 ✅ | Detailed planning doc (`docs/phase-3-plan.md`) | — | Planning | This document |
| 3.2a | Infra foundation: add `flutter_localizations` + `intl` deps, create `l10n.yaml`, add empty `app_en.arb` + `app_ru.arb`, generate `AppLocalizations`, wire `MaterialApp.router` delegates + supportedLocales + fixed locale. App compiles and renders with hardcoded locale. | 10-15 infra keys | Low-Med | No user-visible locale switching yet |
| 3.2b | Locale state + persistence + switcher: `localeProvider` (Riverpod), SharedPreferences persistence, bootstrap resolution (persisted → device → EN), visible switcher in shared chrome, locale-switch smoke tests | 10-25 shell keys | Medium | Depends on 3.2a merged |
| 3.3 ✅ | Recon: Queue + shared shell/chrome (drawer/header/common controls) | 8 actual (6 new after reuse) | Low-Med | Recon doc: `docs/phase-3-slice-3-recon.md`. Merged with 3.4 in single PR due to actual literal count well below 80-140 estimate. See `docs/phase-3-slice-3-pre-recon.md` for recount source. |
| 3.4 ✅ | Implementation: Queue + shared shell/chrome | 8 actual (6 new after reuse) | Medium | Merged with Slice 3.3 recon. See `docs/phase-3-slice-3-recon.md` for approved key map. |
| 3.5 | Recon: Editor (+ related validation/status touchpoints) | 90-170 | Medium | Highest density risk surface |
| 3.6 | Implementation: Editor | 90-170 | Medium-High | Includes plural/validation checks |
| 3.7 | Recon: Preview + Graphics Config (polling lifecycle + errors) | 70-130 | Medium | Include backend-message exposure map |
| 3.8 | Implementation: Preview + Graphics Config | 70-130 | Medium | Include async state copy + fallbacks |
| 3.9a | Recon: Jobs + KPI | 80-140 | Low-Med | String inventory + EN-kept classification |
| 3.9b | Implementation: Jobs + KPI | 80-140 | Medium | May merge with 3.9a only if recon confirms low churn and limited literal count |
| 3.10a | Recon: Cubes + Data Preview | 100-180 | Medium | Higher backend-label exposure; flag every ambiguous case |
| 3.10b | Implementation: Cubes + Data Preview | 100-180 | Medium-High | Data-heavy labels/filters; strict backend boundary per §3j |
| 3.11 | Consolidation: ARB parity checks, unused-key scan, switcher polish, EN/RU smoke tests, design QA checklist, docs update | — | Low | Final hardening |

#### Phase 3b — deferred expanded-surface work

**Scope:** Jobs, KPI, Cubes, Data Preview (current Slices 3.9 and 3.10).

**Entry criteria:**
- Phase 3 core merged and deployed
- Operators have used Phase 3 core for at least 1-2 weeks
- Backend error/label contract direction decided (either stable code-based contract
  confirmed, or explicit debt item with target date)

**Why separate:**
- Backend-label-heavy screens benefit less from frontend i18n until backend contracts
  stabilize
- Allows Phase 3 core to ship and gather real operator feedback before expanding
- Keeps Phase 3 scope tight enough to merge within 1-1.5 weeks of focused work

**Trigger:** Founder announces Phase 3b launch; no automatic continuation.

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
   - Decision: include Jobs/KPI/Cubes/Data Preview in Phase 3 now (full surface) vs
     split into Phase 3 (core) + Phase 3b (expanded) with a pause between.
   - Default: **Phase 3 closes at core (Queue/Editor/Preview/Graphics) completion.
     Phase 3b is a separately-scoped follow-up that covers Jobs/KPI + Cubes/Data
     Preview, launched after operators have used Phase 3 core for at least 1-2 weeks
     and confirmed backend error contract direction.**
   - Rationale: Cubes and Data Preview are data-heavy screens where ~60%+ of visible
     text comes from backend payload (StatCan field labels, source titles, metric
     codes). Frontend i18n benefit is limited until backend error/label contract is
     clarified. Avoid investing 10+ hours in Cubes i18n while backend is still EN-heavy.

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

Estimates are given as two ranges:

- **best-case**: clean implementation path with minimal review churn, no architectural
  surprises, catalogs merge on first attempt
- **safe-planning**: expected number including normal review iteration (2-3 rounds of
  reviewer feedback per slice, one or two minor rework cycles)

Use safe-planning for scheduling and external promises. Best-case is achievable with
unusually clean execution; do not commit to timelines on best-case numbers.

- Slice 3.2a (infra foundation): 1.5-2h best / 2.5-3.5h safe
- Slice 3.2b (locale state + switcher): 2-3h best / 3-4.5h safe
- Slice 3.3/3.4 (Queue + shell): 3-4h best / 5-7h safe
- Slice 3.5/3.6 (Editor): 3-5h best / 5-8h safe
- Slice 3.7/3.8 (Preview + Graphics Config): 3-5h best / 5-8h safe
- **Core subtotal: 12.5-19h best / 20.5-31h safe**

### 7.2 Expanded surfaces estimate (already present routes)

- Slice 3.9a/b (Jobs + KPI recon + impl): 3-5h best / 5-8h safe combined
- Slice 3.10a/b (Cubes + Data Preview recon + impl): 4-6h best / 7-12h safe combined
  (data-heavy + backend boundary complexity)
- Slice 3.11 (consolidation/polish/docs): 2-3h best / 3-5h safe
- **Expanded subtotal: 9-14h best / 15-25h safe**

### 7.3 Total scenarios

- **Scenario A (core only now):** 12.5-19h best / 20.5-31h safe, ~3-5 elapsed days
- **Scenario B (full current Flutter surface):** ~22-33h best / ~36-56h safe, ~5-9 elapsed days

Founder review load:
- Scenario A: ~1.5-2h best / ~2.5-3.5h safe
- Scenario B: ~2.5-3.5h best / ~4-5h safe

**Recommendation:** Plan on safe-planning numbers. Phase 1 actuals tracked 30-50%
above best-case due to review rounds — expect similar here.

---

## 8. Approvals

- [ ] Founder approves infrastructure choice (framework, ARB, provider pattern)
- [ ] Founder confirms Phase 3 scope boundary (core only vs all current routes)
- [ ] Founder resolves open decisions in Section 5
- [ ] Proceed to Slice 3.2a (infra foundation)

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
- `commonRetryVerb`
- `commonCancelVerb`
- `statusLoading`
- `statusFailed`
- `errorsUnknown`

This starter set is intentionally minimal and shell-focused; feature keys are scoped to recon slices.

## Appendix C — Shared-term reuse mapping (Phase 1 → Flutter ARB)

These terms were canonicalized in Phase 1 glossary and must be reused with identical RU
translations in Flutter ARB. Do NOT re-translate these in Phase 3 slices.

**Source-of-truth note:**
- `docs/i18n-glossary.md` is the single source of truth for canonical translations
- This Appendix C is a convenience mirror, kept for quick reference
- If the glossary and Appendix C disagree, **the glossary wins**
- When updating the glossary, the same PR must update Appendix C to match (both or neither)
- A sync-check item for this is in the i18n developer guide's slice checklist

| Phase 1 JSON key | Canonical RU | Flutter ARB key |
|---|---|---|
| `common.cancel.verb` | Отменить | `commonCancelVerb` |
| `common.save.verb` | Сохранить | `commonSaveVerb` |
| `common.delete.verb` | Удалить | `commonDeleteVerb` |
| `common.edit.verb` | Редактировать | `commonEditVerb` |
| `common.confirm.verb` | Подтвердить | `commonConfirmVerb` |
| `common.loading` | Загрузка... | `commonLoading` |
| `common.retry.verb` | Повторить | `commonRetryVerb` |
| `workflow.draft.status` | Черновик | `statusDraft` |
| `workflow.published.status` | Опубликовано | `statusPublished` |
| `workflow.exported.status` | Экспортировано | `statusExported` |
| `workflow.in_review.status` | На проверке | `statusInReview` |
| `workflow.approved.status` | Одобрено | `statusApproved` |
| — | Очередь брифов | `queueTitle` |
| — | Обновить очередь | `queueRefreshTooltip` |
| — | Не удалось загрузить очередь | `queueLoadError` |
| — | В очереди нет брифов.\nНажмите «Обновить», чтобы загрузить новые. | `queueEmptyState` |
| — | Отклонить | `queueRejectVerb` |
| — | Одобрить | `queueApproveVerb` |
| — | Задания | `navJobs` |

This table is seed; recon slices are expected to add to it when touching more shared
terms. Update this appendix in the same PR as the addition.
**Maintenance rule:** Every glossary update that touches a term listed in this appendix
must update this appendix in the same PR. Drift between glossary and Appendix C is
treated as a review-blocking defect.
## Appendix D — Backend error code mapping (Phase 3 scope)
Backend error codes are mapped to ARB keys in a single location:
`lib/l10n/backend_errors.dart`.

**Structure (illustrative; exact shape chosen in implementation slice):**

The mapping layer is a centralized lookup from backend `error_code` to a localized
renderer function. The renderer may return a plain string for simple cases or a
parameterized localized message for errors that carry context (e.g., `{briefId}`,
`{field}`).

Illustrative simple shape:

```dart
// Planning-only sketch. Exact type and signature chosen in implementation slice
// to accommodate parameterized messages, not bound to this shape.
Map<String, String Function(AppLocalizations)> backendErrorMessagesSimple = {
  'brief_not_found': (l) => l.errorBriefNotFound,
  'brief_locked': (l) => l.errorBriefLocked,
  'task_not_ready': (l) => l.errorTaskNotReady,
};
```

For parameterized error messages (e.g., `errorFieldInvalid(field)`), the real signature
will need to carry parameters through the lookup. The implementation slice (Slice 3.7 or
3.8) chooses the final type — may be a sealed class hierarchy, a function with dynamic
params, or a builder pattern. Do NOT commit to the simple map signature at planning time.

A unit test in `test/l10n/backend_errors_test.dart` verifies that every known backend
code has a mapping entry. This test is updated alongside backend contract changes.

**Where raw backend codes come from:** backend API documentation, OpenAPI schema, or
explicit code audit. Capture the list in Slice 3.7 recon (Preview/Graphics Config has
the highest surface for backend error visibility).

