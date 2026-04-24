# Phase 3 Retrospective — Flutter Admin i18n

## 1. Context and scope

Phase 3 of the Flutter admin app i18n effort migrated operator-facing chrome
(Queue, Editor, Graphics config, Preview) to `AppLocalizations`-backed ARB
keys with EN/RU support. This document retrospects on the work merged
through Slice 3.11 Consolidation.

Phase 3b (Jobs, KPI, Cubes, Data Preview) is deferred pending operator
feedback on Phase 3 core.

## 2. Timeline and merged PRs

Phase 3 core was delivered across 5 merged PRs:

- PR #137 — Flutter i18n foundation (shell, bootstrap, locale switcher)
- PR #140 — Queue + shared shell i18n (Slice 3.3+3.4)
- PR #141 — Editor i18n (Slice 3.5+3.6)
- PR #142 — Preview + Graphics Config + backend_errors mapper (Slice 3.8)
- PR #143 — Slice 3.8 fix rounds (errorCode plumbing + stale-leak fix +
  compile fix)
- PR #&lt;TBD&gt; — Slice 3.11 Consolidation (this slice)

## 3. Quantitative outcomes

(Cite Part B §9.5 and Part A1 §2, A2 §3.5)

- **ARB keys added:** 82 total (82 EN + 82 RU, 1-for-1 parity)
  - Shell (Slice 3.2a/b): 11
  - Queue (Slice 3.3+3.4): 6
  - Editor (Slice 3.5+3.6): 15
  - Graphics (Slice 3.8): 50
- **Source files migrated to `AppLocalizations`:** 13
- **Test files added during Phase 3:**
  - Per-feature locale-switch smokes: 3 (queue, editor, graphics)
  - Denied-EN smokes: 3 (queue, editor, graphics)
  - `backend_errors_test.dart`: 1
  - Locale-switch + bootstrap smoke: 1 (`locale_switch_smoke_test.dart`)
  - Widget localization tests per feature screen
- **DEBT entries opened during Phase 3:** 3 (DEBT-029, DEBT-030, DEBT-031)
- **DEBT entries closed during Phase 3:** 0
- **New DEBT added in Slice 3.11:** 1 (DEBT-032 — locale smoke harness
  harmonization)

## 4. Quality and guardrails (introduced in Slice 3.11)

- **ARB parity script** (`scripts/arb_parity.py`): local-runnable verification
  of EN/RU key parity, placeholder parity, and metadata consistency.
  CI integration deferred to separate DEVOPS PR.
- **Dead keys policy:** 3 keys (`commonLoading`, `generationStatusSucceeded`,
  `editorActionError`) retained as explicitly reserved with clarified
  `@<key>.description` metadata. Zero deletions.
- **Language switcher accessibility:** `Semantics` + `Tooltip` annotations
  added without visual redesign or new ARB keys.
- **Aggregator smoke test:**
  `frontend/test/l10n/app_wide_locale_switch_smoke_test.dart` navigates
  Queue → Editor → ChartConfig in both locales.

## 5. Open debt and follow-ups

(Cite Part B §10)

- **DEBT-029** (low, accepted): bootstrap-error fallback in `main.dart` —
  opportunistic fix during future bootstrap refactor.
- **DEBT-030** (medium, accepted): backend admin_publications endpoints
  lack structured `error_code`. Frontend mapper half complete (Slice 3.8
  `backend_errors.dart` covers 7 job-level codes). Full resolution requires
  backend contract PR.
- **DEBT-031** (low, accepted): generation phase enum divergence
  (`completed` vs `success`) across preview/chart-config stacks. Partly
  advanced by Slice 3.8 Fix Round 1 errorCode plumbing. Opportunistic
  unification remaining.
- **DEBT-032** (low, new in 3.11): locale-switch smoke harness harmonization.
  Current 4 locale smokes + aggregator have inconsistent patterns (A3 §5.3).
  Opportunistic refactor target.

## 6. Missing historical recon artifacts

Per Part B §11 observation #11, three recon documents referenced by DEBT
entries and ARB metadata are not present in the tree:

- `docs/phase-3-slice-5-recon.md` (referenced by DEBT-030)
- `docs/phase-3-slice-7-recon.md` (referenced by DEBT-031)
- `docs/phase-3-slice-8-recon.md` (referenced by `@editorChartTypeLabel`)

These recon documents were produced in working branches during implementation
but were not committed as standalone artifacts (branches were squash-merged
with impl PRs). Their content is preserved in:

- Commit messages of the corresponding PRs
- DEBT entry summaries
- ARB `@<key>.description` metadata

This retrospective acknowledges the gap without attempting post-hoc
reconstruction. Future phases should adopt the pre-recon → recon → impl
three-commit pattern explicitly, with each artifact committed separately
before merge.

## 7. Lessons learned

### Test isolation can hide dead plumbing
Slice 3.8: `backend_errors.dart` mapper tested in isolation + widget tests
manually built state with `errorCode`, but `notifier._poll` never copied
`errorCode` from response. 285+ tests green, dead plumbing caught only in
GitHub Codex review. **Lesson:** for any mapper/transform code, require
pipeline integration test (mocked HTTP → notifier → state → UI), not just
unit+widget tests with synthetic state.

### Freezed `copyWith` bug with nullable fields
Slice 3.8 Fix Round 2: pattern `errorCode ?? this.errorCode` in freezed
`copyWith` preserves old value when new value is null. `CHART_EMPTY_DF`
leaked from first failure to second where backend omitted code, showed
wrong localized UI. **Lesson:** for terminal state transitions (failed,
timeout) with nullable error fields, use fresh constructor call, not
`copyWith`.

### Agent brace placement in nested test additions
Slice 3.8 Fix Round 3: agent placed new `test(...)` outside existing
`group(...)` block, left orphan `});` that terminated `void main()` early,
broke compilation (not caught by unit tests since file didn't compile).
**Lesson:** fix prompts with nested-block test additions must show full
before/after structural diagram with braces/indentation, not just diff
snippets.

### Flutter test finder rules
Accumulated across Phase 3:
- `findsAtLeastNWidgets(1)` for duplicate-value strings (e.g., `queueTitle`
  == `navQueue`)
- `skipOffstage: false` for finders reaching dropdowns or offscreen drawer
  content
- `find.textContaining` for Category D tokens in `Chip`s and badges

### Founder review catches architectural issues AI misses
Multiple specific examples in Phase 3:
- DEBT-030 backend error code architectural decision (founder decision in
  Slice 3.7/3.8)
- `chartConfigSizePresetLabel` RU amendment ("Формат публикации" vs proposed
  "Пресет размера") — more idiomatic operator-facing Russian
- `editor_screen_test.dart` hardcoded `'Brief #1'` / `'Brief not found'`
  assertions missed in two separate fix rounds before founder caught them
- Duplicate PR anti-pattern (two agents dispatched in parallel producing
  same PR twice) caught by founder before merge — now documented as
  workflow guard

### Duplicate PR anti-pattern
Slice 3.3+3.4: two agents dispatched same impl prompt in parallel (retry
after timeout + fresh dispatch); both completed, second merged with
conflicts against current HEAD. **Lesson:** check `gh pr list` or PRs tab
before re-dispatching after timeout. Close superseded PR without merge —
never attempt rebase of stale ARB baseline against current HEAD.

## 8. Next-phase recommendations

- **Phase 3b (Jobs/KPI/Cubes/DataPreview):** approximate lower-bound
  ~36 literals across 28 non-generated Dart files (per B §12.1).
  Likely 60-120 actual literals after proper scan. Gated on founder
  decision after Phase 3 operator feedback.
- **CI parity integration:** separate DEVOPS PR wiring
  `python3 scripts/arb_parity.py` into `.github/workflows/frontend-admin.yml`
  between "Install dependencies" and "Run tests" steps.
- **DEBT-032 smoke harness harmonization:** refactor 4 locale smokes +
  aggregator to shared `pumpLocalizedRouter` helper, switch hardcoded
  literal assertions to `l10n.<key>`-derived values.
- **DEBT-030 backend contract:** coordinate with Phase 2 backend work to
  introduce structured `error_code` on admin_publications endpoints,
  then extend `backend_errors.dart` mapper.
- **Phase 3 retrospective commit discipline:** pre-recon → recon → impl
  three-commit pattern with each artifact committed separately
  (not squash-merged) to preserve audit trail.

## 9. Appendices

### Appendix A — ARB parity script usage
See `docs/i18n-developer-guide.md` § Verification.

### Appendix B — Classification snapshot (post-3.11)
From Part A2 §3.5:
- Rendered: 66 keys
- Referenced-indirect (via mappers): 13 keys
  - 7 via `backend_errors.dart`
  - 6 via `BackgroundCategory.localizedLabel(l10n)`
- Dead (reserved with documented intent): 3 keys
