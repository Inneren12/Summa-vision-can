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
