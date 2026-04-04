# Architecture

## Toolchain

- **Language**: Python 3.11+ (developed on 3.14)
- **Dependency Management**: pip with `pyproject.toml`
- **Data Handling**: Pandas, Pydantic V2
- **Network**: httpx (async), playwright + playwright-stealth (CMHC scraping)
- **Cloud**: aiobotocore (S3 storage)
- **Logging**: structlog (JSON for prod, console for dev)
- **Database**: SQLAlchemy 2.0 (async) + Alembic, aiosqlite (dev), asyncpg (prod)
- **LLM**: google-genai (Gemini), cachetools (TTLCache)
- **Charting**: Plotly + Kaleido (SVG export)
- **Testing**: pytest, pytest-asyncio, respx, pytest-cov

## Module Dependency Graph

```
backend/src/
├── main.py                       ← FastAPI app entry point
├── core/
│   ├── config.py                 ← Pydantic BaseSettings (.env)
│   ├── exceptions.py             ← SummaVisionError hierarchy
│   ├── logging.py                ← structlog configuration
│   ├── error_handler.py          ← Global FastAPI exception handler
│   ├── rate_limit.py             ← AsyncTokenBucket (10 req/sec)
│   ├── storage.py                ← StorageInterface + S3/Local backends
│   ├── task_manager.py           ← Async task engine (HTTP 202)
│   ├── scheduler.py              ← APScheduler CRON integration
│   ├── prompt_loader.py          ← YAML prompt template loader
│   ├── database.py               ← AsyncSession + engine factory
│   └── security/
│       ├── ip_rate_limiter.py     ← InMemoryRateLimiter (per-IP, sliding window)
│       └── auth.py                ← AuthMiddleware (X-API-KEY for admin namespace)
├── models/
│   ├── publication.py            ← Publication SQLAlchemy model
│   ├── lead.py                   ← Lead SQLAlchemy model
│   └── llm_request.py            ← LLMRequest SQLAlchemy model
├── repositories/
│   ├── publication_repository.py ← CRUD for publications
│   ├── lead_repository.py        ← CRUD for leads + dedup
│   └── llm_request_repository.py ← Logging LLM requests
├── api/
│   └── routers/
│       ├── tasks.py              ← GET /api/v1/admin/tasks/{task_id}
│       ├── cmhc.py               ← POST /api/v1/admin/cmhc/sync (HTTP 202)
│       ├── public_graphics.py    ← GET /api/v1/public/graphics (paginated)
│       ├── public_leads.py       ← POST /api/v1/public/leads/capture (lead gate)
│       └── admin_graphics.py     ← GET /queue + POST /graphics/generate (admin)
└── services/
    ├── statcan/
    │   ├── maintenance.py        ← StatCanMaintenanceGuard
    │   ├── client.py             ← StatCanClient (httpx wrapper)
    │   ├── schemas.py            ← Pydantic V2 response models
    │   ├── service.py            ← StatCanETLService
    │   └── validators.py         ← DataQualityReport, NaN handling
    └── cmhc/
        ├── browser.py            ← Playwright stealth context
        ├── parser.py             ← CMHCParser (BeautifulSoup4)
        └── service.py            ← CMHC extraction pipeline
    └── ai/
        ├── llm_interface.py      ← LLMInterface ABC + GeminiClient
        ├── llm_cache.py          ← LLMCache (data-aware TTL)
        ├── cost_tracker.py       ← Cost calculation + budget alert
        └── schemas.py            ← ContentBrief + ChartType (LLM output)
    └── graphics/
        ├── svg_generator.py      ← generate_chart_svg (Plotly → SVG)
        ├── ai_image_client.py    ← AIImageClient (mock AI background gen)
        └── compositor.py         ← composite_image (BG + SVG → PNG)
```

## Dependency Flow

```
main.py
  ├── config.py (BaseSettings)
  ├── logging.py (setup_logging)
  ├── error_handler.py (register_exception_handlers)
  │     └── exceptions.py (SummaVisionError hierarchy)
  │     └── logging.py (structlog logger)
  ├── scheduler.py (APScheduler lifespan)
  │     ├── config.py (SCHEDULER_DB_URL, SCHEDULER_ENABLED)
  │     └── StatCanETLService.fetch_todays_releases (CRON target)
  └── routers/
        ├── tasks.py → TaskManager
        │                └── task_manager.py (in-memory dict, asyncio.create_task)
        └── cmhc.py → run_cmhc_extraction_pipeline
                         ├── TaskManager (submit_task → HTTP 202)
                         ├── StorageInterface (upload_raw → HTML snapshot)
                         ├── get_stealth_context() (Playwright)
                         └── CMHCParser (validate_structure + parse)
                               └── DataSourceError (on validation failure)

public_graphics.py → PublicationRepository.get_published_sorted()
                     ├── StorageInterface.generate_presigned_url(s3_key_lowres, ttl=3600)
                     └── InMemoryRateLimiter.is_allowed(client_ip)

public_leads.py    → POST /api/v1/public/leads/capture
                     ├── LeadRepository.find_by_email_and_asset(email, asset_id)
                     ├── LeadRepository.create(email, asset_id)
                     ├── PublicationRepository.get_by_id(asset_id)
                     ├── StorageInterface.generate_presigned_url(s3_key_hires, ttl=900)
                     └── InMemoryRateLimiter.is_allowed(client_ip)

StatCanETLService (not yet wired to router)
  ├── StatCanClient
  │     ├── MaintenanceGuard
  │     ├── AsyncTokenBucket
  │     └── DataSourceError (on retries exhausted)
  ├── schemas.py (Pydantic validation)
  └── validators.py (DataQualityReport)
```

## Module Status

| Module | Type | Purpose | Status |
|--------|------|---------|--------|
| `core/config.py` | Python | Pydantic BaseSettings (.env) | ✅ Complete |
| `core/exceptions.py` | Python | SummaVisionError hierarchy | ✅ Complete |
| `core/logging.py` | Python | structlog configuration | ✅ Complete |
| `core/error_handler.py` | Python | Global FastAPI exception handler | ✅ Complete |
| `core/rate_limit.py` | Python | AsyncTokenBucket rate limiter | ✅ Complete |
| `core/storage.py` | Python | StorageInterface + S3/Local backends | ✅ Complete |
| `core/task_manager.py` | Python | Async task engine (HTTP 202) | ✅ Complete |
| `core/database.py` | Python | SQLAlchemy async engine + session | ✅ Complete |
| `core/scheduler.py` | Python | APScheduler CRON integration | ✅ Complete |
| `models/*` | Python | SQLAlchemy ORM models | ✅ Complete |
| `repositories/*` | Python | CRUD repository layer | ✅ Complete |
| `services/statcan/*` | Python | StatCan ETL pipeline | ✅ Complete |
| `services/cmhc/*` | Python | CMHC scraping pipeline | ✅ Complete |
| `api/routers/tasks.py` | Python | Task polling endpoint | ✅ Complete |
| `api/routers/cmhc.py` | Python | CMHC sync trigger endpoint | ✅ Complete |
| `api/routers/public_graphics.py` | Python | Public gallery (paginated, rate-limited) | ✅ Complete |
| `core/security/ip_rate_limiter.py` | Python | InMemoryRateLimiter (per-IP sliding window) | ✅ Complete |
| `services/ai/llm_interface.py` | Python | LLMInterface ABC + GeminiClient | ✅ Complete |
| `services/ai/llm_cache.py` | Python | Data-aware LLM response cache (TTL 24h) | ✅ Complete |
| `services/ai/cost_tracker.py` | Python | Cost calculation + daily budget alerting | ✅ Complete |
| `services/ai/schemas.py` | Python | ContentBrief + ChartType (LLM output models) | ✅ Complete |
| `core/prompt_loader.py` | Python | YAML prompt template loader | ✅ Complete |
| `services/graphics/svg_generator.py` | Python | Plotly SVG chart generator (Visual Engine) | ✅ Complete |
| `services/graphics/ai_image_client.py` | Python | AI background image generation (mock) | ✅ Complete |
| `services/graphics/compositor.py` | Python | BG + SVG → final PNG compositor | ✅ Complete |
| `api/routers/admin_graphics.py` | Python | Admin queue + async generation endpoint | ✅ Complete |
| `core/security/auth.py` | Python | AuthMiddleware (X-API-KEY for admin namespace) | ✅ Complete |
| `api/routers/public_leads.py` | Python | Lead capture + presigned download URL | ✅ Complete |
| `api/schemas/public_leads.py` | Python | LeadCaptureRequest/Response Pydantic models | ✅ Complete |

## Build Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Start dev server
uvicorn src.main:app --reload

# Type checking
mypy src/

# Run Alembic migrations
alembic upgrade head
```

---

## Security

### AuthMiddleware (`core/security/auth.py`)

Starlette `BaseHTTPMiddleware` that protects all admin endpoints (`/api/v1/admin/*`) with `X-API-KEY` header authentication.

**Authentication flow:**
1. Extract `X-API-KEY` header from the request.
2. Compare against `ADMIN_API_KEY` environment variable (injected via constructor — ARCH-DPEN-001).
3. If valid, apply secondary rate limit (10 req/min keyed by first 8 chars of the key).

**Bypass paths (no auth required):**
- `/api/v1/public/*` — all public endpoints
- `/api/health` — liveness probe
- `/docs`, `/redoc`, `/openapi.json` — API documentation

**Error responses:**
| Condition | Status | Body |
|-----------|--------|------|
| `ADMIN_API_KEY` not configured | 503 | `{"error": "Admin API key not configured"}` |
| Missing `X-API-KEY` header | 401 | `{"error": "Missing X-API-KEY header"}` |
| Invalid API key | 401 | `{"error": "Invalid API key"}` |
| Rate limit exceeded | 429 | `{"error": "Rate limit exceeded. Max 10 requests/min for admin endpoints."}` |

**CORS:** Explicit allowed origins — `https://summa.vision`, `https://www.summa.vision`, `http://localhost:3000`.

---

## Visual Engine Pipeline
The Visual Engine (`services/graphics/`) is a three-stage pipeline:

1. **SVG Generation** (`svg_generator.py`) — DataFrame + ChartType → transparent SVG
2. **Background Generation** (`ai_image_client.py`) — prompt → gradient PNG (mock)
3. **Assembly** (`compositor.py` + `admin_graphics.py`) — BG + SVG → final PNG, uploaded to S3. Fully automated via `POST /api/v1/admin/graphics/generate`.

### Supported Chart Types

| ChartType | Plotly Trace | Notes |
|-----------|-------------|-------|
| `LINE` | `go.Scatter(mode='lines')` | Single-series line chart |
| `BAR` | `go.Bar` | Single-series bar chart |
| `SCATTER` | `go.Scatter(mode='markers')` | Scatter plot |
| `AREA` | `go.Scatter(mode='lines', fill='tozeroy')` | Filled area chart |
| `STACKED_BAR` | `go.Bar` + `barmode='stack'` | Multi-series stacked |
| `HEATMAP` | `go.Heatmap` | First col = y-labels, rest = values |
| `CANDLESTICK` | `go.Candlestick` | OHLC data (currency rates, indices) |
| `PIE` | `go.Pie` | Proportional data (e.g. CPI composition) |
| `DONUT` | `go.Pie` with `hole=0.4` | Donut variant of PIE |
| `WATERFALL` | `go.Waterfall` | Year-over-year changes (GDP, budget) |
| `TREEMAP` | `go.Treemap` | Hierarchical data (budget by ministry) |
| `BUBBLE` | `go.Scatter(mode='markers')` | Scatter with sized markers |
| `CHOROPLETH` | `go.Choropleth` | Canadian province map |

### Size Presets

| Constant | Dimensions (px) | Platform |
|----------|----------------|----------|
| `SIZE_INSTAGRAM` | 1080 × 1080 | Instagram feed |
| `SIZE_TWITTER` | 1200 × 628 | Twitter/X card |
| `SIZE_REDDIT` | 1200 × 900 | Reddit post |

### Styling (Neon Brand)

- Transparent backgrounds (`paper_bgcolor`, `plot_bgcolor`)
- No grid lines, axis lines, or zero lines
- White text (`#FFFFFF`) in Arial, 14px
- Neon colour palette: `#00FF94`, `#00D4FF`, `#FF006E`, `#FFB700`, `#7B2FFF`, `#FF4500`
- Tight margins (40px all sides)

---

## Flutter Admin Panel (`frontend/`)

Internal Web/Desktop application for the journalist to review AI-scored briefs, edit them, and trigger graphic generation.

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|--------|
| State Management | `flutter_riverpod` + `riverpod_annotation` | Reactive, compile-safe providers |
| HTTP Client | `dio` | Interceptors, timeout config, JSON handling |
| Routing | `go_router` | Declarative URL-based navigation |
| Environment | `flutter_dotenv` | `.env` file loading (API keys, URLs) |
| Code Generation | `freezed`, `json_serializable`, `build_runner` | Immutable models + JSON serialisation |

### Directory Structure

```
frontend/
├── .env                  ← Dev config (USE_MOCK=true)
├── .env.production       ← Prod config (USE_MOCK=false)
├── pubspec.yaml
├── lib/
│   ├── main.dart         ← App entry point (ProviderScope + dotenv + GoRouter)
│   ├── core/
│   │   ├── theme/
│   │   │   └── app_theme.dart    ← Dark theme, neon brand colours
│   │   ├── routing/
│   │   │   └── app_router.dart   ← GoRouter + routerProvider + AppRoutes
│   │   └── network/
│   │       ├── auth_interceptor.dart   ← X-API-KEY injection
│   │       ├── mock_interceptor.dart   ← Local JSON fixtures (1s delay)
│   │       └── dio_client.dart         ← Dio factory + Riverpod provider
│   └── features/
│       ├── queue/
│       │   ├── domain/
│       │   │   ├── content_brief.dart        ← Freezed model (PR-22)
│       │   │   ├── content_brief.freezed.dart ← Generated
│       │   │   └── content_brief.g.dart       ← Generated
│       │   ├── data/
│       │   │   └── queue_repository.dart     ← Dio + queueProvider (PR-22)
│       │   └── presentation/
│       │       └── queue_screen.dart         ← Brief cards + Approve/Reject (PR-22)
│       ├── editor/
│       │   ├── domain/
│       │   │   ├── editor_state.dart          ← ChartType enum + EditorState freezed (PR-23)
│       │   │   ├── editor_state.freezed.dart  ← Generated
│       │   │   └── editor_notifier.dart       ← EditorNotifier + editorNotifierProvider (PR-23)
│       │   └── presentation/
│       │       └── editor_screen.dart         ← Form UI with headline, bgPrompt, chart dropdown (PR-23)
│       └── graphics/
│           └── presentation/
│               └── preview_screen.dart      ← Placeholder with taskId (PR-24)
└── test/
    └── core/
        ├── theme_test.dart
        ├── routing/
        │   └── app_router_test.dart          ← 12 unit + widget tests
        └── network/
            ├── dio_client_test.dart
            └── mock_interceptor_test.dart
    └── features/
        ├── queue/
        │   ├── domain/
        │   │   └── content_brief_schema_test.dart  ← Schema drift detection (PR-22)
        │   └── presentation/
        │       └── queue_screen_test.dart          ← 11 widget tests (PR-22)
        └── editor/
            └── presentation/
                └── editor_screen_test.dart         ← 16 widget + unit tests (PR-23)
```

### Routing (`core/routing/app_router.dart`)

Declarative, URL-based navigation powered by `go_router` and injected via Riverpod.

**Route constants** (`AppRoutes`):

| Constant | Path | Screen | Param |
|----------|------|--------|-------|
| `queue` | `/queue` | `QueueScreen` | — |
| `editor` | `/editor/:briefId` | `EditorScreen` | `briefId` |
| `preview` | `/preview/:taskId` | `PreviewScreen` | `taskId` |

**`routerProvider`** — `Provider<GoRouter>` that can be overridden in tests via `routerProvider.overrideWithValue(...)`. Any widget can access the router with `ref.read(routerProvider)` without needing a `BuildContext`.

**Redirect logic** — unknown paths (not matching `/queue`, `/editor/*`, or `/preview/*`) redirect back to `/queue`.

**Placeholder screens** — `PreviewScreen` is a minimal stub that will be replaced in PR-24. `EditorScreen` was replaced in PR-23 with the full form UI.

### Queue Feature (`features/queue/`)

The Queue feature implements the journalist's brief review workflow.

**`ContentBrief`** — Freezed immutable model matching the backend `PublicationResponse` schema. Uses `@JsonKey(name: ...)` for snake_case serialisation. Fields: `id`, `headline`, `chartType`, `viralityScore`, `status`, `createdAt`.

**`QueueRepository`** — Fetches draft briefs from `GET /api/v1/admin/queue` via the shared `Dio` instance. Parses JSON array into `List<ContentBrief>`.

**Riverpod providers:**
- `queueRepositoryProvider` — `Provider<QueueRepository>` (depends on `dioProvider`)
- `queueProvider` — `FutureProvider<List<ContentBrief>>` (invalidate to re-fetch)

**`QueueScreen`** — `ConsumerWidget` with four states:
| State | UI |
|-------|----|
| Loading | `CircularProgressIndicator` |
| Error | Error icon + message + Retry button |
| Empty | "No briefs in queue" message |
| Data | `ListView` of `_BriefCard` widgets |

**Virality score colouring:**
| Score | Colour |
|-------|--------|
| > 8 | `AppTheme.neonGreen` |
| 7–8 | `AppTheme.neonYellow` |
| < 7 | `AppTheme.neonPink` |

**Schema drift detection** — `content_brief_schema_test.dart` loads `backend/schemas/publication_response.schema.json` (exported by `backend/scripts/export_schemas.py`) and verifies that `ContentBrief.toJson()` keys match the backend field names.

### Editor Feature (`features/editor/`)

The Editor feature provides the form UI where the journalist can tweak LLM suggestions before triggering graphic generation.

**`ChartType`** — Dart enum with 13 values matching the Python `ChartType` enum in `backend/src/services/ai/schemas.py`. Provides `apiValue` (wire format), `displayName` (UI label), and `fromApiValue()` (parsing from backend strings). Values: `line`, `bar`, `scatter`, `area`, `stackedBar`, `heatmap`, `candlestick`, `pie`, `donut`, `waterfall`, `treemap`, `bubble`, `choropleth`.

**`EditorState`** — Freezed immutable model holding local form state: `briefId`, `headline`, `bgPrompt`, `chartType`, `isDirty`. Derived from `ContentBrief` but never mutates the original — all edits produce a new state via `copyWith`.

**`EditorNotifier`** — Riverpod `Notifier<EditorState?>` that manages the form. Initialises from a `ContentBrief` (idempotent), provides `updateHeadline()`, `updateBgPrompt()`, `updateChartType()`, and `reset()` methods. State starts as `null` until initialised.

**Immutability contract** — `ContentBrief` is a freezed immutable object. The `EditorNotifier` holds a mutable copy of the form state so the original brief is never touched. This separation ensures that navigating away from the editor without saving discards all edits.

**`EditorScreen`** — `ConsumerStatefulWidget` that:
| Field | Widget | Behaviour |
|-------|--------|-----------|
| Virality Score | `Text` (read-only) | Green if > 8, yellow otherwise |
| Headline | `TextFormField` (280 char max) | Pre-filled from brief |
| Background Prompt | `TextFormField` (multiline) | Starts empty |
| Chart Type | `DropdownButtonFormField<ChartType>` | All 13 types |
| Preview Background | `OutlinedButton` | Disabled stub |
| Generate Graphic | `ElevatedButton` | Navigates to `/preview/:briefId` |
| Reset | `TextButton` (app bar) | Visible only when `isDirty == true` |

### MockInterceptor Toggle

Set `USE_MOCK=true` in `.env` to intercept all Dio requests with local fixtures (no backend needed). The interceptor adds a 1-second `Future.delayed` to simulate network latency — this ensures loading states are visible during development.

| Endpoint | Mock Status | Mock Data |
|----------|------------|----------|
| `GET /admin/queue` | 200 | 3 draft publications |
| `POST /admin/graphics/generate` | 202 | task_id + message |
| `GET /admin/tasks/{id}` | 200 | COMPLETED + result_url |

### CORS Note

The backend CORS allows `http://localhost:3000`. The Flutter web dev server defaults to a random port — use `flutter run -d chrome --web-port=3000` if CORS issues arise.

---

## Next.js Public Site (`frontend-public/`)

Public-facing gallery and lead-capture site. Built with Next.js 16, React 19, and Tailwind CSS v4.

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|--------|
| Framework | Next.js 16 (App Router) | Server Components, ISR, file-system routing |
| Styling | Tailwind CSS v4 | Utility-first CSS with `@theme inline` brand tokens |
| Forms | `react-hook-form` + `@hookform/resolvers` | Controlled form state + validation |
| Validation | `zod` | Schema-based email validation |
| Fonts | `next/font/google` (Geist, Geist_Mono) | Self-hosted, optimised web fonts |
| Testing | Jest 30 + `@testing-library/react` | Component unit tests in jsdom |

### Directory Structure

```
frontend-public/
├── .env.local              ← Dev config (NEXT_PUBLIC_API_URL)
├── .env.production         ← Prod config
├── next.config.ts          ← Remote image patterns, env passthrough
├── jest.config.ts           ← next/jest + jsdom
├── jest.setup.ts            ← @testing-library/jest-dom
├── src/
│   ├── app/
│   │   ├── globals.css      ← CSS variables + Tailwind @theme inline
│   │   ├── layout.tsx       ← Root Server Component (metadata, fonts)
│   │   └── page.tsx         ← Home page (Server Component)
│   ├── lib/
│   │   ├── api.ts           ← fetch wrappers (fetchPublishedGraphics, captureLeadForDownload)
│   │   └── schemas.ts       ← Zod email schema
│   └── components/
│       ├── gallery/
│       │   └── InfographicFeed.tsx  ← Server Component (ISR revalidate:3600)
│       └── forms/
│           └── DownloadModal.tsx    ← 'use client' modal (react-hook-form + zod)
└── tests/
    └── components/
        ├── layout.test.tsx
        └── DownloadModal.test.tsx
```

### Server vs Client Component Boundaries

| Component | Type | Rationale |
|-----------|------|-----------|
| `layout.tsx` | Server | Static metadata, font loading |
| `page.tsx` | Server | Renders `InfographicFeed` (data-fetching) |
| `InfographicFeed.tsx` | Server | Calls `fetchPublishedGraphics()` at build/ISR time |
| `DownloadModal.tsx` | Client (`'use client'`) | Interactive form with `useState`, `useForm` |

### ISR Configuration

`InfographicFeed` uses `{ next: { revalidate: 3600 } }` on the `fetch` call to `GET /api/v1/public/graphics`. This means the gallery is statically generated and revalidated every hour.

### API Client Pattern (`src/lib/api.ts`)

| Function | Method | Endpoint | Used By |
|----------|--------|----------|--------|
| `fetchPublishedGraphics()` | GET | `/api/v1/public/graphics` | `InfographicFeed` (Server) |
| `captureLeadForDownload()` | POST | `/api/v1/public/leads/capture` | `DownloadModal` (Client) |

The API URL is resolved from `NEXT_PUBLIC_API_URL` env var (defaults to `http://localhost:8000`).

### Lead Capture Flow

1. User clicks "Download High-Res" on an infographic card.
2. Modal opens with an email form (validated by Zod).
3. On submit, `captureLeadForDownload(email, assetId)` POSTs to the backend.
4. Backend deduplicates the lead, generates a 15-minute presigned S3 URL.
5. Modal shows a "Download Now" `<a download>` link. No `window.open()` — user clicks explicitly.

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
