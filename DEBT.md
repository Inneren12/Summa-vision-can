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

### DEBT-001: Cooldown query uses text match on JSON payload
- **Source:** PR #17 review
- **Added:** 2026-04-05
- **Severity:** medium
- **Category:** architecture
- **Status:** accepted
- **Description:** `_is_cooled_down()` in runner.py matches `'"product_id":"value"'` via `payload_json.contains()`. This depends on exact JSON serialization without spaces.
- **Impact:** False negatives if Pydantic serialization format changes. Currently tolerated — Pydantic's `model_dump_json()` produces compact
JSON, but any serialization change would silently break the match.
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

### DEBT-015: GraphicPipeline generate() method is monolithic
- **Source:** PR B-3 review
- **Added:** 2026-04-09
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** `GraphicPipeline.generate()` contains the entire E2E process (11 stages) in a single ~120-line method with nested try/except blocks and inline async functions.
- **Impact:** Harder to read and maintain. High cognitive load for future developers modifying individual stages.
- **Resolution:** Refactor `generate()` into smaller private methods (e.g., `_load_data`, `_render_assets`, `_persist_to_db`) while preserving the semaphore boundary semantics.
- **Target:** Future refactoring sprint or before Étape D.

### DEBT-016: docs/architecture/ARCHITECTURE.md references removed MVP features
- **Source:** Technical debt audit (2026-04-12)
- **Added:** 2026-04-12
- **Severity:** medium
- **Category:** code-quality
- **Status:** active
- **Description:** `docs/architecture/ARCHITECTURE.md` (the original architecture document) still describes LLM Gate, Gemini Scoring, and AI Background Art as core active components (17+ references).
- **Impact:** New contributors will misunderstand the current system. The old architecture doc presents a fundamentally different system (Gemini scoring → AI Art) than the actual MVP (Polars → SVG + Pillow backgrounds → Pipeline → Gallery + Lead funnel).
- **Resolution:** Rewrite `docs/architecture/ARCHITECTURE.md` to reflect actual MVP architecture, or delete it in favour of `docs/ARCHITECTURE.md`.
> Updated 2026-04-12: TaskManager references removed from `docs/modules/api.md`, `docs/ARCH_RULES.md`, `docs/modules/core.md`. LLM Gate removed from `docs/ARCHITECTURE.md` flow diagram. Remaining: old `docs/architecture/ARCHITECTURE.md` still has stale LLM references.
- **Target:** Post-launch documentation sprint.

### DEBT-017: Job handlers violate ARCH-DPEN-001 with inline httpx client creation
- **Source:** Technical debt audit (2026-04-12)
- **Added:** 2026-04-12
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** `services/jobs/handlers.py` creates fallback `httpx.AsyncClient()` instances inline at lines 83 and 155 when `app_state` does not provide a pre-configured client. `core/scheduler.py` (line 92) also creates `httpx.AsyncClient()` inline. This violates ARCH-DPEN-001 (classes/handlers cannot instantiate their own heavy dependencies) and the forbidden pattern `self.client = httpx.AsyncClient()` documented in `docs/ARCH_RULES.md`.
- **Impact:** These inline clients bypass the app-scoped client lifecycle (no shared connection pooling, no coordinated shutdown). Harder to mock in tests — handler tests must patch internal imports rather than injecting via DI.
- **Resolution:** Require `app_state` to always provide `http_client` and `statcan_client`. Remove the `if http_client is None` fallback branches. Ensure `main.py` lifespan sets these on `app.state` unconditionally.
- **Target:** Next handler refactoring PR.

### DEBT-018: TESTING.md coverage table is stale
- **Source:** Technical debt audit (2026-04-12)
- **Added:** 2026-04-12
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** `docs/TESTING.md` coverage table has multiple inaccuracies: (1) Shows ⬜ for modules that now have test files — `services/jobs/runner.py`, `services/statcan/catalog_sync.py`, `services/statcan/data_fetch.py`, `services/data/workbench.py` all have corresponding test files. (2) Overall claim of "560+ tests, 96%+ total coverage" has not been reverified after Étapes C and D.
> Updated 2026-04-12: Dead code module rows (`services/cmhc/*`, `services/ai/*`, `core/task_manager.py`, `core/prompt_loader.py`) removed from coverage table via Dead Code Cleanup. Remaining: stale ⬜ rows and unverified overall claim.
- **Impact:** Misleading coverage picture. Contributors cannot tell which modules genuinely lack tests vs. which had tests added in later PRs. Dead code coverage inflates reported numbers.
- **Resolution:** Run `pytest --cov=src --cov-report=term-missing`, update every row in the coverage table, remove or mark dead-code rows as `(dead code — see DEBT-006, DEBT-007)`.
- **Target:** Next documentation update PR.

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
| DEBT-003 | Dockerfile doesn't run migrations on startup | Pre-deploy Hardening | 2026-04-12 |
| DEBT-008 | No startup validation for required secrets | Pre-deploy Hardening | 2026-04-12 |
| DEBT-014 | database.py creates engine at module level | PR A-1 fix | 2026-04-06 |
| DEBT-004 | Old in-memory TaskManager not yet removed | Dead Code Cleanup | 2026-04-12 |
| DEBT-005 | StorageInterface upload_bytes/download_bytes | PR B-3 | 2026-04-09 |
| DEBT-006 | Dead code in services/cmhc/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-007 | Dead code in services/ai/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-012 | Admin graphics API uses placeholder data | PR B-3 | 2026-04-09 |
| DEBT-013 | Admin graphics uploads same file for high-res variant | PR B-3 | 2026-04-09 |
| DEBT-019 | Orphaned LLM infrastructure outside services/ai/ | Dead Code Cleanup | 2026-04-12 |
| DEBT-020 | CMHC and Tasks routers still mounted for deferred features | Dead Code Cleanup | 2026-04-12 |
