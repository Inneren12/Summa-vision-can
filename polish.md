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
