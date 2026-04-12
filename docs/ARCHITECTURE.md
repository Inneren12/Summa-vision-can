# Architecture

## System Overview

The current flow is:

```
   Data Sources → ETL Pipeline → Cube Catalog (search) → Data Workbench → LLM Gate → Visual Engine → Publication
                                                                              ↓                ↓
                                                                     Human-in-the-Loop (Admin)
```
*(Note: LLM Gate is backlogged, but the module architecture remains)*

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
- **Track B (CMHC)**: Planned.

## Data Engine

- CubeCatalog with bilingual FTS (coming in A-1..A-4)
- DataFetchService with Polars-first pipeline (coming in A-5)
- DataWorkbench pure transforms (coming in A-6)
Note: Polars is primary engine, Pandas only in legacy StatCan code.

## Visual Engine

Plotly SVG + backgrounds + compositor.
Note template backgrounds instead of AI backgrounds for MVP.

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
   │   ├── task_manager.py
   │   ├── exceptions.py
   │   ├── error_handler.py
   │   ├── logging.py
   │   ├── prompt_loader.py
   │   └── security/
   │       ├── auth.py
   │       └── ip_rate_limiter.py
   ├── api/routers/
   │   ├── health.py          ← NEW (0-1)
   │   ├── admin_graphics.py  ← Updated (B-4: job-based generate + GET /jobs/{id})
   │   ├── public_graphics.py
   │   ├── public_leads.py    ← Updated (D-2: Turnstile + Magic Link email flow)
   │   ├── public_download.py ← NEW (D-2: token exchange → presigned URL)
   │   ├── cmhc.py
   │   └── tasks.py
   ├── models/
   │   ├── publication.py
   │   ├── lead.py
   │   ├── download_token.py  ← NEW (D-0c: SHA-256 token model)
   │   └── llm_request.py
   ├── repositories/
   │   ├── publication_repository.py
   │   ├── lead_repository.py
   │   ├── download_token_repository.py  ← NEW (D-2: atomic activate)
   │   └── llm_request_repository.py
   └── services/
       ├── statcan/ (Complete: maintenance guard, HTTP client, schemas, ETL service)
       ├── cmhc/ (Stub: browser, parser, service files exist but contain no implementation)
       ├── ai/ (Stub: llm_interface, scoring, cache exist but are not connected to pipeline)
       ├── graphics/ (svg_generator, backgrounds, compositor, pipeline exist with implementation)
       ├── email/ (D-0a: EmailServiceInterface + ConsoleEmailService)
       └── security/ (D-0b: TurnstileValidator)
```
