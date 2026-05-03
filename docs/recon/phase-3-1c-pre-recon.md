# Phase 3.1c Pre-recon

- Branch: `claude/phase-3-1c-pre-recon` (created from current `work` because local `main` branch not found).
- Date: 2026-05-03 (UTC).
- Scope: read-only code/document reconnaissance for resolve endpoint prerequisites.
- Locked decisions (input only): singular `GET /resolve/{cube_id}/{semantic_key}`; include freshness fields `resolved_at` + `source_hash` in DTO.

## §A. Admin router precedent

### A1
- Router exists at `backend/src/api/routers/admin_semantic_mappings.py` with prefix `/api/v1/admin/semantic-mappings` (`router = APIRouter(...)`). (`backend/src/api/routers/admin_semantic_mappings.py:54-57`)
- Dependency wiring uses `Depends(_get_session_factory)` + `Depends(get_statcan_metadata_cache_service)` to build `SemanticMappingService` in `_get_service`. (`backend/src/api/routers/admin_semantic_mappings.py:65-80`)
- Full handler example: `upsert_semantic_mapping(...)` uses `service: SemanticMappingService = Depends(_get_service)`, catches typed exceptions and raises `HTTPException` with structured `detail`. (`backend/src/api/routers/admin_semantic_mappings.py:168-239`)
- X-API-KEY enforcement is middleware-level (`AuthMiddleware`) for `/api/v1/admin/*`, not router-level. (`backend/src/core/security/auth.py:46-53`, `backend/src/core/security/auth.py:122-166`, `backend/src/main.py:186-189`)

### A2
- Admin semantic mappings handlers raise flat-style `detail={"error_code":...,"message":...}` (and sometimes `details`) in `HTTPException`. (`backend/src/api/routers/admin_semantic_mappings.py:194-206`, `backend/src/api/routers/admin_semantic_mappings.py:299-305`)
- Auth middleware errors are nested envelope via `format_error_envelope`: `{"detail":{"error_code","message","context"}}`. (`backend/src/core/error_handler.py:56-83`, `backend/src/core/security/auth.py:126-163`)
- Global SummaVisionError handler still emits flat global envelope (`{"error_code","message","detail"}`), migration tracked as DEBT-048 note in code docstring. (`backend/src/core/error_handler.py:73-76`, `backend/src/core/error_handler.py:110-117`)
- Conclusion: 3.1b area is mixed: nested-auth envelope + flat endpoint-raised envelopes (not publication nested-details shape).

### A3
- Service file is `backend/src/services/statcan/value_cache.py` (not `value_cache_service.py`).
- `get_cached(*, cube_id, semantic_key, coord, ref_period=None) -> list[ValueCacheRow]`. (`backend/src/services/statcan/value_cache.py:329-347`)
- `auto_prime(*, cube_id, semantic_key, product_id, resolved_filters, frequency_code=None) -> AutoPrimeResult` and is async/awaitable. (`backend/src/services/statcan/value_cache.py:94-103`)
- Additional public methods relevant: `refresh_all() -> RefreshSummary`, `evict_stale(retention) -> int`. (`backend/src/services/statcan/value_cache.py:184-323`, `backend/src/services/statcan/value_cache.py:348-360`)

### A4
- Repository at `backend/src/repositories/semantic_value_cache_repository.py`.
- Read signatures: `get_by_lookup(...) -> list[SemanticValueCache]`; `get_latest_by_lookup(...) -> SemanticValueCache | None`; `list_active_lookup_keys() -> list[tuple[str,str,str|None,int]]`. (`backend/src/repositories/semantic_value_cache_repository.py:336-399`)
- Row shape includes `cube_id`, `semantic_key`, `coord` (string), `ref_period`, `period_start`, `value`, `source_hash`, `fetched_at`, `release_time`; **no `resolved_at` field** and **no `coord_json`/`cached_value` named columns**. (`backend/src/models/semantic_value_cache.py:94-148`)

### A5
- 3.1b router does not inject value-cache service; it injects semantic mapping service only. (`backend/src/api/routers/admin_semantic_mappings.py:69-80`, `backend/src/api/routers/admin_semantic_mappings.py:168-173`)
- `StatCanValueCacheService` owns short-lived DB sessions internally via `async_sessionmaker`; router does not pass `get_db` session through to value-cache methods. (`backend/src/services/statcan/value_cache.py:66-89`, `backend/src/services/statcan/value_cache.py:338-346`)
- DI provider exists: `get_statcan_value_cache_service(...)` yields service with session factory and managed `httpx.AsyncClient`. (`backend/src/api/dependencies/statcan.py:67-101`)

## §B. Cache row shape

### B1
`semantic_value_cache` columns/types/nullability from ORM:
- `id` bigint/int pk not null; `cube_id` varchar(50) not null; `product_id` bigint not null; `semantic_key` varchar(100) not null; `coord` varchar(50) not null; `ref_period` varchar(20) not null; `period_start` date nullable; `value` numeric(18,6) nullable; `missing` bool not null; `decimals` int not null; `scalar_factor_code` int not null; `symbol_code` int not null; `security_level_code` int not null; `status_code` int not null; `frequency_code` int nullable; `vector_id` bigint nullable; `response_status_code` int nullable; `source_hash` varchar(64) not null; `fetched_at` timestamptz not null; `release_time` timestamptz nullable; `is_stale` bool not null; `created_at` timestamptz not null; `updated_at` timestamptz not null. (`backend/src/models/semantic_value_cache.py:89-148`)

### B2
- `source_hash` computed by `compute_source_hash(...)` over canonical JSON payload with product/cube/key/coord/ref_period/value/missing/decimals/scalar/symbol/security/status/frequency/vector_id/response_status_code. (`backend/src/services/statcan/value_cache_hash.py:16-55`)
- Timestamps explicitly excluded for stability across unchanged refreshes. (`backend/src/services/statcan/value_cache_hash.py:3-7`, `backend/src/services/statcan/value_cache_hash.py:36-38`)

### B3
- Stored upstream time is `release_time` from StatCan data point; write timestamp is `fetched_at` set from service clock. (`backend/src/services/statcan/value_cache.py:386-387`, `backend/src/services/statcan/value_cache.py:426-427`)
- There is no `resolved_at` column today; freshness semantics currently available are `fetched_at` (cache write/verification time) and `release_time` (upstream release time). (`backend/src/models/semantic_value_cache.py:129-134`)

### B4
- No `units` column on `semantic_value_cache`. (`backend/src/models/semantic_value_cache.py:89-148`)
- `ResolvedValue` schema has optional `units: str | None = None` reserved for DEBT-060. (`backend/src/services/statcan/value_cache_schemas.py:179-193`)
- Mapping config sample includes `unit` in JSON config, but no dedicated column/schema-level `coord_schema`/`period_schema`. (`backend/src/models/semantic_mapping.py:35-40`, `backend/src/models/semantic_mapping.py:88-91`)

## §C. Cube metadata cache

### C1
`cube_metadata_cache` ORM columns:
- `id` bigint/int pk not null; `cube_id` varchar(50) not null; `product_id` bigint not null; `dimensions` jsonb/json not null; `frequency_code` varchar(8) nullable; `cube_title_en` varchar(255) nullable; `cube_title_fr` varchar(255) nullable; `fetched_at` timestamptz not null; `created_at` timestamptz not null; `updated_at` timestamptz not null. (`backend/src/models/cube_metadata_cache.py:45-81`)

### C2
- Repository read methods: `get_by_cube_id(cube_id)` and `list_stale(before=...)`; no `get_units_for(...)` method. (`backend/src/repositories/cube_metadata_cache_repository.py:25-37`)
- Metadata cache service methods documented in module docs include `get_cached/get_or_fetch/refresh/refresh_all_stale`; no explicit units helper found. (`docs/modules/statcan.md:106-116`)

### C3
- Metadata and value caches are refreshed by separate scheduler jobs (`scheduled_metadata_cache_refresh` at stale sweep cadence; `scheduled_value_cache_refresh` at 16:00 UTC per docstring). (`backend/src/core/scheduler.py:165-171`, `backend/src/core/scheduler.py:224-229`)
- Value refresh depends on metadata cache reads for `frequency_code`, so stale/missing metadata can affect retention sizing. (`backend/src/services/statcan/value_cache.py:197-210`)

## §D. Mappings lookup

### D1
- Lookup method: `SemanticMappingRepository.get_by_key(cube_id, semantic_key) -> SemanticMapping | None`; does **not** filter `is_active`. (`backend/src/repositories/semantic_mapping_repository.py:48-58`)
- `get_active_for_cube(cube_id)` does filter `is_active=True` but is cube-wide list path, not composite key lookup. (`backend/src/repositories/semantic_mapping_repository.py:33-43`)

### D2
- Composite uniqueness exists via `UniqueConstraint("cube_id", "semantic_key", name="uq_semantic_mappings_cube_key")`. (`backend/src/models/semantic_mapping.py:61-63`)

### D3
- No dedicated `coord_schema` / `period_schema` columns on mapping model; only generic `config` JSONB. (`backend/src/models/semantic_mapping.py:88-91`)
- Validation currently resolves dimension/member filters against metadata cache in service validation pipeline, not query-param schema objects. (`backend/src/services/semantic_mappings/service.py:323-332`)

## §E. Auto-prime semantics

### E1
- Current callsite: semantic mapping upsert flow invokes `await self._value_cache_service.auto_prime(...)` post-commit. (`backend/src/services/semantic_mappings/service.py:354-375`)
- No other production callsite found via `rg -n "auto_prime\(" backend/src`. (grep transcript in appendix)

### E2
- `auto_prime` is async and awaited inline at callsite. (`backend/src/services/statcan/value_cache.py:94`, `backend/src/services/semantic_mappings/service.py:369`)
- Mechanically possible today without new infra: endpoint can await it; there is no built-in queue/background abstraction in this service for fire-and-forget besides explicit task creation (not present here).

### E3
- `auto_prime` catches `DataSourceError`, generic parse errors, persist errors, invalid coord errors and returns `AutoPrimeResult(error=...)` instead of raising. (`backend/src/services/statcan/value_cache.py:110-173`)
- Callsite checks `auto_prime_result.error` and logs warning; also wraps unexpected exceptions defensively without failing request. (`backend/src/services/semantic_mappings/service.py:376-393`)

### E4
- Upsert idempotency/concurrency mechanism: PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` on `uq_semantic_value_cache_lookup` with hash guard `WHERE source_hash != excluded.source_hash`. (`backend/src/repositories/semantic_value_cache_repository.py:202-250`)
- This prevents duplicate-row writes for same lookup key, but does not prevent duplicate upstream fetch work (potential thundering herd still possible before DB write).

## §F. DTO field matrix

| Candidate field | Source today? | If unavailable, what would be needed? |
|---|---|---|
| `value` (canonical str) | Available: `ValueCacheRow.value` + canonical string convention in `ResolvedValue.value: str`. (`backend/src/services/statcan/value_cache_schemas.py:106`, `backend/src/services/statcan/value_cache_schemas.py:189`) | n/a |
| `cube_id` | Available: `semantic_value_cache.cube_id`. (`backend/src/models/semantic_value_cache.py:94`) | n/a |
| `semantic_key` | Available: `semantic_value_cache.semantic_key`. (`backend/src/models/semantic_value_cache.py:96`) | n/a |
| `coord` (echo) | Available: `semantic_value_cache.coord` (string, not JSON). (`backend/src/models/semantic_value_cache.py:97`) | JSON echo would need parsing/contract addition. |
| `period` (echo) | Available as `ref_period`/`period_start`. (`backend/src/models/semantic_value_cache.py:98-104`) | Need naming decision in DTO only. |
| `resolved_at` | Unavailable as named field. Closest: `fetched_at` and `release_time`. (`backend/src/models/semantic_value_cache.py:129-134`) | DTO mapping rule or new column if distinct semantics required. |
| `source_hash` | Available: `semantic_value_cache.source_hash`. (`backend/src/models/semantic_value_cache.py:128`) | n/a |
| `units` | Not persisted in value cache; optional on `ResolvedValue` only. (`backend/src/services/statcan/value_cache_schemas.py:192`) | Need derivation source and/or persisted column/service helper. |
| `cache_status` (`hit` / `primed` / `stale`) | Partial: row has `is_stale`; service has `auto_prime` result counts but no standardized enum field. (`backend/src/models/semantic_value_cache.py:135-137`, `backend/src/services/statcan/value_cache_schemas.py:149-171`) | Endpoint-level state machine contract. |
| `mapping_version` | Available from `semantic_mappings.version`, not on value cache row. (`backend/src/models/semantic_mapping.py:93`) | Join/second lookup in resolve flow. |

## §G. Founder questions (recon-blockers only)

1) **GQ-01 Units source for resolve DTO**
- Blocker: `units` has no definitive retrieval path in current caches/lookup APIs.
- Options: (a) omit units in 3.1c response and track DEBT, (b) derive from mapping `config.unit`, (c) derive from metadata dimensions, (d) new persisted units column/path.
- Recommendation: derive from mapping `config.unit` only if founder accepts config as canonical; otherwise omit now (true tradeoff).

2) **GQ-02 Error envelope policy for new resolve admin endpoints under mixed DEBT-048 state**
- Blocker: current admin surface mixes nested-auth and flat handler errors; recon needs explicit target for new endpoint consistency.
- Options: (a) flat handler detail style (match semantic mappings), (b) nested `detail` envelope for endpoint errors, (c) dual-tolerant migration path.
- Recommendation: no recommendation — policy tradeoff until DEBT-048 is explicitly scoped.

3) **GQ-03 Auth tier + router family for resolve endpoint consumers**
- Blocker: middleware currently auto-protects `/api/v1/admin/*`; non-admin paths may imply different auth strategy.
- Options: (a) `/api/v1/admin/...` with X-API-KEY, (b) `/api/v1/internal/...` with same middleware extension, (c) public route with different auth.
- Recommendation: use existing admin tier unless founder explicitly needs public-facing access in 3.1c.

## §H. Drift detection

- **H1 `docs/api.md` — STALE.** Claims AuthMiddleware not enforced and uses older endpoint/auth notes; no evident 3.1aaa scheduler or 3.1b semantic mappings coverage in reviewed section. (`docs/api.md:5-7`)
- **H2 `docs/modules/statcan.md` — STALE.** Package structure omits `value_cache.py`/`value_cache_hash.py`/`value_cache_schemas.py` and no `StatCanValueCacheService` section found. (`docs/modules/statcan.md:9-17`)
- **H3 `docs/architecture/BACKEND_API_INVENTORY.md` — STALE.** Last updated 2026-04-26; file header predates 2026-05-03 merges and visible endpoint table section didn’t indicate 3.1b/3.1aaa additions in sampled lines. (`docs/architecture/BACKEND_API_INVENTORY.md:5`)
- **H4 `docs/architecture/ROADMAP_DEPENDENCIES.md` — STALE.** Content is older roadmap track list not showing explicit 3.1aaa completed date or 3.1c/3.1d dependency states. (`docs/architecture/ROADMAP_DEPENDENCIES.md:42-59`)
- **H5 `docs/architecture/DEPLOYMENT_OPERATIONS.md` — STALE (for 3.1aaa specifics).** Generic scheduler section lacks specific 15:00/16:00 UTC metadata/value cache jobs and related env knobs; likely drift. (`docs/architecture/DEPLOYMENT_OPERATIONS.md:125-153`)

## Appendix: grep transcript

```bash
$ rg --files | rg 'admin_semantic_mappings|admin_publications|error_handler|error_codes|value_cache_service|semantic_value_cache|cube_metadata_cache|semantic_mappings|ROADMAP_DEPENDENCIES|BACKEND_API_INVENTORY|DEPLOYMENT_OPERATIONS|api.md|statcan.md|AuthMiddleware|middleware|scheduler'
[see terminal output captured in run]

$ rg -n "AuthMiddleware|X-API-KEY|admin_semantic_mappings|include_router\(|error_code" backend/src | sed -n '1,240p'
[see terminal output captured in run]

$ rg -n "auto_prime\(|value_cache_service" backend/src/services/semantic_mappings/service.py backend/src | sed -n '1,240p'
[see terminal output captured in run]

$ rg -n "get_units_for|units" backend/src/repositories backend/src/services/statcan backend/src/models | sed -n '1,240p'
[not run directly; no dedicated get_units_for method found in inspected files]

$ git branch -a
* work

$ git checkout main
error: pathspec 'main' did not match any file(s) known to git
```
