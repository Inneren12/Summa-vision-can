# Backend API Inventory

**Status:** Living document — update on every backend impl PR
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Source:** Phase 1.3 pre-recon Part A (`docs/recon/phase-1-3-A-backend-inventory.md`) + Phase 2.5 discovery Part B (`docs/discovery/phase-2-5-B-model.md` §1.4 + §1.5)
**Maintenance rule:** any PR that adds/modifies/removes a backend endpoint MUST update this file in the same commit. Drift detector: if memory items reference endpoints/handlers that aren't here, this file is stale.

## How to use this file

- Pre-recon and recon prompts SHOULD read this file FIRST and only do new grep if a section is missing or marked stale.
- Sections track: endpoints (verbs, paths, deps, response shapes), domain models (key columns), repositories (public methods), exception handlers, integration test fixture patterns.
- Verbatim grep output stays in section appendices for reference; the main sections are summary tables.

---

## 1. Endpoints

| Method | Path | File:Line | Deps (`Depends(...)`) | Body schema | Response | Notes |
|---|---|---|---|---|---|---|
| PATCH | `/api/v1/admin/publications/{publication_id}` | `backend/src/api/routers/admin_publications.py:340` | `_get_repo` (`PublicationRepository`), `_get_audit` (`AuditWriter`) | `PublicationUpdate` (`backend/src/schemas/publication.py:152`); reads `If-Match` request header (Phase 1.3) | 200 → `PublicationResponse` with `ETag` response header; 404 → `PublicationNotFoundError`; 412 → `PRECONDITION_FAILED` envelope (`{"detail": {"error_code": "PRECONDITION_FAILED", "message": "...", "details": {"server_etag": str, "client_etag": str}}}`); 422 → DEBT-030 envelope `PUBLICATION_UPDATE_PAYLOAD_INVALID` | Phase 1.3 — ETag/If-Match contract per `docs/architecture/ARCHITECTURE_INVARIANTS.md` §7. ETag header on GET single + PATCH success + clone-201. `If-Match` recommended in v1 (tolerated absent per DEBT-042; flips to required on DEBT-042 resolution). 412 with `PRECONDITION_FAILED` envelope. |
| GET | `/api/v1/admin/jobs` | `backend/src/api/routers/admin_jobs.py:92` | `_get_job_repo` (`JobRepository`) | n/a (query params) | 200 → `JobListResponse{ items: list[JobItemResponse], total: int }` (router schema, `admin_jobs.py:63-67`) | Query params: `job_type` (str, optional), `status` (str, optional — aliased from `status_filter`), `limit` (int, 1..200, default 50). Pagination: `limit` only — **no offset, no cursor**. Order: `created_at DESC` (`job_repository.py:190`). Invalid `status` → 422 (`admin_jobs.py:110-118`). |
| GET | `/api/v1/admin/jobs/{job_id}` | `backend/src/api/routers/admin_jobs.py:159` | `_get_job_repo` (`JobRepository`) | n/a | 200 → `JobItemResponse`; 404 → "Job not found" (`admin_jobs.py:175-179`) | Path param `job_id: int` |
| POST | `/api/v1/admin/jobs/{job_id}/retry` | `backend/src/api/routers/admin_jobs.py:204` | `_get_job_repo` (`JobRepository`) | n/a | 202 → `RetryJobResponse{ job_id: str, status: str }` (`admin_jobs.py:70-74`); 404 (NotFoundError); 409 (ConflictError, "Job is not retryable") | Response carries the **same** job's id + updated status (not a new id), despite Flutter typing it as new. Validation/state mutation in `JobRepository.retry_failed_job` (`job_repository.py:250`). |
| POST | `/api/v1/admin/jobs/{job_id}/cancel` | — | — | — | — | **Not present** (as of inputs date — Phase 2.5 §1.6). No `cancel` endpoint, no `cancel` keyword in `admin_jobs.py` or `job_repository.py`. `JobStatus.CANCELLED` is defined but unused at the API surface. |
| — | bulk-retry / exceptions / failures / queue / enqueue | — | — | — | — | **Not present** (Phase 2.5 §1.4 — only `admin_jobs.py` exists in `backend/src/api/routers/` matching the search). |
| POST | `/api/v1/admin/semantic-mappings/upsert` | `backend/src/api/routers/admin_semantic_mappings.py` | `_get_service` (`SemanticMappingService`) | `SemanticMappingUpsertRequest` (`backend/src/api/schemas/semantic_mapping_admin.py`); accepts `If-Match` request header OR `if_match_version` body field (header wins) | 200 → `SemanticMappingResponse` (updated); 201 → `SemanticMappingResponse` (created); 400 → DEBT-030 envelope (`MEMBER_NOT_FOUND` / `DIMENSION_NOT_FOUND` / `CUBE_NOT_IN_CACHE` / `CUBE_PRODUCT_MISMATCH` / generic `METADATA_VALIDATION_FAILED`); 401 (middleware); 412 → `VERSION_CONFLICT` envelope (`details.expected_version`, `details.actual_version`) | Phase 3.1b. Idempotent on `(cube_id, semantic_key)`. Hybrid optimistic concurrency — see DEBT-054. |
| GET | `/api/v1/admin/semantic-mappings` | `backend/src/api/routers/admin_semantic_mappings.py` | `_get_service` | n/a (query params) | 200 → `SemanticMappingListResponse{ items, total, limit, offset }`; 401 (middleware) | Query params: `cube_id`, `semantic_key`, `is_active`, `limit` (1..200, default 50), `offset` (default 0). Order: `cube_id ASC, label ASC`. |
| GET | `/api/v1/admin/semantic-mappings/{mapping_id}` | `backend/src/api/routers/admin_semantic_mappings.py` | `_get_service` | n/a | 200 → `SemanticMappingResponse`; 401 (middleware); 404 → `MAPPING_NOT_FOUND` envelope | Phase 3.1b — operator detail/edit fetch. |
| DELETE | `/api/v1/admin/semantic-mappings/{mapping_id}` | `backend/src/api/routers/admin_semantic_mappings.py` | `_get_service` | n/a | 200 → `SemanticMappingResponse`; 401; 404 → `MAPPING_NOT_FOUND` | Phase 3.1b — soft delete (sets `is_active=false`). Idempotent: already-inactive returns row unchanged (no version bump). |
| GET | `/api/v1/admin/cube-metadata/{cube_id}` | `backend/src/api/routers/admin_cube_metadata.py` | `_get_metadata_cache_service` (`StatCanMetadataCacheService`) | n/a (query params) | 200 → `CubeMetadataCacheEntryResponse`; 400 → `PRIME_REQUIRES_PRODUCT_ID` (when `prime=true` without `product_id`); 401; 404 → `CUBE_NOT_IN_CACHE`; 503 → `STATCAN_UNAVAILABLE` (only when priming) | Phase 3.1b — autocomplete read source for the Flutter form. Default is read-only; `?prime=true&product_id=N` opts into auto-prime fetch. See DEBT-053. |

> Other admin routers / public routers exist in this codebase (e.g. clone publication endpoint referenced in A.1.6 fixture C, `_get_public_repo` / `_get_public_storage` / `get_gallery_limiter` deps observed in A.1.6 fixture B/D). The inputs consumed do not enumerate their handler signatures, so they are intentionally omitted here. **TBD** — fold in when their dedicated recon docs land.

---

## 2. Domain models

### Publication
File: `backend/src/models/publication.py` (column list, `models/publication.py:80-155`)

Version-relevant columns (per A.1.2 flag table):

| Column | Type | Notes |
|---|---|---|
| `id` | `int` | primary key, autoincrement |
| `updated_at` | `DateTime(timezone=True)`, **nullable** | `onupdate=func.now()` set at model level — fires only on ORM-style mutations, NOT on core-style `update().values(...)` (A.1.3) |
| `version` | `int`, `nullable=False`, `default=1`, `server_default="1"` | **Product-lineage version**, NOT a row-revision counter (A.1.2) |
| `config_hash` | `String(64)`, nullable | R19 lineage |
| `source_product_id` | `String(100)`, nullable, indexed | |
| `content_hash` | `String(64)`, nullable | |
| `cloned_from_publication_id` | `int`, FK → `publications.id` (`ondelete="SET NULL"`), nullable, indexed | |

Other columns (full list in source, `models/publication.py:80-155`): `headline`, `chart_type`, `s3_key_lowres`, `s3_key_highres`, `virality_score`, `status` (`Enum(PublicationStatus)`, default `DRAFT`), `created_at`, `eyebrow`, `description`, `source_text`, `footnote`, `visual_config`, `review`, `document_state`, `published_at` — 15 additional columns; see source file for types.

`__table_args__` (`models/publication.py:71-78`): unique constraint `uq_publication_lineage_version` on `(source_product_id, config_hash, version)`.

**Key gloss (A.1.2):** `updated_at` already exists with DB-level `onupdate=func.now()`; **ETag is derived per `docs/architecture/ARCHITECTURE_INVARIANTS.md` §7**, computed over `(id, updated_at OR created_at, config_hash OR "")` — not a persisted column. `version` is product-lineage version, NOT row-revision counter.

### Job
File: `backend/src/models/job.py` (`__tablename__ = "jobs"`)

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `int` PK | no | autoincrement | |
| `job_type` | `String(50)` | no | — | indexed |
| `status` | `Enum(JobStatus)` | no | `QUEUED` (`"queued"`) | |
| `payload_json` | `Text` | no | — | typed payload, see `job_payloads.py` |
| `result_json` | `Text` | yes | — | |
| `error_code` | `String(100)` | yes | — | DEBT-030 pattern |
| `error_message` | `Text` | yes | — | |
| `attempt_count` | `Integer` | no | `0` | |
| `max_attempts` | `Integer` | no | `3` | |
| `created_at` | `DateTime(tz)` | no | `now(utc)` | |
| `started_at` | `DateTime(tz)` | yes | — | timestamp for stale detection |
| `finished_at` | `DateTime(tz)` | yes | — | terminal timestamp |
| `created_by` | `String(100)` | yes | — | operator/system id |
| `dedupe_key` | `String(255)` | yes | — | indexed; partial unique index `ix_jobs_dedupe_active` per docstring |
| `subject_key` | `String(255)` | yes | — | indexed — **NOT mapped in Flutter `Job` model** |

**Indices (`models/job.py:65-68`):** `ix_jobs_type_status (job_type, status)`, `ix_jobs_created_at (created_at)`.

**Stale detection:** `started_at` + `finished_at` present; zombie reaper `JobRepository.requeue_stale_running` (`job_repository.py:202-234`) uses `started_at < now - 10min AND status == RUNNING AND attempt_count < max_attempts`.

**Relationships:** **None.** No `ForeignKey` and no `relationship(...)` on the `Job` model. Loose coupling via `payload_json` + optional `dedupe_key` / `subject_key` strings only.

**JobStatus enum values** (verbatim, `backend/src/models/job.py:30-37`):

```python
QUEUED = "queued"
RUNNING = "running"
SUCCESS = "success"
FAILED = "failed"
CANCELLED = "cancelled"
```

Note: Frontend has no `enum JobStatus`; `Job.status` is a plain `String`. Literals referenced in Flutter UI: `queued`, `running`, `success`, `failed`. **`cancelled` is never referenced in Flutter** — no UI path handles it (Phase 2.5 §1.2).

---

## 3. Repositories

### PublicationRepository
File: `backend/src/repositories/publication_repository.py`

Public method signatures (from A.1.3, no bodies):

```python
def __init__(self, session: AsyncSession) -> None
async def get_latest_version(self, source_product_id: str, config_hash: str) -> int | None
async def create_published(
    self, *, headline: str, chart_type: str, s3_key_lowres: str, s3_key_highres: str,
    source_product_id: str | None, version: int, config_hash: str, content_hash: str,
    virality_score: float | None = None,
    status: PublicationStatus = PublicationStatus.PUBLISHED,
) -> Publication
async def create(
    self, *, headline: str, chart_type: str,
    s3_key_lowres: str | None = None, s3_key_highres: str | None = None,
    virality_score: float | None = None,
    status: PublicationStatus = PublicationStatus.DRAFT,
) -> Publication
async def create_clone(
    self, *, source: Publication, new_headline: str, new_config_hash: str,
    new_version: int, fresh_review_json: str,
) -> Publication
async def get_published(self, limit: int, offset: int) -> list[Publication]
async def get_published_sorted(self, limit: int, offset: int, sort: str = "newest") -> list[Publication]
async def get_by_id(self, publication_id: int) -> Publication | None
async def get_drafts(self, limit: int) -> list[Publication]
async def update_status(self, publication_id: int, status: PublicationStatus) -> None
async def update_s3_keys(self, publication_id: int, s3_key_lowres: str, s3_key_highres: str) -> None
async def update_s3_keys_and_publish(
    self, publication_id: int, s3_key_lowres: str, s3_key_highres: str,
    status: PublicationStatus,
) -> None
async def create_full(self, data: dict[str, Any]) -> Publication
async def update_fields(self, pub_id: int, data: dict[str, Any]) -> Publication | None
async def publish(self, pub_id: int) -> Publication | None
async def unpublish(self, pub_id: int) -> Publication | None
async def list_by_status(
    self, status_filter: PublicationStatus | None, limit: int, offset: int,
) -> list[Publication]
```

Private helpers in source: `_published_order_clause`, `_serialize_visual_config`, `_serialize_review`, `_deserialize_review`.

**Key observations (A.1.3):**

- `get_published_sorted` **exists** (line 232) — memory fact-check ✅.
- `update_fields` (line 452) is the canonical PATCH update path. Uses `setattr(publication, key, value)` per key in `data`, then `await self._session.flush()` + `await self._session.refresh(publication)`. `updated_at` refresh relies on the SQLAlchemy `onupdate=func.now()` model-level trigger — at the ORM/DB layer, not in repository code.
- `update_status`, `update_s3_keys`, `update_s3_keys_and_publish` use core-style `update(...).values(...)`. Core-style `update()` does **NOT** trigger ORM `onupdate=` in SQLAlchemy 2.x → these paths do **not** bump `updated_at`. `publish` and `unpublish` use ORM-style attribute mutation → DO trigger `onupdate`.

### JobRepository
File: `backend/src/repositories/job_repository.py`

Public methods referenced in inputs (Phase 2.5 §1.4–§1.5):

- `retry_failed_job(...)` (line 250) — invoked by `POST /api/v1/admin/jobs/{job_id}/retry`. Raises `NotFoundError` (404) / `ConflictError` (409 — "Job is not retryable").
- `requeue_stale_running(...)` (lines 202–234) — zombie reaper. Predicate: `started_at < now - 10min AND status == RUNNING AND attempt_count < max_attempts`.
- `count_jobs(...)` (referenced from §1.4 pagination summary) — backs the `total` field on `JobListResponse`.
- List query (line 190) — orders by `created_at DESC`.

Full public method list **not enumerated in inputs** — flagged **TBD** (will need follow-up when the full repository signature recon happens; do NOT grep ad-hoc to fill this section).

---

## 4. Exception handlers

### Registration entry point
File: `backend/src/core/error_handler.py:112` — `register_exception_handlers(app: FastAPI) -> None`. Called once from `backend/src/main.py:151`.

Body (verbatim, `error_handler.py:112-123`):

```python
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        SummaVisionError,
        _summa_vision_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(RequestValidationError, _publication_validation_exception_handler)
    app.add_exception_handler(
        PublicationPreconditionFailedError,
        _publication_precondition_failed_exception_handler,
    )  # Phase 1.3
```

### Existing handlers

- **`_publication_validation_exception_handler`** — `backend/src/core/error_handler.py:87-109`
  - Registered for: `RequestValidationError`
  - Wraps body via `jsonable_encoder`: ✅ **yes** (line 95 + line 108) — DEBT-030 PR1 hotfix in place. Import: `from fastapi.encoders import jsonable_encoder` (line 23).
  - Status code returned: `422 UNPROCESSABLE_CONTENT`
  - Branch logic: when `request.url.path.startswith("/api/v1/admin/publications/") AND request.method == "PATCH"`, returns the structured envelope; otherwise returns the raw `{"detail": exc.errors()}` shape.
  - Envelope shape (PATCH branch): `{"detail": {"error_code": "PUBLICATION_UPDATE_PAYLOAD_INVALID", "message": "The submitted changes are invalid.", "details": {"validation_errors": exc.errors()}}}`
  - Pattern reference for: any new structured error handler.

- **`_summa_vision_exception_handler`** — `backend/src/core/error_handler.py:53-84`
  - Registered for: `SummaVisionError` (and subclasses)
  - Serves the older **flat** `{"error_code", "message", "detail"}` envelope (no nested `"detail"` wrapper). This differs from the `PublicationApiError` hierarchy (see §5).

### Critical implementation note
Any new exception handler that returns JSON MUST wrap the response body via `fastapi.encoders.jsonable_encoder` before `JSONResponse(...)`. Pydantic v2 internals can produce non-JSON-serializable objects (e.g. `ValueError` in `ctx.error`) → handler returns 500 instead of intended status. Reference: DEBT-030 PR1 hotfix.

---

## 5. Error envelope contract (DEBT-030)

> **Note:** there is **no class named `BackendApiError`** in the repo. The role implied by that name is filled by **two separate** hierarchies — see below.

### Hierarchy A — `PublicationApiError` (HTTP-side, `HTTPException` subclass)

File: `backend/src/services/publications/exceptions.py`

Wire envelope (FastAPI wraps `HTTPException.detail` automatically; `details` only appears when the caller passes `details=`):

```json
{
    "detail": {
        "error_code": "PUBLICATION_NOT_FOUND",
        "message": "Publication not found.",
        "details": { "publication_id": 999999, "current_status": "DRAFT" }
    }
}
```

### Hierarchy B — `SummaVisionError` (domain-side, custom global handler)

File: `backend/src/core/exceptions.py:21`. Subclasses (all in `core/exceptions.py`): `WorkbenchError`, `DataSourceError`, `AIServiceError`, `StorageError`, `ValidationError`, `AuthError`, `NotFoundError`, `ConflictError`, `ESPPermanentError`, `ESPTransientError`.

Wire envelope (served by `_summa_vision_exception_handler`, `error_handler.py:53-84`) — **flat** shape, no nested `"detail"` wrapper:

```json
{
    "error_code": "DATASOURCE_ERROR",
    "message": "StatCan WDS returned HTTP 503",
    "detail": { "url": "...", "status_code": 503 }
}
```

### Existing `error_code` values (verbatim from A.1.5)

| `error_code` | HTTP status | Class | File |
|---|---|---|---|
| `PUBLICATION_UNKNOWN_ERROR` | 400 (default `status_code_value`) | `PublicationApiError` (base) | `backend/src/services/publications/exceptions.py:20` |
| `PUBLICATION_UPDATE_PAYLOAD_INVALID` | 422 | `PublicationUpdatePayloadInvalidError` | `backend/src/services/publications/exceptions.py:48` |
| `PUBLICATION_NOT_FOUND` | 404 | `PublicationNotFoundError` | `backend/src/services/publications/exceptions.py` (subclass) |
| `PUBLICATION_INTERNAL_SERIALIZATION_ERROR` | 500 | `PublicationInternalSerializationError` | `backend/src/services/publications/exceptions.py:52,56` |
| `PUBLICATION_CLONE_NOT_ALLOWED` | 409 | `PublicationCloneNotAllowedError` | `backend/src/services/publications/exceptions.py` (subclass) |
| `PRECONDITION_FAILED` | 412 | `PublicationPreconditionFailedError` | `backend/src/services/publications/exceptions.py` (Phase 1.3) |
| `SUMMA_VISION_ERROR` (default) | — | `SummaVisionError` (base) | `backend/src/core/exceptions.py:21` |

Existing test assertions against this envelope (from A.1.5):

- `backend/tests/api/test_admin_publications.py:683-698` — asserts `body["detail"]["error_code"] == "PUBLICATION_NOT_FOUND"` and `body["detail"]["message"] == "Publication not found."` on 404.
- `backend/tests/api/test_admin_publications.py:736-758` — asserts `body["detail"]["error_code"] == "PUBLICATION_UPDATE_PAYLOAD_INVALID"` and `"validation_errors" in body["detail"]["details"]` on 422.

### Namespacing (Option C hybrid per DEBT-030)
- Domain-specific keys: `publication.*`
- Cross-cutting backend errors: `errors.backend.<code_lowercase>`

### Envelope unification
DEBT-034 tracks the auth-side flat-envelope unification follow-up. **Do not bundle.**

---

## 6. Integration test fixture pattern

### Canonical fixture (PATCH publications)
File: `backend/tests/api/test_admin_publications.py:81-113`
Fixture name: `_make_app(session_factory) -> FastAPI`

Fixture body (verbatim, A.1.6):

```python
def _make_app(session_factory) -> FastAPI:
    """Build a FastAPI app with the publications router + auth middleware."""
    app = FastAPI()
    register_exception_handlers(app)               # ← DEBT-030 PR1 lesson: present
    app.include_router(router)

    async def _override_repo() -> AsyncGenerator[PublicationRepository, None]:
        async with session_factory() as session:
            try:
                yield PublicationRepository(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_audit() -> AsyncGenerator[AuditWriter, None]:
        async with session_factory() as session:
            try:
                yield AuditWriter(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[_get_repo] = _override_repo
    app.dependency_overrides[_get_audit] = _override_audit

    app.add_middleware(AuthMiddleware, admin_api_key="test-admin-key")
    return app
```

### Required dependency overrides
The fixture MUST override every `Depends(...)` the endpoint uses. Verbatim override list from A.1.6:

- `_get_repo` → `_override_repo` (yields `PublicationRepository(session)`)
- `_get_audit` → `_override_audit` (yields `AuditWriter(session)`)

**Override count:** 2. **DB:** in-memory SQLite via per-test `engine` fixture (`test_admin_publications.py:61-78`); schema via `Base.metadata.create_all`. **Auth:** `AuthMiddleware` with `admin_api_key="test-admin-key"`.

### Required side effects
- MUST call `register_exception_handlers(app)` (DEBT-030 PR1 lesson — present at line 88 in canonical fixture).
- For Postgres-backed integration tests: use `subprocess.run(['alembic', 'upgrade', 'head'])` (not the programmatic Alembic API).
- Teardown: `alembic downgrade base` (drops PostgreSQL enum types).

### Sibling fixtures in same file (drift watchlist, A.1.6)

- **Fixture B — `_make_admin_and_public_app`** (`test_admin_publications.py:565-601`): 5 overrides (`_get_repo`, `_get_audit`, `_get_public_repo`, `_get_public_storage`, `get_gallery_limiter`). **Does NOT call `register_exception_handlers`** ❌ — any new structured-envelope test reusing this fixture will hit the DEBT-030 PR1 trap.
- **Fixture C — `test_clone_publication_endpoint._make_app`** (`test_clone_publication_endpoint.py:37`): 3 overrides (`get_db`, `_get_repo`, `_get_audit`). `register_exception_handlers` call status not captured by the inputs grep — **TBD**.
- **Fixture D — `test_publication_review_persistence.py`**: 5 overrides (`_get_repo`, `_get_audit`, `_get_public_repo`, `_get_public_storage`, `get_gallery_limiter`). `register_exception_handlers` call status not captured by the inputs grep — **TBD**.

> Note: there is **no** `backend/tests/integration/` file targeting publication PATCH (A.1.6). Canonical PATCH coverage is router-level under `backend/tests/api/test_admin_publications.py` (in-memory SQLite + DI overrides).

### Drift signal
If a new endpoint dep isn't in the override list, integration tests will pass while the endpoint hits the prod DB pool in the test event loop → asyncpg "attached-to-different-loop" errors + 404s (memory item, Phase 1.1 PR165 lesson).

---

## 7. Maintenance log

| Date | PR | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from Phase 1.3 Part A (`docs/recon/phase-1-3-A-backend-inventory.md`) + Phase 2.5 Part B (`docs/discovery/phase-2-5-B-model.md` §1.4 + §1.5) inputs |
| 2026-04-27 | Phase 1.3 impl | §1 PATCH row, §2 Publication gloss, §4 handler registration, §5 error-code table | Added 412 `PRECONDITION_FAILED` row; PATCH now consumes `If-Match` and emits `ETag` on success; GET-single + POST-clone also emit `ETag`. |
