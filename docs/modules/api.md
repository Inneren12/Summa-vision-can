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
    ├── public_graphics.py    ← GET /api/v1/public/graphics
    ├── public_leads.py       ← POST /api/v1/public/leads/capture
    └── public_download.py    ← GET /api/v1/public/download
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

### Lead Capture Router (`routers/public_leads.py`) — ✅ Updated (D-2)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/api/v1/public/leads/capture` | 200 / 403 / 404 / 422 / 429 | Trade email + Turnstile CAPTCHA for a Magic Link email |

**Request Body:** `LeadCaptureRequest` — `email: EmailStr`, `asset_id: int`, `turnstile_token: str`

**Flow:**
1. Rate limit (3 req/min per IP) → 429.
2. Validate Turnstile CAPTCHA → 403 on failure.
3. Validate asset_id exists with status=PUBLISHED → 404.
4. Check lead deduplication — resend logic with separate rate limit (1/2min per IP).
5. Save lead to DB immediately (before any external calls).
6. Generate download token (SHA-256 hash only in DB, R17).
7. Build Magic Link → `{PUBLIC_SITE_URL}/downloading?token={raw_token}`.
8. Send email via BackgroundTasks (Magic Link only — NO presigned URL in email, R1).
9. Write AuditEvents: `lead.captured`, `lead.email_sent`, `token.created`.
10. Return `{"message": "Check your email for the download link"}`.

### Download Router (`routers/public_download.py`) — ✅ New (D-2)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/v1/public/download?token=<raw>` | 307 / 403 / 404 | Exchange magic-link token for presigned S3 URL via redirect |

**Flow:**
1. Hash incoming token → SHA-256.
2. Atomic token activation (UPDATE with guards — use_count, expires_at, revoked).
3. If invalid → 403 with specific error reason (expired/exhausted/revoked/invalid).
4. Look up Lead → Publication → s3_key_highres.
5. Generate presigned URL (TTL: `SIGNED_URL_TTL_MINUTES * 60`).
6. 307 Redirect to presigned URL.
7. Write AuditEvent: `token.activated`. If last use → also `token.exhausted`.

## Schemas

| Schema | Module | Fields |
|--------|--------|--------|
| `CMHCSyncRequest` | `routers/cmhc.py` | `city: str` (min_length=1, strip whitespace) |
| `CMHCSyncResponse` | `routers/cmhc.py` | `task_id: str` |
| `TaskStatusResponse` | `core/task_manager.py` | `task_id`, `status` (enum), `result_url`, `detail` |
| `PublicationResponse` | `routers/public_graphics.py` | `id: int`, `headline: str`, `chart_type: str`, `virality_score: float`, `preview_url: str`, `created_at: datetime` |
| `PaginatedGraphicsResponse` | `routers/public_graphics.py` | `items: list[PublicationResponse]`, `limit: int`, `offset: int` |
| `LeadCaptureRequest` | `schemas/public_leads.py` | `email: EmailStr`, `asset_id: int`, `turnstile_token: str` |
| `LeadCaptureResponse` | `schemas/public_leads.py` | `message: str` |

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
| `repositories.lead_repository.LeadRepository` | — |
| `repositories.download_token_repository.DownloadTokenRepository` | — |
| `services.email.interface.EmailServiceInterface` | — |
| `services.security.turnstile.TurnstileValidator` | — |
| `services.audit.AuditWriter` | — |
| `services.cmhc.service.run_cmhc_extraction_pipeline` | — |
| `fastapi.Depends` | — |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
