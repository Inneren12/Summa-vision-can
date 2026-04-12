# Project Status

## Étape 0: Infrastructure Foundation

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| 0-1 | Docker + Compose + Health + MinIO | 🔄 Fixing | — |
| 0-2 | Job Model + Typed Payloads + Repository | 🔄 | 0-1 |
| 0-3 | Job Runner + Dedupe + Retry | ✅ | 0-2 |
| 0-4 | AuditEvent Foundation | 🔄 | 0-2 |
| 0-5 | Backup + Alerting Baseline | 🔄 | 0-1 |

**Étape 0 status:** All PRs merged. Backup script operational.
Infrastructure foundation: Docker, persistent jobs,
audit events, backup, monitoring. Production hardening items tracked in DEBT.md.

## Étape A: Data Engine

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| A-1 | CubeCatalog Model + Bilingual FTS | 🔄 | Étape 0 |
| A-2 | CubeCatalogRepository | 🔄 | A-1 |
| A-3 | CatalogSyncService | 🔄 | A-2 |
| A-4 | Cube Search API | 🔄 | A-2, A-3 |
| A-5 | DataFetchService (Polars-first) | 🔄 | A-1, A-4 |
| A-6 | DataWorkbench (Pure Polars) | 🔄 | — |
| A-7 | Transform API | 🔄 | A-5, A-6 |

**Étape A: all PRs merged.** Production hardening ongoing. Data Engine: catalog search + Polars fetch + workbench transforms + preview API.

## Previously Completed

### Sprint 1: StatCan ETL Pipeline ✅
| PR | Title | Status |
|----|-------|--------|
| PR-1 | FastAPI Base + HealthCheck | ✅ |
| PR-2 | Maintenance Guard (Timezone) | ✅ |
| PR-3 | Rate Limiter (Token Bucket) | ✅ |
| PR-4 | StatCan HTTP Client | ✅ |
| PR-5 | Pydantic Schemas | ✅ |
| PR-6 | ETL Service + NaN Handling | ✅ |

### Phase 1.5: Persistence Layer ✅
| PR | Title | Status |
|----|-------|--------|
| PR-39 | Database Schema & Models | ✅ |
| PR-40 | Repository Layer | ✅ |
| PR-41 | Public Gallery API | ✅ |

### Phase 2.5: Security ✅
| PR | Title | Status |
|----|-------|--------|
| PR-42 | Auth Middleware | ✅ |

### Foundation Fixes ✅
| PR | Title | Status |
|----|-------|--------|
| FIX-01..08 | Foundation repairs | ✅ |
| 0-1 | Docker + Compose + Health + MinIO | ✅ |

## Étape C: Admin Panel (Flutter)

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| C-1 | Cube Search Screen | 🔄 | A-4, PR-20, PR-46 |
| C-2 | Data Preview | 🔄 | C-1, A-5 |
| C-3 | Chart Config + Generation Screen | 🔄 | C-2, B-4 |
| C-5 | KPI Dashboard Screen | ✅ | C-3, 0-4 |

**Étape C status:** All PRs complete. ✅

**Étape C-1:** CubeSearchScreen with debounced search, CubeSearchTile, CubeDetailScreen stub, MockInterceptor fixtures, AppDrawer navigation, GoRouter routes, freezed models, Riverpod providers, widget + model tests.

**Étape C-3:** ChartConfigScreen with chart type / size preset / background category selectors, title field with validation, async generation flow (submit → poll → result), inline image preview with download button, MockInterceptor polling simulation, widget + model tests. Wires C-2 "Generate Chart" button to /graphics/config route.

**Étape C-5:** KPI Dashboard — backend `GET /api/v1/admin/kpi?days=30` aggregation endpoint (KPIService, KPIResponse schema). Flutter KPIScreen with period selector (7/30/90 days), summary cards (publications, leads, downloads, job success), download funnel visualization, lead breakdown by category, job failure chart, system health row, auto-refresh every 60s. MockInterceptor fixture, freezed model, Riverpod providers, widget + model tests.

## Étape B: Visual Engine

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| B-1 | SVG Generator → Real Data | 🔄 | A-5, A-6 |
| B-2 | Template Backgrounds | 🔄 | — |
| B-3 | End-to-End Pipeline | 🔄 | B-1, B-2 |
| B-4 | Admin Graphics API + Batch CLI | ⬜ | B-3 |

## Étape D: Lead Capture & Download

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| D-0a | EmailService Interface | ✅ | — |
| D-0b | TurnstileValidator | ✅ | — |
| D-0c | DownloadToken Model | ✅ | Étape 0 |
| D-1 | Public Gallery + Individual Page | ✅ | B-4 |
| D-2 | Lead Capture + Secure Download | ✅ | D-0a, D-0b, D-0c |
| D-3 | B2B Scoring + Slack Notifications | ⬜ | D-2 |
