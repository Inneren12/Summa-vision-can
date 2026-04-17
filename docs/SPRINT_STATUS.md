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
| C-4 | Jobs Dashboard Screen | 🔄 | C-3, 0-2, 0-3 |
| C-5 | KPI Dashboard Screen | ✅ | C-3, 0-4 |

**Étape C status:** All PRs complete. ✅

**Étape C-4:** JobsDashboardScreen with filter bar (job type dropdown, status chips), summary stats bar (queued/running/success/failed/stale counts), scrollable job card list, job detail bottom sheet, retry button for retryable failed jobs, stale/zombie warning for jobs running >10 min, auto-refresh every 10s, MockInterceptor fixtures (8 sample jobs), freezed models, Riverpod providers, widget + model tests. Backend `POST /api/v1/admin/jobs/{job_id}/retry` endpoint with 404/409 handling.

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
| B-5 | JSON/CSV Upload → Graphic Generation | ✅ | B-4 |

**B-5 status:** Admin can now feed arbitrary JSON/CSV into the same
graphic pipeline without going through a StatCan cube. Backend exposes
`POST /api/v1/admin/graphics/generate-from-data` which serializes rows
to a temporary Parquet under `temp/uploads/` and enqueues the existing
`graphics_generate` job — pipeline is *unchanged*. Flutter admin adds a
"StatCan Cube / Upload Data" toggle, a `DataUploadWidget` (JSON + CSV
parsing, dtype inference), and an editable `EditableDataTable` preview.
Temp Parquet cleanup tracked as DEBT-021.

## Étape D: Lead Capture & Download

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| D-0a | EmailService Interface | ✅ | — |
| D-0b | TurnstileValidator | ✅ | — |
| D-0c | DownloadToken Model | ✅ | Étape 0 |
| D-1 | Public Gallery + Individual Page | ✅ | B-4 |
| D-2 | Lead Capture + Secure Download | ✅ | D-0a, D-0b, D-0c |
| D-3 | B2B Scoring + Slack Notifications | ✅ | D-2 |
| D-4 | Partner Page — Media Kit | ✅ | D-3 |

## Étape E: Editor (Authoring Workflow)

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| E-3-1 | Stage 3 Domain Model Consolidation (`doc.review`, schema v2) | 🔄 | — |
| E-3-2 | Stage 3 Reducer Actions (workflow transitions, comments) | ⬜ | E-3-1 |
| E-3-3 | Stage 3 Review Panel UI | ⬜ | E-3-2 |
| E-3-4 | Stage 3 End-to-End Tests | ⬜ | E-3-3 |

**E-3-1 status:** Data-layer only. `CanonicalDocument` now carries a `review`
section (workflow + workflow history + comments); root-level `workflow` is
moved under `review.workflow`; `schemaVersion` bumped 1 → 2 with a single
`v1 → v2` migration in `registry/guards.ts`. Renamed legacy `HistoryEntry`
(edit log) to `EditHistoryEntry` so the name is free for the new
`WorkflowHistoryEntry` type. Migration coverage lands in
`src/components/editor/__tests__/migrations.test.ts`. No reducer actions or UI
changed in this PR.

## Theme #2: Marginal Tax Rate Meatgrinder

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| T2-BE | METR Calculator Backend — Engine, API, Card Data | ✅ | — |
| T2-FE | METR Interactive Calculator (Next.js) | ⬜ | T2-BE |

**T2-BE:** Pure-function METR calculation engine (federal tax, CPP/CPP2, EI, provincial tax for ON/BC/AB/QC, CCB, GST/HST Credit, CWB, OTB/BCF/ACFB/QC solidarity). Three public API endpoints: `/calculate`, `/curve`, `/compare`. Signal card data generator (4 cards: hero KPI, waterfall, provincial bars, slope). 90 tests passing. Tax year: 2025.
