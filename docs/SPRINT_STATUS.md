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

**Étape A complete.** Data Engine: catalog search + Polars fetch +
workbench transforms + preview API.

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
