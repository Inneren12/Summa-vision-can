# Phase 3.1c Recon — Resolve Endpoint Implementation Plan (Fix Pass)

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
- **C3 (added in fix pass):** Resolve API takes semantic filter query params, not caller-provided coord. Service derives `coord` internally via shared `derive_coord(...)` helper. (BLOCKER-1 founder resolution, fix pass 2026-05-03)
- In-scope debt continuity: DEBT-060 (units enrichment) and DEBT-062 / P3-024 (prime-on-refresh gap) remain open and unchanged by 3.1c. (pre-recon §B4, pre-recon §E5)
- **DEBT addition candidate:** if `mapping.config` schema cannot supply the filter shape resolve needs, file a new DEBT entry capturing the gap. Recon records findings; impl PR creates entry if needed (Appendix B grep B/C findings).
- Explicitly out of scope: DEBT-048 envelope migration, DEBT-058/059 batch resolve tracks.

## §2. Endpoint contract

### §2.1 URL pattern
- **Route:** `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}`.
- **Trailing slash policy:** follow existing admin convention where collection roots use empty-string route and subpaths omit trailing slash. (`backend/src/api/routers/admin_semantic_mappings.py:247-249`, `backend/src/api/routers/admin_semantic_mappings.py:281-283`)
- **Router declaration (impl pasteable):**
```python
router = APIRouter(prefix="/api/v1/admin/resolve", tags=["admin-resolve"])

@router.get("/{cube_id}/{semantic_key}", response_model=ResolvedValueResponse)
async def resolve_value_handler(...):
    ...
```
- Full path stays `/api/v1/admin/resolve/{cube_id}/{semantic_key}` — prefix + route compose to one path, never doubled.

### §2.2 Path param validation
- `cube_id: str = Path(..., min_length=1, max_length=50)` (DB cap from `semantic_value_cache.cube_id varchar(50)`). (pre-recon §B1)
- `semantic_key: str = Path(..., min_length=1, max_length=200)` (matches the **mapping** table limit `SemanticMapping.semantic_key String(200)` and `SemanticMappingCreate.semantic_key max_length=200`). The original recon used the cache-table limit (varchar(100)), which would make admin-created keys of 101..200 chars unreachable through resolve. Cache write may still fail for keys >100 chars at auto_prime time — tracked as DEBT-063. (Round 3 correction; pre-recon §B1 limit applies to cache rows, not endpoint input.)
- No extra regex in 3.1c (mirrors 3.1b style). (`backend/src/api/routers/admin_semantic_mappings.py:255-259`)

### §2.3 Query params
Resolve accepts semantic filter inputs that the service translates into a canonical
`coord` string before cache lookup or auto-prime. There is NO caller-provided `coord`
parameter in 3.1c (BLOCKER-1 Option B).

**Filter shape (picked): Encoding 1 — repeated query pairs.**
- `?dim={dimension_position_id}&member={member_id}` repeated per dimension.
- Example: `GET /api/v1/admin/resolve/14-10-0287-03/unemployment-rate?dim=1&member=10&dim=2&member=2`
- Choice rationale: Appendix B grep B shows existing mapping config references `dimension_filters` and validator pipeline outputs `resolved_filters`; no JSON-query precedent found. Encoding 1 stays FastAPI-native and aligns with integer dim/member pairing.

**Period:**
- `period: str | None = Query(default=None, max_length=20)`.
- Source-of-truth: caller-specified `ref_period` when present; otherwise latest row after service-derived coord lookup.

**Service-internal coord derivation:**
1. Parse raw dim/member input into `list[ResolvedDimensionFilter]` (Appendix B grep A).
2. Validate filter set against mapping config contract (`dimension_filters` expectations from Appendix B grep B).
3. `coord = derive_coord(filters)` using shared helper. (`backend/src/services/semantic/coord.py:19-61`)
4. Use identical `coord` for `get_cached(...)` and `auto_prime(resolved_filters=filters, ...)`.

This removes caller/mapping coord divergence entirely.

### §2.4 Response shape — ResolvedValue DTO
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedValueResponse(BaseModel):
    cube_id: str = Field(description="Cube identifier.")
    semantic_key: str = Field(description="Semantic mapping key.")
    coord: str = Field(description="Service-derived StatCan coordinate string echoed from cache row.")
    period: str = Field(description="Resolved period token (ref_period).")
    value: str | None = Field(
        default=None,
        description="Canonical stringified numeric value. None when the observation is suppressed/missing upstream (paired with missing=True).",
    )
    missing: bool = Field(
        description="Raw passthrough from cache row. True when the upstream observation is absent/suppressed; in that case value is None.",
    )
    resolved_at: datetime = Field(description="Alias of cache row fetched_at timestamp.")
    source_hash: str = Field(description="Opaque cache provenance hash.")
    is_stale: bool = Field(description="Persisted stale marker from cache row.")
    units: str | None = Field(default=None, description="Unit from mapping.config.unit if string, else null.")
    cache_status: Literal["hit", "primed"] = Field(description="Resolve status.")
    mapping_version: int | None = Field(default=None, description="Optional semantic mapping version.")
```

Mapping notes:
- `period` maps from `row.ref_period` (not `period_start`). (pre-recon §F2)
- `resolved_at` maps from `row.fetched_at` (L2). (pre-recon §F2)
- `units` source is strictly `mapping.config.unit | None` (R1).
- `cache_status` enum literals: `"hit" | "primed"` only (Literal type-narrowed; no `"stale"`).
- `value` is `str | None`. Cache row stores `value: numeric(18,6) nullable` per pre-recon §B1; missing observations have `value=NULL, missing=True`. Service maps `row.value` → `None` when null, else canonical string. NEVER stringify `None` → `"None"`.
- `missing` is RAW PASSTHROUGH from `row.missing` (`bool not null` per pre-recon §B1), parallel to `is_stale`. Frontend uses it to distinguish "observation suppressed at source" (missing=True, expected) from "value present" (missing=False).

### §2.5 Status codes + error responses
- 200: `ResolvedValueResponse`.
- 404 `SEMANTIC_MAPPING_NOT_FOUND`: mapping missing or inactive (C1).
- 404 `RESOLVE_CACHE_MISS`: miss after prime + re-query (C2).
  - `details = {"cube_id":...,"semantic_key":...,"coord":...,"period":...,"prime_attempted":true,"prime_error_code":<sanitized|None>}` (coord is service-derived for ops visibility).
- 400 `RESOLVE_INVALID_FILTERS`: `Invalid filter set: <reason>. Mapping requires dimensions {expected}; got {provided}.`
- 422: FastAPI path/query validation.
- 401: AuthMiddleware.
- 500 note: Appendix B grep E found no existing admin-router `*_INTERNAL_ERROR` constants; use generic 500 handler response shape (flat envelope) without adding resolve-specific internal code.

### §2.6 Headers
- No special headers in 3.1c v1.


### §F2 Baseline DTO matrix (updated in Fix-2)
Field table now has **11 rows**.

| DTO field | Source | Rule |
|---|---|---|
| `value` | `semantic_value_cache.value` (numeric, nullable) → canonical `str | None` | required, nullable for missing |
| `missing` | `semantic_value_cache.missing` (bool not null per pre-recon §B1) | required, RAW PASSTHROUGH from persisted column |
| `cube_id` | row.cube_id | required |
| `semantic_key` | row.semantic_key | required |
| `coord` | row.coord | required |
| `period` | row.ref_period | required |
| `resolved_at` | row.fetched_at | required |
| `source_hash` | row.source_hash | required |
| `is_stale` | row.is_stale | required |
| `units` | mapping.config.unit if string else null | optional |
| `cache_status` | endpoint state machine | required |

## §3. Error code registry additions
Before adding new constants, audit `backend/src/core/error_codes.py` for existing equivalents (per Appendix B grep D); reuse if present.

| error_code | HTTP | action | when raised | message template |
|---|---:|---|---|---|
| `MAPPING_NOT_FOUND` | 404 | **REUSE existing constant/name** | mapping missing/inactive in resolve | `Semantic mapping not found for cube_id='{cube_id}' and semantic_key='{semantic_key}'.` |
| `RESOLVE_CACHE_MISS` | 404 | ADD | no row after prime + re-query | `No cached value available for requested lookup after prime attempt.` |
| `RESOLVE_INVALID_FILTERS` | 400 | ADD | filter parse/validation fails | `Invalid filter set: <reason>. Mapping requires dimensions {expected}; got {provided}.` |

i18n mapping still required for Phase 3.2 (DEBT-030 pattern).

## §4. Repository / service surface changes
### §4.1 Active mapping lookup path (C1)
- Keep repo-extension choice.
- File: `backend/src/repositories/semantic_mapping_repository.py`
- Signature: `async def get_active_by_key(self, cube_id: str, semantic_key: str) -> SemanticMapping | None`

### §4.2 Resolve service
- File: `backend/src/services/resolve/service.py`
- Signature:
```python
async def resolve_value(
    self,
    *,
    cube_id: str,
    semantic_key: str,
    raw_filters: list[tuple[int, int]],
    period: str | None,
) -> ResolvedValueResponse: ...
```
- Session ownership mirrors pre-recon §A5.

### §4.3 Coord helper reuse
- Reuse `derive_coord(resolved_filters)` as sole coord encoder. (`backend/src/services/semantic/coord.py:19-61`)

### §4.4 Mapping config → ResolvedDimensionFilter adapter — REQUIRED FOR 3.1c IMPLEMENTATION
**Status:** Hard prerequisite for §5.2 algorithm. Appendix B grep C found no existing config→resolved-filter helper, so this is genuinely new surface.

**File:** `backend/src/services/resolve/filters.py`.

**Signatures:**
```python
def parse_filters_from_query(*, raw_filters: list[tuple[int, int]]) -> list[ResolvedDimensionFilter]:
    ...


def validate_filters_against_mapping(
    *,
    filters: list[ResolvedDimensionFilter],
    mapping: SemanticMapping,
) -> None:
    ...
```
Validation rules (from Appendix B grep B + service references): required dimensions present, no extras, dimension/member validity delegated to existing semantic validator if reusable.

## §5. Resolve flow pseudocode
### §5.1 Handler block
```python
@router.get("/{cube_id}/{semantic_key}", response_model=ResolvedValueResponse)
async def resolve_value_handler(
    cube_id: str = Path(..., min_length=1, max_length=50),
    semantic_key: str = Path(..., min_length=1, max_length=200),  # Round 3: matches mapping table; see §2.2 + DEBT-063.
    dim: list[int] = Query(default_factory=list),
    member: list[int] = Query(default_factory=list),
    period: str | None = Query(default=None, max_length=20),
    service: ResolveService = Depends(_get_resolve_service),
):
    try:
        return await service.resolve_value(
            cube_id=cube_id,
            semantic_key=semantic_key,
            raw_filters=list(zip(dim, member, strict=False)),
            period=period,
        )
    except MappingNotFoundForResolveError:
        raise HTTPException(404, detail={...MAPPING_NOT_FOUND...})
    except ResolveInvalidFiltersError as exc:
        raise HTTPException(400, detail={...RESOLVE_INVALID_FILTERS...})
    except ResolveCacheMissError as exc:
        raise HTTPException(404, detail={...RESOLVE_CACHE_MISS with details...})
    except Exception:
        logger.exception("resolve.internal_error", cube_id=cube_id, semantic_key=semantic_key)
        raise HTTPException(500, detail={...generic internal envelope...})
```
Handler invariants:
- Handler forwards raw filters only; **must not call `derive_coord`**.
- Flat envelope style preserved (R2).

### §5.2 Service block
```python
async def resolve_value(self, *, cube_id, semantic_key, raw_filters, period):
    mapping = await repo.get_active_by_key(cube_id, semantic_key)
    if mapping is None:
        raise MappingNotFoundForResolveError(...)

    filters = parse_filters_from_query(raw_filters=raw_filters)  # per §4.4
    validate_filters_against_mapping(filters=filters, mapping=mapping)  # per §4.4

    coord = derive_coord(filters)
    lookup = dict(cube_id=cube_id, semantic_key=semantic_key, coord=coord, ref_period=period)

    rows = await value_cache_service.get_cached(**lookup)
    if rows:
        row = pick_row(rows, period=period)
        return map_to_resolved(row, mapping, cache_status="hit")

    prime_result = await value_cache_service.auto_prime(
        cube_id=cube_id,
        semantic_key=semantic_key,
        product_id=mapping.product_id,
        resolved_filters=filters,
        frequency_code=resolve_frequency_code(mapping=mapping, metadata_cache=...),
    )

    rows_after = await value_cache_service.get_cached(**lookup)
    if rows_after:
        if prime_result.error:
            logger.warning("resolve.prime_succeeded_with_error", cube_id=cube_id, semantic_key=semantic_key, coord=coord, error_code=sanitize_prime_error(prime_result.error))
        row = pick_row(rows_after, period=period)
        return map_to_resolved(row, mapping, cache_status="primed")

    raise ResolveCacheMissError(
        cube_id=cube_id,
        semantic_key=semantic_key,
        coord=coord,
        period=period,
        prime_attempted=True,
        prime_error_code=sanitize_prime_error(prime_result.error) if prime_result.error else None,
    )
```
Service invariants:
- Re-query uses identical lookup args.
- Prime errors appear only in logs or miss details, never DTO.
- Coord is service-derived only.
- `map_to_resolved(row, mapping, *, cache_status)` MUST handle missing observations correctly: if `row.value is None` then DTO `value=None`; else DTO `value=canonical_str(row.value)`. The function NEVER produces the string literal `"None"`.
- `map_to_resolved` passes `row.missing` to DTO `missing` field unchanged (raw passthrough).

## §6. Test plan
### §6.1 Unit tests
| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_parse_filters_from_query_valid` | valid dim/member pairs | list[ResolvedDimensionFilter] | unit |
| `test_parse_filters_from_query_malformed` | mismatched or invalid pairs | `RESOLVE_INVALID_FILTERS` | unit |
| `test_validate_filters_against_mapping_extra_dim` | extra dimension provided | `RESOLVE_INVALID_FILTERS` | unit |
| `test_pick_row_warns_on_multiple_rows_with_explicit_period` | explicit period + multiple rows | warning + `rows[0]` | unit |
| `test_map_to_resolved_missing_observation` | row.value=None, row.missing=True | DTO value=None, missing=True; never literal "None" string | unit |

### §6.2 Service-layer tests
| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_resolve_hit_no_prime` | first read returns rows | 200 hit | service |
| `test_resolve_hit_returns_missing_observation_faithfully` | seeded cache row with value=None, missing=True | 200 with DTO value=null, missing=true | service |
| `test_resolve_mapping_missing` | no active mapping | 404 mapping not found | service |
| `test_resolve_invalid_filters_missing_dim` | missing required dim | 400 invalid filters | service |
| `test_resolve_invalid_filters_extra_dim` | extra dim | 400 invalid filters | service |
| `test_resolve_cold_cache_auto_prime_success_returns_primed` | cold cache, prime success, second read row | 200 primed | service |
| `test_resolve_cache_miss_prime_error_but_row_written` | prime error + row appears | 200 primed; error in structured logs only | service |
| `test_resolve_cache_miss_prime_error_no_row` | prime error + no row | 404 miss + prime_error_code | service |
| `test_http_to_service_pipeline_wiring` | mocked HTTP→handler→service | full pipeline assertion | service/pipeline |

### §6.3 Integration tests
| test name | scenario | expected outcome | layer |
|---|---|---|---|
| `test_resolve_happy_existing_cache` | seeded row with dim/member query | 200 hit | integration |
| `test_resolve_missing_observation_round_trip` | end-to-end with null-value row in cache | 200 JSON has `"value": null, "missing": true` | integration |
| `test_resolve_cold_cache_full_pipeline` | cold cache + successful prime path | 200 primed | integration |
| `test_resolve_404_mapping_not_found` | absent mapping | 404 | integration |
| `test_resolve_404_cache_miss_after_prime` | no row after prime | 404 miss | integration |
| `test_resolve_filters_validation_400` | malformed dim/member input | 400 invalid filters | integration |
| `test_resolve_auth_required` | missing API key | 401 | integration |

## §7. Coord derivation contract
Coord is service-derived from query filters per BLOCKER-1 resolution; caller never supplies it. The contract below documents the SHARED encoding used by both auto_prime and resolve.
- auto_prime derives coord through `derive_coord(resolved_filters)` and persists exactly that value. (`backend/src/services/statcan/value_cache.py:111`, `backend/src/services/statcan/value_cache.py:162-163`, `backend/src/services/statcan/value_cache.py:412`)
- derive_coord encoding is canonical 10-slot dot-separated string; order-independent input due to slot assignment by `dimension_position_id`. (`backend/src/services/semantic/coord.py:19-61`)

## §8. Period selection contract
- auto_prime persists `ref_period=dp.ref_per`; read DTO period echoes `ref_period`. (`backend/src/services/statcan/value_cache.py:413`)
- repository ordering is ascending `period_start`, then ascending `ref_period`. (`backend/src/repositories/semantic_value_cache_repository.py:360-363`)
- default when `period` omitted: latest is `rows[-1]` via helper.
- explicit `period`: expected single row; if multiple, warn and return `rows[0]`.

```python
def pick_row(rows: list[ValueCacheRow], *, period: str | None) -> ValueCacheRow:
    if period is None:
        return rows[-1]
    if len(rows) > 1:
        logger.warning("resolve.unexpected_multiple_rows_for_explicit_period", count=len(rows))
    return rows[0]
```

## §9. Drift updates required by 3.1c impl PR
- `docs/api.md` draft updates:
  - Query params table uses `dim` + `member` repeated rows (no caller coord).
  - Errors use `RESOLVE_INVALID_FILTERS`; `RESOLVE_CACHE_MISS` row notes details include derived coord + prime_error_code.
  - Rate Limit cell: `Inherits global/default middleware behavior`.
- `BACKEND_API_INVENTORY.md` row update: query contract becomes filter-based (`dim/member` + optional `period`).
- `ROADMAP_DEPENDENCIES.md` delta unchanged from prior recon.
- DEBT-060 remains unchanged.

## §10. Open questions for recon-impl handoff
1. ResolveService placement (`services/resolve/` recommended).
2. `sanitize_prime_error` output format: short code/category string for logs + `RESOLVE_CACHE_MISS.details` only.
3. Encoding choice documentation: Encoding 1 is selected in this recon based on Appendix B grep B/C; impl should preserve rationale in code comments.
4. `resolve_frequency_code` helper source order: prefer mapping field if present, then metadata cache lookup, then `None` fallback; impl to finalize helper signature in service module.

## §11. Founder questions surfaced during recon (escalation)
**Resolved during fix pass (2026-05-03):**
- **F-fix-1 — coord vs auto_prime contract conflict (BLOCKER-1).** Founder selected Option B: resolve takes semantic filter query params, service derives coord internally.
- **F-fix-2 — warning DTO field.** Founder selected removal; errors surface via structured logs + `RESOLVE_CACHE_MISS.details` only.
- **F-fix-3 — value nullability + missing field (Codex auto-review on PR #283).** Cache row `value` is nullable; original DTO declared `value: str` non-optional, which would corrupt suppressed-observation responses. Resolved by making `value: str | None` and adding `missing: bool` raw-passthrough field. Aligns DTO with cache schema per pre-recon §B1.

**No new founder-blockers surfaced during fix pass.**

## Appendix B: Fix-pass grep transcript

### A. ResolvedDimensionFilter shape
Command:
`rg -n "class ResolvedDimensionFilter\b|^ResolvedDimensionFilter\b" backend/src`
Output:
```
backend/src/services/semantic_mappings/validation.py:49:class ResolvedDimensionFilter:
```

Command:
`rg -n "ResolvedDimensionFilter" backend/src/services/statcan/value_cache.py`
Output:
```
39:from src.services.semantic_mappings.validation import ResolvedDimensionFilter
100:        resolved_filters: list[ResolvedDimensionFilter],
```

Command:
`rg -n "ResolvedDimensionFilter" backend/src/services/semantic`
Output:
```
backend/src/services/semantic/coord.py:14:from src.services.semantic_mappings.validation import ResolvedDimensionFilter
backend/src/services/semantic/coord.py:19:def derive_coord(resolved_filters: list[ResolvedDimensionFilter]) -> str:
```

### B. Mapping config schema clues
Command:
`rg -n "config\[" backend/src/services/semantic_mappings backend/src/models/semantic_mapping.py`
Output:
```
(no matches)
```

Command:
`rg -n "filters|dimensions" backend/src/services/semantic_mappings/service.py`
Output:
```
316:        dimension_filters = config_model.dimension_filters or {}
327:            dimension_filters=dimension_filters,
373:                    resolved_filters=result.resolved_filters,
492:                dimension_filters=config_model.dimension_filters or {},
```

### C. Existing config→filter helper
Command:
`rg -n "def.*config.*filter|def.*filter.*config|build_resolved_filter|resolve_filters" backend/src`
Output:
```
(no matches)
```

### D. Existing semantic-mapping-not-found error code
Command:
`rg -n "SEMANTIC_MAPPING_NOT_FOUND|MAPPING_NOT_FOUND|semantic_mapping.*not_found" backend/src`
Output:
```
backend/src/api/routers/admin_semantic_mappings.py:302:                "error_code": "MAPPING_NOT_FOUND",
backend/src/api/routers/admin_semantic_mappings.py:336:                "error_code": "MAPPING_NOT_FOUND",
```

### E. Internal-error code precedent in admin routers
Command:
`rg -n "INTERNAL_ERROR" backend/src/api/routers backend/src/core/error_codes.py`
Output:
```
(no matches)
```

### F. derive_coord signature
Command:
`sed -n '1,80p' backend/src/services/semantic/coord.py`
Output:
```python
"""Phase 3.1aaa: StatCan ``coord`` derivation from validator output.

Pure helper: takes ``ValidationResult.resolved_filters`` from the
3.1ab validator and produces the StatCan native ``coord`` string used
by the WDS data API (e.g.
``getDataFromCubePidCoordAndLatestNPeriods``).

Per founder lock Q-6 (recon §B): validator output reuse is mandatory.
This module deliberately performs no name-matching of its own — it
trusts the (position_id, member_id) pairs already resolved by 3.1ab.
"""
from __future__ import annotations

from src.services.semantic_mappings.validation import ResolvedDimensionFilter

_MAX_DIMENSIONS = 10


def derive_coord(resolved_filters: list[ResolvedDimensionFilter]) -> str:
    """Convert validator-resolved (position_id, member_id) pairs to a coord.

    StatCan's ``coordinate`` argument is a 10-position dot-separated
    string. Each position corresponds to a dimension (1-indexed); a
    value of ``0`` means "all members" / unset. Validator-resolved
    pairs populate the slots their ``dimension_position_id`` indexes.

    Args:
        resolved_filters: Successfully matched (dimension, member) pairs
            from a :class:`ValidationResult`. Order does not matter.

    Returns:
        A 10-position dot-separated string (e.g.
        ``"1.10.0.0.0.0.0.0.0.0"`` for two filtered dimensions).

    Raises:
        ValueError: If a ``dimension_position_id`` is outside ``[1, 10]``
            or if two filters target the same position.

    Pure function — no I/O, no clock, no logger.
    """
    slots = ["0"] * _MAX_DIMENSIONS
    seen_positions: set[int] = set()

    for item in resolved_filters:
        pos = item.dimension_position_id
        member = item.member_id

        if pos < 1 or pos > _MAX_DIMENSIONS:
            raise ValueError(
                f"dimension_position_id out of range: {pos} "
                f"(must be 1..{_MAX_DIMENSIONS})"
            )
        if pos in seen_positions:
            raise ValueError(
                f"duplicate dimension_position_id in resolved_filters: {pos}"
            )

        seen_positions.add(pos)
        slots[pos - 1] = str(member)

    return ".".join(slots)
```
