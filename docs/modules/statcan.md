# Module: StatCan ETL

**Package:** `backend.src.services.statcan`
**Purpose:** Wraps Statistics Canada public Web Data Service endpoints, applying retry logic, rate limiting via Token Bucket, maintenance window guards, schema validation, scalar factor normalization, and data quality reporting.

## Package Structure

```
services/statcan/
├── __init__.py
├── maintenance.py     ← StatCanMaintenanceGuard
├── client.py          ← StatCanClient (httpx wrapper)
├── schemas.py         ← Pydantic V2 response models
├── service.py         ← StatCanETLService
├── metadata_cache.py  ← StatCanMetadataCacheService
└── validators.py      ← DataQualityReport model
```

## Related Models

### `CubeCatalog` (models/cube_catalog.py)
Index of all ~7,000 StatCan data cubes with bilingual metadata.
- `product_id` (str, unique) — StatCan business identifier (e.g. "14-10-0127-01")
- `cube_id_statcan` (int) — StatCan numeric ID
- `title_en` / `title_fr` — bilingual titles
- `subject_code` / `subject_en` — subject classification
- `frequency` — release cadence (Daily/Monthly/Quarterly/Annual)
- PostgreSQL: weighted full-text search (`search_vector`) + trigram similarity
- SQLite: LIKE-based fallback search in repository (A-2)

Populated by `CatalogSyncService` (A-3).
Queried by `CubeCatalogRepository` (A-2) and Search API (A-4).
Read by `DataFetchService` (A-5) for dynamic periods.

## Classes

### `CatalogSyncService` (services/statcan/catalog_sync.py)
Downloads full StatCan cube catalog and syncs to `cube_catalog` table.
- `sync_full_catalog() -> SyncReport(total, new, updated, errors)`
- Uses `getAllCubesList` endpoint, batch upsert (500), progress log every 1000
- Runs as persistent job: `dedupe_key = catalog_sync:{yyyy-mm-dd}`
- TODO: wire to scheduler in future PR

### `DataFetchService` (services/statcan/data_fetch.py) — Polars zone
Downloads StatCan cube data vectors, validates schema, normalizes
scalar factors, saves as Parquet.
- `fetch_cube_data(product_id) -> FetchResult`
- Polars-native: NO pandas import (R4)
- Parquet-only output (R3)
- Dynamic periods by frequency (R13)
- Schema validation: REQUIRED_COLUMNS contract (R14)
- Data quality: null % warning threshold
- TODO: wire dedupe_key in API endpoint (A-7)

### `StatCanMaintenanceGuard` (maintenance.py) — ✅ Complete
Prevents API calls during the StatCan maintenance window (00:00–08:30 EST).
- `is_maintenance_window(current_time: datetime) -> bool` — Pure function, no `datetime.now()`.

### `StatCanClient` (client.py) — ✅ Complete
Async HTTP client wrapping `httpx.AsyncClient` with integrated guards.
- `__init__(self, http_client: httpx.AsyncClient, maintenance_guard: StatCanMaintenanceGuard, rate_limiter: AsyncTokenBucket)` — Full DI constructor.
- `get(url, **kwargs) -> httpx.Response` — Convenience GET wrapper.
- `request(method, url, **kwargs) -> httpx.Response` — Core method with:
  - Maintenance window check → raises `DataSourceError(error_code="DATASOURCE_MAINTENANCE")`.
  - Token bucket rate limiting (`await self._rate_limiter.acquire()`).
  - Exponential backoff retries for HTTP 429, 409, 503 (up to 3 retries).
  - `structlog.warning()` on every retry with `attempt`, `status_code`, `sleep_duration`.
  - `DataSourceError(error_code="DATASOURCE_RETRIES_EXHAUSTED")` when retries are exhausted.
  - `DataSourceError(error_code="DATASOURCE_NETWORK_ERROR")` on timeouts/connection errors.

### `ChangedCubeResponse` (schemas.py) — ✅ Complete
Pydantic V2 model for StatCan `/getChangedCubeList` response.
- Inherits `StatCanBaseModel` with `ConfigDict(populate_by_name=True, alias_generator=to_camel)`.
- Fields: `product_id`, `cube_title_en`, `cube_title_fr`, `release_time`, `frequency_code`, etc.

### `CubeMetadataResponse` (schemas.py) — ✅ Complete
Pydantic V2 model for cube metadata.
- `scalar_factor_code: int` — **Required field** with `@field_validator(mode="before")` coercing string → int.
- `dimensions: List[DimensionSchema]` — Explicit alias `Field(..., alias="dimension")`.

### `DimensionSchema` (schemas.py) — ✅ Complete
Pydantic V2 model for dimension metadata within cube responses.

### `StatCanETLService` (service.py) — ✅ Complete
Service orchestrator for the StatCan data pipeline.
- `__init__(self, client: StatCanClient)` — DI constructor.
- `fetch_todays_releases() -> list[CubeMetadataResponse]` — Async. Calls `getChangedCubeList` then `getCubeMetadata`.
- `normalize_dataset(raw_csv_content: str, scalar_factor_code: int | None) -> tuple[pd.DataFrame, DataQualityReport]` — Synchronous, pure data processing:
  1. Defaults `scalar_factor_code` to 0 if None.
  2. `pd.to_numeric(df['VALUE'], errors='coerce')` BEFORE scalar multiplication.
  3. Applies `10 ** scalar_factor_code` multiplier.
  4. Returns `DataQualityReport` with NaN metrics.
  5. Logs `WARNING` via structlog when NaN% > 50%.

### `DataWorkbench` (services/data/workbench.py) — Polars zone, PURE
Pure transformation library for StatCan data. No I/O.
- `aggregate_time(df, freq, method)` — resample time series
- `filter_geo(df, geography)` — filter by province/territory
- `filter_date_range(df, start, end)` — date window filter
- `calc_yoy_change(df)` — Year-over-Year % change
- `calc_mom_change(df)` — Month-over-Month % change
- `calc_rolling_avg(df, window)` — rolling average
- `merge_cubes(dfs, merge_keys)` — join multiple cubes (R14 validated)
All functions return NEW DataFrame. Zero side effects.

### `StatCanMetadataCacheService` (metadata_cache.py) — ✅ Complete (Phase 3.1aa)
Persistent cache of StatCan cube metadata used by the semantic mapping
validator (3.1ab) in cache-required mode. Populated either on first
admin save (auto-prime via `get_or_fetch`) or by the nightly
`statcan_metadata_cache_refresh` scheduler job (15:00 UTC).
- `__init__(self, session_factory: async_sessionmaker[AsyncSession], client: StatCanClient, clock: Callable[[], datetime], logger: structlog.BoundLogger)` — Full DI constructor (ARCH-DPEN-001).
- `get_cached(cube_id) -> CubeMetadataCacheEntry | None` — Pure cache read; never calls StatCan.
- `get_or_fetch(cube_id, product_id) -> CubeMetadataCacheEntry` — Read-through; raises `StatCanUnavailableError` on miss + API failure, `CubeNotFoundError` when StatCan returns no SUCCESS envelope. Concurrent-insert safe via `IntegrityError` rollback + re-read.
- `refresh(cube_id, product_id, *, force=False) -> CubeMetadataCacheEntry` — Always fetches and upserts. `force` is reserved for DEBT-051 (event-driven invalidation) and currently a no-op flag.
- `refresh_all_stale(stale_after: timedelta) -> RefreshSummary` — Stale sweep; per-cube errors caught and counted.
- DTO `CubeMetadataCacheEntry` (frozen dataclass): immutable view of a cache row at the service boundary. Repository returns ORM objects; service converts. This is a deliberate convention extension vs `SemanticMappingRepository`, which returns ORM rows directly.
- Exceptions: `MetadataCacheError` (base), `CubeNotFoundError`, `StatCanUnavailableError`, `CubeMetadataProductMismatchError` (raised when `get_or_fetch`/`refresh` is called with a `(cube_id, product_id)` pair that conflicts with an existing cache row — cache-key integrity error; not auto-healed). (Validator-side errors `CubeNotInCacheError` / `DimensionMismatchError` ship with 3.1ab.)

### `DataQualityReport` (validators.py) — ✅ Complete
Frozen Pydantic model: `total_rows`, `valid_rows`, `nan_rows`, `nan_percentage`.

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `core.rate_limit.AsyncTokenBucket` | `api.routers.cmhc` (via future scheduling) |
| `core.exceptions.DataSourceError` | `core.scheduler` (`fetch_todays_releases`, `statcan_metadata_cache_refresh`) |
| `httpx.AsyncClient` | — |
| `pandas` | — |
| `pydantic` v2 | — |
| `structlog` | — |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
