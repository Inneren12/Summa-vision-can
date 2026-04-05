# Architecture

## System Overview

The current flow is:

```
   Data Sources → ETL Pipeline → Cube Catalog (search) → Data Workbench → Visual Engine → Publication
                                                                              ↓
                                                                     Human-in-the-Loop (Admin)
```

## Infrastructure Layer

Docker, PostgreSQL, MinIO (dev), health endpoints, resource semaphores (data_sem, render_sem, io_sem), persistent job manager (coming in 0-2).

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
       ├── statcan/ (maintenance, client, schemas, service, validators)
       ├── cmhc/ (browser, parser, service) — stubs
       ├── ai/ (llm_interface, scoring, cache, cost_tracker, schemas) — stubs
       └── graphics/ (svg_generator, compositor, ai_image_client) — stubs
```