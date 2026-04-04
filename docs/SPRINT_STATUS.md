# Project Status

## Phase 0: Foundation ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-00 | Structured Logging & Exception Hierarchy | ✅ | — |
| PR-00b | CI/CD Pipeline (GitHub Actions) | ✅ | — |

> [!NOTE]
> PR-00b is missing the `alembic upgrade head` step in `backend.yml`. This is intentionally deferred until Phase 1.5 (PR-39) introduces database migrations.

## Phase 1: Data Extraction ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-04 | Resilient StatCan HTTP Client (V2) | ✅ | PR-00 |
| PR-05 | Bulletproof Pydantic Schemas (V2) | ✅ | — |
| PR-06 | ETL Service & NaN Validators (V2) | ✅ | PR-04, PR-05 |
| PR-07 | Multi-Backend Storage Interface (V2) | ✅ | — |
| PR-08 | Playwright Stealth Base | ✅ | — |
| PR-09/10 | CMHC Scraper & HTML Snapshots (V2) | ✅ | PR-07, PR-08 |
| PR-11/44 | Task Manager & Async HTTP 202 | ✅ | PR-09/10 |
| PR-12 | Persistent Job Scheduler (V2) | ✅ | PR-06 |

### Phase 1 Known Deviations

- **PR-07**: `upload_json()` method replaced by more versatile `upload_raw(data, path, content_type)`.

## Phase 1.5: Persistence Layer ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-39 | Database Schema & SQLAlchemy Models | ✅ | PR-00 |
| PR-40 | Repository Layer (CRUD) | ✅ | PR-39 |
| PR-41 | Public Graphics Endpoint | ✅ | PR-40 |

> [!NOTE]
> All Phase 1.5 work is complete: PR-39 (models), PR-40 (repositories), PR-41 (public gallery API with rate limiting and presigned URLs).

## Phase 2: AI Brain & Visual Engine ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-14/47 | LLM Interface, Cache & Budget Tracker | ✅ | PR-39 |
| PR-15 | Prompt Config & Extended Schemas | ✅ | — |
| PR-16 | AI Scoring Service | ✅ | PR-14/47, PR-15 |
| PR-17 | Plotly SVG Visual Engine | ✅ | — |
| PR-17b | Extended Chart Types (13 total) | ✅ | PR-17 |
| PR-18 | Image Compositor & Backgrounds | ✅ | PR-17 |
| PR-19/20 | Async Generation Endpoint (Admin Queue) | ✅ | PR-11/44, PR-18 |

## Phase 2.5: Security Perimeter ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-42 | Auth Middleware & Namespace Isolation | ✅ | PR-00 |

## Phase 3: Flutter Command Center 🔄 IN PROGRESS

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-20/42b | Flutter Init, Theme & Auth Interceptor | ✅ | PR-42 |
| PR-46 | GoRouter Navigation Setup | ✅ | PR-20/42b |
| PR-22 | Models & Queue Screen (Refresh Flow) | ✅ | PR-46, PR-19/20 |
| PR-23 | Editor Screen UI & Form State | ✅ | PR-22 |
| PR-24/44 | Graphic Generation & Polling (Preview) | ⬜ | PR-23, PR-11/44 |

## Phase 4: Public Site & B2C Lead Capture ✅ COMPLETE

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-29 | Next.js Init & Pragmatic Client Boundaries | ✅ | — |
| PR-31 | Secure Lead API & Persistence | ✅ | PR-40, PR-07 |
| PR-33 | Next.js Gallery & Gated Content Modal | ✅ | PR-29, PR-41 |

## Phase 5: B2B Funnel & Monetization ⬜ NOT STARTED

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| PR-35 | B2B Lead Scoring Engine | ⬜ | — |
| PR-34/49 | ESP Client, Background Sync & Failsafe | ⬜ | PR-31, PR-35 |
| PR-36 | Next.js Media Kit ("Partner with Us") | ⬜ | PR-29 |
| PR-37/38 | B2B Inquiry API & Slack Notifications | ⬜ | PR-35 |

---

**Overall Progress:** Phase 0 complete, Phase 1 complete, Phase 1.5 complete, Phase 2 complete, Phase 2.5 complete, Phase 3 in progress (PR-20 done, PR-46 done, PR-22 done, PR-23 done), Phase 4 complete.

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
