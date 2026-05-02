# Module: Semantic Mappings

**Package:** `backend.src.services.semantic_mappings`
**Purpose:** Cache-driven validation + service wrapper around
`SemanticMappingRepository`. Maps operator-facing semantic keys (e.g.
`cpi.canada.all_items.index`) to specific cells of StatCan cubes, and
guarantees that those cells exist in the cube's metadata before the row
is persisted.

## Package Structure

```
services/semantic_mappings/
├── __init__.py
├── validation.py    ← validate_mapping_against_cache (pure)
├── exceptions.py    ← MetadataValidationError hierarchy
└── service.py       ← SemanticMappingService
```

## Related Modules

- **Schema / model / repository (Phase 3.1a):** unchanged in 3.1ab.
  - `src/models/semantic_mapping.py` — `SemanticMapping` ORM (`config` JSONB).
  - `src/schemas/semantic_mapping.py` — `SemanticMappingConfig.dimension_filters: dict[str, str]`.
  - `src/repositories/semantic_mapping_repository.py` — `upsert_by_key(payload, *, updated_by)`.
- **Cache (Phase 3.1aa):** `src/services/statcan/metadata_cache.py` provides
  `StatCanMetadataCacheService.get_or_fetch` used by the validator.

## Pure Function — `validate_mapping_against_cache` (`validation.py`)

ARCH-PURA-001: no I/O, no clock, no logger, no exceptions raised.

```python
def validate_mapping_against_cache(
    *,
    cube_id: str,
    product_id: int,
    dimension_filters: dict[str, str],
    cache_entry: CubeMetadataCacheEntry,
) -> ValidationResult: ...
```

Founder lock 1 (2026-05-01): validation is **name-based**, not id-based.
The mapping's `config.dimension_filters` is a `dict[str, str]` of dimension
`name_en` → member `name_en` pairs. Comparison normalizes both sides via
`str.casefold().strip()`. Resolved numeric IDs (`dimension_position_id`,
`member_id`) are populated in the result for downstream consumers
(future ID-based migration, UI hints).

`ValidationResult` aggregates:
- `is_valid: bool` — `True` iff `errors` is empty.
- `errors: list[ValidationError]` — collected, never short-circuited.
  Each error carries `error_code` (`CUBE_PRODUCT_MISMATCH` /
  `DIMENSION_NOT_FOUND` / `MEMBER_NOT_FOUND`), the failing input names,
  any resolved IDs the cache could supply, and an optional
  `suggested_member_name_en` fuzzy hint.
- `resolved_filters: list[ResolvedDimensionFilter]` — successful matches
  with both names and IDs.

Fuzzy member-name hint uses `difflib.get_close_matches` (stdlib, EN-only —
see DEBT-052).

## Exception Hierarchy (`exceptions.py`)

All raised by `SemanticMappingService` (never by the pure function).

- `MetadataValidationError(result, cube_id, error_code='METADATA_VALIDATION_FAILED')` — base.
  - `CubeNotInCacheError` — re-wraps `StatCanUnavailableError` and
    `CubeNotFoundError` from the cache layer (default `error_code='CUBE_NOT_IN_CACHE'`).
  - `DimensionMismatchError` — at least one `DIMENSION_NOT_FOUND` in `result`.
  - `MemberMismatchError` — at least one `MEMBER_NOT_FOUND` in `result`.

The 3.1b admin save endpoint will catch the base class and serialize
`error_code` into the DEBT-030 envelope. Frontend wire codes are
registered in `frontend-public/src/lib/api/errorCodes.ts` and i18n keys
in `frontend-public/messages/{en,ru}.json` under `errors.backend.*`.

## Service — `SemanticMappingService` (`service.py`)

```python
SemanticMappingService(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    repository_factory: Callable[[AsyncSession], SemanticMappingRepository],
    metadata_cache: StatCanMetadataCacheService,
    logger: structlog.stdlib.BoundLogger,
)
```

R6 — short-lived sessions; ARCH-DPEN-001 — full DI.

- `upsert_validated(*, cube_id, product_id, semantic_key, label, description, config, is_active, updated_by) -> SemanticMapping`
  1. **Pydantic validates `config`** as `SemanticMappingConfig` first.
     A bad shape raises `pydantic.ValidationError` BEFORE any cache fetch
     — bad input never triggers a StatCan call.
  2. Calls `metadata_cache.get_or_fetch(cube_id, product_id)`.
  3. Re-wraps cache exceptions (`StatCanUnavailableError` /
     `CubeNotFoundError` → `CubeNotInCacheError`;
     `CubeMetadataProductMismatchError` →
     `MetadataValidationError(error_code='CUBE_PRODUCT_MISMATCH')`).
  4. Runs `validate_mapping_against_cache`. On failure, raises the most
     specific exception class (precedence: product-mismatch ⇒ dimension
     ⇒ member). Logs `semantic_mapping.validation_failed` with the full
     error-code list for ops visibility.
  5. Constructs a `SemanticMappingCreate` payload from the validated
     config model and calls `repo.upsert_by_key(payload, updated_by=updated_by)`
     inside a fresh session, commits, and returns the ORM row.

Per Phase 3.1b admin endpoint wiring: route handlers will go through
this service. The repository's `upsert_by_key` is no longer called
directly from request handlers once 3.1b ships.

## Seed CLI

`backend/scripts/seed_semantic_mappings.py` defaults to the validated
path (constructs `httpx.AsyncClient` + `StatCanClient` +
`StatCanMetadataCacheService` + `SemanticMappingService` inline). When
validation is on, each YAML row must include a top-level `product_id`
key (StatCan numeric ID). `--skip-validation` reverts to the 3.1a
direct-repo path and emits a structlog warning
(`seed.skip_validation_enabled`) for offline/dev use.

### Atomicity

Validated seed runs (default) commit per row, not per file. A failure on
row N does not roll back rows 1..N-1 that already passed validation and
were committed. To re-run a partially-failed seed, fix the bad row and
re-apply — `upsert_by_key` is idempotent on `(cube_id, semantic_key)`.
Operators who need to bypass StatCan checks during recovery can use
`--skip-validation` (which uses whole-file commit semantics).

A future bulk service with cross-row transactional wrapping for the
validated path is out of scope for 3.1ab.

## Tests

| Test file | Count | Strategy |
|-----------|-------|----------|
| `tests/services/semantic_mappings/test_validation.py` | 8 | Pure function — no async, no mocks |
| `tests/services/semantic_mappings/test_service.py` | 8 | In-memory SQLite + `AsyncMock(spec=StatCanMetadataCacheService)` |
| `tests/integration/test_semantic_mapping_service_integration.py` | 2 | Real Postgres via `pg_session`; StatCan client mocked |
| `tests/scripts/test_seed_semantic_mappings.py` | 2 | `--skip-validation` flag spy; default-path smoke test |

## Architecture Rules Used

- **ARCH-PURA-001** — `validate_mapping_against_cache` and
  `_maybe_fuzzy_suggest` / `_normalize_name` are pure functions.
- **ARCH-DPEN-001** — `SemanticMappingService.__init__` receives every
  collaborator (session factory, repository factory, metadata cache,
  logger) via constructor injection.
- **R6** — service holds a session factory, opens one session per call.

---

## Maintenance

This file MUST be updated in the same PR that changes the described
functionality. If you add/modify/remove a class, module, rule, or test
under `services/semantic_mappings/` — update this doc in the same commit.
