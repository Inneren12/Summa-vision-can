# Testing Strategy

## Operational Scripts

- `scripts/ops/backup_db.sh` — tested manually, not in CI.
  Verification: `aws s3 ls s3://${BACKUP_S3_BUCKET}/backups/$(date +%Y-%m-%d)/`

## Docker Test Strategy
- Two-level: SQLite unit + PostgreSQL integration
- Markers: `@pytest.mark.integration`, `@pytest.mark.slow`
- CI Gate Policy applies to these tests.
- Health endpoint test coverage requirements included.
- New test file: `tests/api/test_health.py`

## Test Framework
- **Runner**: `pytest` with `pytest-asyncio`
- **Async Mode**: `auto` (all async tests discovered automatically)
- **HTTP Mocking**: `respx` for stubbing `httpx` network calls
- **Coverage**: `pytest-cov` with `--cov-fail-under=85` enforced in CI

## Test Naming Convention

```
test_<module>_<scenario>_<expected_result>
```

Example: `test_maintenance_guard_during_window_returns_true`

## How to Run Tests

```bash
# All tests
pytest

# Specific module
pytest tests/services/statcan/
pytest tests/core/

# With coverage
pytest --cov=src --cov-report=term-missing

# Single file
pytest tests/services/statcan/test_maintenance.py -v
```

## Coverage Thresholds

> Last measured: 2026-04-12 — 701 tests passed, 3 failed (plotly/kaleido choropleth), 13 skipped (integration), 90% total coverage.

| Module | Minimum | Current | Tests |
|--------|---------|---------|-------|
| `core/exceptions.py` | >90% | ✅ 100% | `tests/core/test_exceptions.py` |
| `core/logging.py` | >90% | ✅ 100% | `tests/core/test_logging.py` |
| `core/error_handler.py` | >90% | ✅ 100% | `tests/core/test_exceptions.py` |
| `core/config.py` | >90% | ✅ 93% | (tested inline via other modules) |
| `core/rate_limit.py` | >90% | ✅ 100% | `tests/core/test_rate_limit.py` |
| `core/storage.py` | >90% | ✅ 92% | `tests/core/test_storage.py` |
| `core/database.py` | >90% | ⚠️ 52% | (tested via repository tests) |
| `core/scheduler.py` | >90% | ✅ 98% | `tests/core/test_scheduler.py` |
| `core/security/auth.py` | >90% | ✅ 93% | `tests/core/security/test_auth.py` |
| `core/security/ip_rate_limiter.py` | >90% | ✅ 100% | `tests/api/test_public_graphics.py` |
| `api/routers/health.py` | >90% | ✅ 100% | `tests/api/test_health.py` |
| `api/routers/admin_cubes.py` | >90% | ✅ 92% | `tests/api/test_admin_cubes.py` |
| `api/routers/admin_data.py` | >90% | ✅ 90% | `tests/api/test_admin_data.py` |
| `api/routers/admin_graphics.py` | >90% | ✅ 97% | `tests/api/test_admin_graphics.py`, `tests/api/test_admin_graphics_upload.py` |
| `api/routers/admin_jobs.py` | >90% | ✅ 100% | `tests/api/test_admin_jobs.py` |
| `api/routers/admin_kpi.py` | >90% | ✅ 100% | `tests/api/test_admin_kpi.py` |
| `api/routers/admin_leads.py` | >90% | ✅ 100% | `tests/api/test_resync.py` |
| `api/routers/public_graphics.py` | >90% | ✅ 96% | `tests/api/test_public_graphics.py` |
| `api/routers/public_leads.py` | >90% | ✅ 100% | `tests/api/test_lead_capture.py`, `tests/api/test_lead_capture_scoring.py` |
| `api/routers/public_download.py` | >90% | ✅ 100% | `tests/api/test_download.py` |
| `api/routers/public_sponsorship.py` | >90% | ✅ 100% | `tests/api/test_sponsorship.py` |
| `api/schemas/admin_graphics.py` | >90% | ✅ 100% | `tests/api/test_admin_graphics.py`, `tests/api/test_admin_graphics_upload.py` |
| `api/schemas/public_leads.py` | >90% | ✅ 100% | `tests/api/test_lead_capture.py` |
| `models/job.py` | >90% | ✅ 100% | `tests/repositories/test_job_repository.py` |
| `models/audit_event.py` | >90% | ✅ 100% | `tests/repositories/test_*.py` |
| `models/cube_catalog.py` | >90% | ✅ 100% | `tests/models/test_cube_catalog_fts.py` |
| `models/download_token.py` | >90% | ✅ 100% | `tests/repositories/test_download_token_repository.py` |
| `models/lead.py` | >90% | ✅ 100% | `tests/repositories/test_*.py` |
| `models/publication.py` | >90% | ✅ 100% | `tests/repositories/test_*.py` |
| `repositories/job_repository.py` | >90% | ⚠️ 69% | `tests/repositories/test_job_repository.py` |
| `repositories/cube_catalog_repository.py` | >90% | ⚠️ 75% | (tested via service tests) |
| `repositories/download_token_repository.py` | >90% | ✅ 98% | `tests/repositories/test_download_token_repository.py` |
| `repositories/lead_repository.py` | >90% | ✅ 87% | `tests/repositories/test_lead_repository.py` |
| `repositories/publication_repository.py` | >90% | ⚠️ 67% | `tests/repositories/test_publication_repository.py` |
| `schemas/job_payloads.py` | >90% | ✅ 100% | `tests/repositories/test_job_repository.py` |
| `schemas/events.py` | >90% | ✅ 100% | (tested inline via audit tests) |
| `schemas/kpi.py` | >90% | ✅ 100% | `tests/api/test_admin_kpi.py` |
| `services/audit.py` | >90% | ✅ 100% | (tested inline via runner/repository tests) |
| `services/jobs/runner.py` | >90% | ✅ 90% | `tests/services/jobs/test_runner.py` |
| `services/jobs/handlers.py` | >90% | ⚠️ 85% | `tests/services/jobs/test_handlers.py`, `tests/services/jobs/test_graphics_handler.py` |
| `services/jobs/dedupe.py` | >90% | ✅ 100% | `tests/services/jobs/test_runner.py` |
| `services/statcan/maintenance.py` | >90% | ✅ 100% | `tests/services/statcan/test_maintenance.py` |
| `services/statcan/client.py` | >90% | ✅ 100% | `tests/services/statcan/test_client.py` |
| `services/statcan/schemas.py` | >90% | ✅ 100% | `tests/services/statcan/test_schemas.py` |
| `services/statcan/service.py` | >90% | ✅ 100% | `tests/services/statcan/test_service.py` |
| `services/statcan/validators.py` | >90% | ✅ 100% | `tests/services/statcan/test_service.py` |
| `services/statcan/catalog_sync.py` | >90% | ✅ 90% | `tests/services/statcan/test_catalog_sync.py` |
| `services/statcan/data_fetch.py` | >90% | ⚠️ 85% | `tests/services/statcan/test_data_fetch.py` |
| `services/data/workbench.py` | >90% | ⚠️ 88% | `tests/services/data/test_workbench.py` |
| `services/graphics/svg_generator.py` | >90% | ✅ 91% | `tests/services/graphics/test_svg_generator.py` |
| `services/graphics/backgrounds.py` | >90% | ✅ 100% | `tests/services/graphics/test_backgrounds.py` |
| `services/graphics/ai_image_client.py` | >90% | ✅ 100% | `tests/services/graphics/test_ai_image_client.py` |
| `services/graphics/compositor.py` | >90% | ⚠️ 86% | `tests/services/graphics/test_compositor.py` |
| `services/graphics/pipeline.py` | >90% | ✅ 92% | `tests/services/graphics/test_pipeline.py` |
| `services/crm/scoring.py` | >90% | ✅ 100% | `tests/services/crm/test_scoring.py` |
| `services/notifications/slack.py` | >90% | ✅ 98% | `tests/services/notifications/test_slack.py` |
| `services/email/esp_client.py` | >90% | ✅ 98% | `tests/services/email/test_esp_client.py` |
| `services/email/interface.py` | >90% | ⚠️ 70% | (mocked in lead capture tests) |
| `services/security/turnstile.py` | >90% | ⚠️ 35% | (mocked in lead capture tests) |
| `services/kpi/kpi_service.py` | >90% | ✅ 100% | `tests/services/kpi/test_kpi_service.py` |
| `scripts/ops/generate_batch.py` | >90% | ✅ | `tests/scripts/ops/test_generate_batch.py` |

**Overall:** 701 passed, 3 failed, 13 skipped. 90% total coverage (3464 statements, 353 missed). Measured 2026-04-12.

## Mocking Strategy

| Dependency | Mock Approach |
|------------|--------------|
| External HTTP (StatCan API) | `respx` route interception |
| Time/datetime | Injected `datetime` parameter (no `datetime.now()` inside logic) |
| `asyncio.sleep` | Patched to avoid real delays in token bucket tests |
| Service layer (in router tests) | FastAPI `Depends` override with mock objects |
| `structlog` | `unittest.mock.patch` on logger methods |
| `StorageInterface` | `LocalStorageManager` for integration tests, `unittest.mock.AsyncMock` for unit tests |
| `SlackNotifierService` | `AsyncMock` injected via `Depends` override in lead capture + sponsorship tests |
| `ESPSubscriberInterface` (BeehiivClient) | `AsyncMock` injected via `Depends` override; error classification tested with `httpx` mock |
| `LeadScoringService` | Direct instantiation (pure sync, no mocking needed) |
| Job repository (in runner tests) | Direct SQLite-backed AsyncSession |
| Database (AsyncSession) | In-memory `aiosqlite` via `create_async_engine("sqlite+aiosqlite://")` |
| `InMemoryRateLimiter` | Injected via `Depends` override in public graphics tests |
| `PublicationRepository` / `LeadRepository` | Direct in-memory SQLite integration tests |
| `JobRepository` (in endpoint tests) | `AsyncMock` injected via `Depends` override |
| `GraphicPipeline` (in handler tests) | `unittest.mock.patch` on class, `AsyncMock` on generate method |
| `CairoSVG` (`_svg2png`) | `unittest.mock.patch` with synthetic PNG generator (native cairo not available on Windows) |

## Known Issues

- `core/database.py` coverage at 61% — production session creation paths are not exercised in tests (uses in-memory SQLite instead)
- `pytest-asyncio` deprecation warnings for `get_event_loop_policy` on Python 3.14

## Test Fixtures

- StatCan tests use inline JSON/CSV data within test functions
- Repository tests use shared `conftest.py` with async SQLite engine fixture

### FTS Integration Tests

`tests/models/test_cube_catalog_fts.py` requires PostgreSQL.
Marked with `@pytest.mark.integration`. Skipped when
`TEST_DATABASE_URL` is not set.
FTS integration tests (PostgreSQL trigram/tsvector) are in
test_cube_catalog_fts.py with @pytest.mark.integration marker.
SQLite LIKE-based search is tested in unit tests.

Run: `TEST_DATABASE_URL=postgresql+asyncpg://... pytest -m integration`

---

## Flutter Tests (`frontend/`)

### Test Framework
- **Runner**: `flutter test` (built-in test runner)
- **Widget Testing**: `flutter_test` SDK package
- **No Backend Required**: `MockInterceptor` with `enableDelay: false` for instant test execution

### How to Run

```bash
cd frontend

# All tests
flutter test

# Specific file
flutter test test/core/network/mock_interceptor_test.dart

# Verbose output
flutter test -v
```

### Test Files

| Test File | Tests | Covers |
|-----------|------:|--------|
| `test/core/theme_test.dart` | 6 | `AppTheme` brand colours, dark theme, widget smoke test |
| `test/core/network/dio_client_test.dart` | 4 | `dotenv` env var loading, Dio instantiation |
| `test/core/network/mock_interceptor_test.dart` | 5 | `MockInterceptor.isEnabled`, fixture data for all 3 endpoints |
| `test/features/queue/domain/content_brief_schema_test.dart` | 6 | Schema drift detection against backend `publication_response.schema.json` |
| `test/features/queue/presentation/queue_screen_test.dart` | 11 | Loading/data/empty/error states, virality score colours, refresh, Approve navigation |
| `test/features/editor/presentation/editor_screen_test.dart` | 16 | EditorScreen rendering, form interactions, EditorNotifier state management, ChartType parsing |
| `test/features/kpi/presentation/kpi_screen_test.dart` | 13 | KPI summary cards, conversion rate, job success rate, division-by-zero, funnel steps, lead breakdown, job failures, data contract warning, period selector, loading/error states |
| `test/features/kpi/domain/kpi_data_test.dart` | 3 | KPIData.fromJson full parsing, empty failedByType map, JSON round-trip |
| `test/features/graphics/domain/raw_data_upload_test.dart` | 6 | `RawDataColumn` / `GenerateFromDataRequest` snake_case JSON round-trip, default dtype + size |
| `test/features/graphics/presentation/data_upload_widget_test.dart` | 5 | `DataUploadWidget` pick-button rendering, `EditableDataTable` header/rows/truncation hint, inline cell edit dialog |
| **Total** | **75** | |

### Notes
- Tests use `dotenv.testLoad(mergeWith: {...})` to inject env vars without reading `.env` from disk
- `MockInterceptor` tests use a custom `_CapturingHandler` to capture resolved `Response` objects
- Widget smoke tests pump a minimal `MaterialApp` with `AppTheme.dark` — no dotenv required
- Queue widget tests override `queueProvider` with `overrideWith(...)` to inject mock data
- Editor widget tests override `queueProvider` similarly; `EditorNotifier` is tested both in-widget and as a standalone unit via `ProviderContainer`
- Schema drift test loads `../backend/schemas/publication_response.schema.json` — requires `python scripts/export_schemas.py` to have been run

---

## Public Site Tests (`frontend-public/`)

### Test Framework
- **Runner**: Jest 30 with `next/jest` transformer
- **Environment**: jsdom (`jest-environment-jsdom`)
- **Assertions**: `@testing-library/react` + `@testing-library/jest-dom`
- **Module Aliases**: `@/*` mapped to `<rootDir>/src/*`

### How to Run

```bash
cd frontend-public

# All tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

### Test Files

| Test File | Tests | Covers |
|-----------|------:|--------|
| `tests/components/layout.test.tsx` | 2 | `RootLayout` children rendering, `bg-background` body class |
| `tests/components/DownloadModal.test.tsx` | 12 | Trigger button, modal open/close, Turnstile widget, email validation, success state ("Check your email"), error states (403/429/404), no auto-open |
| `tests/app/downloading/page.test.tsx` | 5 | Missing token error, "Verify and Download" button (no auto-download), URL token clearing, download trigger, branding |
| **Total** | **19** | |

### Notes
- `next/font/google` is mocked to avoid network calls — returns stub CSS variable names
- React 19 promotes `<html>` and `<body>` as singleton elements to `document.body`, so body class assertions use `document.body.className`
- Tailwind v4 `@theme inline` lint warnings in IDE are false positives — the CSS is valid at build time
- `DownloadModal` tests mock `@/lib/api/client` via `jest.mock()` and use `@testing-library/user-event` for realistic interactions
- `TurnstileWidget` is mocked with a button that triggers `onSuccess` on click
- Zod validation: empty email triggers `min(1)` ("Email is required"); invalid format triggers `.email()` ("Please enter a valid email address")
- `/downloading` page tests verify NO auto-download on mount (R17) and that token is cleared from URL (R1)

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
