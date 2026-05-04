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

## P3-012 — Layer dependency: validation imports from export

- **Source:** Phase 2.1 PR#4 fix1 review (founder)
- **Added:** 2026-04-28
- **Severity:** P3
- **Category:** architecture
- **File:** `frontend-public/src/components/editor/validation/validate.ts`
  + `frontend-public/src/components/editor/export/renderToBlob.ts`
- **Description:** PR#4 added `import { computeLongInfographicHeight,
  LONG_INFOGRAPHIC_HEIGHT_CAP } from '../export/renderToBlob'` in
  `validate.ts`. Functionally fine because `renderToBlob.ts` exports
  these as pure helpers with no DOM/canvas side-effects on module
  load. But by layering, `validation` should not depend on `export`
  — both should depend on a lower neutral layer.
- **Fix sketch:** extract the cap-height helper + constant into a
  new file like `renderer/longInfographicMeasure.ts` (or
  `validation/sizeRules.ts`). Both `renderToBlob.ts` and
  `validate.ts` then import from the neutral module. Pure code
  move; no behavior change. The PR#4 fix1 parity test still passes
  unchanged because the function reference resolves to the same
  implementation.
- **Status:** pending

---

## P3-013 — RU label `OK · ПРЕД` reads technical for end users

- **Source:** Phase 2.1 PR#4 review (founder)
- **Added:** 2026-04-28
- **Severity:** P3
- **Category:** i18n
- **File:** `frontend-public/messages/ru.json`
- **Description:** `inspector.export_presets.qa_status.ok_with_warnings`
  is currently `"OK · ПРЕД"` (abbreviation of "предупреждения"). The
  abbreviation is non-standard in Russian UI conventions and reads
  as overly technical. EN equivalent is `"OK · WARN"` which is also
  abbreviated but `WARN` is widely recognized in technical UIs;
  `ПРЕД` is not.
- **Fix sketch:** consider one of:
  - `"OK · ВНИМ"` (abbreviation of "внимание") — closer to
    EN "WARN" register
  - `"WARN"` alone (matches EN, no translation overhead — many
    badges-as-status patterns keep English token in RU UIs)
  - Leave as-is if explicit founder preference for full RU
- **Status:** pending

---

## P2-002 — Replace MagicMock with SimpleNamespace in lineage helper tests

- **Source:** Phase 2.2.0 Chunk 3b PR #229 review
- **Added:** 2026-04-29
- **Severity:** P2
- **Category:** test-quality
- **File:** `backend/tests/services/publications/test_lineage.py`
- **Description:** Tests for `derive_clone_lineage_key` use `MagicMock`
  to fake a Publication source object. `MagicMock` can hide attribute
  errors and type mismatches — if `derive_clone_lineage_key` accesses
  `source.foo` and `foo` isn't set, MagicMock returns a new mock
  instead of raising AttributeError. `SimpleNamespace` is more honest:
  raises AttributeError on missing attrs, no method call recording
  surface area.
- **Fix sketch:**
  ```python
  from types import SimpleNamespace

  source = SimpleNamespace(
      lineage_key="01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c",
      id=42,
  )
  result = derive_clone_lineage_key(source)
  assert result == source.lineage_key
  ```
- **Affected tests:** `test_derive_clone_lineage_key_returns_source_value_verbatim`,
  `test_derive_clone_lineage_key_raises_on_null_source_key`,
  `test_derive_clone_lineage_key_is_pure_no_io_required` (3 tests)
- **Status:** pending

---

## P2-003 — Fixed container_name on db service limits compose project isolation

- **Source:** Phase 2.2.0 docker-compose production-defaults PR review
- **Added:** 2026-04-29
- **Severity:** P2
- **Category:** infra-quality
- **File:** `docker-compose.yml`
- **Description:** `container_name: summa-db` was added so the backup
  script can predict the container name across `docker compose down/up`
  cycles. Trade-off: fixed names break compose project isolation —
  running multiple instances of the same compose project (e.g. parallel
  CI jobs, dev + staging on same host) collides on the container name
  and one fails to start.
- **Founder note:** decision was deliberate — single VPS deployment +
  predictable backup targeting was prioritized over multi-tenancy. This
  item exists to flag the trade-off if multi-tenant becomes relevant.
- **Fix sketch (deferred):** if multi-tenant ever needed, drop
  `container_name` and switch backup script to discover the container
  via:
  ```bash
  CONTAINER_ID=$(docker compose ps -q db)
  docker exec "$CONTAINER_ID" pg_dump ...
  ```
- **Status:** pending — defer until multi-tenant requirement surfaces
- **Note:** unlike most polish items, this is a known trade-off rather
  than a code defect. Documented for future reconsideration, not
  immediate fix.

---

## P3-014 — Bump time.sleep margin in UUID v7 sortability test

- **Source:** Phase 2.2.0 Chunk 3b PR #229 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** test-stability
- **File:** `backend/tests/services/publications/test_lineage.py`
- **Description:** `test_generate_lineage_key_is_time_sortable` uses
  `time.sleep(0.002)` between UUID generations. On loaded CI / Windows
  with coarse timer resolution, 2ms can rarely produce same-millisecond
  UUIDs causing flaky sort assertion. 5ms is comfortably above all
  observed timer resolutions and adds only +30ms total test runtime.
- **Fix sketch:**
  ```python
  for _ in range(10):
      results.append(generate_lineage_key())
      time.sleep(0.005)  # was 0.002
  ```
- **Status:** pending
- **Trigger to escalate:** any flake observation in CI or local runs.
  Until then, P3.

---

## P3-015 — Extract FIXTURE_UUID_V7 constant for repeated UUID literal

- **Source:** Phase 2.2.0 Chunk 3b PR #229 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** code-quality
- **File:** `backend/tests/services/publications/test_lineage.py`
- **Description:** UUID literal `"01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c"`
  appears in 3 different test bodies. Extract to module-level constant
  `FIXTURE_UUID_V7` near `UUID_V7_REGEX` for DRY.
- **Fix sketch:**
  ```python
  # Top of file, near UUID_V7_REGEX
  FIXTURE_UUID_V7 = "01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c"

  # In test bodies
  source = SimpleNamespace(lineage_key=FIXTURE_UUID_V7, id=42)
  ```
- **Status:** pending
- **Note:** combine with P2-002 in same batch — both touch identical
  test functions.

---

## P3-016 — Strengthen UUID v7 format test with stdlib parse + version check

- **Source:** Phase 2.2.0 Chunk 3b PR #229 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** test-coverage
- **File:** `backend/tests/services/publications/test_lineage.py`
- **Description:** `test_generate_lineage_key_returns_canonical_uuid_v7_format`
  uses regex match. While the regex enforces shape correctly, adding a
  `uuid.UUID(result)` parse + `parsed.version == 7` check provides a
  second independent assertion using stdlib semantics. Defense in depth.
- **Fix sketch:**
  ```python
  from uuid import UUID

  parsed = UUID(result)
  assert str(parsed) == result
  assert parsed.version == 7
  ```
- **Status:** pending

---

## P3-017 — Consolidate per-test asyncio decorators to module-level pytestmark

- **Source:** Phase 2.2.0 Chunk 3c PR #230 fix round 2 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** code-quality
- **File:** `backend/tests/integration/migrations/test_lineage_key_backfill.py`
- **Description:** All 5 tests are decorated with `@pytest.mark.asyncio`
  individually. Module-level `pytestmark = [pytest.mark.integration,
  pytest.mark.asyncio]` would consolidate to one line. Current
  per-test pattern was chosen explicitly during fix round 2 to satisfy
  acceptance criteria literally; consolidation is a stylistic
  improvement only.
- **Fix sketch:**
  ```python
  # Replace these two:
  pytestmark = pytest.mark.integration

  @pytest.mark.asyncio
  async def test_X(...): ...

  # With this:
  pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

  async def test_X(...): ...
  ```
- **Status:** pending
- **Note:** purely cosmetic. Don't ship in same batch as functional
  fixes — could mask intent during review.

---

## P3-018 — Alembic error message matching in conftest is brittle

- **Source:** Phase 2.2.0 Chunk 3c PR #230 fix round 2 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** test-stability
- **File:** `backend/tests/integration/migrations/conftest.py`
- **Description:** The narrow `except RuntimeError` blocks check error
  text via substring matching: `"can't locate revision"`, `"no such
  table"`, `"alembic_version" + "does not exist"`. Alembic upstream
  could change error wording, breaking these checks silently. Acceptable
  for fixture code, but brittle if Alembic version is upgraded.
- **Fix sketch:** consider catching specific exception types if Alembic
  exposes them:
  ```python
  from alembic.util.exc import CommandError
  # Or check error code attribute if available
  ```
  Investigate whether Alembic provides typed exceptions for these cases.
  If yes, switch to type-based checks. If no, keep current approach.
- **Status:** pending
- **Trigger to escalate:** observed test failure after Alembic version
  bump.

---

## P3-019 — Quote style drift (single vs double) in clone endpoint tests

- **Source:** Phase 2.2.0 Chunk 3c PR #230 round 3 review
- **Added:** 2026-04-29
- **Severity:** P3
- **Category:** code-quality
- **File:** `backend/tests/api/test_clone_publication_endpoint.py`
- **Description:** New tests added in Chunk 3c use single quotes
  (`'lineage_key'`) while file's pre-existing convention is double
  quotes. `black` would normalize but the project's CI runs
  `black --check` with `|| true` so drift can land.
- **Fix sketch:** run `black backend/tests/api/test_clone_publication_endpoint.py`
  to normalize quotes consistently. Verify `git diff` only shows quote
  changes, not logic.
- **Status:** pending
- **Note:** can be batched with any other code-quality nits; single
  black run resolves.

---

## P3-020 — `parse_ref_period_to_date` function naming is generic

- **Source:** Phase 3.1aaa impl reviewer round 2026-05-03
- **Added:** 2026-05-03
- **Severity:** P3
- **Category:** architecture
- **File:** `backend/migrations/versions/478d906c6410_add_semantic_value_cache.py`
- **Description:** PL/pgSQL function name does not scope to its
  semantic-value-cache use. A future migration creating a similar parser
  with different format support would collide on this name.
- **Fix sketch:** rename to `parse_semantic_value_ref_period_to_date`
  in the migration + matching `Computed()` expression in the ORM.
  Requires migration revision bump (rename function + drop old one in
  upgrade), so park until next 3.1 polish PR.
- **Status:** pending
- **Note:** tracked under DEBT-061 sub-item 1 — do NOT close that DEBT
  entry until this polish item ships.

---

## P3-021 — Verify PG integration tests actually exercise generated column

- **Source:** Phase 3.1aaa impl reviewer round 2026-05-03
- **Added:** 2026-05-03
- **Severity:** P3
- **Category:** test-coverage
- **File:** `backend/tests/integration/test_semantic_value_cache_migration.py`
- **Description:** Integration tests skip on non-PostgreSQL via
  `Base.metadata.create_all` fallback. Unclear whether all assertions
  exercising GENERATED `period_start`, partial `is_stale` index, and
  FK CASCADE actually run against PG in CI vs falling through to
  SQLite no-op paths.
- **Fix sketch:** add a CI-gated assertion at module level —
  ```python
  pytestmark = pytest.mark.skipif(
      os.getenv("TEST_DATABASE_URL") is None,
      reason="PG-only integration tests",
  )
  ```
  Then verify the GitHub Actions matrix sets `TEST_DATABASE_URL` for
  the relevant job. Confirm via single failing run if `TEST_DATABASE_URL`
  is unset.
- **Status:** pending
- **Note:** tracked under DEBT-061 sub-item 2.

---

## P3-022 — Pin source_hash timestamp exclusion as explicit test

- **Source:** Phase 3.1aaa impl reviewer round 2026-05-03
- **Added:** 2026-05-03
- **Severity:** P3
- **Category:** test-coverage
- **File:** `backend/tests/services/statcan/test_value_cache_hash.py`
- **Description:** `compute_source_hash` excludes `fetched_at`,
  `release_time`, `created_at`, `updated_at` by contract (recon §C6).
  Existing tests cover field changes individually but no test asserts
  the timestamp-exclusion invariant directly.
- **Fix sketch:**
  ```python
  def test_source_hash_excludes_timestamps():
      """fetched_at / release_time / created_at / updated_at are NOT inputs."""
      base = _kwargs(value=Decimal("100.0"))
      h1 = compute_source_hash(**base)
      h2 = compute_source_hash(**base)  # identical inputs at different
                                         # call times must produce
                                         # identical hashes
      assert h1 == h2
      # Sanity: hash function does not accept timestamp kwargs at all
      import inspect
      sig = inspect.signature(compute_source_hash)
      timestamp_params = {p for p in sig.parameters if "_at" in p or "_time" in p}
      assert not timestamp_params, f"Unexpected timestamp params: {timestamp_params}"
  ```
- **Status:** pending
- **Note:** tracked under DEBT-061 sub-item 3.

---

## P3-023 — Pin StatCanDataPoint.value Decimal parsing branches

- **Source:** Phase 3.1aaa impl reviewer round 2026-05-03
- **Added:** 2026-05-03
- **Severity:** P3
- **Category:** test-coverage
- **File:** `backend/tests/services/statcan/test_value_cache_schemas.py`
  (new file or appended to existing schema tests)
- **Description:** WDS serializes `value` as string (`"165.7"`) for
  numeric data and `null` paired with `missing=true`. Pydantic V2's
  `Decimal` coercion handles both, but the contract is not pinned by
  test. A future Pydantic upgrade or schema config change could
  silently break parsing.
- **Fix sketch:**
  ```python
  def test_string_numeric_value_parses_to_decimal():
      dp = StatCanDataPoint.model_validate({
          "refPer": "2026-04",
          "value": "165.7",   # string, not float
          "decimals": 1,
          "scalarFactorCode": 0,
          "symbolCode": 0,
          "securityLevelCode": 0,
          "statusCode": 0,
          "frequencyCode": 6,
          "missing": False,
      })
      assert dp.value == Decimal("165.7")
      assert isinstance(dp.value, Decimal)

  def test_null_value_with_missing_flag():
      dp = StatCanDataPoint.model_validate({
          "refPer": "2026-04",
          "value": None,
          "decimals": 0,
          "scalarFactorCode": 0,
          "symbolCode": 0,
          "securityLevelCode": 0,
          "statusCode": 0,
          "frequencyCode": 6,
          "missing": True,
      })
      assert dp.value is None
      assert dp.missing is True
  ```
- **Status:** pending
- **Note:** tracked under DEBT-061 sub-item 4.

---

## P3-024 — Prime-on-refresh path for active mappings without cached coord

- **Source:** Phase 3.1aaa impl FIX-R2 (Blocker 2 collateral)
- **Added:** 2026-05-03
- **Severity:** P2
- **Category:** correctness
- **File:** `backend/src/services/statcan/value_cache.py`
- **Description:** `refresh_all` skips mappings whose value cache is
  empty (no cached coord to drive WDS request). Such mappings stay
  uncached until first resolve OR next manual mapping save. The
  best-effort retry contract should cover this case.
- **Fix sketch:** for `coord=None` rows in the refresh fan-out:
  ```python
  for cube_id, semantic_key, coord, product_id in keys:
      if coord is None:
          # Re-derive coord from latest mapping config + cached metadata
          mapping = await mapping_repo.get_by_key(cube_id, semantic_key)
          cache_entry = await metadata_cache.get_cached(cube_id)
          if mapping is None or cache_entry is None:
              continue  # skip — DEBT-062 normal path
          validation_result = validate_mapping_against_cache(
              mapping_config=mapping.config,
              cache_entry=cache_entry,
          )
          if not validation_result.valid:
              continue  # mapping became invalid; nightly is not
                        # the right place to flag this
          coord = derive_coord(validation_result.resolved_filters)
          # then proceed with normal refresh path
  ```
  Add unit test: `test_refresh_all_primes_uncached_active_mapping`.
- **Status:** pending
- **Note:** Phase 3.1c will likely consume this code path (resolve
  service triggers prime on first access). Coordinate with 3.1c work
  to avoid duplicate logic. Tracked under DEBT-062.

---

## P3-025 — Phase 3.1b reviewer P2/P3 cluster (3 items)

- **Source:** Phase 3.1b PR #274 reviewer round 2026-04-30
- **Added:** 2026-05-03 (logged from memory after 3.1aaa cycle)
- **Severity:** P2 (mixed — narrowest item is P3)
- **Category:** mixed (correctness + UX consistency)
- **Files:**
  - `backend/src/api/admin/semantic_mappings.py`
  - `backend/src/repositories/semantic_mapping_repository.py`
  - `flutter_admin/lib/features/semantic_mappings/data/admin_repository.dart`
- **Description:** 3 distinct items deferred from 3.1b merge:
  1. **IntegrityError narrow path** — current handler catches generic
     `IntegrityError` and surfaces as `MAPPING_CONFLICT`. Should narrow
     to specific constraint name (`uq_semantic_mappings_cube_key`) to
     distinguish from FK / unique violations on other tables.
  2. **If-Match-on-missing semantics** — request with `If-Match: <etag>`
     against a non-existent mapping currently returns 404. Spec
     ambiguity: should it be 412 Precondition Failed (preserves
     resource-version contract) OR 404 (resource lookup convention)?
     Founder pinned 404 in 3.1b but reviewer P3 noted RFC 7232
     leaves room for either.
  3. **Flutter dual auth** — Flutter admin sends auth as both header
     (`X-API-KEY`) AND body (`api_key`). Backend accepts either. Reviewer
     P3 flagged the body path as defense-in-depth that may obscure
     CSRF surface. Drop body path; header-only.
- **Fix sketch:**
  - Item 1: `except IntegrityError as exc: if "uq_semantic_mappings_cube_key" in str(exc.orig): raise MappingConflictError(...) else: raise`
  - Item 2: revisit if 3.1c resolve surfaces user-visible
    `If-Match` flow; document as 404 explicitly in `BACKEND_API_INVENTORY.md`
    if no change needed
  - Item 3: remove `api_key` body field from Flutter admin requests +
    Pydantic schemas; verify Postman / curl flows still work header-only
- **Status:** pending
- **Note:** tracked under DEBT-057. Combine with P3-026 (3.1ab carryovers)
  if same polish PR.

---

## P3-026 — Phase 3.1ab validator P2/P3 cluster (3 items)

- **Source:** Phase 3.1ab impl reviewer round (carried through 3.1b/3.1aaa)
- **Added:** 2026-05-03
- **Severity:** P2 / P3 mixed
- **Category:** code-quality + test-coverage
- **Files:** `backend/src/services/semantic_mappings/validation.py`
- **Description:** 3 items deferred from 3.1ab merge:
  1. **isinstance guards in pure validator** — config payload comes
     from JSON; defensive `isinstance(filters, dict)` checks before
     `.items()` would prevent surprising `AttributeError` on
     malformed input. Currently relies on Pydantic schema validation
     upstream.
  2. **Non-null guard for resolved IDs** — when validator produces
     `ResolvedDimensionFilter(dimension_position_id=None, member_id=None)`
     for unresolved filters, downstream `derive_coord` will raise
     `ValueError`. Add explicit non-null guard at the end of validation
     so the failure mode is `ValidationResult.valid=False` instead of
     `ValueError` surfacing later in coord derivation.
  3. **`CubeNotInCacheError` default code** — error class doesn't set
     `error_code` by default; callers must pass it explicitly. Set
     `error_code = "CUBE_METADATA_NOT_CACHED"` as class attribute
     for consistency with other domain exceptions.
- **Fix sketch:**
  - Item 1: add `isinstance` guards before each `.items()` / `.get()`
    on config sub-dicts
  - Item 2: filter `resolved_filters` for non-None pairs at end of
    `validate_mapping_against_cache`; if any expected resolution is
    missing, mark `valid=False` with reason `RESOLUTION_INCOMPLETE`
  - Item 3: `class CubeNotInCacheError(DomainError): error_code = "CUBE_METADATA_NOT_CACHED"`
- **Status:** pending
- **Note:** combine with P3-025 (DEBT-057 cluster) for single 3.1
  polish PR. Net ~30 minutes total work.

---

## P3-027 — Tighten generic Exception handlers in 3.1aaa value cache service

- **Source:** Phase 3.1aaa Codex bot review 2026-05-03
- **Added:** 2026-05-03
- **Severity:** P3
- **Category:** code-quality
- **File:** `backend/src/services/statcan/value_cache.py`
- **Description:** `auto_prime` and `_persist_response` use bare
  `except Exception as exc: # noqa: BLE001` to honor Q-3 RE-LOCK
  best-effort contract. Per project linting baseline, BLE001 noqa
  suppressions should be reviewed every 6 months — narrow to specific
  expected exceptions where possible.
- **Fix sketch:** audit each `except Exception` site:
  ```python
  # Before:
  except Exception as exc:  # noqa: BLE001
      ...

  # Where applicable, narrow:
  except (ValidationError, DataSourceError, IntegrityError) as exc:
      ...
  except Exception as exc:  # noqa: BLE001 — best-effort retry contract
      ...
  ```
  Document why generic catch is required (best-effort) in inline
  comment for sites that legitimately need it. Drop `noqa` for sites
  that can be narrowed.
- **Status:** pending
- **Note:** standalone item; not blocking other polish work. Can ship
  in any cosmetic backend batch.

---

## P3-028 — Rename `test_publish_capture_db_upsert_failure_does_not_fail_publish` → `test_publish_capture_validation_failure_does_not_fail_publish`

- **Source:** Phase 3.1d PR 2 Part 1 reviewer flag (post-fix-round)
- **Added:** 2026-05-04
- **Severity:** P2
- **Category:** test-naming
- **File:** `backend/tests/api/test_publication_[compare.py](http://compare.py)`
- **Description:** Test name claims "DB upsert failure" but the
  mechanism it exercises is `validate_snapshot_dims_members`
  raising `ValueError` (negative member) — fires BEFORE any DB
  write. The service-level swallow contract is identical for shape-
  validation and DB-upsert failures, so the test does cover the
  correct surface; only the name is misleading. Reviewer accepted
  the test for merge but flagged the name as misleading future
  readers.
- **Fix sketch:** rename to
  `test_publish_capture_validation_failure_does_not_fail_publish`.
  Update docstring comment likewise. Optionally add a sibling test
  that injects a broken repo via dependency override to exercise a
  literal upsert raise — but only if a fake/broken repo helper
  already exists, otherwise that's net-new infrastructure for
  redundant coverage.
- **Status:** pending

---

## P3-029 — Optional route-level guard around `staleness.capture_for_publication`

- **Source:** Phase 3.1d PR 2 Part 1 reviewer suggestion
- **Added:** 2026-05-04
- **Severity:** P3
- **Category:** code-quality (defense-in-depth)
- **File:** `backend/src/api/routers/admin_[publications.py](http://publications.py)`
  (`publish_publication` handler)
- **Description:** `publish_publication` calls
  `staleness.capture_for_publication(...)` without a route-level
  try/except. Service contract guarantees per-block swallow inside
  the loop, so any single block's failure cannot escape. But if a
  future regression in the service raises OUTSIDE the per-block
  loop (e.g. before-loop setup, after-loop aggregation, an unhandled
  validation in the wrapper), publish would 500 even though the
  publication mutation already committed. Belt-and-suspenders fix
  is route-level catch.
- **Fix sketch:**
  ```python
  bound_blocks = payload.bound_blocks if payload else []
  if bound_blocks:
      try:
          captured = await staleness.capture_for_publication(
              publication_id=[publication.id](http://publication.id),
              bound_blocks=bound_blocks,
          )
      except Exception:  # noqa: BLE001 — defense-in-depth
          logger.exception(
              "publication_snapshot_capture_failed",
              publication_id=[publication.id](http://publication.id),
              bound_count=len(bound_blocks),
          )
          captured = 0
      [logger.info](http://logger.info)(
          "publication_snapshots_captured",
          publication_id=[publication.id](http://publication.id),
          bound_count=len(bound_blocks),
          captured_count=captured,
      )
  ```
  Add corresponding integration test that injects an exploding
  StalenessService stub and verifies publish returns 200 anyway.
- **Status:** pending
- **Note:** trade-off — this duplicates the service contract and
  obscures regressions in the per-block swallow path. Recon §5 had
  service-level best-effort as the locked contract. Discuss before
  shipping.

---

## P3-030 — DEBT-066 references DEBT-046, but DEBT-046 may be stale

- **Source:** Phase 3.1d PR 2 Part 1 reviewer flag
- **Added:** 2026-05-04
- **Severity:** P3
- **Category:** documentation
- **File:** `[DEBT.md](http://DEBT.md)`
- **Description:** DEBT-066 (Phase 3.1d — public viewer staleness
  display) reads `Resolution: Extend PublicationPublicResponse with
  backend-computed flag (depends on DEBT-046).` The reference to
  DEBT-046 was carried over from an earlier draft of the recon doc
  where DEBT numbering started at 045. After the actual [DEBT.md](http://DEBT.md)
  insertion landed at DEBT-064..070, the cross-reference inside
  DEBT-066's Resolution field was not updated to point at the new
  number for the scheduled-background-compare entry (which is now
  DEBT-065).
- **Fix sketch:** verify what DEBT-046 currently is in `[DEBT.md](http://DEBT.md)` (if
  it exists at all), and what DEBT-066 actually depends on. The
  intent in the recon was "depends on the scheduled background
  compare entry" (now DEBT-065). Update DEBT-066:
  ```markdown
  - **Resolution:** Extend `PublicationPublicResponse` with
    backend-computed flag (depends on DEBT-065).
  ```
- **Status:** pending

---

## P3-031 — Router-to-router DI factory import smell

- **Source:** Phase 3.1d PR 2 Part 1 reviewer flag (P2 in original
  review, downgraded to P3 polish)
- **Added:** 2026-05-04
- **Severity:** P3
- **Category:** architecture
- **Files:**
  - `backend/src/api/routers/admin_[publications.py](http://publications.py)`
    (imports `_get_resolve_service` from `admin_[resolve.py](http://resolve.py)`)
  - `backend/src/api/routers/admin_[resolve.py](http://resolve.py)`
    (defines `_get_resolve_service`)
- **Description:** `admin_[publications.py](http://publications.py)` reaches into a sibling
  router module to grab `_get_resolve_service`. Works (no cycle), but
  creates structural coupling between unrelated endpoint modules.
  Same DI factory will likely be needed by future routers (e.g.
  `admin_validate`, `admin_freshness`, hypothetical scheduler
  endpoints). Cleaner placement: shared `dependencies/` module that
  every router imports without coupling to peer-router internals.
- **Fix sketch:**
  1. Create `backend/src/api/dependencies/[resolve.py](http://resolve.py)` exporting
     `get_resolve_service` (drop the private-prefix underscore for
     the moved factory).
  2. `admin_[resolve.py](http://resolve.py)` re-imports from there and uses as its own
     dependency factory (or re-exports `_get_resolve_service` as
     alias for back-compat).
  3. `admin_[publications.py](http://publications.py)` imports from `dependencies/resolve`
     directly; remove the `from src.api.routers.admin_resolve`
     import.
  4. While at it, audit other router-to-router DI imports
     (`grep -rn "from src.api.routers." backend/src/api/routers/`).
- **Status:** pending
- **Note:** straightforward refactor, ~30 min if no other smell
  routers; longer if grep finds 3+ similar imports.

---

## P3-032 — Phase 3.1d docs polish (line numbers + wording)

- **Source:** Phase 3.1d PR 2 Part 2 reviewer flags (P2 cosmetic)
- **Added:** 2026-05-04
- **Severity:** P3
- **Category:** documentation
- **Files:**
  - `docs/architecture/BACKEND_API_[INVENTORY.md](http://INVENTORY.md)`
  - `docs/[api.md](http://api.md)`
  - `docs/architecture/ROADMAP_[DEPENDENCIES.md](http://DEPENDENCIES.md)`
- **Description:** Three small wording/format issues in Phase 3.1d
  drift docs:
  1. **Line numbers brittle** in BACKEND_API_[INVENTORY.md](http://INVENTORY.md) —
     references like `admin_publications.py:545`,
     `admin_publications.py:622`, `staleness.py:173`,
     `staleness.py:148` will drift on next refactor.
  2. **`docs/[api.md](http://api.md)` "never raise" wording** — current text says
     "per-block resolve or shape-validation failures are logged
     inside `PublicationStalenessService.capture_for_publication`
     and never raise into the caller." The "never" is stronger than
     route-level enforcement guarantees today (linked to P3-029 —
     if route-level guard added, "never" becomes accurate; until
     then, prefer "should not raise").
  3. **ROADMAP_[DEPENDENCIES.md](http://DEPENDENCIES.md) SHIPPED timestamp** — Phase 3.1d
     entry says `SHIPPED (2026-05)` which is correct after this PR
     lands but was technically premature during PR review window.
     Already merged so this is informational; future closeout PRs
     should phrase as `READY TO SHIP` until merge confirmed.
- **Fix sketch:**
  1. Replace line-number suffixes with symbol references:
     ```diff
     - admin_publications.py:545
     + admin_[publications.py](http://publications.py)::publish_publication
     ```
     Same for `compare_publication`, `PublicationPublishRequest`,
     `PublicationComparatorResponse`. Audit other entries in the
     inventory for the same pattern.
  2. In `docs/[api.md](http://api.md)`, change "and never raise into the caller" to
     "and should not raise into the caller" (or upgrade to "and
     never raise" once P3-029 ships).
  3. ROADMAP wording — leave as-is (already merged correctly), but
     adopt `READY TO SHIP` convention in future closeout PRs.
- **Status:** pending
- **Note:** combine with P3-031 in a Phase 3.1d closeout polish
  batch — both touch related surface (router DI + drift docs).

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
- **Phase 2.1 frontend batch**: P3-007, P3-008, P3-009, P3-010, P3-011,
  P3-012, P3-013 — all in `frontend-public/`, mix of code/test/doc
  cosmetics, ~45 minutes total. P3-010 (architectural cycle break) is
  the most substantive; the rest are wording/test-name/format polish.
  > Updated 2026-04-28: extended batch to include P3-012 (architecture)
  > and P3-013 (i18n). Total now 7 items spanning code-quality,
  > test-coverage, architecture, documentation, and i18n categories.
- **Phase 2.2.0 backend test polish batch**: P2-002, P3-014, P3-015,
  P3-016 — all in `backend/tests/services/publications/test_lineage.py`,
  ~30 minutes total. Combine SimpleNamespace migration (P2-002) with
  the constant extraction (P3-015) and stdlib UUID parse check (P3-016)
  in single sweep. Time.sleep bump (P3-014) lands trivially in same PR.
- **Phase 2.2.0 integration test polish batch**: P3-017, P3-018, P3-019
  — three separate files. Lower coupling than batch above. P3-017 is
  cosmetic-only and should NOT ship same time as functional fixes
  (per its note). P3-019 is mechanical (single `black` run).
- **Compose infrastructure batch**: P2-003 alone for now. Defer until
  multi-tenant requirement surfaces or another compose nit accumulates.
- **Phase 3.1 closure batch (3.1ab + 3.1b + 3.1aaa carryovers)**:
  P3-020 (function naming), P3-021 (PG test gate), P3-022 (timestamp
  exclusion test), P3-023 (Pydantic value parsing), P3-024 (prime-on-
  refresh), P3-025 (DEBT-057 cluster — 3 items), P3-026 (3.1ab cluster
  — 3 items), P3-027 (BLE001 audit). Spans backend/, migrations/, and
  flutter_admin/. ~2 hours total. Dispatch after Phase 3.1d closes,
  before Phase 3.2 starts. Single PR, single review pass.
- **Phase 3.1d closeout batch**: P3-028 (test rename), P3-029 (optional
  route-level capture guard), P3-030 (DEBT-066 → DEBT-065 reference
  fix), P3-031 (router-to-router DI smell), P3-032 (docs line numbers
  + wording). Mixed surface: backend tests, router code, [DEBT.md](http://DEBT.md),
  drift docs. P3-029 is the most substantive (~30 min + integration
  test); rest are mechanical polish (~5-10 min each). Total ~1 hour.
  Sequencing: ship P3-030 (DEBT reference) and P3-032 (docs) first as
  pure docs PR; ship P3-028 (rename) standalone or with P3-029
  (route guard) which adds the integration test that justifies the
  rename's name being canonical. P3-031 is independent — can ship
  with the Phase 3.1 closure batch above if surface overlaps.
