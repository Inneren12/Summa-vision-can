# Polish backlog

Append-only log of non-blocking polish items found during phase reviews
and bot comments. Items here are intentionally NOT blocking phase
closure — they ship in dedicated cosmetic PRs when batch is large
enough to justify a sprint slot.

**Conventions:**
- Items added top-to-bottom in chronological order
- Each item has: source phase, file paths, severity (P2/P3),
  category, description, fix sketch
- Status: `pending` (default), `in-batch-N` when scheduled,
  `done` when shipped
- Batch when ≥3 related items accumulate, OR when one becomes
  blocking due to context shift
- Cross-cutting items (i18n, a11y, doc-style) prioritized for
  same-batch grouping for review efficiency

---

## P2-001 — TopBar crop toggle: add `aria-pressed`

- **Source:** Phase 1.4 PR #167 review (post-fix-round-1)
- **Added:** 2026-04-26
- **Severity:** P2
- **Category:** accessibility
- **File:** `frontend-public/src/components/editor/components/TopBar.tsx`
- **Description:** The Crop button has only `aria-label`. Without
  `aria-pressed`, screen readers don't communicate the toggle's
  on/off state. Same gap likely applies to the DBG button (similar
  toggle pattern in same file).
- **Fix sketch:**
  ```tsx
  // Add to crop button:
  aria-pressed={cropZoneActive}

  // Same treatment for debug toggle (DBG button) for consistency:
  aria-pressed={debugEnabled}
  ```
- **Test addition:** widget test asserting `aria-pressed` reflects
  toggle state.
- **Status:** pending

---

## P3-001 — PreviewResponse field comment style

- **Source:** Phase 1.5 backend PR #168 review
- **Added:** 2026-04-26
- **Severity:** P3
- **Category:** code-quality
- **File:** `backend/src/schemas/transform.py`
- **Description:** `product_id` field has long inline comment;
  Pydantic convention prefers `Field(description=...)` for
  serialization-relevant docs.
- **Fix sketch:**
  ```python
  product_id: str | None = Field(
      default=None,
      description="StatCan product ID parsed from storage_key; null for non-StatCan paths.",
  )
  ```
- **Status:** pending

---

## P3-002 — Uppercase .PARQUET extension test for key parser

- **Source:** Phase 1.5 backend PR #168 review (optional)
- **Added:** 2026-04-26
- **Severity:** P3
- **Category:** test-coverage
- **File:** `backend/tests/services/statcan/test_key_parser.py`
- **Description:** Helper rejects `.csv` and other extensions;
  add explicit case for uppercase `.PARQUET`. Convention is
  lowercase, so this is defensive coverage.
- **Fix sketch:**
  ```python
  def test_uppercase_extension_returns_none(self) -> None:
      assert extract_product_id_from_storage_key(
          "statcan/processed/18-10-0004-01/2026-04-26.PARQUET"
      ) is None
  ```
- **Status:** pending

---

## P3-003 — Document `limit` query param on preview endpoint

- **Source:** Phase 1.5 backend PR #168 review
- **Added:** 2026-04-26
- **Severity:** P3
- **Category:** documentation
- **File:** `docs/api.md`
- **Description:** `GET /api/v1/admin/data/preview/{storage_key}` now
  documents response shape but query parameters (especially `limit`,
  default 100, max 500) aren't listed.
- **Fix sketch:** add a `**Query Parameters:**` table to the endpoint
  doc block:
  ```markdown
  | Param | Type | Default | Description |
  |-------|------|---------|-------------|
  | `limit` | `int` | 100 | Max rows returned. Range: 1–500. |
  ```
- **Status:** pending

---

## P3-004 — Tests must use `localizationsDelegates` for any localized UI

- **Source:** Phase 1.5 frontend fix round 2 (preventive)
- **Added:** 2026-04-26
- **Severity:** P3
- **Category:** test-infrastructure
- **File:** project-wide pattern
- **Description:** Several Phase 1.5 widget tests originally passed
  by accident: `AppLocalizations.of(context)?.X ?? 'EN fallback'`
  pattern in production code, paired with `MaterialApp` in tests
  WITHOUT `localizationsDelegates`. Result: `AppLocalizations.of(context)`
  returns null, UI shows hardcoded EN fallback, test asserts on the
  fallback string and passes — regardless of whether localization is
  actually wired. This was caught for diff banners during fix round 2.
  Same risk exists in any other widget test that uses MaterialApp
  without delegates AND tests localized strings. This is the third
  time this lesson has appeared (Slice 3.5, Slice 3.6, Phase 1.5).
- **Fix sketch:** sweep `frontend/test/` for `MaterialApp(...)`
  widget setup; verify each that renders localized text either:
  - Uses `pumpLocalizedRouter` / `pumpLocalizedWidget` helper
  - Includes `localizationsDelegates: AppLocalizations.localizationsDelegates`
    + `supportedLocales: AppLocalizations.supportedLocales`
  - Asserts via `final l10n = AppLocalizations.of(context)!;` then
    `expect(find.text(l10n.X), findsOneWidget)`, NOT against hardcoded EN
  Tests that fail this audit get fixed; production code with
  `?.l10n_key ?? 'fallback'` also gets the `??` removed.
- **Status:** pending

---

## P3-005 — Document Dart `const Set` with custom equality limitation

- **Source:** Phase 1.5 frontend fix round 2 (preventive)
- **Added:** 2026-04-26
- **Severity:** P3
- **Category:** documentation
- **File:** `docs/EDITOR_ARCHITECTURE.md` or new `docs/dart-gotchas.md`
- **Description:** Dart `const Set<T>{}` requires `T` to have
  primitive equality (`==` based on identity, not custom override).
  `DiffCellKey` in this PR uses field-based `==`/`hashCode` for
  Set deduplication — necessary for diff correctness, but means
  `const Set<DiffCellKey>{}` triggers compile-time error
  "does not have a primitive equality." This caused 3 test
  compilation errors in fix round 2.
- **Fix sketch:** add a short "Dart const collection gotchas"
  subsection somewhere visible (architecture doc or new gotchas
  doc). Mention:
  - `const Set` requires primitive equality on element type
  - Workaround: drop outer `const`, keep inner `const T(...)` if
    T's constructor is const: `<T>{const T(...)}` works
  - Alternative: use `final Set<T> X = {...}` for module-level
    constants
  - Custom-equality classes can still be used in non-const Sets
    without issue
- **Status:** pending

---

## P3-006 — Localize retry snackbar literals on /jobs and /exceptions

- **Source:** Phase 2.5 implementation, retry parity decision per Q-C.2.
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** i18n-tech-debt
- **Files:**
  - `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart` (existing debt, lines around 45-65)
  - `frontend/lib/features/exceptions/presentation/exceptions_screen.dart` (new, mirrors the same debt)
- **Description:** Retry-action snackbar messages on both screens are hard-coded English literals: `'Job retried (new job: $newJobId)'`, `'Job is not retryable'`, `'Retry failed: ${e.message}'`. The Phase 2.5 inbox inherits the literals byte-for-byte (Q-C.2 = parity, retry uses identical handler).
- **Fix sketch:** add 3 ARB keys (`jobRetrySuccess`, `jobRetryNotRetryable`, `jobRetryFailed` — name aligns with the existing `nav*`/feature-namespace conventions on screen) under both EN and RU; both screens consume from the same keys. Include `{newJobId}` ICU placeholder in `jobRetrySuccess` and `{error}` in `jobRetryFailed`.
- **Status:** pending

---

## P3-007 — LeftPanel.tsx long JSX line readability

- **Source:** Phase 2.1 PR#1 fix round 1 review (post-merge cosmetic note)
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** code-quality
- **File:** `frontend-public/src/components/editor/components/LeftPanel.tsx`
- **Description:** During PR#1 fix1 review the size-picker rendering
  block grew to a single long JSX line that's hard to read in a
  diff. The behavior is correct; only the line wrapping is a
  cosmetic readability issue. Reformatting is purely stylistic and
  does not change runtime behavior or test outcomes.
- **Fix sketch:**
  ```tsx
  // Wrap the EXPORTABLE_PRESET_IDS.map(...) block onto multi-line
  // JSX with one prop per line, e.g.:
  {EXPORTABLE_PRESET_IDS.map((pid) => (
    <option
      key={pid}
      value={pid}
    >
      {SIZES[pid].n}
    </option>
  ))}
  ```
- **Status:** pending

---

## P3-008 — Padding contract test name precision

- **Source:** Phase 2.1 PR#1 fix round 1 review
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** test-quality
- **File:** `frontend-public/tests/components/editor/export/renderToBlob.test.ts`
- **Description:** The test currently named `computeLongInfographicHeight
  padding contract` could be more precise about what it pins. The
  test verifies that the helper's height formula matches the
  `measureLayout` page-padding model in `engine.ts` (currently
  `2 × 64 × s` width-scaled top + bottom, no inter-section gap).
  A more explicit name surfaces this contract and makes future
  failures self-documenting.
- **Fix sketch:**
  ```ts
  // BEFORE
  describe('computeLongInfographicHeight padding contract', () => { ... });

  // AFTER
  describe('computeLongInfographicHeight pins formula against engine.ts measureLayout padding contract', () => { ... });
  ```
- **Status:** pending

---

## P3-009 — validateImportStrict regression test for unknown page.size

- **Source:** Phase 2.1 PR#2 fix round 1 review (residual risk note)
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** test-coverage
- **File:** `frontend-public/tests/components/editor/registry/guards.test.ts`
  (or wherever `validateImportStrict` regression tests live — verify
  with `grep -rn "validateImportStrict" frontend-public/tests/`)
- **Description:** PR#2 fix1 introduced a cast in
  `hydrateImportedDoc` (`size as CanonicalDocument["page"]["size"]`)
  to satisfy the tightened `PresetId` type. The architecture
  relies on `validateImportStrict` rejecting documents with
  unknown `page.size` values BEFORE hydration runs, so the cast
  never receives garbage at the consumer. This contract is
  documented in JSDoc on `hydrateImportedDoc` but not directly
  tested. Add a regression test that constructs a doc with an
  unknown `page.size` (e.g. `"not_a_real_preset"`) and asserts
  `validateImportStrict` rejects it before any hydration path
  reaches consumer code.
- **Fix sketch:**
  ```ts
  test('validateImportStrict rejects doc with unknown page.size before hydration', () => {
    const malformed = {
      schemaVersion: 3,
      templateId: 'test',
      page: { size: 'not_a_real_preset', /* ... */ },
      sections: [],
      blocks: {},
    };
    const result = validateImportStrict(malformed);
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ key: 'validation.page.unknown_size' }),
    );
  });
  ```
- **Status:** pending

---

## P3-010 — Move SizePreset interface to config/sizes.ts

- **Source:** Phase 2.1 PR#2 fix round 2 review (final approval, follow-up suggestion)
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** architectural
- **Files:**
  - `frontend-public/src/components/editor/config/sizes.ts` (add `SizePreset` interface declaration)
  - `frontend-public/src/components/editor/types.ts` (remove `SizePreset` declaration; optionally re-export from sizes.ts for back-compat with external consumers)
- **Description:** PR#2 fix2 closed the `presetIds.ts` ↔ `sizes.ts`
  type-only cycle by relocating `PresetId` adjacent to `SIZES`. A
  smaller residual cycle remains: `sizes.ts` imports `SizePreset`
  from `types.ts`, while `types.ts` imports `PresetId` from
  `sizes.ts`. Both imports are `import type` (no runtime coupling),
  so TypeScript and Next.js builds pass cleanly today. But the
  cycle becomes a real problem if the project enables strict
  `import/no-cycle` lint, adopts `madge`/`depcruise` for
  dependency-graph CI checks, or migrates to a build tool that
  enforces type-import cycles. Cleanest fix: declare `SizePreset`
  directly in `sizes.ts` adjacent to `SIZES` and `PresetId`
  (the same pattern that resolved the prior cycle in fix2).
- **Fix sketch:**
  ```ts
  // config/sizes.ts — add at top
  export interface SizePreset {
    readonly w: number;
    readonly h: number;
    readonly n: string;
  }

  export const SIZES = {
    instagram_1080: { w: 1080, h: 1080, n: "IG 1:1" },
    // ...
  } as const satisfies Record<string, SizePreset>;

  export type PresetId = keyof typeof SIZES;

  // types.ts — option A: delete the old SizePreset declaration
  // types.ts — option B: re-export for back-compat with external consumers
  export type { SizePreset, PresetId } from './config/sizes';
  ```
- **Verification:** `madge --circular frontend-public/src/components/editor/`
  (or equivalent) should not flag `sizes.ts ↔ types.ts`. Existing
  typecheck must still pass — `SizePreset` interface shape
  unchanged, only declaration site moves.
- **Status:** pending

---

## P3-011 — EXPORTABLE_PRESET_IDS comment naming clarity

- **Source:** Phase 2.1 PR#1 fix round 1 review (continued through PR#2 fix1, partially closed by PR#3)
- **Added:** 2026-04-27
- **Severity:** P3
- **Category:** documentation
- **File:** `frontend-public/src/components/editor/config/sizes.ts`
- **Description:** The JSDoc on `EXPORTABLE_PRESET_IDS` evolved
  across PR#1 / PR#2 fix1 / PR#3 to describe its scope as the
  "legacy single-PNG export size picker". By the end of PR#3 the
  list now contains all 7 presets (long_infographic was added once
  the ZIP flow could handle the cap-exceeded case), which makes
  the "legacy" qualifier potentially misleading — the constant is
  still used by the size picker, but it's no longer scoped down.
  This is a wording-only refresh of the comment to clarify that
  the constant is the **complete current size-picker scope**, not
  a deliberately-restricted subset, and that the Inspector
  "Export presets" list reads `Object.keys(SIZES)` separately.
  (The Inspector vs. size-picker distinction stays the same;
  only the comment is reworded.)
- **Fix sketch:**
  ```ts
  /**
   * Preset IDs exposed in the editor size picker dropdown
   * (single-PNG export flow).
   *
   * As of Phase 2.1 PR#3 this list contains all 7 presets in
   * SIZES. The Inspector "Export presets" list reads
   * `Object.keys(SIZES)` directly and is a distinct surface
   * — those two lists serve different UX purposes (size picker
   * = active canvas selector; export presets = ZIP opt-in set)
   * and should not be conflated.
   */
  export const EXPORTABLE_PRESET_IDS = [
    "instagram_1080",
    "instagram_portrait",
    "twitter_landscape",
    "reddit_standard",
    "linkedin_landscape",
    "instagram_story",
    "long_infographic",
  ] as const;
  ```
- **Status:** pending

---

## Batch dispatch policy

When 3+ items accumulate in same category, OR 5+ items total:
1. Pick a sprint slot (~1 hour total work)
2. Write a single cosmetic PR prompt covering all batched items
3. Whitelist: union of all items' files
4. Single commit, single PR
5. Mark items `in-batch-N` then `done` after merge

Current batch candidates:
- **Backend cosmetics batch (1.5)**: P3-001, P3-002, P3-003 — all
  in `backend/` and `docs/`, ~30 minutes total
- **A11y batch**: needs more items before justifying batch (P2-001
  alone is too small to dispatch standalone unless it becomes
  blocking)
- **Phase 2.1 frontend batch**: P3-007, P3-008, P3-009, P3-010, P3-011
  — all in `frontend-public/`, mix of code/test/doc cosmetics,
  ~45 minutes total. P3-010 (architectural cycle break) is the
  most substantive; the rest are wording/test-name/format polish.
