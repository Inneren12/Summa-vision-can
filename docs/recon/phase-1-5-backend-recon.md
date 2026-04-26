# Phase 1.5 Backend Recon — `product_id` in `PreviewResponse`

Date: 2026-04-26  
Branch target: `claude/phase-1-5-backend-recon` (cut from `work`)  
Mode: plan-only, no implementation changes in this PR.

## §A. Decisions reference

### D1. Schema change — add nullable product_id

`PreviewResponse` gains:

```python
product_id: str | None = None
```

Nullable for graceful behavior on non-StatCan storage paths and for
backward compatibility during deploy gap (frontend ships before
backend would still parse responses, just without diff baseline key).

Default `None` so existing test fixtures don't break.

### D2. Population logic — parse from storage_key

In `preview_data` endpoint, after computing `preview_df`, derive
`product_id` from the storage_key string. Implementation:

```python
import re
_STATCAN_PRODUCT_ID_PATTERN = re.compile(
    r"^statcan/processed/([^/]+)/[^/]+\.parquet$"
)


def _extract_product_id_from_storage_key(storage_key: str) -> str | None:
    """Extract StatCan product_id from a processed-data storage key.

    Returns None for non-StatCan paths (user uploads, derived tables,
    test fixtures with custom keys). The frontend treats None as
    "no diff baseline available" — graceful degradation.
    """
    match = _STATCAN_PRODUCT_ID_PATTERN.match(storage_key)
    return match.group(1) if match else None
```

Place in a small helper module (e.g., `backend/src/services/statcan/key_parser.py`)
to keep the regex testable in isolation, OR inline in the endpoint
file with module-level docstring (recon picks based on existing
project patterns).

### D3. No DB lookup for product_id

Even though cube_catalog could provide a more authoritative mapping,
v1 uses parsing only. Rationale:
- Zero DB query overhead per preview request
- Pure function, easy to unit-test
- StatCan path structure is the single source of truth for product_id

Future hardening (DEBT-track): if storage path structure changes,
parser silently returns None and feature degrades gracefully. No
breakage.

### D4. No frontend changes in this PR

This recon's scope is backend-only. Frontend integration ships in
**PR 2 (Phase 1.5 Frontend)** which depends on this PR being merged
first. PR 2 recon will reference this PR's merged state.

### D5. Tests required

- Unit test for `_extract_product_id_from_storage_key`
  - StatCan path → returns product_id
  - Non-StatCan path → returns None
  - Malformed path → returns None
  - Empty string → returns None
- Endpoint test: response includes `product_id` for StatCan key
- Endpoint test: response has `product_id=None` for non-StatCan key
- Backward-compat: existing test response shapes still valid after
  field addition (None default)

## §V. Verification log

### §V.1 storage_key pattern

Command output (verbatim):

```bash
$ sed -n '40,60p' backend/src/services/statcan/data_fetch.py

# Dynamic periods by frequency (R13)
PERIODS_MAP: dict[str, int] = {
    "Daily": 1000,
    "Monthly": 120,
    "Quarterly": 40,
    "Annual": 20,
}

# S3 key pattern for processed data (R3)
PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
RAW_KEY_TEMPLATE = "statcan/raw/{product_id}/{date}.csv"

# Scalar factor multipliers (StatCan SCALAR_ID values)
SCALAR_FACTOR_MAP: dict[int, float] = {
    0: 1.0,           # units
    1: 10.0,
    2: 100.0,
    3: 1_000.0,       # thousands
    4: 10_000.0,
    5: 100_000.0,

$ sed -n '170,200p' backend/src/services/statcan/data_fetch.py
                total_rows=quality.total_rows,
            )

        # --- Stage 5: Validate schema contract ---
        self._validate_schema(df, product_id)
        self._validate_duplicates(df, product_id)

        # --- Stage 6: Save as Parquet (R3) ---
        processed_key = PROCESSED_KEY_TEMPLATE.format(
            product_id=product_id, date=today
        )
        await self._save_parquet(processed_key, df)

        log.info(
            "fetch_completed",
            rows=df.height,
            columns=df.width,
            storage_key=processed_key,
            null_pct=round(quality.null_percentage, 1),
        )

        return FetchResult(
            product_id=product_id,
            rows=df.height,
            columns=df.width,
            storage_key=processed_key,
            quality=quality,
        )

    # ------------------------------------------------------------------
    # Internal methods

$ rg -n "PROCESSED_KEY_TEMPLATE|processed_key" backend/src/services/statcan/
backend/src/services/statcan/data_fetch.py:50:PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
backend/src/services/statcan/data_fetch.py:178:        processed_key = PROCESSED_KEY_TEMPLATE.format(
backend/src/services/statcan/data_fetch.py:181:        await self._save_parquet(processed_key, df)
backend/src/services/statcan/data_fetch.py:187:            storage_key=processed_key,
backend/src/services/statcan/data_fetch.py:195:            storage_key=processed_key,
```

Conclusion: prior halt finding is confirmed exactly (Case 2-like key shape with `{date}` segment).

### §V.2 preview_data endpoint signature

Command output (verbatim slices):

```bash
$ sed -n '1,50p' backend/src/api/routers/admin_data.py
"""Admin endpoints for data fetch, transform, and preview.

Protected by AuthMiddleware — requires ``X-API-KEY`` header.

Endpoints:
    POST /api/v1/admin/cubes/{product_id}/fetch — Trigger data download
    POST /api/v1/admin/data/transform             — Apply transforms
    GET  /api/v1/admin/data/preview/{storage_key}  — Preview stored data
"""
...

$ sed -n '220,280p' backend/src/api/routers/admin_data.py
# -----------------------------------------------------------------------
# GET /api/v1/admin/data/preview/{storage_key:path}
# -----------------------------------------------------------------------

@router.get(
    "/data/preview/{storage_key:path}",
    response_model=PreviewResponse,
    summary="Preview stored data",
...
)
async def preview_data(
    storage_key: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> PreviewResponse:
    """Preview stored Parquet data."""
...
    return PreviewResponse(
        storage_key=storage_key,
        rows=preview_df.height,
        columns=preview_df.width,
        column_names=preview_df.columns,
        data=data,
    )
```

Findings:
- Endpoint path param is `storage_key:path` (allows slash-containing keys).
- `preview_data` currently returns `PreviewResponse` without `product_id`.

### §V.3 PreviewResponse schema

Command output (verbatim):

```bash
$ rg -n "class PreviewResponse" backend/src/schemas/
backend/src/schemas/transform.py:63:class PreviewResponse(BaseModel):

$ sed -n '1,80p' backend/src/schemas/transform.py
...
class PreviewResponse(BaseModel):
    """Response for GET /data/preview/{storage_key}."""

    storage_key: str
    rows: int
    columns: int
    column_names: list[str]
    data: list[dict[str, Any]]
```

Finding: add `product_id: str | None = None` at end to preserve existing field order.

### §V.4 Other storage paths assessment

Command output (verbatim):

```bash
$ rg -n "\.parquet|S3_KEY|storage_key" backend/src/services/ | head -30
backend/src/services/statcan/data_fetch.py:50:PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
backend/src/services/statcan/data_fetch.py:92:    storage_key: str
backend/src/services/statcan/data_fetch.py:187:            storage_key=processed_key,
backend/src/services/statcan/data_fetch.py:195:            storage_key=processed_key,
backend/src/services/jobs/handlers.py:172:        "storage_key": result.storage_key,

$ rg -n "temp/uploads|processed/|output_key|\.parquet" backend/src/api backend/src/services | head -80
backend/src/api/schemas/admin_graphics.py:107:    under ``temp/uploads/{uuid}.parquet`` and then enqueues the existing
backend/src/services/statcan/data_fetch.py:50:PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
backend/src/api/routers/admin_graphics.py:16:    temporary Parquet in S3 (``temp/uploads/{uuid}.parquet``) and then
backend/src/api/routers/admin_graphics.py:245:        3. Upload to ``temp/uploads/{uuid}.parquet`` via
backend/src/api/routers/admin_graphics.py:268:    # 3. Upload under temp/uploads/
backend/src/api/routers/admin_graphics.py:269:    temp_key = f"temp/uploads/{uuid.uuid4().hex}.parquet"
backend/src/api/routers/admin_data.py:202:    output_key = body.output_key or _generate_output_key(body)
backend/src/api/routers/admin_data.py:207:    await _save_parquet_bytes(storage, output_key, parquet_bytes)
backend/src/api/routers/admin_data.py:211:        output_key=output_key,
backend/src/api/routers/admin_data.py:217:        output_key=output_key,
backend/src/api/routers/admin_data.py:316:def _generate_output_key(body: TransformRequest) -> str:
backend/src/api/routers/admin_data.py:325:    return f"statcan/transformed/{today}/{h}.parquet"

$ sed -n '300,340p' backend/src/api/routers/admin_data.py
...
def _generate_output_key(body: TransformRequest) -> str:
    """Generate a deterministic output key from input + operations."""
...
    return f"statcan/transformed/{today}/{h}.parquet"
```

Assessment:
- Non-StatCan-processed families exist and can be previewed via `/data/preview/{storage_key:path}`:
  1) `temp/uploads/{uuid}.parquet` (graphics upload temp data)
  2) `statcan/transformed/{date}/{hash}.parquet` (transform endpoint outputs)
- The proposed regex `^statcan/processed/([^/]+)/[^/]+\.parquet$` intentionally matches only processed keys and returns `None` for these families (desired graceful degradation).

### §V.5 Test inventory

Command output (verbatim):

```bash
$ rg -l "preview_data|PreviewResponse" backend/tests/

$ ls backend/tests/api/
__init__.py
test_admin_cubes.py
test_admin_data.py
test_admin_graphics.py
test_admin_graphics_upload.py
test_admin_jobs.py
test_admin_kpi.py
test_admin_publications.py
test_admin_publications_document_state.py
test_auth_middleware.py
test_download.py
test_error_handler_validation.py
test_health.py
test_lead_capture.py
test_lead_capture_scoring.py
test_public_graphics.py
test_public_leads.py
test_public_metr.py
test_resync.py
test_sponsorship.py

$ rg -n "preview|PreviewResponse|/data/preview" backend/tests/api/test_admin_data.py backend/tests/api/test_admin_*.py
backend/tests/api/test_admin_data.py:1:"""Tests for admin data endpoints: fetch, transform, preview.
backend/tests/api/test_admin_data.py:202:# ---- GET /data/preview ----
backend/tests/api/test_admin_data.py:205:async def test_preview_returns_data(client: AsyncClient) -> None:
backend/tests/api/test_admin_data.py:215:            "/api/v1/admin/data/preview/statcan/processed/test.parquet",
backend/tests/api/test_admin_data.py:229:async def test_preview_respects_limit(client: AsyncClient) -> None:
backend/tests/api/test_admin_data.py:239:            "/api/v1/admin/data/preview/test.parquet?limit=3",
backend/tests/api/test_admin_data.py:248:async def test_preview_not_found(client: AsyncClient) -> None:
backend/tests/api/test_admin_data.py:257:            "/api/v1/admin/data/preview/nonexistent.parquet",
backend/tests/api/test_admin_data.py:265:async def test_preview_requires_auth(client_no_auth: AsyncClient) -> None:
backend/tests/api/test_admin_data.py:266:    """GET /data/preview without API key → 401."""
backend/tests/api/test_admin_data.py:267:    resp = await client_no_auth.get("/api/v1/admin/data/preview/test.parquet")

$ sed -n '180,300p' backend/tests/api/test_admin_data.py
...
async def test_preview_returns_data(client: AsyncClient) -> None:
...
        resp = await client.get(
            "/api/v1/admin/data/preview/statcan/processed/test.parquet",
            headers=API_KEY,
        )
...
async def test_preview_respects_limit(client: AsyncClient) -> None:
...
        resp = await client.get(
            "/api/v1/admin/data/preview/test.parquet?limit=3",
            headers=API_KEY,
        )
```

Assessment:
- Existing endpoint tests live in `backend/tests/api/test_admin_data.py`.
- Current “StatCan-like” key in tests is `statcan/processed/test.parquet` (missing `{product_id}/{date}` shape), so a new realistic StatCan key case should be added in implementation PR.
- Non-StatCan path case already exists (`test.parquet` / `nonexistent.parquet`) and can be extended to assert `product_id is None`.

## §B. Backend specification

### B.1 Helper function

Project layout read:

```bash
$ ls backend/src/services/statcan/
__init__.py
catalog_sync.py
client.py
data_fetch.py
maintenance.py
schemas.py
service.py
validators.py
```

Decision: create **new helper module** `backend/src/services/statcan/key_parser.py` (no existing parser module).

Required function (exact):

```python
import re

_STATCAN_PRODUCT_ID_PATTERN = re.compile(
    r"^statcan/processed/([^/]+)/[^/]+\.parquet$"
)


def _extract_product_id_from_storage_key(storage_key: str) -> str | None:
    """Extract StatCan product_id from a processed-data storage key.

    Returns None for non-StatCan paths (user uploads, derived tables,
    test fixtures with custom keys). The frontend treats None as
    "no diff baseline available" — graceful degradation.
    """
    match = _STATCAN_PRODUCT_ID_PATTERN.match(storage_key)
    return match.group(1) if match else None
```

### B.2 Endpoint modification

File: `backend/src/api/routers/admin_data.py`

In `preview_data`, modify response construction to:

```python
return PreviewResponse(
    storage_key=storage_key,
    rows=preview_df.height,
    columns=preview_df.width,
    column_names=preview_df.columns,
    data=data,
    product_id=_extract_product_id_from_storage_key(storage_key),
)
```

Import parser helper at module top.

### B.3 Schema modification

File: `backend/src/schemas/transform.py`

Add field at end of `PreviewResponse` model:

```python
class PreviewResponse(BaseModel):
    storage_key: str
    rows: int
    columns: int
    column_names: list[str]
    data: list[dict[str, Any]]
    product_id: str | None = None  # NEW, keep last for JSON order stability
```

### B.4 Tests

#### B.4.1 Helper unit tests

New file: `backend/tests/services/statcan/test_key_parser.py`

Required cases:
- StatCan path returns product ID
- Dotted product ID returns product ID
- User upload path returns `None`
- Transformed path returns `None`
- Empty string returns `None`
- Malformed path returns `None`
- Wrong extension returns `None`

#### B.4.2 Endpoint integration tests

Extend `backend/tests/api/test_admin_data.py` with:
- `test_preview_includes_product_id_for_statcan_key` using realistic key, e.g. `statcan/processed/18-10-0004-01/2026-04-26.parquet`
- `test_preview_product_id_none_for_user_upload` using e.g. `temp/uploads/abc-123.parquet`
- Keep/verify existing preview tests for backward compatibility

Execution note for impl PR: ensure test app fixture wiring includes `register_exception_handlers(app)` per project memory.

### B.5 Documentation

- Update `docs/api.md` PreviewResponse schema to include `product_id: string | null`.
- `docs/ARCHITECTURE.md`: no change.
- `DEBT.md`: no entry required for this PR.

## §C. Frontend specification

No frontend changes in this PR.

Frontend consumption (`product_id` as baseline key for diffing) is explicitly deferred to Phase 1.5 PR 2.

## §D. Implementation execution gates (for impl PR after this recon)

1. `mypy backend/src/` clean.
2. New tests pass first run.
3. Existing endpoint tests still pass.
4. `git diff --name-only` whitelist exactly:
   - `backend/src/services/statcan/key_parser.py` (new or extended)
   - `backend/src/api/routers/admin_data.py`
   - `backend/src/schemas/transform.py`
   - `backend/tests/services/statcan/test_key_parser.py` (new)
   - `backend/tests/api/test_admin_data.py` (extended)
   - `docs/api.md`
5. Frontend untouched gate: `git diff --name-only | rg '^frontend'` must be empty.
6. No DB lookup added gate: `rg -n "session\.execute|session\.scalar|select\(" backend/src/api/routers/admin_data.py` must show no new query in `preview_data`.

## §E. Open follow-ups (NOT scope)

- Storage path schema resilience: regex parse failure intentionally degrades to `product_id=None`. If storage key taxonomy changes materially, revisit with catalog-backed lookup.
- Phase 1.5 PR 2 (frontend): Hive baseline by product_id, diff service wiring, UI highlighting.

## Notes on pre-recon availability

Pre-recon files were not present at either expected path during this run:
- `/mnt/user-data/outputs/phase-1-5-data-diffing-pre-recon.md` → missing
- `docs/recon/phase-1-5-data-diffing-pre-recon.md` → missing

This recon was authored from the prompt-embedded context plus verification reads captured above.
