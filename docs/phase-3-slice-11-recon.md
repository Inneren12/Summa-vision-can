# Phase 3 Slice 3.11 — Recon (Consolidation)

## §1 Overview

### Proposal
Proceed with a single implementation PR that executes five consolidation tracks: (1) ARB parity verification script, (2) dead-key documentation updates, (3) language-switcher accessibility polish, (4) aggregator cross-feature smoke test, and (5) Phase 3 retrospective doc, plus a minor DEBT registry cleanup track aligned to carryover items.

### Rationale (pre-recon evidence)
- The inventory/classification baseline is stable and complete: 82 ARB keys total with full EN↔RU parity and complete bucket classification, so consolidation can target quality guardrails rather than discovery work (A1 §2, A2 §3.5).
- Switcher accessibility gaps are concretely identified (no explicit Semantics/Tooltip/focus handling), making a bounded polish track feasible (A3 §4.2).
- Parity checks are currently clean but manual; formalizing repeatable verification is justified (B §7).
- Active DEBT items exist and include Phase-3 carryovers requiring registry hygiene/changelog updates during consolidation (B §10).

### Alternatives considered
1. **Defer all consolidation tracks to later slices.** Rejected because pre-recon already isolates actionable, low-risk follow-ups (A2 §3.4, A3 §4.2, A3 §5.4, B §10).
2. **Split into multiple PRs by track.** Rejected due to founder policy requiring single-PR delivery for Slice 3.11.

### Out of scope
- Any source-behavior migration beyond listed tracks.
- Backend contract changes for editor endpoint error codes (not part of this recon’s implementation slice) (B §10.2).

## §2 Track 1 — ARB parity verification script

### Proposal
Implement a local-only parity script in `backend/scripts/verify_arb_parity.py` (Python), documented for manual/local invocation, with CI integration explicitly deferred to a separate DEVOPS PR.

Suggested CLI signature:
- `--en <path>` (default `frontend/lib/l10n/app_en.arb`)
- `--ru <path>` (default `frontend/lib/l10n/app_ru.arb`)
- `--strict-metadata` (optional: fail if RU metadata appears unexpectedly)
- `--json` (machine-readable output for future CI reuse)

Exit codes:
- `0`: all checks pass
- `1`: parity drift found (user-fixable check failure)
- `2`: invocation/runtime error (missing file, invalid JSON, bad args)

Required checks (minimum set):
1. Key-set parity EN vs RU
2. Placeholder parity per key
3. Metadata declaration vs actual placeholder usage (EN metadata)
4. Count checks (value-key counts + metadata convention counts)

Documentation additions:
- Add usage + examples to `docs/i18n-developer-guide.md`
- Add a short mention in the Slice 3.11 retrospective doc as an infrastructure outcome
- Do **not** modify CI workflow files in this slice (founder-approved defer)

### Rationale (pre-recon evidence)
- `backend/scripts/` is already Python-only and already hosts cross-tree tooling (`export_schemas.py` used across backend/frontend boundaries), so a Python parity utility aligns with established runtime/tooling precedent (A3 §6.3, A3 §6.4).
- Root `scripts/` is PowerShell-centric; adding Python there introduces mixed-runtime semantics where none currently exist (A3 §6.2, A3 §6.4).
- There is currently no ARB parity CI step; local script first is policy-aligned and provides immediate guardrail value (B §7, B §8).

### Alternatives considered
1. **Place script under root `scripts/`.** Viable, but conflicts with current PowerShell-only convention and increases runtime heterogeneity there (A3 §6.2, A3 §6.4).
2. **Create new `frontend/tool/` location.** Viable long-term, but introduces new directory convention absent today and increases slice scope (A3 §6.4).
3. **Bash script instead of Python.** Simpler dependency footprint, but weaker JSON/placeholder handling ergonomics than Python for ARB validation logic.

### Out of scope
- CI wiring (`frontend-admin.yml`) and gating policy changes (deferred DEVOPS PR) (B §8).
- Any ARB content/value edits.

## §3 Track 2 — Dead keys documentation

### Proposal
Keep all three currently dead keys (zero deletions in this slice) and strengthen `@<key>.description` metadata to explicitly mark each as **reserved** with concrete reason/activation condition:
1. `commonLoading`: reserved common-shell fallback string; currently unused due to spinner/status-driven loading UX.
2. `generationStatusSucceeded`: reserved explicit success-status label for future UX variant that may show terminal success text before/alongside result view.
3. `editorActionError`: reserved pending structured endpoint error-code rollout; intended fallback wrapper once DEBT-030 path is resolved.

### Rationale (pre-recon evidence)
- Exactly three dead keys are confirmed with zero runtime references and documented intent; they are not accidental leftovers (A2 §3.4, B §11 #6).
- Founder policy for Q2 requires mixed strategy, and in this specific subset all three keys already have documented intent; deletion would discard planned semantics and churn translator context (A2 §3.4).

### Alternatives considered
1. **Delete dead keys immediately.** Rejected for these keys because each has explicit reserve intent and future-path linkage (A2 §3.4, B §10.2).
2. **Do nothing.** Rejected because reserved intent should be made unambiguous in metadata to avoid future “dead-code cleanup” misclassification.

### Out of scope
- Runtime code changes to activate these keys.
- Any additional dead-key sweep outside the three pre-recon-confirmed keys.
## §4 Track 3 — Language switcher polish

### Proposal
Apply accessibility-only improvements to `LanguageSwitcher` by adding explicit `Semantics` and `Tooltip` coverage around locale buttons/label, while keeping current visual layout and interaction model intact.

Planned scope:
- Add semantics labels/hints for English/Russian selection controls and current-state announcement.
- Add tooltips for discoverability on pointer/desktop contexts.
- Preserve existing segmented TextButton UI and selected-state styling.

Explicit exclusions:
- No visual redesign
- No flags/emoji/iconography
- No keyboard-shortcut feature work
- No focus-system rearchitecture in this slice

### Rationale (pre-recon evidence)
- Pre-recon identified zero explicit Semantics and zero Tooltip usage in switcher implementation; accessibility semantics currently rely on default TextButton labeling only (A3 §4.2, B §11 #3).
- This yields a bounded, low-risk polish track aligned with founder policy to scope switcher work from findings, not redesign assumptions.

### Alternatives considered
1. **Do nothing (accept default semantics).** Rejected because pre-recon explicitly surfaced accessibility annotation gaps (A3 §4.2).
2. **Broader UX refresh (icons/flags/layout changes).** Rejected as out-of-scope design work lacking evidence requirement in recon inputs.
3. **Include explicit focus-handling refactor now.** Deferred; pre-recon records absence but does not establish immediate defect severity requiring deeper control-level changes (A3 §4.2).

### Out of scope
- Any non-accessibility visual changes.
- Keyboard shortcut additions.
- Language-switcher placement/navigation changes.

## §5 Track 4 — Aggregator cross-feature smoke

### Proposal
Add one new cross-feature aggregator smoke test that navigates through queue → editor → graphics surfaces and validates locale switching continuity across these feature boundaries.

Proposed files:
- New test: `frontend/test/smoke/locale_switch_cross_feature_smoke_test.dart`
- Optional helper (only if needed): `frontend/test/smoke/helpers/locale_smoke_harness.dart`

Navigation/assertion intent:
- Start from shell route (drawer/shell locale toggle path)
- Enter queue view and validate localized queue marker text
- Move into editor path and validate localized editor marker text
- Continue into graphics/preview-config entry point and validate localized graphics marker text
- Switch locale at least once mid-flow and re-assert across already-visited + newly-visited screens

What it catches beyond per-feature smokes:
- Cross-screen locale propagation/regression when moving between independently localized feature trees
- Router/shell boundary issues not visible in isolated single-feature tests
- Shared key naming/rendering drifts that only surface during end-to-end feature transitions

### Rationale (pre-recon evidence)
- Existing smoke coverage is fragmented with mixed harness patterns and no dedicated cross-feature aggregator test (A3 §5.3, A3 §5.4, B §11 #4-#5).
- Founder policy explicitly keeps per-feature smokes and adds aggregator coverage rather than replacing current files.

### Alternatives considered
1. **Refactor existing four smoke files into one unified framework now.** Rejected for this slice to control scope; pre-recon already flags this as pattern debt suitable for separate cleanup (A3 §5.3).
2. **Skip aggregator and rely on current per-feature tests.** Rejected because cross-feature traversal gap is explicitly identified (A3 §5.4).

### Out of scope
- Refactoring existing 4 smoke files/harness architecture in this slice.
- Converting all assertions from literals to l10n-key-driven assertions.

## §6 Track 5 — Phase 3 retrospective doc

### Proposal
Create retrospective at `docs/phase-3-retrospective.md` capturing outcomes, metrics, debt posture, and follow-up recommendations from completed Phase 3 slices plus Slice 3.11 consolidation.

Proposed structure:
1. Context and scope
2. Timeline and merged PR summary
3. Quantitative outcomes (keys/tests/files migrated)
4. Quality and guardrails (parity, smoke strategy, switcher a11y)
5. Open debt and follow-ups
6. Lessons learned / next-phase recommendations

Data sources to embed/cite:
- Phase 3 counts/metrics from B §9.5 and B §9.2
- ARB totals from A1 §2
- Classification composition from A2 §3.5
- Active DEBT state from B §10

Handling B §11 observation #11 (missing recon artifacts):
- Acknowledge missing historical recon files explicitly.
- Reconstruct only from available in-repo evidence (DEBT entries, commit history, extant docs).
- Mark any non-reconstructable details as unknown rather than inferred.

### Rationale (pre-recon evidence)
- No Phase 1/2 retrospective precedent exists, so a clean structure must be defined now from available artifacts (B §9.4, B §11 #10).
- Missing referenced recon docs are a known factual gap; transparent treatment prevents silent historical assumptions (B §11 #11).

### Alternatives considered
1. **Skip retrospective due to missing historical recon docs.** Rejected; founder policy says retrospective is required.
2. **Recreate missing old recon docs within this slice.** Rejected as archival restoration scope creep; focus should remain on truthful retrospective synthesis from available evidence.

### Out of scope
- Backfilling/reauthoring historical missing recon documents as separate artifacts.
- Re-litigating prior slice decisions beyond documented evidence.

## §7 Minor — DEBT registry cleanup

### Proposal
Perform targeted DEBT registry hygiene as part of 3.11 implementation:
1. Add one new DEBT entry for deferred smoke harness harmonization (mixed patterns across locale smokes) as explicit carryover.
2. Update changelog lines for DEBT-029/030/031 to reflect 3.11 consolidation impacts/status checks without changing underlying acceptance intent.

### Rationale (pre-recon evidence)
- Mixed smoke-test patterns are confirmed and intentionally not fully refactored in this slice; formal carryover tracking avoids implicit debt drift (A3 §5.3, B §11 #4).
- Active Phase-3 DEBT set currently includes 029/030/031 with no resolved entries; changelog hygiene keeps debt narrative current (B §10, B §9.5).

### Alternatives considered
1. **No new DEBT entry; keep carryover implicit in recon prose.** Rejected because explicit registry tracking is more durable than doc-only mention.
2. **Attempt to close an existing DEBT in 3.11.** Rejected; pre-recon does not support closure criteria for 029/030/031 yet (B §10).

### Out of scope
- Resolving DEBT-030 backend contract dependencies.
- Resolving DEBT-031 enum unification in graphics stacks.
## §8 Impl scope summary

### Proposal (expected implementation-file footprint)
Planned 3.11 implementation file set (single PR):
1. `backend/scripts/verify_arb_parity.py` (new)
2. `docs/i18n-developer-guide.md` (update)
3. `frontend/lib/l10n/app_en.arb` (metadata description updates for 3 reserved keys)
4. `frontend/lib/widgets/language_switcher.dart` (a11y polish)
5. `frontend/test/smoke/locale_switch_cross_feature_smoke_test.dart` (new)
6. `frontend/test/smoke/helpers/locale_smoke_harness.dart` (new, only if needed)
7. `docs/phase-3-retrospective.md` (new)
8. `DEBT.md` (new carryover entry + 029/030/031 changelog updates)

Files explicitly **not** changed in 3.11 scope:
- RU ARB values (`frontend/lib/l10n/app_ru.arb`) unless a founder decision in §9 requires translated a11y label copy
- Existing per-feature locale smokes (`queue_locale_switch_smoke_test.dart`, `editor_locale_switch_smoke_test.dart`, `graphics_locale_switch_smoke_test.dart`, `locale_switch_smoke_test.dart`) beyond minimal integration touchpoints
- CI workflows (`.github/workflows/*.yml`) due deferred DEVOPS policy
- Backend endpoint implementations/contracts

Estimated tests added:
- 1 new aggregator smoke file
- Estimated 3–5 new test cases/assert blocks inside that file

Single-PR confirmation:
- All 3.11 implementation work remains in one PR per founder policy.

### Rationale (pre-recon evidence)
Scope reflects validated gaps only: no parity automation script yet (B §7, B §8), no switcher a11y annotations (A3 §4.2), no aggregator smoke (A3 §5.4), and active debt carryovers (B §10).

### Alternatives considered
1. **Broader modernization touching existing smoke files and CI workflows now.** Deferred to avoid violating policy and enlarging blast radius.
2. **Minimal doc-only implementation.** Rejected because several approved tracks require executable/test artifacts.

### Out of scope
- Multi-PR splitting.
- Comprehensive smoke harness refactor.

## §9 Ambiguities / founder questions

1. **Parity script placement confirmation**
   - Question: Should the ARB parity script land in `backend/scripts/` (Python precedent) or root `scripts/` (ops discoverability)?
   - Options:
     1. `backend/scripts/verify_arb_parity.py`
     2. `scripts/verify_arb_parity.py`
     3. `frontend/tool/verify_arb_parity.dart` (new convention)
   - Recommendation: **Option 1** — matches existing Python utility pattern and avoids introducing mixed-runtime conventions in root `scripts/` (A3 §6.2, A3 §6.4).

2. **Switcher accessibility copy localization path**
   - Question: For new tooltip/semantics phrases, should we introduce new ARB keys now or use existing visible labels only?
   - Options:
     1. Add dedicated ARB keys for tooltip/semantics strings in both locales
     2. Reuse existing `languageEnglish/languageRussian/languageLabel` text only (no new keys)
     3. Add English-only temporary semantics text (discouraged)
   - Recommendation: **Option 1** for long-term accessibility quality, but **Option 2** is acceptable if founder prioritizes strict no-new-translation overhead in 3.11 (A3 §4.2, A1 §2).

3. **Aggregator depth calibration**
   - Question: Should the aggregator smoke include full queue→editor→graphics chained navigation in one test flow, or run three shorter subflows in one file?
   - Options:
     1. Single long chained journey
     2. One file with 3 focused subtests sharing setup
     3. Minimal shell+one-feature aggregator only
   - Recommendation: **Option 2** — preserves cross-feature intent while reducing flake/debug complexity relative to one long chain (A3 §5.3, A3 §5.4).

4. **Retrospective handling of missing historical recon docs**
   - Question: In `phase-3-retrospective.md`, how should missing referenced recon artifacts be treated?
   - Options:
     1. Explicitly log missing docs and proceed with reconstructed evidence only
     2. Omit mention of missing docs and summarize available outcomes
     3. Block retrospective until missing docs are restored
   - Recommendation: **Option 1** — transparent and evidence-safe, while keeping founder-approved retrospective delivery on track (B §11 #11, B §9.4).

## §10 Acceptance gates

### Proposal
Implementation PR should pass all gates below before merge:

1. **Prereq artifacts still present:** all four pre-recon docs exist at expected paths.
2. **Parity script executable locally:**
   - Baseline run exits `0` against current EN/RU ARBs.
   - Negative check (intentional temporary mismatch in isolated fixture or dry-run test mode) returns exit `1`.
   - Invalid input path returns exit `2`.
3. **Analyzer/lint health:** `flutter analyze` for `frontend/` is clean (no new diagnostics introduced).
4. **Test health:** existing test suite remains green plus new aggregator smoke test passes.
5. **Switcher a11y verification:** widget tests or semantics checks confirm added tooltip/semantics labels render as intended.
6. **Dead-key metadata updates applied:** three reserved keys carry explicit rationale in EN metadata.
7. **Retrospective doc exists and includes required data blocks:** counts/classification/debt references aligned with pre-recon sections.
8. **DEBT registry updates complete:** new carryover DEBT entry present and 029/030/031 changelog lines updated.
9. **CI files untouched in this PR:** no `.github/workflows/*.yml` edits (DEVOPS defer policy).
10. **Single-PR scope adherence:** all 3.11 deliverables contained in one implementation PR.

### Rationale (pre-recon evidence)
These gates map directly to the validated gaps and policy constraints: parity automation absent from CI (B §8), switcher accessibility omissions (A3 §4.2), missing aggregator smoke (A3 §5.4), dead-key reserve status (A2 §3.4), and active DEBT carryovers (B §10).

### Alternatives considered
1. **Rely only on `flutter test` gate.** Rejected; does not validate parity script behavior or doc/debt deliverables.
2. **Include CI-integration gate now.** Rejected for this slice due explicit defer policy.

### Out of scope
- Enforcing new CI workflow policies in this PR.
