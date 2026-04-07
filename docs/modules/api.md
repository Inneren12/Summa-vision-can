# Module: API Layer

**Package:** `backend.src.api`
**Purpose:** FastAPI REST endpoints that expose the ETL pipeline and task management functionality. Controllers handle only request/response mapping — no business logic.

## Package Structure

```
api/
├── __init__.py
└── routers/
    ├── __init__.py
    ├── health.py             ← GET /api/health, GET /api/health/ready
    ├── tasks.py              ← GET /api/v1/admin/tasks/{task_id}
    ├── cmhc.py               ← POST /api/v1/admin/cmhc/sync
    └── public_graphics.py    ← GET /api/v1/public/graphics
```

## Endpoints

### Admin Cubes Router (`routers/admin_cubes.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/admin/cubes/search` | Full-text search with typo tolerance | X-API-KEY |
| POST | `/api/v1/admin/cubes/sync` | Trigger catalog sync (persistent job → 202) | X-API-KEY |
| GET | `/api/v1/admin/cubes/{product_id}` | Full cube metadata | X-API-KEY |

Query params for search: `q` (required, min 1 char), `limit` (default 20, max 100).
Sync uses dedupe_key `catalog_sync:{date}` — same-day requests return existing job.

### Health Check (`routers/health.py`)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/health` | 200 | Liveness probe with timestamp |
| `GET` | `/api/health/ready` | 200 / 503 | Readiness, checks DB + temp dir, returns 503 if not ready |

### Task Polling Router (`routers/tasks.py`) — ✅ Complete

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/v1/tasks/{task_id}` | 200 / 404 | Poll task status (PENDING → RUNNING → COMPLETED / FAILED) |

- Returns `TaskStatusResponse` with `task_id`, `status`, `result_url`, `detail`.
- Injects `TaskManager` via `Depends(get_task_manager)`.
- Returns `HTTP 404` if `task_id` is unknown.

### CMHC Router (`routers/cmhc.py`) — ✅ Complete

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/api/v1/cmhc/sync` | 202 | Trigger CMHC extraction pipeline as background task |

- Accepts `CMHCSyncRequest` body with `city: str`.
- Submits `run_cmhc_extraction_pipeline` coroutine to `TaskManager`.
- Returns `HTTP 202 Accepted` with `CMHCSyncResponse(task_id=...)` immediately.
- Injects `TaskManager` and `StorageInterface` via `Depends`.

### Public Graphics Router (`routers/public_graphics.py`) — ✅ Complete

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/v1/public/graphics` | 200 / 422 / 429 | Paginated list of published infographics with presigned preview URLs |

**Query Parameters:**

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `limit` | `int` | `12` | `1 ≤ limit ≤ 50` | Items per page |
| `offset` | `int` | `0` | `≥ 0` | Number of items to skip |
| `sort` | `str` | `"newest"` | `newest \| oldest \| score` | Sort order |

**Behaviour:**
- **Public endpoint** — no API key required.
- Rate-limited to **30 requests/minute per IP** via `InMemoryRateLimiter`.
- Returns `HTTP 429` with `{"detail": "Rate limit exceeded. Try again later."}` when exceeded.
- Includes `Cache-Control: public, max-age=3600` header on every 200 response.
- Each item's `preview_url` is a presigned S3 URL (TTL 3600s) generated from `s3_key_lowres`.
- **Does NOT expose** `s3_key_lowres` or `s3_key_highres` in the response.
- Injects `PublicationRepository`, `StorageInterface`, and `InMemoryRateLimiter` via `Depends`.

## Schemas

| Schema | Module | Fields |
|--------|--------|--------|
| `CMHCSyncRequest` | `routers/cmhc.py` | `city: str` (min_length=1, strip whitespace) |
| `CMHCSyncResponse` | `routers/cmhc.py` | `task_id: str` |
| `TaskStatusResponse` | `core/task_manager.py` | `task_id`, `status` (enum), `result_url`, `detail` |
| `PublicationResponse` | `routers/public_graphics.py` | `id: int`, `headline: str`, `chart_type: str`, `virality_score: float`, `preview_url: str`, `created_at: datetime` |
| `PaginatedGraphicsResponse` | `routers/public_graphics.py` | `items: list[PublicationResponse]`, `limit: int`, `offset: int` |

## Architectural Rules

- **ARCH-DPEN-001**: Controllers receive services via `Depends`, never instantiate them.
- **ARCH-TASK-001**: Long-running operations use TaskManager + HTTP 202.
- HTTP controllers must only handle Request/Response mapping.
- No business logic in routing files.

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `core.task_manager.TaskManager` | `main.py` (router registration) |
| `core.storage.StorageInterface` | — |
| `core.security.ip_rate_limiter.InMemoryRateLimiter` | — |
| `repositories.publication_repository.PublicationRepository` | — |
| `services.cmhc.service.run_cmhc_extraction_pipeline` | — |
| `fastapi.Depends` | — |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
