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
| **Description** | Factual statement of what the debt IS (not "may be") |
| **Impact** | What breaks or degrades if not fixed |
| **Resolution** | Concrete action to resolve |
| **Target** | Specific PR, étape, or milestone |

Rules:
- Every entry must be a **verified fact**, not a hypothesis.
- Do NOT add "may be" or "might have" items — verify first, then add.
- Backlog features and future enhancements go in ROADMAP, not here.
- When resolving: move entry to Resolved table with PR link and date.
- When updating severity/target: edit in-place, add comment with date.

---

## Active Debt

### DEBT-001: Cooldown query uses text match on JSON payload
- **Source:** PR #17 review
- **Added:** 2026-04-05
- **Severity:** medium
- **Category:** architecture
- **Status:** accepted
- **Description:** `_is_cooled_down()` in runner.py matches `'"product_id":"value"'` via `payload_json.contains()`. This depends on exact JSON serialization without spaces.
- **Impact:** False negatives if Pydantic serialization format changes. Currently safe because `model_dump_json()` produces compact JSON.
- **Resolution:** Add `subject_key` column to Job model, or migrate payload to JSONB column with proper JSON path queries.
- **Target:** When Job model is next modified (B-3 or later).

### DEBT-002: Integration tests use metadata.create_all, not Alembic migrations
- **Source:** PR #16 review
- **Added:** 2026-04-05
- **Severity:** medium
- **Category:** testing
- **Status:** active
- **Description:** PostgreSQL integration tests in `test_job_repository_integration.py` create schema via `Base.metadata.create_all()`. The partial unique index `ix_jobs_dedupe_active` is defined in Alembic migration SQL, not in SQLAlchemy model metadata.
- **Impact:** Integration tests test a metadata-generated schema instead of the real production schema. Dedupe race condition test is a false-positive.
- **Resolution:** Add integration test path that runs `alembic upgrade head` instead of `create_all()`, at least for the dedupe test.
- **Target:** Before first production deploy.

### DEBT-003: Dockerfile doesn't run migrations on startup
- **Source:** PR #11 review
- **Added:** 2026-04-05
- **Severity:** high
- **Category:** ops
- **Status:** active
- **Description:** Dockerfile CMD starts uvicorn directly. Migrations must be run manually via `docker compose exec api alembic upgrade head`. A TODO comment exists but no entrypoint script implements it.
- **Impact:** Forgotten manual migration → app starts with stale schema.
- **Resolution:** Create `entrypoint.sh` that runs `alembic upgrade head && exec uvicorn ...`. Or use init container.
- **Target:** Pre-deploy hardening PR (before Étape D-5).

### DEBT-004: Old in-memory TaskManager not yet removed
- **Source:** Architecture (Sprint 1 → Étape 0 transition)
- **Added:** 2026-04-05
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** `core/task_manager.py` (in-memory dict for async tasks) still exists. Persistent Job system (PR 0-2/0-3) replaces it.
- **Impact:** Dead code. May confuse contributors about which task system to use.
- **Resolution:** Delete TaskManager and update any remaining references (routers, tests) after all consumers use Job system.
- **Target:** After no code depends on TaskManager (verify with grep).

### DEBT-005: StorageInterface lacks upload_bytes / download_bytes
- **Source:** A-5 implementation
- **Added:** 2026-04-05
- **Severity:** high
- **Category:** architecture
- **Status:** active
- **Description:** `StorageInterface` defines `upload_dataframe_as_csv()` and `upload_json()` but not `upload_bytes()` or `download_bytes()`. Parquet storage (R3) requires raw bytes upload/download.
- **Impact:** DataFetchService and Transform API use workarounds (temp files, method detection via hasattr). Fragile and inconsistent.
- **Resolution:** Add `upload_bytes(data: bytes, key: str)` and `download_bytes(key: str) -> bytes` to StorageInterface and both implementations (S3StorageManager, LocalStorageManager).
- **Target:** Before B-3 (pipeline needs clean storage interface).

### DEBT-006: Dead code in services/cmhc/ directory
- **Source:** Sprint 1 scope
- **Added:** 2026-04-05
- **Severity:** low
- **Category:** architecture
- **Status:** accepted
- **Description:** `services/cmhc/` directory contains dead code with 7 total definitions (browser.py: 1, service.py: 3, parser.py: 3).
- **Impact:** Dead code. May confuse contributors.
- **Resolution:** Delete or clearly mark as backlog feature stubs. Add `# BACKLOG: Not used in current pipeline` header to each file.
- **Target:** Cleanup PR before Étape D.

### DEBT-007: Dead code in services/ai/ directory
- **Source:** Sprint 2 scope / architecture pivot
- **Added:** 2026-04-05
- **Severity:** low
- **Category:** architecture
- **Status:** accepted
- **Description:** `services/ai/` directory contains dead code with 26 total definitions (scoring_service.py: 5, cost_tracker.py: 2, schemas.py: 2, llm_interface.py: 10, llm_cache.py: 7).
- **Impact:** Dead code. May confuse contributors.
- **Resolution:** Delete or clearly mark as backlog feature stubs. Add `# BACKLOG: Not used in current pipeline` header to each file.
- **Target:** Cleanup PR before Étape D.

### DEBT-008: No startup validation for required secrets
- **Source:** Roadmap Secret Management Policy
- **Added:** 2026-04-05
- **Severity:** high
- **Category:** security
- **Status:** active
- **Description:** Settings class does not validate that required secrets (e.g. DATABASE_URL, ADMIN_API_KEY) are non-empty at startup. Missing secret → runtime error on first request, not startup failure.
- **Impact:** App appears healthy but fails on first real operation.
- **Resolution:** Add `@model_validator(mode="after")` to Settings that checks required fields. Different fields required per stage (Étape 0 vs D).
- **Target:** Pre-deploy hardening PR (before Étape D-5).

### DEBT-010: No audit event retention cleanup
- **Source:** PR #19 / Roadmap R18
- **Added:** 2026-04-05
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `AUDIT_RETENTION_DAYS=90` setting exists but no scheduled job or cron deletes old audit_events rows.
- **Impact:** Table grows unbounded. Not a problem at low volume (pre-launch), becomes relevant after sustained traffic.
- **Resolution:** Add a daily cleanup job: `DELETE FROM audit_events WHERE created_at < NOW() - INTERVAL '90 days'`
- **Target:** After Étape D when real traffic generates events.

### DEBT-012: Admin graphics API uses placeholder data
- **Source:** Code scan (backend/src/api/routers/admin_graphics.py)
- **Added:** 2026-04-05
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** Admin graphics API does not fetch real StatCan data from storage using `publication.cube_id`, building a placeholder DataFrame instead.
- **Impact:** Chart rendering uses placeholder data instead of real data.
- **Resolution:** Fetch real StatCan data from storage when available.
- **Target:** Before feature launch.

### DEBT-013: Admin graphics API uploads same file for high-res variant
- **Source:** Code scan (backend/src/api/routers/admin_graphics.py)
- **Added:** 2026-04-05
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** Admin graphics API uploads the exact same `png_bytes` variable to both `s3_key_lowres` and `s3_key_highres` paths instead of a real high-res image.
- **Impact:** High-res images are the same resolution as low-res images.
- **Resolution:** Generate actual high-res variant.
- **Target:** Before feature launch.

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
