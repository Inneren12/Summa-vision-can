# API Reference

## Authentication

All `/api/v1/admin/*` endpoints require authentication (Phase 2.5 — PR-42).
Currently, no `AuthMiddleware` is enforced; endpoints are accessible without an API key.

---

## Health Check

### `GET /api/health`

| Property | Value |
|----------|-------|
| Auth | None |
| Rate Limit | None |

**Response (200):**
```json
{
  "status": "ok",
  "timestamp": "2026-03-17T03:45:00+00:00"
}
```

---

## Admin Endpoints

### `GET /api/v1/admin/queue`

List draft publications ordered by virality score (highest first).

| Property | Value |
|----------|-------|
| Auth | Admin (future PR-42) |
| Rate Limit | 10 req/min (future PR-42) |

**Query Parameters:**

| Param | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `limit` | `int` | `20` | 1–100 | Max items to return |

**Response (200):**
```json
[
  {
    "id": 1,
    "headline": "Canadian Housing Starts Surge 15%",
    "chart_type": "BAR",
    "virality_score": 8.5,
    "status": "DRAFT",
    "created_at": "2026-03-17T03:00:00+00:00"
  }
]
```

Returns `[]` if no drafts exist (never 404).

---

### `POST /api/v1/admin/graphics/generate`

Trigger asynchronous graphic generation for a draft publication.

| Property | Value |
|----------|-------|
| Auth | Admin (future PR-42) |
| Rate Limit | 10 req/min (future PR-42) |

**Request Body:**
```json
{
  "brief_id": 1,
  "size_preset": "instagram",
  "dpi": 150,
  "watermark": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brief_id` | `int` | *required* | Publication ID (must be DRAFT) |
| `size_preset` | `"instagram" \| "twitter" \| "reddit"` | `"instagram"` | Target platform size |
| `dpi` | `int` | `150` | Rendering DPI (72–300) |
| `watermark` | `bool` | `true` | Apply watermark |

**Size Presets:**

| Preset | Dimensions |
|--------|-----------|
| `instagram` | 1080 × 1080 |
| `twitter` | 1200 × 628 |
| `reddit` | 1200 × 900 |

**Response (202 Accepted):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Generation started"
}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| 404 | `brief_id` does not match any publication |
| 409 | Publication exists but is not in `DRAFT` status |
| 422 | Invalid request body (validation error) |

**Polling:** Use `GET /api/v1/admin/tasks/{task_id}` to poll for completion.

---

### `POST /api/v1/admin/graphics/generate-from-data`

Enqueue graphic generation from user-uploaded JSON/CSV data. The backend
converts rows into a temporary Parquet (`temp/uploads/{uuid}.parquet`)
and reuses the existing `graphics_generate` job type — the
`GraphicPipeline` itself is unchanged.

| Property | Value |
|----------|-------|
| Auth | Admin (`X-API-KEY`) |
| Rate Limit | 10 req/min |

**Request Body:**
```json
{
  "data": [
    {"year": "2020", "value": 100},
    {"year": "2021", "value": 120}
  ],
  "columns": [
    {"name": "year", "dtype": "str"},
    {"name": "value", "dtype": "float"}
  ],
  "chart_type": "line",
  "title": "Custom Series",
  "size": [1200, 900],
  "category": "housing",
  "source_label": "custom"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data` | `list[dict]` | *required* | Rows as JSON objects. Must be 1–10 000 rows (R15). |
| `columns` | `list[{name, dtype}]` | *required* | Column specs. `dtype` ∈ `str`, `int`, `float`, `date`. |
| `chart_type` | `str` | *required* | Same chart types as `/generate`. |
| `title` | `str` | *required* | Chart headline. |
| `size` | `[w, h]` | `[1200, 900]` | Pixel dimensions, each in 1–4096. |
| `category` | `str` | *required* | Background template category. |
| `source_label` | `str` | `"custom"` | Label stored in metadata (no `source_product_id`). |

**Response (202 Accepted):**
```json
{"job_id": "7", "status": "queued"}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| 401 | Missing/invalid `X-API-KEY` |
| 422 | Empty / oversized data, invalid dimensions, or malformed rows |

Poll via `GET /api/v1/admin/jobs/{job_id}` exactly as for `/generate`.

---


### `GET /api/v1/admin/data/preview/{storage_key:path}`

Preview rows from a stored Parquet file.

| Field | Type | Description |
| --- | --- | --- |
| `storage_key` | string | Storage key requested for preview. |
| `rows` | integer | Number of rows returned (capped by server and `limit`). |
| `columns` | integer | Number of columns in the previewed file. |
| `column_names` | array of string | Ordered column names in the file. |
| `data` | array of object | Preview rows serialized as typed JSON objects. |
| `product_id` | string \| null | StatCan product ID parsed from storage_key, null for non-StatCan paths. |

---

### `GET /api/v1/admin/tasks/{task_id}`

Poll the status of a background task.

| Property | Value |
|----------|-------|
| Auth | Admin (future PR-42) |
| Rate Limit | None |

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | UUID returned by a submission endpoint |

**Response (200):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "COMPLETED",
  "result_url": null,
  "detail": "Task completed successfully."
}
```

**Task Status Values:** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`

**Errors:**

| Status | Condition |
|--------|-----------|
| 404 | Unknown `task_id` |

---

### `POST /api/v1/admin/cmhc/sync`

Trigger CMHC data extraction (background task).

| Property | Value |
|----------|-------|
| Auth | Admin (future PR-42) |
| Rate Limit | None |

**Request Body:**
```json
{
  "city": "toronto"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## Public Endpoints

### `GET /api/v1/public/graphics`

Paginated list of published infographics with public CDN URLs for previews.

| Property | Value |
|----------|-------|
| Auth | None (public) |
| Rate Limit | 30 req/min per IP |

**Query Parameters:**

| Param | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `limit` | `int` | `12` | 1–50 | Items per page |
| `offset` | `int` | `0` | ≥0 | Items to skip |
| `sort` | `str` | `"newest"` | `newest`, `oldest`, `score` | Sort order |

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "headline": "Example Headline",
      "chart_type": "BAR",
      "virality_score": 8.5,
      "cdn_url": "https://cdn.summa.vision/...",
      "version": 1,
      "created_at": "2026-03-17T03:00:00+00:00"
    }
  ],
  "limit": 12,
  "offset": 0
}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| 429 | Rate limit exceeded |

---

### `GET /api/v1/public/graphics/{id}`

Returns a single published infographic by its ID.

| Property | Value |
|----------|-------|
| Auth | None (public) |
| Rate Limit | 30 req/min per IP |

**Path Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `id` | `int` | Publication ID |

**Response (200):**
```json
{
  "id": 1,
  "headline": "Example Headline",
  "chart_type": "BAR",
  "virality_score": 8.5,
  "cdn_url": "https://cdn.summa.vision/...",
  "version": 1,
  "created_at": "2026-03-17T03:00:00+00:00"
}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| 404 | Unknown `id` or not published |
| 429 | Rate limit exceeded |

---

## Admin Resolve Router

Phase 3.1c. Singular cache-first resolve endpoint that fronts
`StatCanValueCacheService.get_cached` with auto-prime on miss.

### `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}`

| Property | Value |
|----------|-------|
| Auth | Admin (X-API-KEY via `AuthMiddleware`) |
| Rate Limit | Inherits global/default middleware behavior |

**Path params:**

| Param | Type | Constraints |
|-------|------|-------------|
| `cube_id` | `str` | 1–50 chars |
| `semantic_key` | `str` | 1–200 chars (matches `SemanticMapping.semantic_key`; cache table is varchar(100), see DEBT-063) |

**Query params (Encoding 1 — repeated pairs):**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `dim` | `int` (repeated) | `[]` | Dimension `position_id` values |
| `member` | `int` (repeated) | `[]` | Corresponding `member_id` values |
| `period` | `str` (optional) | `null` | Pinned `ref_period` (≤20 chars). Omit for latest. |

The router pairs `dim[i]` with `member[i]` and forwards them to the
service, which derives the canonical 10-slot StatCan `coord` internally
via `derive_coord(...)`. Caller-provided `coord` is NOT accepted (BLOCKER-1
Option B).

**Response (200) — `ResolvedValueResponse`:**

```json
{
  "cube_id": "18-10-0004",
  "semantic_key": "cpi.canada.all_items.index",
  "coord": "1.10.0.0.0.0.0.0.0.0",
  "period": "2025-12",
  "value": "157.4",
  "missing": false,
  "resolved_at": "2026-05-01T12:00:00+00:00",
  "source_hash": "...",
  "is_stale": false,
  "units": "index",
  "cache_status": "hit",
  "mapping_version": 3
}
```

`value` is `string | null`. When the upstream observation is suppressed,
`value` is `null` and `missing` is `true` (raw passthrough from the
cache row — F-fix-3 missing-observation contract).

**Errors:**

| Status | `error_code` | Condition |
|--------|--------------|-----------|
| 400 | `RESOLVE_INVALID_FILTERS` | Filter set fails parse / mapping-shape validation. Details include derived `expected`/`provided`/`reason`. |
| 401 | `auth.*` | Missing or invalid `X-API-KEY`. |
| 404 | `MAPPING_NOT_FOUND` | Mapping is missing or `is_active=false`. |
| 404 | `RESOLVE_CACHE_MISS` | No cached row after auto-prime + re-query. Details include derived `coord`, `period`, `prime_attempted`, `prime_error_code`. |
| 422 | (FastAPI) | Path / query parameter validation failure. |

---

## Maintenance

This file MUST be updated in the same PR that changes the described API.
| POST | `/api/v1/admin/publications/{id}/clone` | Clone a published publication into a new draft. Returns 201 + new publication. |
