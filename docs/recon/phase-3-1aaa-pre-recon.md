# Phase 3.1aaa Pre-recon — `semantic_value_cache` infrastructure

**Date:** 2026-05-03 (UTC)  
**Branch target:** `claude/phase-3-1aaa-pre-recon`  
**Mode:** Pre-recon only (no recon-proper decisions, no implementation)

---

## Scope guardrails (explicit)

- This document **surfaces** decision surfaces for Phase 3.1aaa and dependencies for 3.1c/3.1d.
- This document does **not** lock decisions for Q-3.1aaa-* questions.
- No HTTP/admin endpoint scope is introduced here; backend infra only.

---

## §A — StatCan WDS data API audit

### A1 — Current StatCan client endpoint inventory (repo evidence)

Observed in `backend/src/services/statcan/client.py`: current typed helper is only `get_cube_metadata()` and it only targets `getCubeMetadata`; no helper currently exists for `getDataFromCubePidCoordAndLatestNPeriods`, `getSeriesInfoFromCubePidCoord`, `getFullTableDownloadCSV`, or `getChangedSeriesList`.

**Verbatim grep block (required):**

```bash
$ rg -n "getCubeMetadata|getDataFromCubePidCoordAndLatestNPeriods|getSeriesInfoFromCubePidCoord|getFullTableDownloadCSV|getChangedSeriesList" backend/src/services/statcan/client.py -S
38:    "https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata"
100:        """POST to ``getCubeMetadata`` and return the validated envelope.
126:                    f"for getCubeMetadata"
```

Conclusion surface for recon-proper: 3.1aaa needs at least one **new** client method for a data endpoint.

### A2 — Existing rate-limit / retry behavior and pacing baseline

`StatCanClient.request()` wraps all calls with:
- maintenance guard check
- token-bucket acquire per request
- retry on {429, 409, 503}
- exponential backoff 1s, 2s, 4s (3 retries max)

**Verbatim grep block (required):**

```bash
$ rg -n "AsyncTokenBucket|MAX_RETRIES|BASE_DELAY|_RETRYABLE_STATUS_CODES|acquire\(" backend/src/services/statcan/client.py -S
33:from src.core.rate_limit import AsyncTokenBucket
49:MAX_RETRIES: Final[int] = 3
52:BASE_DELAY: Final[float] = 1.0
55:_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 409, 503})
83:        rate_limiter: AsyncTokenBucket,
187:            await self._rate_limiter.acquire()
```

Scheduler metadata-refresh path currently constructs `StatCanClient(..., AsyncTokenBucket())` with default bucket parameters (not explicitly overridden in scheduler). Decision surface: whether value-cache refresh should use same default bucket config or explicit tuned constructor values.

### A3 — Request/response shape for `getDataFromCubePidCoordAndLatestNPeriods`

Repo status: no local fixture/mock for that endpoint found under current StatCan service module; only metadata schemas are present.

External contract source (StatCan WDS user guide) indicates:
- POST URL: `https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods`
- request body supports array payload objects such as: `[{"productId": 35100003, "coordinate": "1.12.0.0.0.0.0.0.0.0", "latestN": 3}]`
- response envelope includes `status`, `object`, with `object.vectorDataPoint` list.

Reference: https://www.statcan.gc.ca/en/developers/wds/user-guide

### A4 — Batching capability surface

From public WDS examples, request body format is an array (`[...]`), implying potential multi-item batch in one POST.

Unknowns that recon-proper must verify against real endpoint behavior:
1. hard max array length per request
2. whether mixed `productId` values in one call are supported vs best-effort
3. partial failure semantics per batch item (per-item status or whole-request fail)
4. ordering guarantees in response relative to request order

### A5 — Data point field surface (from WDS docs/examples)

WDS examples show `vectorDataPoint` entries with (at least) the following fields:
- `refPer`
- `refPer2`
- `refPerRaw`
- `refPerRaw2`
- `value`
- `decimals`
- `scalarFactorCode`
- `symbolCode`
- `securityLevelCode`
- `statusCode`

Plus parent object often includes `productId`, `coordinate`, `vectorId`, `responseStatusCode`.

This set drives cache schema options in §C.

---

## §B — Coord derivation algorithm

### B1 — Coord format surface

Target format is dot-separated fixed-width coordinate positions (StatCan native), e.g. `"1.10.0.0.0.0.0.0.0.0"`. Unset positions are `0` placeholders.

### B2 — Mapping → coord walk-through using existing validator output

Existing validator (`validate_mapping_against_cache`) already resolves each mapping filter to:
- `dimension_position_id`
- `member_id`

This is available in `ValidationResult.resolved_filters` as `ResolvedDimensionFilter` entries.

Algorithm surface for 3.1aaa (deterministic, built on validator output):

1. Validate mapping against cached metadata via existing pure validator.
2. Initialize 10-slot int array with zeros: `[0,0,0,0,0,0,0,0,0,0]`.
3. For each `resolved_filter` pair:
   - read `position = dimension_position_id` (1-indexed by StatCan metadata)
   - read `member = member_id`
   - assign `slots[position-1] = member`
4. Join with `.`.

Worked sample:
- mapping filters: `{"Geography": "Canada", "Products": "All-items"}`
- resolved pairs: `(position 1 -> member 1)`, `(position 2 -> member 10)`
- slots after assignment: `[1,10,0,0,0,0,0,0,0,0]`
- coord: `"1.10.0.0.0.0.0.0.0.0"`

This is implementable **without** duplicating matching logic because normalization/casefold matching already exists in validator.

### B3 — Edge-case decision surface

Items for founder/recon-proper resolution:
- Missing filter dimensions: leave `0` vs treat as invalid for selected semantic keys?
- Multi-member per dimension: current schema is `dict[str,str]` (single member), so multi-member would require schema extension; likely out-of-scope in 3.1aaa.
- Time/period representation: period is returned in datapoints (`refPer`), not likely encoded as coord slot in value retrieval path.
- `has_uom` flagged dimensions: unknown whether these should remain explicit filter requirements vs allow `0` fallback.

---

## §C — `semantic_value_cache` schema design surface

### C1 — Storage model options (no decision locked here)

Option 1: row-per-period
- Unique key candidate: `(cube_id, semantic_key, coord, ref_period)`
- Better SQL queryability, easier staleness sweep per period.

Option 2: one row per `(cube_id, semantic_key, coord)` with JSONB periods payload
- Simpler atomic overwrite, fewer rows.
- Harder index/query semantics for period-based filtering.

### C2 — Draft column list (surface)

```sql
CREATE TABLE semantic_value_cache (
    id BIGINT PRIMARY KEY,
    cube_id VARCHAR(50) NOT NULL,
    semantic_key VARCHAR(100) NOT NULL,
    coord VARCHAR(50) NOT NULL,

    -- Period payload (row-per-period variant)
    ref_period VARCHAR(20) NOT NULL,
    period_start DATE,
    value NUMERIC(18,6),
    decimals INTEGER,
    scalar_factor_code INTEGER,
    symbol_code INTEGER,
    security_level_code INTEGER,
    status_code INTEGER,

    -- Optional additional provenance fields from response object
    vector_id BIGINT,
    response_status_code INTEGER,

    source_hash VARCHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    is_stale BOOLEAN NOT NULL DEFAULT false,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_semantic_value_cache_lookup
    ON semantic_value_cache (cube_id, semantic_key, coord, ref_period);
CREATE INDEX ix_semantic_value_cache_coord
    ON semantic_value_cache (cube_id, semantic_key, coord);
CREATE INDEX ix_semantic_value_cache_fetched_at
    ON semantic_value_cache (fetched_at);
CREATE INDEX ix_semantic_value_cache_is_stale
    ON semantic_value_cache (is_stale) WHERE is_stale = true;
```

### C3 — Value typing surface

Known lock from prior recon says API canonical value string is required for deterministic hash story. Storage may be numeric internally (NUMERIC) with canonicalization at read boundary, or string persisted as authoritative source. Keep as open question.

### C4 — `period_start` surface

`period_start` can be stored for query ergonomics or derived from `ref_period` at runtime. This is deferred decision (Q-3.1aaa-7).

### C5 — Capacity estimate surface

Order-of-magnitude estimate from prompt assumptions: 250k rows under default monthly retention assumptions is well within normal Postgres comfort, but recon-proper should validate using actual mapping counts and frequency mix.

---

## §D — Auto-prime integration

### D1 — Existing hook in mapping upsert path

Current `SemanticMappingService.upsert_validated()` flow:
1. validate config shape
2. fetch metadata cache entry (`_fetch_cache_entry`) — this is auto-prime behavior
3. validate mapping against cache
4. persist mapping

**Verbatim grep block (required):**

```bash
$ rg -n "Cache fetch \(auto-prime\)|_fetch_cache_entry\(|validate_mapping_against_cache\(" backend/src/services/semantic_mappings/service.py -S
312:        # 2. Cache fetch (auto-prime).
313:        cache_entry = await self._fetch_cache_entry(
318:        result = validate_mapping_against_cache(
```

Integration surface: add value-cache prime invocation after successful metadata validation, before commit or after commit depending on failure semantics selected in §D3.

### D2 — Sync vs async vs hybrid (decision surface only)

- **Sync:** deterministic but can increase save latency and availability coupling to WDS.
- **Async:** better save UX, but transient empty cache for downstream resolve.
- **Hybrid:** sync minimal row(s), async full history, intermediate complexity.

No choice locked in pre-recon.

### D3 — Failure semantics surface

If WDS unavailable during value prime:
- fail save (strong consistency)
- save mapping and defer cache fill (eventual consistency)
- save with stale placeholders

Decision deferred to founder in recon-proper.

---

## §E — Nightly refresh job

### E1 — Existing 3.1aa scheduler pattern

Source of truth is `backend/src/core/scheduler.py` (not `services/statcan/scheduler.py`): job `statcan_metadata_cache_refresh` registered as cron at 15:00 UTC, `coalesce=True`, `max_instances=1`, `misfire_grace_time=3600`.

**Verbatim grep block (required):**

```bash
$ rg -n "statcan_metadata_cache_refresh|scheduled_metadata_cache_refresh|coalesce|max_instances|misfire_grace_time|hour=15" backend/src/core/scheduler.py -S
165:async def scheduled_metadata_cache_refresh() -> None:
173:        logger.info("Scheduled job started: statcan_metadata_cache_refresh")
211:            "Scheduled job completed: statcan_metadata_cache_refresh",
218:            "Scheduled job failed: statcan_metadata_cache_refresh",
316:        scheduled_metadata_cache_refresh,
318:        hour=15,
321:        id="statcan_metadata_cache_refresh",
323:        coalesce=True,
324:        max_instances=1,
325:        misfire_grace_time=3600,
```

### E2 — Candidate 3.1aaa job parameters surface

Founder target name: `statcan_value_cache_refresh`. Surface to confirm in recon-proper:
- cron time relative to existing metadata refresh
- same coalesce/max_instances/misfire settings or different
- retry behavior inside wrapper vs in service

### E3 — Job algorithm surface

Candidate flow:
1. enumerate active mappings
2. derive coord for each mapping
3. fetch latest N datapoints
4. upsert changed/new periods
5. mark rows outside retention as stale (or delete, depending policy)
6. commit at per-mapping (or per-batch) granularity

### E4 — Batch optimization surface

If endpoint supports array batches safely, group by cube and submit batched coord requests. Requires confirmed batch semantics (§A4).

### E5 — Failure mode surface

Mirror metadata pattern: catch/log at scheduler wrapper, continue on per-item failures in service where feasible, preserve idempotency across reruns.

---

## §F — Service layer design surface

### F1 — `StatCanValueCacheService` shape

Candidate methods:
- `auto_prime(cube_id, semantic_key, mapping_config)`
- `refresh_all()`
- `get_cached(cube_id, semantic_key, coord)`
- `evict_stale(retention_days)`

DI and wiring should mirror existing metadata cache service patterns.

### F2 — Repository shape

Candidate methods:
- `upsert_period(...)`
- `get_by_lookup(...)`
- `mark_stale(...)`
- `delete_older_than(...)`

### F3 — Reuse validator resolution

Prefer deriving coord from `ValidationResult.resolved_filters` to avoid second implementation of normalized dimension/member matching.

---

## §G — Test plan surface

- unit: client-data parser and envelope handling for data endpoint
- unit: coord derivation using validator `resolved_filters`
- unit: auto-prime behavior variants (sync/async semantics once chosen)
- unit: refresh-all with partial failures and retry paths
- repo tests: upsert idempotency, uniqueness behavior, stale-marking
- integration: alembic + postgres + simulated WDS responses
- scheduler: job registration, one-run invocation, no crash on exceptions

---

## §H — Founder questions surface (Q-3.1aaa-N)

1. **Q-3.1aaa-1 (§C1):** row-per-period vs JSONB periods array?
2. **Q-3.1aaa-2 (§D2):** auto-prime sync vs async vs hybrid?
3. **Q-3.1aaa-3 (§D3):** if prime fails, fail mapping save vs eventual consistency?
4. **Q-3.1aaa-4 (§A3/§E3):** value serialization contract in DB (`NUMERIC` vs canonical string) while preserving deterministic source hash behavior?
5. **Q-3.1aaa-5 (§A4/§E4):** endorse batch requests on data endpoint after contract verification?
6. **Q-3.1aaa-6 (§B2/§F3):** mandate reuse of validator output for coord derivation (single source of matching truth)?
7. **Q-3.1aaa-7 (§C4):** persist `period_start` physically or derive from `ref_period` lazily?
8. **Q-3.1aaa-8 (§E2):** exact cron time for value refresh relative to existing 15:00 UTC metadata refresh?

No recommendations finalized here.

---

## §I — DEBT entries planned (surface)

DEBT register scan indicates max seen ID currently **DEBT-057** in repository snapshot.

Potential future DEBT candidates for post-3.1aaa follow-on:
- high-scale WDS throttling tuning for nightly value refresh fanout
- retention/lifecycle policy beyond latest-N requirement
- cross-frequency ref-period normalization edge handling

---

## §J — Pre-recon → recon-proper handoff blockers

Recon-proper should not be drafted until:
1. Founder answers Q-3.1aaa-1 through Q-3.1aaa-8.
2. Data endpoint contract is validated against either a local fixture or captured real sample response from WDS.
3. Batch semantics (array size/failure contract) are confirmed.
4. Cron placement for value refresh is approved relative to metadata job.
5. Storage model (row vs JSONB) is selected to unblock migration sketch in recon-proper.

---

## Evidence appendix

### Appendix A — Key file pointers

- StatCan client currently only has typed metadata helper: `backend/src/services/statcan/client.py`
- Scheduler metadata refresh registration: `backend/src/core/scheduler.py`
- Mapping upsert auto-prime hook (metadata cache fetch): `backend/src/services/semantic_mappings/service.py`
- Validator resolved IDs for coord derivation input: `backend/src/services/semantic_mappings/validation.py`

### Appendix B — External references

- StatCan WDS user guide (endpoint names, sample payload/response shape):  
  https://www.statcan.gc.ca/en/developers/wds/user-guide

