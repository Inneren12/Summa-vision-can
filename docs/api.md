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

## Maintenance

This file MUST be updated in the same PR that changes the described API.
