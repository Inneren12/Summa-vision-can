# Architecture

## System Overview

The current flow is:

```
   Data Sources → ETL Pipeline → Cube Catalog (search) → Data Workbench → LLM Gate → Visual Engine → Publication
                                                                              ↓                ↓
                                                                     Human-in-the-Loop (Admin)
```
*(Note: LLM Gate is backlogged, but the module architecture remains)*

## Infrastructure Layer

- **Docker:** Dockerfile + two compose files
- **Health endpoints:** `/api/health` (liveness), `/api/health/ready` (readiness)
- **Resource semaphores:** data_sem(2), render_sem(2), io_sem(10)
- **Database:** PostgreSQL-only runtime, pool_size=8
- **Storage:** MinIO (dev) / S3 (prod)
- **Background Jobs:** persistent job manager (coming in 0-2)

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
   │   ├── admin_graphics.py
   │   ├── public_graphics.py
   │   ├── public_leads.py
   │   ├── cmhc.py
   │   └── tasks.py
   ├── models/
   │   ├── publication.py
   │   ├── lead.py
   │   └── llm_request.py
   ├── repositories/
   │   ├── publication_repository.py
   │   ├── lead_repository.py
   │   └── llm_request_repository.py
   └── services/
       ├── statcan/ (Complete: maintenance guard, HTTP client, schemas, ETL service)
       ├── cmhc/ (Stub: browser, parser, service files exist but contain no implementation)
       ├── ai/ (Stub: llm_interface, scoring, cache exist but are not connected to pipeline)
       └── graphics/ (svg_generator, backgrounds, compositor exist with basic implementation)
```
