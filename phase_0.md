# Phase 0: The Absolute Foundation (Pack 0)
Отправляй эти два PR самыми первыми. На них будет строиться всё остальное.

## PR-00: Structured Logging & Exception Hierarchy

```
Role: Expert Python Backend Engineer.
Task: Execute PR-00 for the "Summa Vision" project.
Context (Human): Before any business logic, we must establish a unified exception hierarchy and structured JSON logging. Without this, debugging in production is impossible.
```

<ac-block id="Ph0-PR00-AC1">
**Acceptance Criteria for PR00 (Logging & Exceptions):**
- [ ] Install `structlog`. Configure JSON formatting for production and human-readable formatting for local development.
- [ ] Create base exception `class SummaVisionError(Exception)` with fields: `message: str`, `error_code: str`, `context: dict`.
- [ ] Create inherited exceptions: `DataSourceError`, `AIServiceError`, `StorageError`, `ValidationError`, `AuthError`.
- [ ] Create a global FastAPI `exception_handler` that catches `SummaVisionError` and returns standardized JSON: `{"error_code": "...", "message": "...", "detail": {...}}`.
- [ ] CRITICAL ARCHITECTURE: Every exception MUST be logged via `structlog` with context (timestamp, service_name, traceback) inside the exception handler.
- [ ] Unit Tests: Throw a custom exception via `TestClient`, assert the JSON response matches the standard, and assert the logger was called.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/exceptions.py`, `/backend/src/core/logging.py`, `/backend/src/core/error_handler.py`
- [ ] Test location: `/backend/tests/core/test_exceptions.py`, `/backend/tests/core/test_logging.py`
</ac-block>

Output: Provide the complete, production-ready code.

---

## PR-00b: CI/CD Pipeline (GitHub Actions)

```
Role: DevOps Engineer.
Task: Execute PR-00b for the "Summa Vision" project.
Context (Human): Implement automated testing pipelines to prevent regressions on every push.
```

<ac-block id="Ph0-PR00b-AC1">
**Acceptance Criteria for PR00b (CI/CD):**
- [ ] Create `.github/workflows/backend.yml`: run `pytest --cov` on every push/PR to the `backend/` directory.
- [ ] Create `.github/workflows/frontend-admin.yml`: run `flutter test` on every push to `frontend/`.
- [ ] Create `.github/workflows/frontend-public.yml`: run `npm test` on every push to `frontend-public/`.
- [ ] Add dependency caching (pip cache, pub cache, node_modules cache) to speed up runs.
- [ ] **[FIX]** Add `alembic upgrade head` step in the backend workflow BEFORE running pytest. After Phase 1.5 (PR-39), tests will depend on database migrations being applied.
- [ ] CRITICAL ARCHITECTURE: Configure fail-on-coverage for the backend. If coverage drops below 85%, the pipeline MUST fail.
- [ ] File location: `/.github/workflows/backend.yml`, `/.github/workflows/frontend-admin.yml`, `/.github/workflows/frontend-public.yml`
</ac-block>

Output: Provide the exact YAML files. No Python code is needed.
