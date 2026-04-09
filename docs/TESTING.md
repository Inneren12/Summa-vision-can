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
- **Browser Mocking**: Patched Playwright context for CMHC tests
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

| Module | Minimum Coverage | Current | Tests |
|--------|-----------------|---------|-------|
| `core/exceptions.py` | >90% | ✅ 100% | `tests/core/test_exceptions.py` |
| `core/logging.py` | >90% | ✅ 100% | `tests/core/test_logging.py` |
| `core/error_handler.py` | >90% | ✅ 100% | `tests/core/test_exceptions.py` |
| `core/config.py` | >90% | ✅ 100% | (tested inline via other modules) |
| `core/rate_limit.py` | >90% | ✅ 100% | `tests/core/test_rate_limit.py` |
| `core/storage.py` | >90% | ✅ 92% | `tests/core/test_storage.py` |
| `core/task_manager.py` | >90% | ✅ 100% | `tests/core/test_task_manager.py` |
| `core/database.py` | >90% | ⚠️ 61% | (tested via repository tests) |
| `api/routers/health.py` | >90% | ✅ 100% | `tests/api/test_health.py` |
| `services/statcan/maintenance.py` | >90% | ✅ 100% | `tests/services/statcan/test_maintenance.py` |
| `services/statcan/client.py` | >90% | ✅ 100% | `tests/services/statcan/test_client.py` |
| `services/statcan/schemas.py` | >90% | ✅ 100% | `tests/services/statcan/test_schemas.py` |
| `services/statcan/service.py` | >90% | ✅ 100% | `tests/services/statcan/test_service.py` |
| `services/statcan/validators.py` | >90% | ✅ 100% | `tests/services/statcan/test_service.py` |
| `services/cmhc/browser.py` | >90% | ✅ 100% | `tests/services/cmhc/test_browser.py` |
| `services/cmhc/parser.py` | >90% | ✅ 97% | `tests/services/cmhc/test_parser.py` |
| `services/cmhc/service.py` | >90% | ✅ 100% | `tests/services/cmhc/test_service.py` |
| `api/routers/tasks.py` | >90% | ✅ 100% | `tests/api/test_routers.py` |
| `api/routers/cmhc.py` | >90% | ✅ 95% | `tests/api/test_routers.py` |
| `models/*.py` | >90% | ✅ 100% | `tests/repositories/test_*.py` |
| `repositories/*.py` | >90% | ✅ 100% | `tests/repositories/test_*.py` |
| `api/routers/admin_cubes.py` | >90% | ⬜ | |
| `api/routers/admin_data.py` | >90% | 🔄 (in progress) | `tests/api/test_admin_data.py` |
| `repositories/cube_catalog_repository.py` | >90% | ⬜ | |
| `core/scheduler.py` | >90% | ✅ 98% | `tests/core/test_scheduler.py` |
| `models/job.py` | >90% | ⬜ | |
| `repositories/job_repository.py` | >90% | ⬜ | |
| `schemas/job_payloads.py` | >90% | ⬜ | |
| `services/jobs/runner.py` | >90% | ⬜ | |
| `services/jobs/handlers.py` | >90% | ⬜ | |
| `services/jobs/dedupe.py` | >90% | ⬜ | |
| `services/statcan/catalog_sync.py` | >90% | ⬜ | |
| `services/statcan/data_fetch.py` | >90% | ⬜ | |
| services/data/workbench.py | >90% | ⬜ |
| `models/audit_event.py` | >90% | ⬜ | |
| `models/cube_catalog.py` | >90% | ⬜ | |
| `schemas/events.py` | >90% | ⬜ | |
| `services/audit.py` | >90% | ⬜ | |
| `core/security/ip_rate_limiter.py` | >90% | ✅ 100% | `tests/api/test_public_graphics.py` |
| `api/routers/public_graphics.py` | >90% | ✅ 96% | `tests/api/test_public_graphics.py` |
| `services/ai/llm_interface.py` | >90% | ✅ 100% | `tests/services/ai/test_llm_interface.py` |
| `services/ai/llm_cache.py` | >90% | ✅ 100% | `tests/services/ai/test_llm_cache.py` |
| `services/ai/cost_tracker.py` | >90% | ✅ 100% | `tests/services/ai/test_cost_tracker.py` |
| `services/ai/schemas.py` | >90% | ✅ 100% | `tests/services/ai/test_schemas.py` |
| `core/prompt_loader.py` | >90% | ✅ 100% | `tests/core/test_prompt_loader.py` |
| `services/graphics/svg_generator.py` | >90% | ⬜ | `tests/services/graphics/test_svg_generator.py` |
| `services/graphics/backgrounds.py` | >90% | ✅ | `tests/services/graphics/test_backgrounds.py` |
| `services/graphics/ai_image_client.py` | >90% | ✅ 100% | `tests/services/graphics/test_ai_image_client.py` |
| `services/graphics/compositor.py` | >90% | ✅ 86% | `tests/services/graphics/test_compositor.py` |
| `services/graphics/pipeline.py` | >90% | ✅ | `tests/services/graphics/test_pipeline.py` |
| `api/routers/admin_graphics.py` | >90% | ✅ 97% | `tests/api/test_admin_graphics.py` |
| `api/schemas/admin_graphics.py` | >90% | ✅ 100% | `tests/api/test_admin_graphics.py` |
| `core/security/auth.py` | >90% | ✅ 100% | `tests/core/security/test_auth.py` |
| `api/routers/public_leads.py` | >90% | ✅ 100% | `tests/api/test_public_leads.py` |
| `api/schemas/public_leads.py` | >90% | ✅ 100% | `tests/api/test_public_leads.py` |

**Overall:** 475+ tests, 96%+ total coverage (as of 2026-03-19).

## Mocking Strategy

| Dependency | Mock Approach |
|------------|--------------|
| External HTTP (StatCan API) | `respx` route interception |
| Time/datetime | Injected `datetime` parameter (no `datetime.now()` inside logic) |
| `asyncio.sleep` | Patched to avoid real delays in token bucket tests |
| Playwright browser | Mocked context returning static HTML |
| Service layer (in router tests) | FastAPI `Depends` override with mock objects |
| `structlog` | `unittest.mock.patch` on logger methods |
| `google-genai` (Gemini SDK) | `unittest.mock.MagicMock` on `genai.Client.models.generate_content` |
| `StorageInterface` | `LocalStorageManager` for integration tests, `unittest.mock.AsyncMock` for unit tests |
| `TaskManager` | In-memory instance with mock coroutines |
| Job repository (in runner tests) | Direct SQLite-backed AsyncSession |
| Database (AsyncSession) | In-memory `aiosqlite` via `create_async_engine("sqlite+aiosqlite://")` |
| `InMemoryRateLimiter` | Injected via `Depends` override in public graphics tests |
| `PublicationRepository` / `LeadRepository` | Direct in-memory SQLite integration tests |
| `CairoSVG` (`_svg2png`) | `unittest.mock.patch` with synthetic PNG generator (native cairo not available on Windows) |

## Known Issues

- `core/database.py` coverage at 61% — production session creation paths are not exercised in tests (uses in-memory SQLite instead)
- `pytest-asyncio` deprecation warnings for `get_event_loop_policy` on Python 3.14

## Test Fixtures

- CMHC tests use static HTML fixtures via `conftest.py` (`tests/services/cmhc/conftest.py`)
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
| **Total** | **48** | |

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
| `tests/components/DownloadModal.test.tsx` | 8 | Trigger button, modal open/close, email validation, successful download, no auto-open, server error |
| **Total** | **10** | |

### Notes
- `next/font/google` is mocked to avoid network calls — returns stub CSS variable names
- React 19 promotes `<html>` and `<body>` as singleton elements to `document.body`, so body class assertions use `document.body.className`
- Tailwind v4 `@theme inline` lint warnings in IDE are false positives — the CSS is valid at build time
- `DownloadModal` tests mock `@/lib/api` via `jest.mock()` and use `@testing-library/user-event` for realistic interactions
- Zod validation: empty email triggers `min(1)` ("Email is required"); invalid format triggers `.email()` ("Please enter a valid email address")

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
