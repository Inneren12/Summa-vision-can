# Phase 3 Slice 3.11 — Pre-Recon Part B (Analysis & Context)

> Read-only analysis consolidating parity, CI, retrospective scope, DEBT state,
> observations, deferred concerns, and audit trail. Prerequisites verified:
> A1 (26 579 B / 357 L), A2 (17 178 B / 180 L), A3 (18 065 B / 284 L) all
> present on disk.

## Section 7 — ARB parity current state

Python script from the task prompt executed verbatim against
`frontend/lib/l10n/app_en.arb` and `frontend/lib/l10n/app_ru.arb`. Full output:

```
=== Key count parity ===
EN keys: 82
RU keys: 82
Missing in RU: none
Missing in EN: none

=== Metadata count (EN only by convention) ===
EN @<key> entries: 82
RU @<key> entries: 0 (expected 0)

=== Placeholder parity ===
Mismatches: 0

=== Metadata declaration vs actual usage ===
Declared vs actual mismatches: 0
```

**Interpretation (factual).**
- **Key parity:** clean. 82 value keys in EN, 82 in RU, symmetric difference is empty — no orphan keys either direction.
- **Metadata convention:** holds. All 82 `@<key>` entries live in EN; RU carries zero `@<key>` entries (the `@@locale` directive is excluded by the script's `startswith('@@')` filter).
- **Placeholder parity:** clean. For every key present in both locales, the set of `{token}` placeholders matches 1-for-1. The 16 placeholder-bearing keys enumerated in A1 §2 have identical placeholder sets in EN and RU.
- **Declared vs actual placeholders:** clean. Every `@<key>.placeholders` map declared in `app_en.arb` matches the exact set of `{token}` substrings extracted from the corresponding EN value. No declared-but-unused and no used-but-undeclared tokens.

**Drift items found:** **zero across all four checked axes** (key set, metadata set, placeholder parity, metadata declaration vs usage).

## Section 8 — CI configuration inventory

`ls -la .github/workflows/` — directory exists, 4 YAML files present:

| File | Bytes | Trigger(s) | `flutter test` | `flutter analyze` | l10n / arb step |
|------|-----:|------------|:--------------:|:-----------------:|:---------------:|
| `backend.yml` | 3 748 | `push` + `pull_request` + `workflow_dispatch`, paths-scoped to `backend/**`, `DEBT.md`, `verify_debt.py` | no | no | no |
| `frontend-admin.yml` | 606 | `push` + `pull_request`, paths-scoped to `frontend/**` | **yes** (step `Run tests`: `flutter test` at L35–36) | no | no |
| `frontend-public.yml` | 685 | `push` + `pull_request`, paths-scoped to `frontend-public/**` | no (Node stack: `npm ci` + `npm run test`) | no | no |
| `smoke-test.yml` | 8 201 | `schedule` (cron `0 4 * * *` — daily 04:00 UTC) + `workflow_dispatch` | no (Docker compose smoke of backend stack) | no | no |

**Absent integrations.**
- No `flutter analyze` / `dart analyze` step anywhere.
- No l10n-specific step: no `flutter gen-l10n`, no ARB parity check, no placeholder-consistency check, no glossary check.
- No workflow on `workflows/*.yml` changes themselves (self-lint).

**Best insertion point observation (no prescription).** `frontend-admin.yml` is the only workflow that already checks out `frontend/`, installs Flutter, and runs `flutter pub get` — an ARB-parity step would fit between `Install dependencies` (L32–33) and `Run tests` (L35–36). A standalone parity script would still be runnable on its own without CI integration (founder-deferred per task framing).

## Section 9 — Phase 3 retrospective scope inventory

### 9.1 — Artifacts inventory

`find docs frontend/docs -name "phase-3-*" -o -name "*i18n*"` — 12 files:

| Path | Lines | Description (1-phrase) |
|------|-----:|------------------------|
| `docs/i18n-developer-guide.md` | 117 | Developer-facing i18n guide (categories, policies, worked examples) |
| `docs/i18n-glossary.md` | 428 | Bilingual EN↔RU term glossary (Phase 0 baseline, later patched) |
| `docs/i18n-recon-slice1-editor-core.md` | 85 | Slice 1 recon (editor-core i18n) |
| `docs/i18n-recon-slice2-inspector-validation.md` | 348 | Slice 2 recon (inspector + validation) |
| `docs/i18n-recon-slice3-block-editors.md` | 273 | Slice 3 recon (block editors, left panel, template meta) |
| `docs/i18n-recon-slice4-admin-shell.md` | 89 | Slice 4 recon (admin shell / frontend-public) |
| `docs/phase-3-slice-0-font-blocker-check.md` | 86 | Phase 3 Slice 0: Cyrillic font blocker investigation |
| `docs/phase-3-slice-3-recon.md` | 272 | Phase 3 Slice 3.3/3.4 recon (queue i18n) |
| `docs/phase-3-slice-11-pre-recon-part-a1.md` | 357 | Slice 3.11 Pre-Recon A1 — ARB catalog (this series) |
| `docs/phase-3-slice-11-pre-recon-part-a2.md` | 180 | Slice 3.11 Pre-Recon A2 — usage classification |
| `docs/phase-3-slice-11-pre-recon-part-a3.md` | 284 | Slice 3.11 Pre-Recon A3 — switcher + smokes + scripts |
| `frontend/docs/phase-3-plan.md` | 941 | Authoritative Phase 3 Flutter i18n plan (sections §3a–§3l, Appendix A–D) |

Two naming conventions are in play: the older `i18n-recon-sliceN-*.md` series (slices 1–4) lives under `docs/` and references the **frontend-public** React app; the newer `phase-3-*-recon.md` / `phase-3-slice-*.md` series covers the **Flutter admin** app's Phase 3 i18n work. No rename or merge between the two series is present in the tree.

Phase-3-plan total (941 L) dwarfs the recon docs and is the plan of record.

Note: `docs/phase-3-slice-5-recon.md`, `docs/phase-3-slice-7-recon.md`, and `docs/phase-3-slice-8-recon.md` are referenced by DEBT-030, DEBT-031, and `@editorChartTypeLabel` metadata respectively, but are **not present** in the current tree (referenced paths only; the `find` above returns no match for `slice-5`/`slice-7`/`slice-8`). This is flagged as an observation, not a defect.

### 9.2 — Commit history

`git log --oneline --all | grep -iE "phase 3|slice 3\.|i18n|localiz"` (head -60, most recent first):

```
a89b72a docs: Slice 3.11 Pre-Recon Part A3 — switcher + smokes + scripts
12839c0 docs: Slice 3.11 Pre-Recon Part A2 — ARB usage classification
4d165c7 docs: Slice 3.11 Pre-Recon Part A1 — ARB catalog inventory
8514214 i18n Phase 3 Slice 3.8 Fix Round 3: compile blocker + result hygiene
2594bed i18n Phase 3 Slice 3.8 Fix Round 2: stale errorCode leak across failed runs
0a6f315 i18n Phase 3 Slice 3.8 Fix Round 1: errorCode plumbing + assertion hygiene
8961668 Merge pull request #142 from Inneren12/claude/i18n-phase3-slice38-uqVgf
e2a32b5 i18n Phase 3 Slice 3.8: Preview + Graphics Config + backend error mapper
65e513c Fix offstage chart label assertions in editor localization test
7d3e552 Fix editor test localization assertions and import paths
e6409d2 Implement i18n slice 3.5+3.6 editor localization and tests
3687817 Set AppTheme.dark default in localized test pumps
af30a04 Fix queue/router test harness localization setup
45f5f92 Implement Slice 3.3+3.4 queue i18n and docs updates
d89b765 Merge pull request #137 from Inneren12/codex/add-flutter-i18n-infrastructure-foundation
9342436 Address i18n follow-up: real drawer test and l10n policy updates
b9dac88 Add Flutter i18n foundation with ARB-backed shell labels
2f1ac5c Merge pull request #136 from Inneren12/codex/produce-detailed-i18n-plan-for-flutter-app
7aba2de docs: apply final polish edits to phase 3 i18n plan
f8d5fb2 docs: apply targeted polish edits to phase 3 i18n plan
a41ee38 docs: add phase 3 flutter i18n planning document
3590379 Merge pull request #133 from Inneren12/codex/consolidate-i18n-infrastructure-and-close-slice-3-nits
ee8d3c0 Add Phase 3 Cyrillic font blocker investigation report
ea5bbbd Slice 5 follow-up: tighten lint/docs and RU i18n integration smoke
571fbd1 Phase 1 slice 5 i18n consolidation and safeguards
d5ff09a Refactor inspector i18n key resolution and localize RU variants
9cb4526 fix(slice3): update review labels and align tests with i18n keys
efe1866 fix(i18n): remove unsafe translator has() and unify status badges
dd6e708 feat(i18n): localize block editors, left panel, and template metadata
a8eb04f docs: add slice 4 admin shell i18n recon report
df02ea8 docs: add slice 3 i18n recon for block editors
a81a946 Finish Slice 2c test assertions for i18n key output
ddedf21 Update editor i18n tests to assert mocked translation keys
0e41139 Polish i18n mode labels and RU review terminology
a379772 i18n: apply slice 2a review fixes
082c119 i18n: localize Inspector and RightRail strings
389e47e docs: add slice 2 i18n recon for inspector and validation
f556a3a Update autosave test for i18n not-found banner key
d7be1a0 Update i18n-mocked test assertions for editor import messages
be9e875 Merge pull request #124 from Inneren12/codex/patch-i18n-glossary-with-review-fixes-x1as2t
34d3699 Merge pull request #123 from Inneren12/codex/patch-i18n-glossary-with-review-fixes
d0c822b docs: polish i18n glossary nav/status/render notes
8ed8cf4 docs: apply round-2 i18n glossary surgical fixes
b54b6ec docs: apply phase 0 i18n glossary structural fixes
bf7d9fc Rename PHASE0_BILINGUAL_GLOSSARY_EN_RU.md to docs/i18n-glossary.md
```

Counts:

| Metric | Value |
|--------|------:|
| Total commits matching `phase 3 \| slice 3. \| i18n \| localiz` (case-insensitive) | **45** |
| Merge-PR commits within the above set | **6** |
| Phase 3 Flutter-specific merges (PR #136, #137, #141, #142, #143) | **5** |
| Pre-Phase-3 `frontend-public` i18n merges (PR #123, #124, #133) | **3** (overlapping the 6-merge total through the grep) |

The 6 matching merge-PRs are: #123, #124, #133 (frontend-public i18n glossary/slice work) and #136, #137, #142 (Phase 3 plan + foundation + Slice 3.8). PR #141 (Slice 3.5/3.6 editor) and PR #143 (Slice 3.8 fix rounds) appear in the broader log but their exact merge-commit subject lines do not include `"i18n"`/`"phase 3"` tokens — they merge branches named `codex/implement-slices-3.5-and-3.6` and `claude/fix-error-code-plumbing-TwFBK` respectively.

### 9.3 — File migration count

`grep -rln "AppLocalizations" frontend/lib/ | grep -v "\.g\.dart\|\.freezed\.dart\|l10n/generated/" | sort -u`:

```
frontend/lib/core/app_bootstrap/app_bootstrap_provider.dart
frontend/lib/core/routing/app_drawer.dart
frontend/lib/core/shell/language_switcher.dart
frontend/lib/features/editor/domain/editor_notifier.dart
frontend/lib/features/editor/presentation/editor_screen.dart
frontend/lib/features/graphics/domain/chart_constants.dart
frontend/lib/features/graphics/presentation/chart_config_screen.dart
frontend/lib/features/graphics/presentation/data_upload_widget.dart
frontend/lib/features/graphics/presentation/editable_data_table.dart
frontend/lib/features/graphics/presentation/preview_screen.dart
frontend/lib/features/queue/presentation/queue_screen.dart
frontend/lib/l10n/backend_errors.dart
frontend/lib/main.dart
```

**Count: 13 files** reference `AppLocalizations` across core/shell/routing/bootstrap (4) + features (queue 1, editor 2, graphics 5) + l10n infra (1) + entrypoint (1).

### 9.4 — Prior retrospective precedent

`find docs -iname "retrospect*" -o -iname "phase-1*" -o -iname "phase-2*"` → **empty result**. Repo-wide `find -maxdepth 4 -iname "*phase-1*" -o -iname "*phase-2*" -o -iname "*retrospect*"` (excluding `.git`/`.dart_tool`/`build`/`node_modules`) also returns empty.

No Phase 1 or Phase 2 retrospective document exists in the repo. Slice 3.11 retrospective, when authored, has no in-tree template precedent.

### 9.5 — Retrospective content scope bullets

| Metric | Value | Source |
|--------|-------|--------|
| Phase 3 merged PRs | 5 (Flutter-specific: #136, #137, #141, #142, #143) | §9.2 |
| ARB keys added | 82 (82 EN + 82 RU, 1-for-1 parity) | A1 §2 |
| Source files migrated to `AppLocalizations` | 13 | §9.3 |
| Locale-switch smoke test files added | 4 (3 feature smokes + 1 shell/bootstrap smoke) | A3 §5.1 |
| Other l10n test files in `test/l10n/` | 2 (`backend_errors_test.dart`, `drawer_localization_test.dart`) | A3 §5.1 |
| Active DEBT entries sourced from Phase 3 | 3 (DEBT-029, DEBT-030, DEBT-031) | §10 |
| Resolved DEBT entries sourced from Phase 3 | 0 | §10 |

## Section 10 — DEBT.md Phase 3 related entries

`cat DEBT.md` (164 L). Three active entries are sourced from Phase 3 work; the remainder of the Active list (DEBT-027, DEBT-021) are sourced from Stage 4 autosave and Stage 2 upload work respectively (out of scope here).

### 10.1 — DEBT-029: Locale-aware bootstrap-error fallback in Flutter admin app

| Field | Value |
|-------|-------|
| Source | Phase 3 Slice 3.3+3.4 recon (`docs/phase-3-slice-3-recon.md` §6) |
| Added | 2026-04-23 |
| Severity | low |
| Category | code-quality |
| Status | accepted |
| Target | Opportunistic fix during future Flutter bootstrap refactor |
| Summary | `_BootstrapError` in `frontend/lib/main.dart` renders hardcoded EN (`App bootstrap failed: $error`) as a Category B diagnostic; RU operators see an untranslated message on rare bootstrap failure. Resolution path proposed: pre-localization fallback via `PlatformDispatcher.instance.locale` + tiny EN/RU map. |

### 10.2 — DEBT-030: Editor endpoints lack structured error codes

| Field | Value |
|-------|-------|
| Source | Phase 3 Slice 3.5+3.6 recon (`docs/phase-3-slice-5-recon.md` §5/§9) |
| Added | 2026-04-24 |
| Severity | medium |
| Category | architecture |
| Status | accepted |
| Target | Slice 3.7/3.8 backend-error mapping alignment PR (or earlier backend contract PR) |
| Summary | `PATCH /publications/{id}`, publish, unpublish endpoints do not emit stable `error_code` values; UI falls back to `editorActionError` generic wrapper with raw backend detail passthrough. Partial progress: `frontend/lib/l10n/backend_errors.dart` exists for the **7 Slice 3.8 error codes** (A2 §3.3) but the three editor-action endpoints listed here are not yet covered. Resolution path: introduce endpoint-level structured codes + extend the mapper. |

### 10.3 — DEBT-031: Unify generation phase enums across preview and chart config stacks

| Field | Value |
|-------|-------|
| Source | Phase 3 Slice 3.7 recon (`docs/phase-3-slice-7-recon.md` §4 Decision 4) |
| Added | 2026-04-24 |
| Severity | low |
| Category | code-quality |
| Status | accepted |
| Target | Opportunistic — during future graphics refactor or when chart config flow is re-architected for backend Phase 2 integration |
| Summary | Two parallel generation stacks: `domain/generation_notifier.dart` uses `GenerationPhase { idle, submitting, polling, completed, timeout, failed }`; `application/generation_state_notifier.dart` uses `{ idle, submitting, polling, success, failed, timeout }`. The `completed` vs `success` divergence caused duplicated phase→ARB-key switches in Slice 3.8. Changelog line dated 2026-04-24: errorCode plumbing in both notifier stacks completed in Slice 3.8 Fix Round 1; enum unification itself remains open. |

### 10.4 — Newer Phase-3-sourced DEBTs (DEBT-032+)

None. Scan of `DEBT.md` shows the active list currently runs DEBT-021, DEBT-027, DEBT-029, DEBT-030, DEBT-031. There is no DEBT-032 or higher.

### 10.5 — Resolved Phase-3-sourced DEBTs

None. All 22 entries in the `## Resolved` table trace to Stage 3 / Stage 4 autosave, Pre-deploy Hardening, Docs & Quality, Dead Code Cleanup, PR B-3, PR A-1, or upload PR — none name Phase 3 / i18n / Slice 3 as their resolution source.

## Section 11 — Observations / ambiguities

Factual observations surfaced by Parts A1–A3 + B §§7–10. Prescriptive language deliberately avoided.

1. **ARB parity is currently clean across all four machine-checkable axes** (key set, metadata set, placeholder parity, declared-vs-actual placeholders — §7). Slice 3.11 parity script would not find any drift to report against `HEAD = a89b72a`.
2. **CI runs `flutter test` on every `frontend/**` push/PR via `frontend-admin.yml`** (§8) but has no `flutter analyze`, no ARB parity step, and no l10n-specific step. Script execution in 3.11 is currently standalone-invocable; CI integration is a separate decision.
3. **LanguageSwitcher has no explicit accessibility annotations** — no `Semantics`, `semanticsLabel`, `Tooltip`, or `ExcludeSemantics`; no explicit keyboard focus handling (A3 §4.2). Default `TextButton` semantics carry the label.
4. **Locale-switch smoke test patterns are mixed** across 3 variance axes (router vs non-router `MaterialApp`; drawer vs `AppBar.actions` switcher mount; no shared `pumpLocalizedRouter` helper — A3 §5.3). All four files assert with hardcoded string literals, not `l10n.<key>` lookups.
5. **No cross-feature aggregator smoke exists** (A3 §5.4). `locale_switch_smoke_test.dart` is the closest, but stays on shell/drawer level.
6. **Three ARB keys are Dead** (A2 §3.4): `commonLoading`, `generationStatusSucceeded`, `editorActionError`. Each has explicit "reserved" documentation — not accidental dead code.
7. **The spec-hypothesised 5 `generationStatus*` indirect references do not exist** — A2 §3.6 confirmed those keys are Rendered directly from screen widgets (no phase→ARB-key mapper function), except `generationStatusSucceeded` which is Dead.
8. **DEBT-030 cross-slices with future Phase 2 backend work** (§10.2). The frontend mapper is present (`backend_errors.dart`, 7 Slice 3.8 codes), but three editor-action endpoints (`PATCH`/publish/unpublish) are unmapped — addressing DEBT-030 requires backend contract changes, not frontend-only work.
9. **DEBT-031 was partly advanced by Slice 3.8 Fix Round 1** (2026-04-24 changelog line on the entry) — the errorCode plumbing was unified across both notifier stacks, but the enum divergence (`completed` vs `success`) itself persists.
10. **No prior Phase 1 / Phase 2 retrospective template exists in-tree** (§9.4). A Slice 3.11 retrospective has no in-repo precedent to mirror.
11. **Three recon artifacts referenced by DEBT-030, DEBT-031, and `@editorChartTypeLabel` metadata are missing from the tree**: `docs/phase-3-slice-5-recon.md`, `docs/phase-3-slice-7-recon.md`, `docs/phase-3-slice-8-recon.md`. They are named as authoritative sources in DEBT entries and ARB comments but `find` returns no match for any of them.
12. **Two naming conventions coexist for i18n docs**: the older `docs/i18n-recon-slice{1..4}-*.md` series (frontend-public React) and the newer `docs/phase-3-*.md` series (Flutter admin). No consolidation is in progress.

## Section 12 — Deferred observations

### 12.1 — Phase 3b preview (non-migrated features)

Heuristic literal scan: `grep -rE "Text\('[A-Z]|hintText: '[A-Z]|labelText: '[A-Z]|tooltip: '[A-Z]"` over each feature, excluding codegen, is a **lower bound** (misses literals wrapped in `const`, inside child lists, inside `SnackBar(content: Text(...))`, string interpolation, etc.) but serves as a relative-magnitude signal.

| Feature dir | Lower-bound literal occurrences | Files (`.dart`, ex-codegen) |
|-------------|-------------------------------:|-----------------------------:|
| `frontend/lib/features/jobs` | ~9 | 9 |
| `frontend/lib/features/kpi` | ~3 | 8 |
| `frontend/lib/features/cubes` | ~12 | 6 |
| `frontend/lib/features/data_preview` | ~12 | 5 |
| **Subtotal (Phase 3b candidates)** | **~36** | **28** |

For contrast, the currently migrated features (queue, editor, graphics) yielded 82 ARB keys across 13 files (§9.3) and a substantially denser literal footprint — the ~36 here is likely an underestimate for `cubes` (which has table-column headers, filter chips, and search suggestions) and `data_preview` (dialog titles, validation messages).

### 12.2 — Cross-DEBT concerns

- **DEBT-030 ↔ DEBT-031 relation.** Both sit on the graphics/editor generation flow but at different layers: DEBT-030 is a **backend contract** gap (editor endpoints lack `error_code`); DEBT-031 is a **frontend state-machine** divergence (two parallel `GenerationPhase` enums). Slice 3.8 Fix Round 1 (commit `0a6f315`) advanced both — it wired `backend_errors.dart` (DEBT-030's frontend mapper half) and unified the errorCode plumbing in both notifier stacks (DEBT-031's changelog update) — but neither DEBT is closed.
- **Phase 2 backend coupling.** Both DEBT-030's resolution (adding `error_code` to admin_publications endpoints) and DEBT-031's resolution (refactor during "backend Phase 2 integration") are dependent on future backend work. The frontend can stage preparatory refactors (e.g., unify the two enums behind a feature flag) without a backend dependency for DEBT-031; DEBT-030's frontend half is already done.
- **`editorActionError` reserved key.** A2 §3.4 classified this key as Dead (runtime). Its ARB `@editorActionError.description` explicitly references DEBT-030 and reserves the key for a future code-based mapping. DEBT-030 resolution would transition this key from Dead to Rendered.

### 12.3 — Other deferred observations

- **A1 §2 gate-check estimate mismatch:** A1 expected ~84 total keys (~46 graphics); actual total is 82 (49 graphics under the 5-group definition, 50 counting `commonSaveVerb`). Per-locale parity is exact; the ~84 estimate was a spec rounding.
- **Two EN keys share a value by design** (A1 §2): `queueTitle`≡`navQueue` = "Brief Queue", and `editorErrorAppBarTitle`≡`editorNotFoundAppBarTitle` = "Editor". Both pairs carry explicit `@<key>.description` notes documenting the intentional split for future divergent tuning (per §3l migration rule).
- **Cross-screen rendered keys** (A2 §3.6): `editorChartTypeLabel` and `editorGenerateGraphicButton` (named for the editor) are rendered from both `editor_screen` and `chart_config_screen`. `previewDownloadSaved` / `previewDownloadFailed` (named for the preview) are rendered from both `preview_screen` and `chart_config_screen`. Naming intent on whether these names should generalize is not documented in the ARB metadata.
- **`commonLoading` Dead state** (A2 §3.4) is compatible with the pattern: AsyncValue-driven screens use `CircularProgressIndicator` directly and the Graphics stack uses `generationStatusSubmitting` / `generationStatusPolling` for its loading states. No hardcoded `"Loading..."` literal exists anywhere in `lib/`.
- **Scripts placement** (A3 §6.4): `scripts/` is PowerShell-only, `backend/scripts/` is Python-only; no `frontend/tool/` exists. Any parity-script placement is an unconstrained recon decision.

## Section 13 — Verification commands run

Chronological trace. Every factual claim in §§7–12 traces back to a command below.

| # | Command | Purpose |
|--:|---------|---------|
| 1 | `ls -la docs/phase-3-slice-11-pre-recon-part-a{1,2,3}.md` | §prereq — verify A1/A2/A3 on disk |
| 2 | `git rev-parse --short HEAD` + `git branch --show-current` | branch + HEAD hash for Summary |
| 3 | `python3 <<PYEOF ...PYEOF` (parity script from task prompt) | §7 — key/metadata/placeholder/declared parity |
| 4 | `ls -la .github/workflows/` | §8 — CI workflow presence |
| 5 | `find .github -type f -name '*.yml' -o -name '*.yaml'` | §8 — enumerate workflow files |
| 6 | `ls -la .gitlab-ci.yml .circleci/config.yml .buildkite` | §8 — rule out other CI providers |
| 7 | `Read .github/workflows/frontend-admin.yml` | §8 — Flutter CI details |
| 8 | `head -40 .github/workflows/backend.yml` | §8 — backend CI paths & triggers |
| 9 | `head -40 .github/workflows/frontend-public.yml` | §8 — Node CI details |
| 10 | `head -40 .github/workflows/smoke-test.yml` | §8 — smoke schedule |
| 11 | `find docs frontend/docs -name "phase-3-*" -o -name "*i18n*" \| sort` | §9.1 — artifact inventory |
| 12 | `wc -l` on artifacts from #11 | §9.1 — line counts |
| 13 | `git log --oneline --all \| grep -iE "phase 3\|slice 3\.\|i18n\|localiz" \| head -60` | §9.2 — commit history |
| 14 | `git log --oneline --all \| grep -iE … \| wc -l` (×2 for merge filter) | §9.2 — commit + merge counts |
| 15 | `grep -rln "AppLocalizations" frontend/lib/ \| grep -v "\.g\.dart\|\.freezed\.dart\|l10n/generated/" \| sort -u \| wc -l` | §9.3 — migrated file count |
| 16 | `find docs -iname "retrospect*" -o -iname "phase-1*" -o -iname "phase-2*"` + repo-wide `-maxdepth 4` equivalent | §9.4 — retrospective precedent check |
| 17 | `ls DEBT.md && wc -l DEBT.md` | §10 — verify DEBT.md presence |
| 18 | `Read DEBT.md` (full file, 164 L) | §10.1–10.5 — DEBT entries + resolved table |
| 19 | `for feat in jobs kpi cubes data_preview; do grep -rE … \| wc -l; find … \| wc -l; done` | §12.1 — Phase 3b preview counts |
| 20 | `ls -la` on docs/phase-3-slice-11-pre-recon-part-b.md between chunks | §13 audit — verify chunked write |

No source files were modified during any of the above. Only two artifacts were created in this task: this document and a git commit appending it (plus commits for A2, A3 earlier in the series).
