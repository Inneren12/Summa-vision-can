# Architecture

## System Overview

The current flow is:

```
   Data Sources → ETL Pipeline → Cube Catalog (search) → Data Workbench → Visual Engine → Publication
                                                                                              ↓
                                                                                     Human-in-the-Loop (Admin)
```

### Download Flow (D-2)

```
   User clicks "Download High-Res" → DownloadModal (Turnstile + email)
           ↓
   POST /api/v1/public/leads/capture
           ↓
   Lead saved → Token (SHA-256) stored → Magic Link email sent
           ↓
   User clicks email link → /downloading page (token in URL, cleared immediately)
           ↓
   User clicks "Verify and Download" → GET /api/v1/public/download?token=...
           ↓
   Atomic token activation → 307 redirect to presigned S3 URL → file downloads
```

**Security constraints (R1, R17):** No presigned URLs in emails. No auto-downloads.
Raw tokens never stored in DB (SHA-256 only). Tokens limited to 5 uses, 48h TTL.

### Lead Scoring + Notifications Flow (D-3)

```
   Lead captured (POST /capture)
           ↓ (background task)
   LeadScoringService.score_lead(email)  ← pure sync, ARCH-PURA-001
           ↓
   Update lead: is_b2b, company_domain, category
           ↓
   ┌─ b2b/education → SlackNotifierService.notify_lead() (with dedupe)
   └─ isp/b2c → skip Slack
           ↓
   ESPClient.add_subscriber(email)
   ├─ Success → mark esp_synced=True
   ├─ 4xx → mark esp_sync_failed_permanent=True
   └─ 5xx/timeout → leave esp_synced=False (retried via /admin/leads/resync)
```

**Admin resync:** `POST /api/v1/admin/leads/resync` retries unsynced leads with exponential backoff (3 attempts, delays 1s/2s).

## Infrastructure Layer

- **Docker:** Dockerfile + two compose files
- **Health endpoints:** `/api/health` (liveness), `/api/health/ready` (readiness)
- **Resource semaphores:** data_sem(2), render_sem(2), io_sem(10)
- **Database:** PostgreSQL-only runtime, pool_size=8
- **Storage:** MinIO (dev) / S3 (prod)
  - *Note:* Public gallery API returns `cdn_url` (e.g. `https://cdn.summa.vision/publications/...`) directly from the CDN base URL config rather than generating presigned URLs (per R1).
- **Background Jobs:** persistent DB-backed job system (JobRunner + handler registry)
  - Handlers: `catalog_sync` (A-3), `cube_fetch` (A-5), `graphics_generate` (B-4)

## ETL Pipelines

- **Track A (StatCan)**: Catalog Sync → Search → Fetch → Workbench → Chart.

## Data Engine

- CubeCatalog with bilingual FTS (coming in A-1..A-4)
- DataFetchService with Polars-first pipeline (coming in A-5)
- DataWorkbench pure transforms (coming in A-6)
Note: Polars is primary engine, Pandas only in legacy StatCan code.

## Visual Engine

Plotly SVG + backgrounds + compositor.
Note template backgrounds instead of AI backgrounds for MVP.

### Pipeline data input paths

``GraphicPipeline.generate()`` takes a single ``data_key`` pointing at a
Parquet object in storage. Two paths feed into this contract:

1. **StatCan path** — `POST /api/v1/admin/graphics/generate`. The
   ``data_key`` is a StatCan-origin Parquet written by the ETL /
   Workbench pipeline (Étape A).
2. **Upload path** — `POST /api/v1/admin/graphics/generate-from-data`.
   The endpoint serializes the user-supplied rows into a temporary
   Parquet under ``temp/uploads/{uuid}.parquet`` (via the injected
   ``StorageInterface.upload_bytes``) and enqueues the same
   ``graphics_generate`` job type against that key.

`GraphicPipeline` itself is unchanged — Stage 1 (`_load_data`) can't
tell which path the Parquet came from. Temp Parquet cleanup is tracked
as `DEBT-021` (24 h TTL via ``temp_upload_ttl_hours``).

## Editor (Authoring Workflow)

- Editor document type is `CanonicalDocument` in
  `frontend-public/src/components/editor/types.ts`. Schema version is tracked
  exclusively on `doc.schemaVersion` at the root; `meta.schemaVersion` is
  forbidden.
- Review-related state (workflow, workflow history, comments) lives in
  `doc.review`. Edit history remains in `doc.meta.history` with its own
  `EditHistoryEntry` type — two histories, two purposes, never merged.
- Schema migrations are declarative in `registry/guards.ts#MIGRATIONS`.
  Current version is v2; a single `v1 → v2` step moves root-level `workflow`
  into `doc.review.workflow`. See `docs/modules/editor.md` for the full shape.

## Technology Summary

| Component | Technology |
|---|---|
| Infrastructure | Docker, PostgreSQL, MinIO |
| Database | PostgreSQL |
| Storage | MinIO |
| Pipeline Engine | Polars, Parquet |

## Module Dependency Graph

```
   backend/src/
   ├── main.py
   ├── core/
   │   ├── config.py
   │   ├── database.py
   │   ├── rate_limit.py
   │   ├── storage.py
   │   ├── scheduler.py
   │   ├── exceptions.py
   │   ├── error_handler.py
   │   ├── logging.py
   │   └── security/
   │       ├── auth.py
   │       └── ip_rate_limiter.py
   ├── api/routers/
   │   ├── health.py              ← (0-1)
   │   ├── admin_graphics.py      ← (B-4: job-based generate + GET /jobs/{id})
   │   ├── admin_leads.py         ← (D-3: ESP resync with exponential backoff)
   │   ├── public_graphics.py
   │   ├── public_leads.py        ← (D-3: scoring + Slack + ESP background tasks)
   │   ├── public_download.py     ← (D-2: token exchange → presigned URL)
   │   ├── public_metr.py         ← (Theme #2: METR calculator — calculate, curve, compare)
   │   └── public_sponsorship.py  ← (D-3: tiered sponsorship inquiry)
   ├── models/
   │   ├── publication.py
   │   ├── lead.py
   │   └── download_token.py  ← (D-0c: SHA-256 token model)
   ├── repositories/
   │   ├── publication_repository.py
   │   ├── lead_repository.py
   │   └── download_token_repository.py  ← (D-2: atomic activate)
   └── services/
       ├── statcan/ (Complete: maintenance guard, HTTP client, schemas, ETL service)
       ├── graphics/ (svg_generator, backgrounds, compositor, pipeline)
       ├── crm/
       │   └── scoring.py         ← (D-3: pure sync lead scoring — ARCH-PURA-001)
       ├── notifications/
       │   └── slack.py           ← (D-3: Slack webhook alerts with dedupe)
       ├── email/
       │   ├── interface.py       ← (D-0a: EmailServiceInterface + ConsoleEmailService)
       │   └── esp_client.py      ← (D-3: Beehiiv ESP client with error classification)
       ├── metr/                  ← (Theme #2: METR calculation engine + card data)
       │   ├── engine.py          ← Pure functions: federal/provincial tax, CPP, EI, CCB, CWB, GST
       │   └── card_data.py       ← Signal card dataset generator (4 cards)
       └── security/ (D-0b: TurnstileValidator)
```
