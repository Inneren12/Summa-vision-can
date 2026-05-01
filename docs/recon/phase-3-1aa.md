# Phase 3.1aa Recon — `cube_metadata_cache` + `StatCanMetadataCacheService`

## 0) Verification preflight

### Commands and outputs

```bash
git status --porcelain
# (no output)

git remote -v
# (no output)

git branch --show-current
# work
```

Result: workspace is clean; no remote configured in this sandbox.

---

## §A. StatCan API surface investigation

### A1. Existing `StatCanClient` surface

`backend/src/services/statcan/client.py` contains only a generic resilient HTTP wrapper with `get()` and `request()`; it does **not** expose a dedicated `get_cube_metadata()` helper yet. `request()` enforces maintenance-window guard, rate-limit acquire, retry on 429/409/503, and maps network/retry exhaustion to `DataSourceError`.【F:backend/src/services/statcan/client.py†L54-L181】

Maintenance guard behavior: the client checks `self._maintenance_guard.is_maintenance_window(now)` and raises `DataSourceError(error_code="DATASOURCE_MAINTENANCE")`. There is no `MaintenanceWindowError` class used in this module.【F:backend/src/services/statcan/client.py†L121-L129】

Rate-limit posture source: `AsyncTokenBucket` defaults are documented in `core.md` (`capacity=10`, `refill_rate=10.0`) and implementation requires explicit constructor args in `rate_limit.py`; callers must pass configured values or this code path breaks. This is an existing mismatch in docs vs implementation to flag, not reinterpret.【F:docs/modules/core.md†L118-L123】【F:backend/src/core/rate_limit.py†L38-L43】

`StatCanETLService.fetch_todays_releases()` currently performs the only in-repo `getCubeMetadata` call flow: POST to `https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata` with `json=[{"productId": ...}]`, then validates successful objects into `CubeMetadataResponse`.【F:backend/src/services/statcan/service.py†L69-L111】

### A2. `schemas.py` shape confirmation

`DimensionSchema` fields:
- `dimension_name_en: str`
- `dimension_name_fr: str`
- `dimension_position_id: int`
- `has_uom: bool`【F:backend/src/services/statcan/schemas.py†L41-L48】

`CubeMetadataResponse` fields:
- `product_id: int`
- `cube_title_en: str`
- `cube_title_fr: str`
- `cube_start_date: datetime | None`
- `cube_end_date: datetime | None`
- `frequency_code: int`
- `scalar_factor_code: int` (validator coerces string→int)
- `member_uom_code: int | None`
- `dimensions: list[DimensionSchema]` aliased from API key `dimension`
- `subject_code/survey_en/survey_fr/corrections_en/corrections_fr: str | None`【F:backend/src/services/statcan/schemas.py†L50-L102】

### A3. `getCubeMetadata` API contract (for impl)

From existing callsite in `service.py`:
- Endpoint: `https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata`
- Method: POST
- Request body: list of objects with `productId` key
- Response consumed as list of envelopes; each successful envelope has `status == "SUCCESS"` and payload in `object` key.【F:backend/src/services/statcan/service.py†L95-L109】

WDS guide reference to cite in impl doc only (not fetched in this recon):
- `https://www.statcan.gc.ca/en/developers/wds/user-guide`

### A4. Open question (do not resolve): `semantic_mappings.cube_id` format

3.1a migration defines `semantic_mappings.cube_id` as `sa.String(length=50)` (not integer), and uniqueness is `(cube_id, semantic_key)`. Therefore this is an unresolved mapping-format question vs WDS `productId` requirement. If semantic IDs are dash-form (e.g. `18-10-0004-01`), 3.1aa needs deterministic parse/lookup to numeric `productId`; if already numeric strings, validate format boundary explicitly.【F:backend/migrations/versions/f3b8c2e91a4d_add_semantic_mappings.py†L30-L56】

---

## §B. Cache table design (`cube_metadata_cache`)

### B1. Proposed migration/ORM schema

- `id BIGINT PK`
- `cube_id VARCHAR(50) NOT NULL UNIQUE`
- `product_id INTEGER NOT NULL`
- `dimensions JSONB NOT NULL`
- `frequency_code VARCHAR(8) NULL` (string-normalized for codes; source currently int in schema)
- `cube_title_en VARCHAR(255) NULL`
- `cube_title_fr VARCHAR(255) NULL` (recommended keep for parity with existing bilingual metadata model conventions)
- `fetched_at TIMESTAMPTZ NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- omit `source_etag` unless API proves header/field exists (no evidence in current call path).

### B2. `dimensions` JSONB normalized shape

Store normalized validation-focused payload:

```json
{
  "dimensions": [
    {
      "position_id": 1,
      "name_en": "Geography",
      "name_fr": "Géographie",
      "has_uom": false,
      "members": [
        {"member_id": 1, "name_en": "Canada", "name_fr": "Canada"}
      ]
    }
  ]
}
```

Note: current `DimensionSchema` does **not** include members; recon found only top-level dimension fields. So 3.1aa likely needs schema extension or a parallel raw response model to include members used by validator. Flag for founder approval before impl.【F:backend/src/services/statcan/schemas.py†L41-L48】

Recommendation: persist only fields required for validation + user-readable diagnostics; drop transient/unneeded fields (`terminated`, etc.) at write time unless future use is planned.

### B3. Indexes

- `uq_cube_metadata_cache_cube_id` (unique constraint on `cube_id`)
- `ix_cube_metadata_cache_fetched_at` (staleness scan)
- Optional: `ix_cube_metadata_cache_product_id` only if reverse lookup by product id is a planned query path; otherwise skip.

### B4. ORM `__table_args__` invariant

Mirror migration index names exactly in model `__table_args__`, following 3.1a pattern where explicit index/constraint names are used in migration and model-level table args exist for constraints/indexes.【F:backend/migrations/versions/f3b8c2e91a4d_add_semantic_mappings.py†L54-L62】【F:backend/src/models/semantic_mapping.py†L31-L36】

Proposed model snippet (for impl doc):

```python
__table_args__ = (
    sa.UniqueConstraint("cube_id", name="uq_cube_metadata_cache_cube_id"),
    sa.Index("ix_cube_metadata_cache_fetched_at", "fetched_at"),
)
```

### B5. Migration chain

Down revision should be `f3b8c2e91a4d`; filename pattern `<sha>_add_cube_metadata_cache.py`.

---

## §C. `StatCanMetadataCacheService` design

### C1. Module location

Use `backend/src/services/statcan/metadata_cache.py` (sibling to existing `client.py`/`service.py`).【F:docs/modules/statcan.md†L8-L16】

### C2. DI type conventions

- Session factory convention in repo uses `get_session_factory()` returning `async_sessionmaker[AsyncSession]`; there is no existing `AsyncSessionFactory` alias in scanned code, so 3.1aa should introduce one in `core/database.py` or use concrete `async_sessionmaker[AsyncSession]` in signatures for consistency.
- Clock convention exists as `Callable[[], datetime]` in `TempUploadCleaner`; use same shape unless a project-wide `Clock` alias is added in `core/types` during impl.【F:backend/src/core/database.py†L62-L70】【F:backend/src/services/storage/temp_cleanup.py†L248-L250】

### C3. Proposed public methods

```python
async def get_cached(cube_id: str) -> CubeMetadataCacheEntry | None
async def get_or_fetch(cube_id: str) -> CubeMetadataCacheEntry
async def refresh(cube_id: str, *, force: bool = False) -> CubeMetadataCacheEntry
async def refresh_all_stale(stale_after: timedelta) -> RefreshSummary
```

Error surface for 3.1aa service module:
- `CubeNotFoundError`
- `StatCanUnavailableError`

### C4. Idempotency/change detection strategy

Prefer repo-level explicit change detection (aligned with `SemanticMappingRepository.upsert_by_key`) to avoid unnecessary `updated_at` bump: compare normalized JSON + metadata fields before mutating ORM object; no-op path returns existing row unchanged.【F:backend/src/repositories/semantic_mapping_repository.py†L100-L116】

#### Pseudocode — upsert with no-op detection

```python
existing = repo.get_by_cube_id(cube_id)
if not existing:
    insert(..., fetched_at=now)
    return created

normalized = normalize(statcan_payload)
if existing.dimensions == normalized.dimensions and existing.frequency_code == normalized.frequency_code and ...:
    return existing  # do not touch updated_at

existing.dimensions = normalized.dimensions
existing.frequency_code = normalized.frequency_code
existing.fetched_at = now
flush()
return existing
```

### C5. Domain return type

Project pattern today returns ORM entities directly from repositories (`SemanticMappingRepository` methods return `SemanticMapping`). For service API boundary in 3.1aa, prefer an immutable dataclass DTO `CubeMetadataCacheEntry` to keep ORM internal, but this is a small convention extension to approve explicitly.【F:backend/src/repositories/semantic_mapping_repository.py†L33-L59】

#### Pseudocode — concurrent `get_or_fetch`

```python
cached = await repo.get_by_cube_id(cube_id)
if cached:
    return cached

payload = await statcan.fetch_cube_metadata(product_id)
try:
    await repo.insert_unique(cube_id, payload)  # ON CONFLICT DO NOTHING
except UniqueViolation:
    pass

return await repo.get_by_cube_id(cube_id)  # winner or loser both read final row
```

---

## §D. APScheduler warm refresh job

### D1/D3. Wiring and persistence

Scheduler is centralized in `backend/src/core/scheduler.py`, using `SQLAlchemyJobStore` and a singleton `AsyncIOScheduler`; new job must be added through `start_scheduler()` `add_job(...)` path (no parallel scheduler).【F:backend/src/core/scheduler.py†L45-L62】【F:backend/src/core/scheduler.py†L202-L267】

### D2. Proposed job

- ID: `statcan_metadata_cache_refresh`
- Trigger: `cron`
- Time: daily `15:00 UTC` (10:00 EST / 11:00 EDT), safely outside 00:00–08:30 EST maintenance window
- Params: `coalesce=True`, `max_instances=1`, `misfire_grace_time=3600`, `replace_existing=True`
- Action: `refresh_all_stale(stale_after=timedelta(hours=23))`

### D4. Observability keys

- Start log: `job_id`, `stale_after_hours`, `started_at`
- Per cube debug: `cube_id`, `status` (`refreshed|failed|skipped`), `error_code`, `duration_ms`
- End summary info: `refreshed_count`, `failed_count`, `skipped_count`, `duration_ms`

#### Pseudocode — stale sweep loop

```python
rows = await repo.list_stale(before=clock()-stale_after)
summary = RefreshSummary(refreshed=0, failed=0, skipped=0)
for row in rows:
    try:
        await refresh(row.cube_id)
        summary.refreshed += 1
    except Exception as exc:
        log.debug(...)
        summary.failed += 1
return summary
```

---

## §E. Validator integration contract (3.1ab)

### E1

Using `get_cached(cube_id)` (not `get_or_fetch`) for validator is aligned with founder-locked cache-required mode: save should fail only when no cache row exists; stale cached row is acceptable.

### E2. Error hierarchy to ship in 3.1aa

```python
class MetadataValidationError(Exception): ...
class CubeNotInCacheError(MetadataValidationError): ...
class DimensionMismatchError(MetadataValidationError): ...
class MemberMismatchError(DimensionMismatchError): ...  # optional granularity
```

### E3. Open question

Should admin “create mapping” flow call `get_or_fetch` on first-use cube to auto-prime cache, or keep strict pre-warm requirement and let save fail with `CubeNotInCacheError`?

---

## §F. Test plan inventory (recon only)

Proposed count:
- Repository unit tests: 5
- Service unit tests: 8
- Scheduler unit tests: 2
- Integration tests: 1
- **Total: 16 tests**

Async mock invariant reference: architecture mandates `AsyncMock` for async test mocks.【F:docs/architecture/ARCHITECTURE_INVARIANTS.md†L89-L92】

Integration migration pattern note is consistent with prior direction to run alembic upgrade/downgrade in test lifecycle (carry into impl test).

---

## §G. DEBT, glossary, ROADMAP, architecture-doc touch plan

### G1. DEBT proposals

#### DEBT-045 (proposed)
1. **ID:** DEBT-045
2. **Title:** Event-driven StatCan metadata cache invalidation via `getChangedCubeList`
3. **Status:** Proposed
4. **Created:** 2026-05-01
5. **Owner:** Backend
6. **Area:** StatCan integration / scheduler
7. **Impact:** Nightly blind refresh over-fetches and delays propagation of daytime cube changes
8. **Plan:** Add delta refresh path keyed by changed `productId` set, fallback to nightly stale sweep
9. **Exit criteria:** Cache refresh job primarily uses change feed; full sweep retained as safety fallback

#### DEBT-046 (proposed)
1. **ID:** DEBT-046
2. **Title:** Unify StatCan maintenance exception taxonomy
3. **Status:** Proposed
4. **Created:** 2026-05-01
5. **Owner:** Backend
6. **Area:** Error handling
7. **Impact:** Recon request references `MaintenanceWindowError`, code currently emits `DataSourceError(DATASOURCE_MAINTENANCE)` only
8. **Plan:** Decide whether to keep single `DataSourceError` mapping or add explicit domain wrapper used by metadata cache service
9. **Exit criteria:** One documented/implemented contract used consistently in client/service/tests

### G2

No glossary additions required (backend internal concepts only).

### G3

ROADMAP 3.1aa entry should get PR placeholder in impl PR (recon does not edit).

### G4. Files to touch in impl phase (planned)

- CREATE `backend/migrations/versions/<sha>_add_cube_metadata_cache.py`
- CREATE `backend/src/models/cube_metadata_cache.py`
- CREATE `backend/src/repositories/cube_metadata_cache_repository.py`
- CREATE `backend/src/services/statcan/metadata_cache.py`
- MODIFY `backend/src/services/statcan/client.py` (optional helper method for `getCubeMetadata`)
- MODIFY `backend/src/services/statcan/schemas.py` (if member list schema extension needed)
- MODIFY `backend/src/core/scheduler.py` (register refresh job)
- MODIFY `docs/modules/statcan.md`
- MODIFY `docs/architecture/BACKEND_API_INVENTORY.md`
- MODIFY `DEBT.md`
- Optional MODIFY `_DRIFT_DETECTION_TEMPLATE.md` (if drift tracking policy requires schema additions)

---

## Appendix: Commands used for evidence

```bash
rg --files | rg 'statcan.md|core.md|BACKEND_API_INVENTORY.md|ARCHITECTURE_INVARIANTS.md|f3b8c2e91a4d|backend/src/services/statcan/(client|schemas|service)\.py|backend/src/core/scheduler\.py|semantic_mappings'
# backend/src/services/statcan/schemas.py
# backend/src/services/statcan/client.py
# backend/src/services/statcan/service.py
# backend/src/core/scheduler.py
# backend/scripts/seed_semantic_mappings.py
# backend/migrations/versions/f3b8c2e91a4d_add_semantic_mappings.py
# docs/modules/core.md
# docs/modules/statcan.md
# docs/architecture/BACKEND_API_INVENTORY.md
# docs/architecture/ARCHITECTURE_INVARIANTS.md

nl -ba backend/src/services/statcan/client.py
nl -ba backend/src/services/statcan/schemas.py
nl -ba backend/src/services/statcan/service.py
nl -ba backend/src/core/rate_limit.py
nl -ba backend/src/core/scheduler.py
nl -ba backend/migrations/versions/f3b8c2e91a4d_add_semantic_mappings.py
nl -ba backend/src/repositories/semantic_mapping_repository.py
nl -ba backend/src/core/database.py
nl -ba backend/src/services/storage/temp_cleanup.py | sed -n '220,320p'
nl -ba docs/modules/statcan.md | sed -n '1,260p'
nl -ba docs/modules/core.md | sed -n '1,260p'
nl -ba docs/architecture/ARCHITECTURE_INVARIANTS.md | sed -n '1,260p'
nl -ba docs/architecture/BACKEND_API_INVENTORY.md | sed -n '1,220p'
```
