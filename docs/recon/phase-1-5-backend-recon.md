# Stage B Phase 1.5 — Backend Recon: `product_id` in `PreviewResponse`

Date: 2026-04-26  
Branch target: `claude/phase-1-5-backend-recon` (cut from `work`)  
Mode: plan-only recon (no implementation changes in this PR)

---

## §A. Decisions reference (Founder lock, 2026-04-26)

### D1. Schema change — add nullable product_id

`PreviewResponse` gains:

```python
product_id: str | None = None
```

Nullable for graceful behavior on non-StatCan storage paths and for backward compatibility during deploy gap (frontend ships before backend would still parse responses, just without diff baseline key).

Default `None` so existing test fixtures don't break.

### D2. Population logic — parse from storage_key

In `preview_data` endpoint, after computing `preview_df`, derive `product_id` from the storage_key string. Implementation:

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

Place in a small helper module (e.g., `backend/src/services/statcan/key_parser.py`) to keep the regex testable in isolation, OR inline in the endpoint file with module-level docstring (recon picks based on existing project patterns).

### D3. No DB lookup for product_id

Even though cube_catalog could provide a more authoritative mapping, v1 uses parsing only. Rationale:
- Zero DB query overhead per preview request
- Pure function, easy to unit-test
- StatCan path structure is the single source of truth for product_id

Future hardening (DEBT-track): if storage path structure changes, parser silently returns None and feature degrades gracefully. No breakage.

### D4. No frontend changes in this PR

This recon's scope is backend-only. Frontend integration ships in **PR 2 (Phase 1.5 Frontend)** which depends on this PR being merged first. PR 2 recon will reference this PR's merged state.

### D5. Tests required

- Unit test for `_extract_product_id_from_storage_key`
  - StatCan path → returns product_id
  - Non-StatCan path → returns None
  - Malformed path → returns None
  - Empty string → returns None
- Endpoint test: response includes `product_id` for StatCan key
- Endpoint test: response has `product_id=None` for non-StatCan key
- Backward-compat: existing test response shapes still valid after field addition (None default)

---

## §V. Verification log

### §V.1 storage_key pattern

Verification commands:

```bash
sed -n '40,60p' backend/src/services/statcan/data_fetch.py
sed -n '170,200p' backend/src/services/statcan/data_fetch.py
rg -n "PROCESSED_KEY_TEMPLATE|processed_key" backend/src/services/statcan/
```

Observed source excerpts:

```python
# S3 key pattern for processed data (R3)
PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
...
processed_key = PROCESSED_KEY_TEMPLATE.format(
    product_id=product_id, date=today
)
```

Confirmed pattern matches prior halt finding exactly:

```python
PROCESSED_KEY_TEMPLATE = "statcan/processed/{product_id}/{date}.parquet"
processed_key = PROCESSED_KEY_TEMPLATE.format(product_id=product_id, date=today)
```

### §V.2 `preview_data` endpoint signature + response construction

Verification commands:

```bash
sed -n '1,50p' backend/src/api/routers/admin_data.py
sed -n '220,280p' backend/src/api/routers/admin_data.py
```

Observed endpoint slice:

```python
@router.get(
    "/data/preview/{storage_key:path}",
    response_model=PreviewResponse,
    summary="Preview stored data",
    description=(
        "Returns the first N rows of a stored Parquet file as JSON. "
        "Capped at MAX_PREVIEW_ROWS (default 100, R15). "
        "Values are typed: null→None, datetime→ISO string, "
        "numeric→Python scalar."
    ),
)
async def preview_data(
    storage_key: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> PreviewResponse:
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
- Path parameter shape is `{storage_key:path}`, so slashes are accepted in key.
- `storage_key` is consumed as raw string and passed to storage loader.
- `PreviewResponse` currently populates only: `storage_key`, `rows`, `columns`, `column_names`, `data`.

### §V.3 `PreviewResponse` schema

Verification commands:

```bash
rg -n "class PreviewResponse" backend/src/schemas/
sed -n '1,80p' backend/src/schemas/transform.py
```

Observed schema definition:

```python
class PreviewResponse(BaseModel):
    """Response for GET /data/preview/{storage_key}."""

    storage_key: str
    rows: int
    columns: int
    column_names: list[str]
    data: list[dict[str, Any]]
```

Field order is currently exactly as above; `product_id` should be appended last for non-disruptive ordering.

### §V.4 Other storage paths assessment

Verification command:

```bash
rg -n "\.parquet|S3_KEY|storage_key" backend/src/services/ | head -30
```

Observed hits were concentrated in StatCan fetch flow and job handler payloading:
- `backend/src/services/statcan/data_fetch.py` contains explicit processed/raw key templates.
- `backend/src/services/jobs/handlers.py` passes through `result.storage_key` from StatCan fetch result.

No additional concrete non-StatCan `.parquet` key template family was discovered from this scan in `backend/src/services/`.

Behavioral conclusion for parser strategy:
- Regex `^statcan/processed/([^/]+)/[^/]+\.parquet$` will return `product_id` for StatCan processed keys.
- It returns `None` for all non-matching keys (including short test keys like `test.parquet`), which is acceptable graceful degradation for PR 2 UX fallback.

### §V.5 Test inventory

Verification commands:

```bash
rg -l "preview_data|PreviewResponse" backend/tests/
ls backend/tests/api/
rg -n "preview|/data/preview|storage_key" backend/tests/api/test_admin_data.py
```

Observed relevant tests:
- `backend/tests/api/test_admin_data.py`
  - `test_preview_returns_data`
  - `test_preview_respects_limit`
  - `test_preview_not_found`
  - `test_preview_requires_auth`

Existing preview test URLs include:
- `.../data/preview/statcan/processed/test.parquet` (StatCan-like prefix but no `{product_id}/{date}` shape)
- `.../data/preview/test.parquet`
- `.../data/preview/nonexistent.parquet`

Assessment:
- Endpoint preview behavior is covered.
- There is **not yet** a test with fully realistic StatCan processed key shape `statcan/processed/{product_id}/{date}.parquet`.
- No dedicated helper tests exist yet for product_id parsing.

---

## §B. Backend specification

### B.1 Helper function placement

Command used:

```bash
ls backend/src/services/statcan/
```

Current module set does not include a key parser module. Decision: create new helper module:

- `backend/src/services/statcan/key_parser.py`

with module docstring + exact function/regex source from D2.

### B.2 Endpoint modification (`admin_data.py`)

In `backend/src/api/routers/admin_data.py`, update `preview_data` response construction to include parsed product id:

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

Also add import for helper function.

### B.3 Schema modification (`transform.py`)

Append field at end of `PreviewResponse`:

```python
class PreviewResponse(BaseModel):
    # existing fields unchanged order
    product_id: str | None = None  # NEW
```

Rationale: preserve current serialized field order, maintain compatibility with existing tests/clients.

### B.4 Tests

#### B.4.1 Helper unit tests

Add new file:

- `backend/tests/services/statcan/test_key_parser.py`

Cover:
- valid StatCan path → product_id extracted
- dotted product_id allowed
- non-StatCan path → None
- malformed path → None
- empty string → None
- wrong extension → None

#### B.4.2 Endpoint integration tests

Extend/create:

- `backend/tests/api/test_admin_data_preview.py` (or extend `test_admin_data.py` to match repo style)

Cases required:
- `test_preview_includes_product_id_for_statcan_key`
- `test_preview_product_id_none_for_user_upload`
- `test_existing_preview_assertions_still_pass`

Fixture note: ensure app test setup mirrors main wiring by including `register_exception_handlers(app)` per memory #14.

### B.5 Documentation updates

- `docs/api.md`: add `product_id: string | null` to preview response schema docs.
- `docs/ARCHITECTURE.md`: no change.
- `DEBT.md`: no entry required at recon stage.

---

## §C. Frontend specification

No frontend changes in this PR.

PR 2 (Phase 1.5 Frontend) will consume `PreviewResponse.product_id` as Hive baseline key and fall back to "No baseline" UX when null.

If implementation unexpectedly requires frontend touches in this PR, STOP and escalate.

---

## §D. Implementation execution gates (for implementation PR after this recon)

1. `mypy backend/src/` clean.
2. New tests pass first run.
3. Existing endpoint tests still pass.
4. `git diff --name-only` whitelist:
   - `backend/src/services/statcan/key_parser.py` (new or extended)
   - `backend/src/api/routers/admin_data.py`
   - `backend/src/schemas/transform.py`
   - `backend/tests/services/statcan/test_key_parser.py` (new)
   - `backend/tests/api/test_admin_data_preview.py` (new or extended)
   - `docs/api.md`
   - Anything outside → STOP.
5. Frontend untouched gate: `git diff --name-only | rg '^frontend'` returns empty.
6. No DB lookup added gate: `rg -n "session\.execute|session\.scalar|select\(" backend/src/api/routers/admin_data.py` shows no new query in `preview_data`.

---

## §E. Open follow-ups (NOT scope)

- Storage path schema resilience: if StatCan path structure changes later, parser should return `None` and frontend degrades gracefully; evaluate DB-backed mapping only if this becomes recurring maintenance overhead.
- Phase 1.5 PR 2 (frontend): implement Hive keying/diff UX on `product_id` after this backend PR merges.
