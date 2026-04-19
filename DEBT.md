# Technical Debt Registry

> Source of truth for known technical debt.
> Maintained per-PR: creating debt → add entry; resolving → move to Resolved.

## Format

| Field | Description |
|-------|-------------|
| **ID** | `DEBT-NNN` (sequential, never reused) |
| **Source** | PR number or review that identified it (e.g. `PR #16 review`, `Roadmap R18`) |
| **Added** | Date added (YYYY-MM-DD) |
| **Severity** | `critical` / `high` / `medium` / `low` |
| **Category** | `architecture` / `testing` / `security` / `ops` / `code-quality` |
| **Status** | `active` — confirmed, needs work; `accepted` — known, deferred intentionally; `in-progress` — being fixed |
| **Description** | Factual statement of what the debt IS (not hypotheses) |
| **Impact** | What breaks or degrades if not fixed |
| **Resolution** | Concrete action to resolve |
| **Target** | Specific PR, étape, or milestone |

Rules:
- Every entry must be a **verified fact**, not a hypothesis.
- Do NOT add speculative or unverified items — verify first, then add.
- Backlog features and future enhancements go in ROADMAP, not here.
- When resolving: move entry to Resolved table with PR link and date.
- When updating severity/target: edit in-place and append a changelog
  line at the bottom of the entry:
  `> Updated YYYY-MM-DD: severity high→medium, moved target to B-3.`

---

## Active Debt

### DEBT-026: Lossy round-trip between `CanonicalDocument` and `AdminPublicationResponse`

- **Source:** Stage 4 Task 0 wire-up (branch `claude/wire-infographic-editor-9w3wr`)
- **Added:** 2026-04-19
- **Severity:** medium
- **Category:** architecture
- **Status:** accepted
- **Description:** `hydrateDoc()` in
  `frontend-public/src/components/editor/utils/persistence.ts` starts
  from the default `single_stat_hero` template and overlays only the
  well-known editorial text blocks (`headline_editorial`,
  `eyebrow_tag`, `source_footer`, `body_annotation`,
  `subtitle_descriptor`) plus `doc.review` and a subset of
  `doc.page` (palette/background/size). All other block props — chart
  data (`bar_horizontal.items`, `line_editorial.series`,
  `comparison_kpi.items`, `table_enriched.rows`,
  `small_multiple.items`), `hero_stat.value/label`, `delta_badge`,
  `brand_stamp.position`, `source_footer.methodology` — are reset to
  template defaults on hydrate. Symmetrically, `buildUpdatePayload()`
  only extracts the matching editorial text fields into the PATCH.
  The size mapping is also lossy: `instagram_1080` and
  `instagram_port` both collapse to backend `size="instagram"` and
  round-trip back to `instagram_1080`.
- **Impact:** Block-level chart edits that do not have a mirror at
  the top-level publication columns are not persisted across a
  browser reload. Review/workflow state, the editorial headline/eyebrow/
  source_text, and the loose visual config (palette/background/size)
  DO round-trip. For Task 0 scope (read/edit workflow metadata + text
  + theme) this is acceptable; chart-data editing is not yet wired.
- **Resolution:** Choose one:
  (a) Extend the backend schema with a dedicated `document_state`
      JSON column that stores the full `CanonicalDocument` verbatim
      (editor owns the shape; backend treats it opaquely).
  (b) Broaden `VisualConfig` to cover every block-level prop the
      editor can mutate (invasive, couples two schemas tightly).
  Option (a) is preferred — aligns with how `review` is stored today.
- **Target:** Stage 4 Task 2 (autosave) or a dedicated persistence PR
  before any block-data editing flow ships to production.

### DEBT-021: Temp upload Parquet files not cleaned up

- **Source:** JSON/CSV upload PR (`claude/add-data-upload-graphics-i8IWc`)
- **Added:** 2026-04-14
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `POST /api/v1/admin/graphics/generate-from-data` writes a
  temporary Parquet to S3 under `temp/uploads/{uuid}.parquet` before
  enqueuing the existing `graphics_generate` job. The `GraphicPipeline`
  does not delete its input object, and no cleanup cron exists yet,
  so these temp Parquet files accumulate indefinitely.
- **Impact:** Low — individual objects are small (≤ 10 000 rows × columns
  of CSV/JSON data). Growth is proportional to upload volume; eventually
  increases storage cost and clutters bucket listings.
- **Resolution:** Add a scheduled task that deletes objects under
  `temp/uploads/` with a `LastModified` older than
  `settings.temp_upload_ttl_hours` (default 24 h).
- **Target:** Follow-up PR (not blocking for the upload feature).

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
| DEBT-010 | No audit event retention cleanup | Final Debts | 2026-04-12 |
| DEBT-015 | GraphicPipeline generate() method is monolithic | Final Debts | 2026-04-12 |
| DEBT-001 | Cooldown query uses text match on JSON | Docs & Quality | 2026-04-12 |
| DEBT-002 | Integration tests use metadata.create_all | Docs & Quality | 2026-04-12 |
| DEBT-003 | Dockerfile doesn't run migrations on startup | Pre-deploy Hardening | 2026-04-12 |
| DEBT-004 | Old in-memory TaskManager not yet removed | Dead Code Cleanup | 2026-04-12 |
| DEBT-005 | StorageInterface upload_bytes/download_bytes | PR B-3 | 2026-04-09 |
| DEBT-006 | Dead code in services/cmhc/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-007 | Dead code in services/ai/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-008 | No startup validation for required secrets | Pre-deploy Hardening | 2026-04-12 |
| DEBT-012 | Admin graphics API uses placeholder data | PR B-3 | 2026-04-09 |
| DEBT-013 | Admin graphics uploads same file for high-res variant | PR B-3 | 2026-04-09 |
| DEBT-014 | database.py creates engine at module level | PR A-1 fix | 2026-04-06 |
| DEBT-016 | ARCHITECTURE.md references removed MVP features | Docs & Quality | 2026-04-12 |
| DEBT-017 | Job handlers violate ARCH-DPEN-001 with inline httpx | Docs & Quality | 2026-04-12 |
| DEBT-018 | TESTING.md coverage table is stale | Docs & Quality | 2026-04-12 |
| DEBT-019 | Orphaned LLM infrastructure outside services/ai/ | Dead Code Cleanup | 2026-04-12 |
| DEBT-020 | CMHC and Tasks routers still mounted for deferred features | Dead Code Cleanup | 2026-04-12 |
| DEBT-022 | `validateImport` dual-signature (string + throwing) | Stage 3 PR 2a (`claude/add-workflow-state-machine-mUM3P`) | 2026-04-17 |
| DEBT-023 | `validateImportStrict` does not deep-validate `Comment` entries | Stage 3 PR 2b (`claude/recon-comments-subsystem-HwvB1`) | 2026-04-17 |
| DEBT-024 | Rename `validateDocumentShape` → `assertCanonicalDocumentV2Shape` | Stage 3 PR 4 (`claude/reconnaissance-persistence-cleanup-EJ4uX`) | 2026-04-19 |
