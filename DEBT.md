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

### DEBT-022: `validateImport` dual-signature (string + throwing)

- **Source:** Stage 3 PR 1 (`claude/add-review-section-IL0pl`)
- **Added:** 2026-04-17
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** `frontend-public/src/components/editor/registry/guards.ts`
  exports two parallel import validators: the legacy
  `validateImport(doc): string | null` used by
  `components/editor/index.tsx` and `components/editor/store/reducer.ts`,
  and the new throwing `validateImportStrict(raw): CanonicalDocument`.
  The two are kept in sync but both paths exist so PR 1 could land
  data-layer-only without touching reducer/UI call sites.
- **Impact:** Low — two validation entry points for the editor import
  pipeline; one can fall out of sync with the other if a future invariant
  is added to only one.
- **Resolution:** Migrate reducer / `index.tsx` call sites to
  `validateImportStrict`, drop the string-returning overload.
- **Target:** Stage 3 PR 2 (reducer actions).

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
