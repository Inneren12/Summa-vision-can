# Module: API Layer

**Package:** `backend.src.api`
**Purpose:** FastAPI REST endpoints that expose the ETL pipeline and task management functionality. Controllers handle only request/response mapping — no business logic.

## Package Structure

```
api/
├── __init__.py
└── routers/
    ├── __init__.py
    ├── health.py               ← GET /api/health, GET /api/health/ready
    ├── admin_kpi.py            ← GET /api/v1/admin/kpi
    ├── admin_leads.py          ← POST /api/v1/admin/leads/resync (D-3)
    ├── admin_publications.py   ← CRUD /api/v1/admin/publications (Editor + Gallery)
    ├── public_graphics.py      ← GET /api/v1/public/graphics
    ├── public_leads.py         ← POST /api/v1/public/leads/capture (D-2, D-3)
    ├── public_download.py      ← GET /api/v1/public/download
    ├── public_metr.py          ← GET /api/v1/public/metr/* (Theme #2)
    └── public_sponsorship.py   ← POST /api/v1/public/sponsorship/inquire (D-3)
```

## Endpoints

### Admin Jobs Router (`routers/admin_jobs.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/admin/jobs` | List jobs with optional filters | X-API-KEY |
| POST | `/api/v1/admin/jobs/{job_id}/retry` | Retry a failed job | X-API-KEY |

Query params for list: `job_type` (optional), `status` (optional, one of: queued/running/success/failed/cancelled), `limit` (default 50, max 200).

List response: `{ items: [JobItemResponse], total: int }` — items include all job fields (id, job_type, status, payload_json, result_json, error_code, error_message, attempt_count, max_attempts, created_at, started_at, finished_at, created_by, dedupe_key).

Retry logic:
- Job not found → 404.
- Job status != failed → 409 "Only failed jobs can be retried".
- attempt_count >= max_attempts → 409 "Job has exhausted retry attempts".
- Success → 202 Accepted with `{ job_id, status: "queued" }`.

### Admin Cubes Router (`routers/admin_cubes.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/admin/cubes/search` | Full-text search with typo tolerance | X-API-KEY |
| POST | `/api/v1/admin/cubes/sync` | Trigger catalog sync (persistent job → 202) | X-API-KEY |
| GET | `/api/v1/admin/cubes/{product_id}` | Full cube metadata | X-API-KEY |

Query params for search: `q` (required, min 1 char), `limit` (default 20, max 100).
Sync uses dedupe_key `catalog_sync:{date}` — same-day requests return existing job.

### Admin Publications Router (`routers/admin_publications.py`) — ✅ New (Editor + Gallery)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST   | `/api/v1/admin/publications`                 | Create a publication in `DRAFT`                 | X-API-KEY |
| GET    | `/api/v1/admin/publications`                 | List publications (optional status filter)      | X-API-KEY |
| GET    | `/api/v1/admin/publications/{publication_id}`| Fetch a single publication                       | X-API-KEY |
| PATCH  | `/api/v1/admin/publications/{publication_id}`| Partial update (editorial + visual_config)       | X-API-KEY |
| POST   | `/api/v1/admin/publications/{publication_id}/publish`   | Flip DRAFT → PUBLISHED + emit audit event | X-API-KEY |
| POST   | `/api/v1/admin/publications/{publication_id}/unpublish` | Flip PUBLISHED → DRAFT (preserves `published_at`) | X-API-KEY |
| GET    | `/api/v1/admin/publications/{publication_id}/leads`     | List leads attributed to this publication via UTM (Phase 2.3) | X-API-KEY |

**Query params for list:**
- `status` (optional, one of `draft` / `published` / `all`, default `all`).
- `limit` (default 50, min 1, max 200).
- `offset` (default 0, min 0).

**Behaviour:**
- All endpoints sit behind `AuthMiddleware` (`X-API-KEY` required) — missing key returns 401.
- `POST /` accepts `PublicationCreate`. Returns **201 Created** with the full `PublicationResponse` (status forced to `DRAFT`).
- `PATCH /{id}` accepts `PublicationUpdate` (`extra='forbid'` — typos rejected with 422). PATCH semantics:
  - Field **omitted** from the body → column unchanged.
  - Field sent as **`null`** → column is **cleared** (`None` in DB). Applies to nullable editorial fields (`eyebrow`, `description`, `source_text`, `footnote`, `visual_config`).
  - Field sent with a value → column updated.
  - Driven by `model.model_dump(exclude_unset=True)` + a repository `update_fields` that applies every key present in the dict (including explicit `None`).
- `visual_config` is persisted as a JSON string in the database. The router serialises a `VisualConfig` Pydantic model on the way in and parses it back into a `VisualConfig` on the way out. Parse failures are logged (`publication_visual_config_parse_failed`) and surface as `null` rather than 500. `VisualConfig.branding` is a typed `BrandingConfig` (`show_top_accent: bool`, `show_corner_mark: bool`, `accent_color: str`).
- **`review` (Stage 3 PR 4)** — optional top-level field on `PublicationCreate`, `PublicationUpdate`, and `PublicationResponse`. Shape: `{ workflow: "draft" | "in_review" | "approved" | "exported" | "published", history: list[dict], comments: list[dict] }`. Persisted as a JSON string in the `review` column (Text, SQLite-compat). Nested `history` / `comments` entries are accepted as opaque dicts — deep validation is the frontend's responsibility (`assertCanonicalDocumentV2Shape`). Parse failures on the read path surface as `review: null` (same fall-back as `visual_config`).
  - **Workflow → status sync rule.** When a PATCH carries a `review` with `workflow == "published"`, the router additionally flips `Publication.status` to `PUBLISHED` and stamps `published_at`. A transition out of `"published"` demotes `status` back to `DRAFT` but preserves `published_at` for audit.
  - **Audit events on transition.** A PATCH that changes `review.workflow` emits one of the new `EventType` members via `_classify_workflow_event(previous, target)`. Mapping (business semantics, not target-only):
    - `draft → in_review` → `PUBLICATION_WORKFLOW_SUBMITTED`
    - `in_review → approved` → `PUBLICATION_WORKFLOW_APPROVED`
    - `in_review → draft` → `PUBLICATION_WORKFLOW_CHANGES_REQUESTED` (reviewer pushback)
    - any other `* → draft` (e.g. `approved → draft`, `exported → draft`) → `PUBLICATION_WORKFLOW_RETURNED_TO_DRAFT` (revocation)
    - `approved → exported` → `PUBLICATION_WORKFLOW_EXPORTED`

    `metadata = {"from": <prev>, "to": <new>}`. Transitions into `"published"` also emit `PUBLICATION_PUBLISHED` with `metadata.source = "patch_review"`; the `PUBLICATION_WORKFLOW_*` axis is skipped for the `"published"` target — publish has its own audit channel.
  - **Never exposed publicly** — `PublicationPublicResponse` deliberately omits `review`. See `backend/src/schemas/publication.py` for the inline leak-prevention comment.
- `POST /{id}/publish` writes an `AuditEvent` of type `EventType.PUBLICATION_PUBLISHED` (`entity_type="publication"`, `entity_id={id}`, `actor="admin_api"`, `metadata={"headline": ...}`). Stamps `published_at = func.now()`. When the row carries a `review`, the endpoint also mirrors `review.workflow = "published"` and appends a `"system"`-authored history entry so the editor's timeline reflects admin-driven transitions.
- `POST /{id}/unpublish` writes a symmetric `AuditEvent` of type `EventType.PUBLICATION_PUBLISHED` with `metadata={"action": "unpublish", "new_status": "DRAFT", "headline": ...}` (the enum has no dedicated `PUBLICATION_UNPUBLISHED` member). Does **not** clear `published_at` — the original publish timestamp is preserved for audit history. When a `review` exists, the endpoint also mirrors `review.workflow = "draft"` with a `"system"` history entry.
- Missing IDs → 404 `{"detail": "Publication not found"}`.
- Sensitive S3 keys (`s3_key_lowres`, `s3_key_highres`) are **never** included in the admin response — only `cdn_url` (currently always `null` until CDN integration lands).
- Dependencies: `PublicationRepository` and `AuditWriter` are injected via `_get_repo` / `_get_audit` (ARCH-DPEN-001).
- **Phase 2.3 — `GET /{publication_id}/leads`.** Returns the leads attributed to this publication via `Lead.utm_content == Publication.lineage_key`. Response is `list[AdminLeadResponse]` and includes UTM attribution fields. It does not return `ip_address`. Ordered newest-first; `limit` query param defaults to 200 (1–500). 404 if the publication does not exist. The contract relies on the publish-kit lock that `utm_content == lineage_key` (Phase 2.2) — leads with no UTM (organic submissions) are deliberately excluded.

### Admin KPI Router (`routers/admin_kpi.py`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/admin/kpi` | Aggregated KPI dashboard metrics | X-API-KEY |

Query params: `days` (default 30, min 1, max 365) — aggregation window in days. The API accepts any integer in the 1–365 range; the Flutter admin UI offers preset shortcuts (7, 30, 90 days).

Returns `KPIResponse` with:
- **Publications**: total, published, draft counts (all-time).
- **Leads**: total, B2B, Education, ISP, B2C counts, ESP sync status (within period).
- **Download funnel**: emails_sent, tokens_created/activated/exhausted (from AuditEvent within period).
- **Jobs**: total, succeeded, failed, queued, running, failed_by_type breakdown (within period).
- **System**: catalog_syncs, data_contract_violations (from AuditEvent within period).
- **Period**: period_start, period_end timestamps.

Dependency: `KPIService` injected via `Depends`. Uses `get_session_factory()` for a short-lived read-only session.

### Health Check (`routers/health.py`)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/health` | 200 | Liveness probe with timestamp |
| `GET` | `/api/health/ready` | 200 / 503 | Readiness, checks DB + temp dir, returns 503 if not ready |

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

**Request Body:** `LeadCaptureRequest` (`extra="forbid"`) — `email: EmailStr`, `asset_id: int`, `turnstile_token: str`, plus optional Phase 2.3 UTM attribution: `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`. Visitors arriving via a publish-kit share URL forward these from `URLSearchParams`; `utm_content` carries the source publication's `lineage_key`.

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

### Admin Leads Router (`routers/admin_leads.py`) — ✅ New (D-3)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/admin/leads/resync` | Retry ESP sync for unsynced leads | X-API-KEY |

**Behaviour:**
- Fetches all leads where `esp_synced=False` and `esp_sync_failed_permanent=False`.
- For each lead, attempts ESP `add_subscriber` with exponential backoff (max 3 attempts, delays `2^attempt` seconds via `asyncio.sleep()`).
- On `ESPPermanentError` (4xx) → marks lead as permanently failed.
- On `ESPTransientError` (5xx/timeout) after 3 attempts → increments `failed_transient`, does not mark permanent.
- Returns `ResyncResult` with `total`, `synced`, `failed_transient`, `failed_permanent` counts.

### Sponsorship Inquiry Router (`routers/public_sponsorship.py`) — ✅ New (D-3)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/public/sponsorship/inquire` | Submit B2B sponsorship inquiry | None (public) |

**Request Body:** `SponsorshipInquiryRequest` — `name: str`, `email: EmailStr`, `budget: str`, `message: str`

**Behaviour:**
- Rate-limited to **1 request per 5 minutes per IP** via `InMemoryRateLimiter`.
- Lead scored via `LeadScoringService`:
  - **b2c** (free email) → 422 "Please use a corporate email address."
  - **b2b** → Slack notification with `[B2B LEAD]` tag, saved to DB.
  - **education** → Slack notification with `[EDUCATION]` tag, saved to DB.
  - **isp** → Saved to DB only (no Slack notification).
- Dedupe key: `inquiry:{email}`.
- Returns `{"message": "Your inquiry has been received. ..."}`

### METR Calculator Router (`routers/public_metr.py`) — ✅ New (Theme #2)

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/api/v1/public/metr/calculate` | 200 / 422 / 429 | Calculate METR at a specific income point |
| `GET` | `/api/v1/public/metr/curve` | 200 / 422 / 429 | Generate full METR curve across income range |
| `GET` | `/api/v1/public/metr/compare` | 200 / 422 / 429 | Compare METR across all 4 provinces |

**Calculate — Query Parameters:**

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `income` | `int` | — | `0 ≤ income ≤ 500,000` | Annual gross employment income |
| `province` | `str` | `"ON"` | `ON \| BC \| AB \| QC` | Province code |
| `family_type` | `str` | `"single"` | `single \| single_parent \| couple` | Family type |
| `n_children` | `int` | `0` | `0 ≤ n ≤ 6` | Number of children |
| `children_under_6` | `int` | `0` | `0 ≤ n ≤ 6` | Children under age 6 |

**Curve — Additional Parameters:**

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `income_min` | `int` | `15,000` | `≥ 0` | Income range start |
| `income_max` | `int` | `155,000` | `≤ 500,000` | Income range end |
| `step` | `int` | `1,000` | `500 ≤ step ≤ 5,000` | Income step size |

**Behaviour:**
- **Public endpoint** — no API key required.
- Rate-limited to **60 requests/minute per IP** via `InMemoryRateLimiter`.
- Pure CPU calculations — no DB, no network I/O. Engine functions are pure (ARCH-PURA-001).
- Quebec uses simplified modelling (separate Revenu Québec filing not modelled).
- Compare endpoint returns provinces sorted by METR descending.
- Curve endpoint includes dead zone detection, peak METR, and annotations.
- Tax year: **2025**.

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
| `PublicationPublicResponse` (public) | `schemas/publication.py` | Single source of truth for the public gallery. `id: int`, `headline`, `chart_type`, `virality_score?`, `preview_url?`, `status` (`default="PUBLISHED"`), `cdn_url?`, `created_at`, editorial fields (`eyebrow?`, `description?`, `source_text?`, `footnote?`), lifecycle timestamps (`updated_at?`, `published_at?`). **No** `visual_config`, **no** S3 keys. Re-exported from `routers/public_graphics.py` as `PublicationResponse` for backward-compat imports. |
| `PaginatedGraphicsResponse` | `routers/public_graphics.py` | `items: list[PublicationPublicResponse]`, `limit: int`, `offset: int` |
| `BrandingConfig` | `schemas/publication.py` | `show_top_accent: bool = True`, `show_corner_mark: bool = True`, `accent_color: str = "#FBBF24"` — typed branding block inside `VisualConfig`. |
| `VisualConfig` | `schemas/publication.py` | `layout: str`, `palette: str`, `background: str`, `size: str`, `custom_primary?: str`, `branding: BrandingConfig` (typed — replaces loose dict). |
| `PublicationCreate` | `schemas/publication.py` | `headline: str` (req), `chart_type: str` (req), `eyebrow?`, `description?`, `source_text?`, `footnote?`, `visual_config?: VisualConfig`, `virality_score?: float` |
| `PublicationUpdate` | `schemas/publication.py` | All fields optional; `model_config = ConfigDict(extra="forbid")`. PATCH contract: omitted field → unchanged; explicit `null` → cleared; value → updated. Driven by `model_dump(exclude_unset=True)`. |
| `PublicationResponse` (admin) | `schemas/publication.py` | Full record — `id: str`, lifecycle (`status`, `created_at`, `updated_at`, `published_at`), editorial fields, `visual_config: VisualConfig?`, `cdn_url?` |
| `LeadCaptureRequest` | `schemas/public_leads.py` | `email: EmailStr`, `asset_id: int`, `turnstile_token: str` |
| `LeadCaptureResponse` | `schemas/public_leads.py` | `message: str` |
| `KPIResponse` | `schemas/kpi.py` | Aggregated metrics: publications, leads, download funnel, jobs, system health, period |
| `SponsorshipInquiryRequest` | `routers/public_sponsorship.py` | `name: str`, `email: EmailStr`, `budget: str`, `message: str` |
| `ResyncResult` | `routers/admin_leads.py` | `total: int`, `synced: int`, `failed_transient: int`, `failed_permanent: int` |
| `JobItemResponse` | `routers/admin_jobs.py` | `id: str`, `job_type: str`, `status: str`, `payload_json`, `result_json`, `error_code`, `error_message`, `attempt_count: int`, `max_attempts: int`, `created_at`, `started_at`, `finished_at`, `created_by`, `dedupe_key` |
| `JobListResponse` | `routers/admin_jobs.py` | `items: list[JobItemResponse]`, `total: int` |
| `RetryJobResponse` | `routers/admin_jobs.py` | `job_id: str`, `status: str` |
| `METRCalculateResponse` | `schemas/metr.py` | `gross_income: int`, `net_income: int`, `metr: float`, `zone: str`, `keep_per_dollar: float`, `components: METRComponentsResponse` |
| `METRCurveResponse` | `schemas/metr.py` | `province: str`, `family_type: str`, `n_children: int`, `children_under_6: int`, `curve: list[CurvePoint]`, `dead_zones`, `peak`, `annotations` |
| `METRCompareResponse` | `schemas/metr.py` | `income: int`, `family_type: str`, `provinces: list[ProvinceCompareItem]` |

## Architectural Rules

- **ARCH-DPEN-001**: Controllers receive services via `Depends`, never instantiate them.
- **ARCH-TASK-001**: Long-running operations use persistent Job system + HTTP 202.
- HTTP controllers must only handle Request/Response mapping.
- No business logic in routing files.

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `repositories.job_repository.JobRepository` (admin_jobs) | `main.py` (router registration) |
| `core.storage.StorageInterface` | — |
| `core.security.ip_rate_limiter.InMemoryRateLimiter` | — |
| `repositories.publication_repository.PublicationRepository` | — |
| `schemas.publication.{PublicationCreate, PublicationUpdate, PublicationResponse, PublicationPublicResponse, VisualConfig, BrandingConfig}` (admin_publications + public_graphics) | — |
| `repositories.lead_repository.LeadRepository` | — |
| `repositories.download_token_repository.DownloadTokenRepository` | — |
| `services.email.interface.EmailServiceInterface` | — |
| `services.security.turnstile.TurnstileValidator` | — |
| `services.audit.AuditWriter` | — |
| `services.crm.scoring.LeadScoringService` | — |
| `services.notifications.slack.SlackNotifierService` | — |
| `services.email.esp_client.ESPSubscriberInterface` | — |
| `services.metr.engine` (public_metr) | — |
| `schemas.metr` (public_metr) | — |
| `fastapi.Depends` | — |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
