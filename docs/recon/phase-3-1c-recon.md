# Phase 3.1c Recon — Resolve Endpoint Implementation Plan

## §1. Header + scope summary
- Branch: `claude/phase-3-1c-recon` (created from current `work` baseline because local `main` branch is absent, matching pre-recon branch note). (pre-recon §A header)
- Date: 2026-05-03 (UTC).
- Scope: read-only recon to lock implementation contract for singular resolve endpoint and downstream impl PR content. (pre-recon §E5)
- L1: Endpoint vocabulary locked to singular `GET /resolve/{cube_id}/{semantic_key}` only (no batch in 3.1c). (pre-recon §A header)
- L2: ResolvedValue MUST include `resolved_at` and `source_hash` (`resolved_at` aliases `fetched_at`, no schema migration). (pre-recon §F2)
- R1: `units` source locked to `mapping.config.unit` if string else `null`; no metadata derivation in 3.1c; DEBT-060 remains open. (pre-recon §G2, pre-recon §F2)
- R2: Error envelope locked to flat handler-detail style (`HTTPException(detail={error_code,message,details?})`) consistent with admin semantic mappings. (pre-recon §A2, pre-recon §G2)
- R3: Route lives under `/api/v1/admin/...` and relies on existing `AuthMiddleware` X-API-KEY enforcement. (pre-recon §A1, pre-recon §G2)
- C1: Inactive mapping must be treated as not found → 404 `SEMANTIC_MAPPING_NOT_FOUND`. (pre-recon §D4)
- C2: Cache-miss path must execute the 8-step state machine including auto-prime and re-query before terminal miss error. (pre-recon §E5)
- In-scope debt continuity: DEBT-060 (units enrichment) and DEBT-062 / P3-024 (prime-on-refresh gap) remain open and unchanged by 3.1c. (pre-recon §B4, pre-recon §E5)
- Explicitly out of scope: DEBT-048 envelope migration, DEBT-058/059 batch resolve tracks.

## §2. Endpoint contract

### §2.1 URL pattern
- **Route:** `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}`.
- **Trailing slash policy:** follow existing admin convention where collection roots use empty-string route (`""`) and subpaths omit trailing slash (e.g., `/upsert`, `/{mapping_id}`), so resolve path should be declared without trailing slash. (`backend/src/api/routers/admin_semantic_mappings.py:150-152`, `backend/src/api/routers/admin_semantic_mappings.py:247-249`, `backend/src/api/routers/admin_semantic_mappings.py:281-283`)
- **Auth tier:** `/api/v1/admin/...` ensures middleware protection; no endpoint-local auth wiring. (`backend/src/core/security/auth.py:46-53`, `backend/src/core/security/auth.py:122-166`)

### §2.2 Path param validation
- `cube_id: str = Path(..., min_length=1, max_length=50)` (DB cap from `semantic_value_cache.cube_id varchar(50)`). (pre-recon §B1)
- `semantic_key: str = Path(..., min_length=1, max_length=100)` (DB cap from `semantic_value_cache.semantic_key varchar(100)`). (pre-recon §B1)
- Regex/pattern: **no additional regex** in 3.1c; existing 3.1b admin semantic mapping handlers do not enforce regex on `cube_id`/`semantic_key`, only typed fields and length/range validators. (`backend/src/api/routers/admin_semantic_mappings.py:255-259`)

### §2.3 Query params
Resolve accepts exactly two query inputs:

1) `coord: str` (required)
- Type: string, required.
- Validation: `min_length=1`, `max_length=50`; pattern `^\d+(\.\d+){9}$` (10 dot-separated numeric slots), matching existing coord encoding helper output. (`backend/src/services/semantic/coord.py:22-33`, `backend/src/services/semantic/coord.py:41-61`, pre-recon §B1)
- Source-of-truth: caller-provided resolved coord string.
- Rationale: auto_prime writes cache rows using `derive_coord(resolved_filters)` and persists that exact string as `coord`; resolve must query by exact same opaque coord format to hit cache. (`backend/src/services/statcan/value_cache.py:111-112`, `backend/src/services/statcan/value_cache.py:408-413`)

2) `period: str | None = Query(default=None, max_length=20, alias="period")`
- Type: optional string.
- Validation: max length 20 (DB cap for `ref_period`), no regex hardening in 3.1c to avoid rejecting valid StatCan period formats not currently enumerated. (pre-recon §B1)
- Source-of-truth: caller-specified StatCan `ref_period` token when present; otherwise endpoint selects latest row from returned set.
- Default behavior when omitted: use latest cached row for `(cube_id, semantic_key, coord)` by sorting returned rows and picking newest (see §8 contract).

### §2.4 Response shape — ResolvedValue DTO
Final schema (Pydantic V2) for route response:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResolvedValueResponse(BaseModel):
    cube_id: str = Field(description="Cube identifier.")
    semantic_key: str = Field(description="Semantic mapping key.")
    coord: str = Field(description="StatCan 10-slot coordinate string echoed from cache row.")
    period: str = Field(description="Resolved period token (ref_period).")
    value: str = Field(description="Canonical stringified numeric value.")
    resolved_at: datetime = Field(description="Alias of cache row fetched_at timestamp.")
    source_hash: str = Field(description="Opaque cache provenance hash.")
    is_stale: bool = Field(description="Persisted stale marker from cache row.")
    units: str | None = Field(
        default=None,
        description="Unit from mapping.config.unit if string, else null.",
    )
    cache_status: str = Field(description='"hit" or "primed" based on resolve state machine.')
    mapping_version: int | None = Field(
        default=None,
        description="Optional semantic mapping version echoed for client observability.",
    )
    prime_warning: str | None = Field(
        default=None,
        description="Sanitized prime warning code/category if auto_prime reported error but row was returned.",
    )

    model_config = ConfigDict(populate_by_name=True)
```

Mapping notes:
- `period` maps from `row.ref_period` (not `period_start`) for stable caller echo and query parity. (pre-recon §F2)
- `resolved_at` maps from `row.fetched_at` (L2 lock). (pre-recon §F2)
- `units` source is strictly `mapping.config.unit | None` (R1).
- `cache_status` enum literals in 3.1c: `"hit" | "primed"` only (no `"stale"` literal; staleness remains separate `is_stale`). (pre-recon §F2)

### §2.5 Status codes + error responses
- **200 OK**: returns `ResolvedValueResponse` with no custom headers.
- **404 `SEMANTIC_MAPPING_NOT_FOUND`**: mapping absent OR `is_active=False` (C1).
  - `detail = {"error_code": "SEMANTIC_MAPPING_NOT_FOUND", "message": "...", "details": {"cube_id": ..., "semantic_key": ...}}`
- **404 `RESOLVE_CACHE_MISS`**: cache still empty after auto-prime + re-query (C2 step 8).
  - `detail = {"error_code":"RESOLVE_CACHE_MISS","message":"...","details":{"cube_id":...,"semantic_key":...,"coord":...,"period":...,"prime_attempted":true,"prime_error_code":<sanitized|None>}}`
- **400 `RESOLVE_INVALID_COORD`**: service-level rejection when `coord` fails semantic validation that passes shape checks (e.g., non-canonical or all-zero forbidden rule if adopted in helper). FastAPI handles basic shape/length as 422.
- **422 Unprocessable Entity**: FastAPI validation for path/query bounds/pattern/type.
- **401 Unauthorized**: emitted by `AuthMiddleware`, not route handler.
- **500 `RESOLVE_INTERNAL_ERROR`**: defensive handler catch for unexpected programmer/runtime failures outside expected state machine; returns flat envelope and logs error. `auto_prime` swallows expected data-source/parse/persist failures into result.error, but other exceptions (e.g., mapping serialization bug) can still leak and should be normalized at handler boundary. (`backend/src/services/statcan/value_cache.py:110-173`)

### §2.6 Headers
- No special response headers in 3.1c v1 (no ETag, no Cache-Control override).
- Justification: existing semantic mapping admin routes do not set custom headers except publication concurrency paths in another router; resolve follows semantic-mappings shape. (`backend/src/api/routers/admin_semantic_mappings.py:150-253`)

## §3. Error code registry additions
Add constants in `backend/src/core/error_codes.py` (flat code registry path used by admin handlers and DEBT-030 conventions). (pre-recon §A2)

| error_code | HTTP | when raised | message template (EN) |
|---|---:|---|---|
| `SEMANTIC_MAPPING_NOT_FOUND` | 404 | Active mapping lookup misses or mapping is inactive (C1) | `Semantic mapping not found for cube_id='{cube_id}' and semantic_key='{semantic_key}'.` |
| `RESOLVE_CACHE_MISS` | 404 | After auto-prime attempt + mandatory re-query still no rows (C2 step 8) | `No cached value available for requested lookup after prime attempt.` |
| `RESOLVE_INVALID_COORD` | 400 | Caller-provided `coord` is syntactically/semantically invalid for resolve contract | `Invalid coord format; expected 10 dot-separated numeric positions.` |
| `RESOLVE_INTERNAL_ERROR` | 500 | Unexpected unclassified exception in resolve handler/service | `Internal resolve error. Please retry or contact support.` |

i18n: Yes, frontend Phase 3.2 should map wire error codes to display keys per DEBT-030 code→i18n mapping pattern; impl PR should ensure new codes are added to whichever translation mapping layer currently consumes error codes.

## §4. Repository / service surface changes

### 4.1 Active mapping lookup path (C1 decision)
- **Pick:** repository extension path (preferred over service-only guard for explicitness and reuse).
- **File:** `backend/src/repositories/semantic_mapping_repository.py`
- **Signature:**
  ```python
  async def get_active_by_key(self, cube_id: str, semantic_key: str) -> SemanticMapping | None:
      ...
  ```
- **Justification:** pre-recon §D4 allows both paths; explicit repo contract reduces future caller mistakes vs hidden service guard.

### 4.2 Resolve service
- **File:** `backend/src/services/resolve/service.py` (new module under services).
- **Class + signatures:**
  ```python
  class ResolveService:
      def __init__(
          self,
          *,
          mapping_session_factory: async_sessionmaker[AsyncSession],
          mapping_repository_factory: type[SemanticMappingRepository],
          value_cache_service: StatCanValueCacheService,
          logger: structlog.stdlib.BoundLogger,
      ) -> None: ...

      async def resolve_value(
          self,
          *,
          cube_id: str,
          semantic_key: str,
          coord: str,
          period: str | None,
      ) -> ResolvedValueResponse: ...
  ```
- **DI/session ownership:** match §A5 pattern — `StatCanValueCacheService` keeps owning its internal short-lived sessions; resolve service opens a separate short-lived mapping session via session factory for mapping lookup only. (pre-recon §A5)

### 4.3 Coord helper reuse/extension
- **File:** `backend/src/services/semantic/coord.py` (reuse existing pure helper + add parser/validator helper if needed).
- **Signature additions:**
  ```python
  def validate_coord(coord: str) -> str: ...
  ```
- **Rationale:** auto_prime already uses `derive_coord(...)` from this module; keeping resolve coord contract here centralizes encoding semantics and avoids drift. (`backend/src/services/statcan/value_cache.py:38`, `backend/src/services/statcan/value_cache.py:111`)

## §5. Resolve flow pseudocode

### §5.1 Handler pseudocode
```python
@router.get("/resolve/{cube_id}/{semantic_key}", response_model=ResolvedValueResponse)
async def resolve_value_handler(
    cube_id: str = Path(..., min_length=1, max_length=50),
    semantic_key: str = Path(..., min_length=1, max_length=100),
    coord: str = Query(..., min_length=1, max_length=50, pattern=r"^\d+(\.\d+){9}$"),
    period: str | None = Query(default=None, max_length=20),
    service: ResolveService = Depends(_get_resolve_service),
):
    try:
        return await service.resolve_value(
            cube_id=cube_id,
            semantic_key=semantic_key,
            coord=coord,
            period=period,
        )
    except MappingNotFoundForResolveError as exc:
        raise HTTPException(404, detail={...SEMANTIC_MAPPING_NOT_FOUND flat envelope...})
    except ResolveCacheMissError as exc:
        raise HTTPException(404, detail={...RESOLVE_CACHE_MISS flat envelope...})
    except ResolveInvalidCoordError as exc:
        raise HTTPException(400, detail={...RESOLVE_INVALID_COORD flat envelope...})
    except Exception as exc:
        logger.exception("resolve.internal_error", cube_id=cube_id, semantic_key=semantic_key)
        raise HTTPException(500, detail={...RESOLVE_INTERNAL_ERROR flat envelope...})
```

Handler invariants:
- Must preserve flat envelope style (R2).
- Must not implement auth checks directly; middleware handles 401 (R3).
- Must pass `cube_id`, `semantic_key`, `coord`, `period` unchanged into service for deterministic re-query.

### §5.2 Service pseudocode (C2 expansion)
```python
async def resolve_value(...):
    # 1) active mapping lookup (C1)
    mapping = await repo.get_active_by_key(cube_id, semantic_key)
    if mapping is None:
        raise MappingNotFoundForResolveError(...)

    # 2) coord derivation/validation (locked concrete shape is coord query param)
    coord_norm = validate_coord(coord)

    # derive shared args once to prevent drift
    lookup = dict(cube_id=cube_id, semantic_key=semantic_key, coord=coord_norm, ref_period=period)

    # 3) first cache read
    rows = await value_cache_service.get_cached(**lookup)

    # 4) immediate hit
    if rows:
        row = select_latest(rows) if period is None else rows[-1]  # deterministic
        return map_to_resolved(row, mapping, cache_status="hit", prime_warning=None)

    # 5) auto-prime attempt
    prime_result = await value_cache_service.auto_prime(
        cube_id=cube_id,
        semantic_key=semantic_key,
        product_id=mapping.product_id,
        resolved_filters=resolve_filters_from_mapping_config(mapping.config),
        frequency_code=None,
    )

    # 6) mandatory re-query using IDENTICAL args
    rows_after = await value_cache_service.get_cached(**lookup)

    # 7) return primed if row now exists; include sanitized warning if any
    if rows_after:
        row = select_latest(rows_after) if period is None else rows_after[-1]
        warning = sanitize_prime_error(prime_result.error) if prime_result.error else None
        return map_to_resolved(row, mapping, cache_status="primed", prime_warning=warning)

    # 8) terminal miss with surfaced prime attempt metadata
    raise ResolveCacheMissError(
        cube_id=cube_id,
        semantic_key=semantic_key,
        coord=coord_norm,
        period=period,
        prime_attempted=True,
        prime_error_code=sanitize_prime_error(prime_result.error) if prime_result.error else None,
    )
```

Service invariants:
- Step 6 re-query MUST use exactly same lookup args as step 3 (C2).
- Prime errors must never be dropped; they must surface either as `prime_warning` on success-after-prime or in cache-miss error details.
- Mapping inactive and mapping missing must be indistinguishable to caller (single 404 code).

## §6. Test plan

### §6.1 Unit tests

| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_validate_coord_accepts_10_slot_numeric` | valid coord string | same coord returned | unit |
| `test_validate_coord_rejects_bad_slot_count` | coord has <10 or >10 slots | `ResolveInvalidCoordError`/ValueError mapped | unit |
| `test_units_extraction_from_mapping_config_string_only` | config.unit string vs non-string | string passes; non-string→None | unit |
| `test_prime_warning_sanitization_strips_trace_content` | prime error raw text contains stack-ish content | sanitized code/category only | unit |

### §6.2 Service-layer tests

| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_resolve_hit_no_prime` | mapping active + first get_cached returns rows | 200 DTO w `cache_status="hit"`; auto_prime not called | service |
| `test_resolve_mapping_missing` | repo returns None | mapping-not-found exception -> 404 mapping code | service |
| `test_resolve_mapping_inactive_filtered` | inactive row not returned by active lookup | same as missing | service |
| `test_resolve_cache_miss_prime_success_row_written` | first miss, prime success, second read rows | DTO w `cache_status="primed"` | service |
| `test_resolve_cache_miss_prime_error_but_row_written` | prime_result.error set, second read rows | DTO includes sanitized `prime_warning` + `cache_status="primed"` | service |
| `test_resolve_cache_miss_prime_error_no_row` | prime error and second read empty | `RESOLVE_CACHE_MISS` details include prime_error_code | service |
| `test_resolve_cache_miss_prime_no_error_no_row` | prime no-op and second read empty | `RESOLVE_CACHE_MISS` with prime_attempted=true | service |
| `test_resolve_invalid_coord` | coord fails validator | `RESOLVE_INVALID_COORD` path | service |
| `test_http_to_service_pipeline_wiring` | mocked HTTP request through FastAPI test client into handler/service mocks | full request→state transition→response body assertion; ensures wiring, not mapper-only | service/pipeline |

Mandates:
- All async collaborators use `AsyncMock`.
- Explicitly include pipeline integration scenario (mocked HTTP → handler → service transition → response assertion), not only function-level mapper tests.

### §6.3 Integration tests

| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_resolve_happy_existing_cache` | seeded mapping + cache row | 200 with hit | integration |
| `test_resolve_404_mapping_not_found` | no mapping | 404 `SEMANTIC_MAPPING_NOT_FOUND` | integration |
| `test_resolve_404_mapping_inactive` | mapping inactive | same 404 code | integration |
| `test_resolve_404_cache_miss_after_prime` | cold cache + prime unable to populate | 404 `RESOLVE_CACHE_MISS` with details | integration |
| `test_resolve_query_validation` | invalid coord/period length | 422 | integration |
| `test_resolve_auth_required` | missing X-API-KEY | 401 from middleware | integration |
| `test_resolve_auth_success` | valid X-API-KEY | non-401 response path | integration |

Fixture note: follow existing integration infra pattern (Testcontainers Postgres + alembic upgrade/downgrade lifecycle) per team memory and `TEST_INFRASTRUCTURE.md` guidance.

## §7. Coord derivation contract
- **What auto_prime writes:** `coord` is produced by `derive_coord(resolved_filters)` then passed unchanged to persistence writes:
  - `coord = derive_coord(resolved_filters)` and later `_persist_response(..., coord=coord, ...)`. (`backend/src/services/statcan/value_cache.py:111`, `backend/src/services/statcan/value_cache.py:162-163`)
  - Each row upsert includes `coord=coord` at repository callsite. (`backend/src/services/statcan/value_cache.py:412`)
- **Existing shared function already exists:** `derive_coord(resolved_filters)` in `backend/src/services/semantic/coord.py`; this MUST remain single encoding authority for mapping-derived coord generation. (`backend/src/services/semantic/coord.py:19-61`)
- **Actual encoding:** 10-position dot-separated numeric string; slots default to `"0"`; each resolved filter sets `slots[dimension_position_id-1] = str(member_id)`; final coord is `".".join(slots)`. (`backend/src/services/semantic/coord.py:41-61`)
- **Ordering/canonicalization:** canonical by dimension-position slot indexing, not caller order; function comment explicitly states input order does not matter. (`backend/src/services/semantic/coord.py:27-33`, `backend/src/services/semantic/coord.py:44-60`)
- **Resolve contract decision:** use required `coord` query param in this exact 10-slot format for 3.1c. Re-deriving from ad-hoc dim query params is out of scope because no existing parser from external params to `ResolvedDimensionFilter` exists in resolve path, and drift risk is high.

## §8. Period selection contract
- **What auto_prime writes into period fields:** in persistence loop, each data point uses `ref_period=dp.ref_per`; `period_start` is generated/maintained at DB layer (model shows generated column) and returned in rows. (`backend/src/services/statcan/value_cache.py:413`, `backend/src/models/semantic_value_cache.py:100-105`)
- **get_cached ordering reality:** repository `get_by_lookup` orders ascending by `period_start` then ascending `ref_period`. (`backend/src/repositories/semantic_value_cache_repository.py:357-363`)
- **Default resolve behavior when `period` omitted:** service must select latest entry from returned list by taking last item of ascending-ordered results (`rows[-1]`) OR re-sorting DESC explicitly; chosen rule: `rows[-1]` for deterministic latest.
- **When `period` provided:** pass it as `ref_period` filter into `get_cached`; if rows returned, use first/last equivalently (single period expected) and echo `row.ref_period` into DTO `period`.
- **If multiple rows for same lookup without period filter:** pick latest by period chronology as above; never return an array (L1 singular endpoint).

## §9. Drift updates required by 3.1c impl PR

### 9.1 `docs/api.md` draft subsection (verbatim)
```md
### `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}`

Resolve a semantic mapping to a cached value for a caller-supplied StatCan coordinate.

| Property | Value |
|----------|-------|
| Auth | Admin (`X-API-KEY`, enforced by `AuthMiddleware`) |
| Rate Limit | None (inherits global/default middleware behavior) |

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `cube_id` | `str` | StatCan cube id (max 50 chars) |
| `semantic_key` | `str` | Semantic mapping key (max 100 chars) |

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `coord` | `str` | yes | 10-slot dot-separated StatCan coord (e.g. `1.10.0.0.0.0.0.0.0.0`) |
| `period` | `str` | no | Optional `ref_period`; when omitted, resolves latest cached period |

**Response (200):** `ResolvedValueResponse`

**Errors:**

| Status | error_code | Condition |
|--------|------------|-----------|
| 401 | `AUTH_INVALID_API_KEY` / `AUTH_MISSING_API_KEY` | Missing/invalid API key |
| 404 | `SEMANTIC_MAPPING_NOT_FOUND` | Mapping missing or inactive |
| 404 | `RESOLVE_CACHE_MISS` | No cached row after auto-prime + re-query |
| 400 | `RESOLVE_INVALID_COORD` | Coord fails contract |
| 422 | — | FastAPI validation failure |
| 500 | `RESOLVE_INTERNAL_ERROR` | Unexpected server error |
```

### 9.2 `docs/architecture/BACKEND_API_INVENTORY.md` row draft (verbatim)
```md
| GET | `/api/v1/admin/resolve/{cube_id}/{semantic_key}` | `backend/src/api/routers/admin_resolve.py` | `_get_resolve_service` (`ResolveService`) | n/a (path/query params) | 200 → `ResolvedValueResponse`; 401 (middleware); 404 → `SEMANTIC_MAPPING_NOT_FOUND` or `RESOLVE_CACHE_MISS`; 400 → `RESOLVE_INVALID_COORD`; 422 validation | Phase 3.1c singular resolve endpoint. Query: required `coord`, optional `period` (`ref_period` filter). Cache miss path performs auto-prime + mandatory re-query before terminal 404. |
```

### 9.3 `docs/architecture/ROADMAP_DEPENDENCIES.md` §2 delta draft (verbatim)
```md
| 3.1c Resolve endpoint (singular admin) | IN-PROGRESS (or COMPLETE once merged) | S | 1 | Depends on 3.1b semantic mapping CRUD + 3.1aaa value cache services |
| 3.1d Batch resolve / multi-key hydration | PENDING | M | 1-2 | Depends on 3.1c contract stabilization; DEBT-058/059 scope |
```

DEBT-060 handling in impl PR: **leave unchanged** (status/scope persists; do not edit DEBT.md as part of 3.1c).

## §10. Open questions for recon-impl handoff (non-founder)
1. `ResolveService` placement: `services/resolve/service.py` (recommended) vs colocating under `services/statcan/` for proximity to value-cache; recon recommends dedicated `services/resolve/` to keep API orchestration separate from low-level StatCan cache engine.
2. `prime_warning` payload format: recon recommends sanitized short code/category string (e.g., `"datasource_unavailable"`) instead of raw message to avoid leaking internals; impl should finalize exact sanitizer mapping utility.
3. Mapping config→resolved_filters conversion reuse: confirm existing semantic mapping validation output object can be re-used to reconstruct `ResolvedDimensionFilter` for auto-prime in resolve flow; if no direct helper exists, impl should add one thin adapter with tests.

## §11. Founder questions surfaced during recon (escalation)
- None. Pre-recon founder blocker set (GQ-01/02/03) is already ratified and no new founder-tier tradeoff emerged.
