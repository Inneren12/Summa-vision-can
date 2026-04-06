# Technical Debt Registry

> Maintained per-PR. Every PR that creates debt adds an entry.
> Every PR that resolves debt removes the entry and adds a line
> to the Resolved section at the bottom.

## Format

Each entry:
- **ID:** DEBT-NNN (sequential)
- **Source:** PR or review that created it
- **Severity:** `blocking` | `high` | `medium` | `low`
- **Category:** `architecture` | `testing` | `performance` | `security` | `ops` | `code-quality`
- **Description:** What the debt is
- **Impact:** What happens if not fixed
- **Resolution:** What needs to be done
- **Target:** Which PR/étape should fix it

---

## Active Debt

### DEBT-001: Cooldown query uses text search on JSON payload
- **Source:** 0-3 review
- **Severity:** medium
- **Category:** architecture
- **Description:** `_is_cooled_down()` matches `'"product_id":"..."'` via
  `payload_json.contains()`. Depends on exact JSON serialization.
- **Impact:** False negatives if serialization changes (e.g. spaces after colon).
- **Resolution:** Move to JSONB column + JSON path query, or add a
  `subject_key` column on Job model for typed lookup.
- **Target:** When Job model gets JSONB payload or when cooldown is extended.

### DEBT-002: Integration tests use Base.metadata.create_all, not Alembic
- **Source:** 0-2 review
- **Severity:** medium
- **Category:** testing
- **Description:** PostgreSQL integration tests create schema via
  `Base.metadata.create_all()` instead of `alembic upgrade head`.
  Partial unique index `ix_jobs_dedupe_active` is in Alembic migration
  SQL, not in model metadata.
- **Impact:** Integration tests may not test the real production schema.
  Tests could pass while production deployment fails.
- **Resolution:** Add an integration test path that applies Alembic
  migrations before running tests.
- **Target:** Before first production deploy.

### DEBT-003: Dockerfile entrypoint doesn't run migrations
- **Source:** 0-1 review
- **Severity:** high
- **Category:** ops
- **Description:** Dockerfile has a TODO comment about running
  `alembic upgrade head` before uvicorn, but it's not implemented.
  Migrations must be run manually after deploy.
- **Impact:** Forgetting manual migration = app starts with stale schema.
- **Resolution:** Create entrypoint.sh that runs `alembic upgrade head`
  then exec's uvicorn. Or use init container in compose.
- **Target:** Before production deploy (Étape D-5).

### DEBT-004: In-memory TaskManager still exists alongside Job system
- **Source:** Architecture
- **Severity:** low
- **Category:** architecture
- **Description:** Old `TaskManager` (in-memory dict) from Sprint 1
  still exists in the codebase. New persistent Job system replaces it.
- **Impact:** Confusion about which system to use. Dead code.
- **Resolution:** Delete TaskManager and its references after all
  consumers are migrated to Job system.
- **Target:** After Étape A when all async operations use Jobs.

### DEBT-005: StorageInterface lacks upload_bytes / download_bytes
- **Source:** A-5 implementation
- **Severity:** high
- **Category:** architecture
- **Description:** DataFetchService and Transform API need
  `upload_bytes()` / `download_bytes()` for Parquet files, but
  StorageInterface only defines `upload_dataframe_as_csv()`.
- **Impact:** Parquet storage path uses workarounds (temp files,
  method detection). New code can't rely on a clean interface.
- **Resolution:** Add `upload_bytes(data, key)` and `download_bytes(key)`
  to StorageInterface and both implementations.
- **Target:** A-5 or B-3 (before pipeline needs it).

### DEBT-006: CMHC scraper is stub-only
- **Source:** Sprint 1 scope
- **Severity:** low
- **Category:** architecture
- **Description:** `services/cmhc/` directory has browser.py, parser.py,
  service.py but they are stubs with no real implementation.
- **Impact:** None currently — CMHC is deferred to backlog.
- **Resolution:** Implement when CMHC data is needed, or delete stubs
  if direction changes.
- **Target:** Backlog (post-PMF).

### DEBT-007: AI services (LLM interface, scoring, cache) are stubs
- **Source:** Sprint 2 scope / architecture pivot
- **Severity:** low
- **Category:** architecture
- **Description:** `services/ai/` directory has llm_interface.py,
  scoring_service.py, llm_cache.py, cost_tracker.py — all stubs or
  minimal implementations from before the LLM-removal pivot.
- **Impact:** Dead code. May confuse new contributors.
- **Resolution:** Either delete or clearly mark as backlog. LLM is
  now optional "AI Enhance" button, not pipeline-critical.
- **Target:** Cleanup PR before Étape D.

### DEBT-008: No startup validation for required secrets
- **Source:** Roadmap Secret Management Policy
- **Severity:** high
- **Category:** security
- **Description:** Settings class doesn't validate that required secrets
  (DATABASE_URL, ADMIN_API_KEY) are non-empty at startup.
  Missing secrets cause runtime errors, not startup failures.
- **Impact:** App starts but breaks on first request.
- **Resolution:** Add `@model_validator` to Settings that checks
  required fields by deployment stage.
- **Target:** Before production deploy (Étape D-5).

### DEBT-009: MAX_PREVIEW_ROWS not in Settings
- **Source:** A-7 / R15
- **Severity:** low
- **Category:** code-quality
- **Description:** Hard cap MAX_PREVIEW_ROWS=100 may be hardcoded in
  router instead of configurable via Settings.
- **Impact:** Cannot adjust without code change.
- **Resolution:** Add `max_preview_rows: int = 100` to Settings.
- **Target:** A-7 or B-4.

### DEBT-010: No audit event retention cleanup
- **Source:** 0-4 / R18
- **Severity:** low
- **Category:** ops
- **Description:** `AUDIT_RETENTION_DAYS=90` is configured but no
  cleanup job deletes old events.
- **Impact:** audit_events table grows unbounded.
- **Resolution:** Add a scheduled cleanup job or SQL cron.
- **Target:** After Étape D when traffic generates real events.

### DEBT-011: AI Image API is a stub
- **Source:** Code scan (`backend/src/services/graphics/ai_image_client.py`)
- **Severity:** low
- **Category:** architecture
- **Description:** AI image client is a placeholder that does not call a real AI image API (Stable Diffusion / DALL-E / Imagen).
- **Impact:** Actual image generation does not happen.
- **Resolution:** Replace with real AI image API.
- **Target:** Backlog.

### DEBT-012: Admin graphics API uses placeholder data
- **Source:** Code scan (`backend/src/api/routers/admin_graphics.py`)
- **Severity:** medium
- **Category:** architecture
- **Description:** Admin graphics API does not fetch real StatCan data from storage using `publication.cube_id`, building a placeholder DataFrame instead.
- **Impact:** Chart rendering uses placeholder data instead of real data.
- **Resolution:** Fetch real StatCan data from storage when available.
- **Target:** Before feature launch.

### DEBT-013: Admin graphics API uploads same file for high-res variant
- **Source:** Code scan (`backend/src/api/routers/admin_graphics.py`)
- **Severity:** low
- **Category:** architecture
- **Description:** Admin graphics API generates a placeholder high-res variant by uploading the same file instead of actual high-res variant.
- **Impact:** High-res images are same as normal resolution.
- **Resolution:** Generate actual high-res variant.
- **Target:** Before feature launch.

### DEBT-014: Auth uses X-API-KEY instead of JWT Bearer tokens
- **Source:** Code scan (`backend/src/core/security/auth.py`)
- **Severity:** low
- **Category:** security
- **Description:** Authentication mechanism relies on `X-API-KEY` rather than JWT Bearer tokens.
- **Impact:** Limited functionality for more complex auth setups like B2B expansion.
- **Resolution:** Replace `X-API-KEY` with JWT Bearer tokens.
- **Target:** Future B2B expansion.

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
| — | (none yet) | — | — |
