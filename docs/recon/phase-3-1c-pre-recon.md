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

## §D4. Active-mapping requirement — REQUIRED FOR 3.1c IMPLEMENTATION

Per §D1, `SemanticMappingRepository.get_by_key(cube_id, semantic_key)`
returns mappings regardless of `is_active`. `get_active_for_cube(cube_id)`
filters but is a cube-wide list path, not a composite-key lookup.

**Rule (binding for 3.1c impl):** Resolve endpoint MUST NOT use inactive
mappings. Inactive lookup → 404 with error_code `SEMANTIC_MAPPING_NOT_FOUND`
(or whichever code recon-proper assigns). Treat inactive identically to
"row does not exist" from the consumer's standpoint.

**Two acceptable implementation paths (recon-proper picks one):**

1. **Repository extension:** add `get_active_by_key(cube_id, semantic_key)`
   to `SemanticMappingRepository`, mirroring the WHERE clause from
   `get_active_for_cube` plus the composite key predicate. Production
   callers of `get_by_key` (admin CRUD) keep using `get_by_key` —
   no breaking change.

2. **Service-level guard:** keep `get_by_key`, branch in resolve service:
   `if mapping is None or not mapping.is_active: raise NotFound`. Cheaper
   diff, but the guard is invisible at repo signature; future callers
   could miss it.

**Rationale for binding rule:** an inactive mapping that still resolves
data leaks deprecated/wrong semantic shape to consumers. Phase 3.2
(Zustand frontend) treats resolve responses as authoritative — silent
inactive-mapping resolution would mean stale bindings ship to operators.

This is a CORRECTNESS rule, not a founder question. Do not relitigate.

## §E5. Resolve cache-miss state machine — REQUIRED FOR 3.1c IMPLEMENTATION

Per §E3, `auto_prime` does NOT raise on `DataSourceError`, parse errors,
persist errors, or invalid coord errors. It returns
`AutoPrimeResult(error=...)`. The existing mapping-upsert callsite only
logs a warning on `auto_prime_result.error` (per §E3) and does not fail
the parent request. Resolve endpoint MUST NOT inherit that pattern: a
failed prime on a cache miss is consumer-visible, not a background
warning.

**Algorithm (binding for 3.1c impl):**

1. Look up active mapping (per §D4 rule). If absent or inactive → 404
   `SEMANTIC_MAPPING_NOT_FOUND`.
2. Derive `coord` from query params + mapping config (recon-proper
   defines exact derivation).
3. First cache read: `value_cache_service.get_cached(...)`.
4. If row(s) returned: return ResolvedValue with `cache_status="hit"`.
   STOP.
5. If no rows: `await auto_prime(...)`. Capture `AutoPrimeResult` —
   never discard.
6. Re-query `get_cached(...)` regardless of whether prime returned
   error or success (per §E3 the result may be partial; per §E4 the
   ON CONFLICT upsert may have written the row even if the result
   object surfaces a downstream warning).
7. If second query has rows: return ResolvedValue with
   `cache_status="primed"`. Include sanitized `prime_warning` field if
   `AutoPrimeResult.error` was present (recon-proper decides exact
   field name and sanitization rules — at minimum strip stack traces).
8. If second query still has no rows: return explicit error response
   with error_code `RESOLVE_CACHE_MISS` (or whichever code recon-proper
   assigns). Response body MUST surface:
   - whether auto_prime was attempted (always YES in this branch)
   - sanitized prime error code/category if present
   - `cube_id` + `semantic_key` echoed back

**Forbidden patterns:**

- Returning HTTP 200 with `value: null` on miss-after-prime-failure.
- Returning HTTP 200 with empty list (singular endpoint per lock).
- Logging the prime error and returning a generic 404 that doesn't
  distinguish "mapping not found" from "data not yet available."
- Discarding `AutoPrimeResult.error` after re-query without surfacing
  it in the error response.

**Why this is binding:** §E3 + §E4 together mean a naïve
`if not cached: await auto_prime(); return cached or 404` will silently
return 404 on every transient StatCan failure, indistinguishable from
"this mapping has never had data." Phase 3.2 frontend cannot show the
right binding-status dot (yellow vs red vs gray) without that
distinction. This is a CORRECTNESS rule.

**Concurrency note (informational, not a rule):** per §E4, ON CONFLICT
upsert prevents duplicate rows but NOT duplicate upstream fetch work.
Two simultaneous resolve requests for the same cold key may both call
`auto_prime` against StatCan. This is acceptable for 3.1c v1; tracked
as P3-related debt if it becomes a load issue.

## §F2. DTO mapping decisions for 3.1c — RECON-READY DEFAULTS

The §F matrix lists field availability. This subsection translates
availability into the field set 3.1c IS EXPECTED to ship, modulo
recon-proper revision.

**Field mappings (binding unless recon-proper overrides with rationale):**

| DTO field | Source | Rule |
|---|---|---|
| `value` | `semantic_value_cache.value` (numeric → canonical str) | required |
| `cube_id` | row.cube_id | required, echo |
| `semantic_key` | row.semantic_key | required, echo |
| `coord` | row.coord (varchar, not JSON) | required, echo as-is |
| `period` | row.ref_period (or period_start, recon picks) | required |
| `resolved_at` | row.fetched_at | required, ALIAS — no new column |
| `source_hash` | row.source_hash | required, opaque token (see note below) |
| `is_stale` | row.is_stale | required, RAW PASSTHROUGH from persisted column |
| `units` | mapping.config.get("unit") if string, else null | optional, mapping-config-only path |
| `cache_status` | endpoint state machine: "hit" \| "primed" | required, NO "stale" value in 3.1c |
| `mapping_version` | recon-proper decides if 3.1c surfaces it | optional |

**Critical clarifications:**

1. **`resolved_at` is NOT a new column.** It is a DTO field name that
   maps to the existing `fetched_at` column. Locked freshness-fields
   decision does not require schema migration. Per §B3, `fetched_at`
   semantics = "cache write/verification time," which is the correct
   frontend-facing meaning of "resolved at."

2. **`cache_status` is endpoint-derived, NOT row-derived.** It reflects
   the path taken through §E5 state machine: "hit" if step 4 returned,
   "primed" if step 7 returned. There is no "stale" value because
   3.1c does NOT compute staleness. 3.1d adds compare logic that may
   either add a new "stale" cache_status value, or remain a separate
   flag — recon-3.1d's call.

3. **`is_stale` ships as RAW PASSTHROUGH.** Per §B1, `is_stale` is a
   `bool not null` persisted column on `semantic_value_cache`. 3.1c
   surfaces it byte-for-byte without runtime computation. This gives
   3.1d a starting field to read; 3.1d may then add a separate
   computed staleness comparison (e.g. age-based) without breaking
   3.1c's contract.

4. **`source_hash` opaque token contract.** Per §B2, the hash inputs
   include `vector_id` and `response_status_code`. Frontend should
   treat the value as an opaque equality token: same hash = same
   underlying StatCan state. Do NOT decompose into structured fields
   for the consumer. Phase 3.1d hash compare will be a simple string
   equality check.

5. **`units` source is `mapping.config.unit` ONLY.** No metadata-cache
   derivation in 3.1c (DEBT-060 keeps tracking a richer source). If
   `mapping.config` is missing the key OR the value isn't a string,
   the DTO field is `null`. No fallback derivation.

**Schema migrations required for 3.1c: NONE.**

## §G2. Founder decision recommendations (strong defaults)

§G enumerates three blockers (GQ-01 units, GQ-02 envelope, GQ-03 auth
tier). This subsection adds STRONG RECOMMENDATIONS to each so founder
can ratify with one-line confirmation, override with one-line direction,
or escalate to deeper discussion.

**GQ-01 units — RECOMMENDATION: option (b) mapping.config.unit only.**
Per §F2, this requires no new infrastructure and no cross-table joins.
DEBT-060 continues tracking richer derivation. Override only if the
mapping-config path is unacceptable; in that case 3.1c ships without
units and DEBT-060 expands.

**GQ-02 envelope — RECOMMENDATION: option (a) flat handler-detail
style, matching admin_semantic_mappings precedent (§A2).**
Rationale: minimum-surprise for impl agents who just shipped 3.1b
using the same style. DEBT-048 migration to nested envelope is a
separate, opt-in scope decision; doing it inside 3.1c bundles two
unrelated changes. Override if founder explicitly wants 3.1c to lead
DEBT-048 migration — in that case 3.1c becomes the reference impl
for nested-detail handler errors, and §A2 mixed reality gets one less
exception.

**GQ-03 auth tier — RECOMMENDATION: option (a) `/api/v1/admin/...`
with existing X-API-KEY middleware.**
Rationale: per §A1 the middleware auto-protects `/api/v1/admin/*`,
no router-level wiring needed. Phase 3.2 (Zustand frontend) will be
admin-tier consumer. Override only if founder anticipates non-admin
consumers in near-term — in that case auth strategy needs explicit
design, blocking recon further.

These are RECOMMENDATIONS, not locks. §G remains the authoritative
list of founder-blocker questions; this section just makes the
default path obvious so a one-line "ratify all three" unblocks recon.

## §I. Drift cleanup scope for the 3.1c implementation PR

Per `_DRIFT_DETECTION_TEMPLATE.md`, any PR adding/modifying endpoints
MUST update related architecture MDs in the same commit. §H found 5
STALE MDs. This subsection scopes drift cleanup to ONLY what 3.1c
itself touches; historical drift from earlier phases is explicitly
NOT in scope.

**REQUIRED in 3.1c impl PR (same commit as endpoint code):**

1. **`docs/api.md`:** add new "Resolve Router" subsection mirroring
   "Admin Cubes Router" / "Admin Publications Router" structure.
   Document the new endpoint, query params, response shape, error
   codes. Do NOT also fix historical drift in this file from §H1.

2. **`docs/architecture/BACKEND_API_INVENTORY.md`:** add new row to §1
   Endpoints table for the resolve endpoint. Bump "Last updated" date.
   Do NOT also fix historical drift from §H3 (3.1aaa scheduler row,
   3.1b admin rows) — those are separate debt.

3. **`docs/architecture/ROADMAP_DEPENDENCIES.md`:** §2 status table —
   move 3.1c from "blocked" to "in progress" → "completed" on PR
   merge. Add 3.1d row showing 3.1c as dependency. Do NOT also fix
   historical drift from §H4 (3.1aaa completion date) — separate debt.

**EXPLICITLY OUT OF SCOPE for 3.1c impl PR:**

- Backfilling 3.1aaa scheduler documentation in `statcan.md` (§H2).
- Backfilling 3.1aaa env/scheduler section in `DEPLOYMENT_OPERATIONS.md`
  (§H5).
- Fixing prior phases' missing inventory rows.
- DEBT-048 envelope migration (per GQ-02 recommendation).

**Rationale:** drift template requires same-PR updates for what THIS PR
touches. It does not require fixing every historical gap. Scoping
prevents 3.1c from accumulating unrelated review surface.

**Tracking:** historical drift items from §H1, §H2, §H4, §H5 should
be filed as a single follow-up DEBT entry "Architecture MD drift
backfill — Phase 3.1 series" after 3.1c merges. Recon-proper for
3.1c may either file this DEBT or defer to founder.

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
