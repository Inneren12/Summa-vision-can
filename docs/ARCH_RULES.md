# Architectural Rules

## ARCH-PURA-001: Pure Data Transformations
- **Constraint:** All data processing logic must be distinct from I/O bounds like HTTP or Databases.
- **Rationale:** Enables completely isolated unit testing for mathematical normalizations like scalar factor adjustments, avoiding flaky HTTP mocks.
- **Applies to:** `backend/src/services/**/service.py` (e.g. `normalize_dataset`), `backend/src/services/**/validators.py`
- **Required pattern:** `def transform_data(data: AbstractData) -> Model:`
- **Forbidden pattern:** `await client.get(`

## ARCH-DPEN-001: Strict Dependency Injection
- **Constraint:** Classes cannot instantiate their own heavy dependencies (e.g., HTTP clients, db connections).
- **Rationale:** Ensures mocking is cleanly configurable and classes are isolated.
- **Applies to:** `backend/src/services/**/*.py`, `backend/src/core/task_manager.py`
- **Required pattern:** `def __init__(self, client: AsyncClient):`
- **Forbidden pattern:** `self.client = httpx.AsyncClient()`

## ARCH-ERR-001: Unified Exception Hierarchy
- **Constraint:** All domain exceptions must inherit from `SummaVisionError`. No bare `raise Exception()`.
- **Rationale:** The global error handler (`error_handler.py`) only catches `SummaVisionError` subclasses. Bare exceptions bypass structured logging and return unformatted 500 errors.
- **Applies to:** All `backend/src/` modules
- **Required pattern:** `raise DataSourceError(message="...", error_code="...", context={...})`
- **Forbidden pattern:** `raise Exception("something went wrong")`
- **Enforced in:** `core/error_handler.py`, `services/statcan/client.py`, `services/cmhc/parser.py`, `services/cmhc/service.py`

## ARCH-LOG-001: Structured Logging via structlog
- **Constraint:** All WARNING and CRITICAL logs must use `structlog` bound loggers with context dictionaries. No `print()` or stdlib `logging.warning()`.
- **Rationale:** JSON-structured logs are essential for production observability. Unstructured `print()` calls are invisible to log aggregators.
- **Applies to:** All `backend/src/` modules
- **Required pattern:** `logger.warning("message", key=value, another_key=value)`
- **Forbidden pattern:** `print(...)`, `logging.warning(...)`
- **Enforced in:** `services/statcan/client.py` (retry warnings), `services/statcan/service.py` (NaN warnings), `services/cmhc/parser.py` (CRITICAL on DOM validation failure)

## ARCH-TASK-001: Async HTTP 202 for Long-Running Operations
- **Constraint:** Any HTTP endpoint performing work that takes >5 seconds must use `TaskManager` and return `HTTP 202 Accepted` with a `task_id`.
- **Rationale:** Synchronous HTTP requests to scraping/LLM endpoints will timeout. The 202 + polling pattern prevents client-side timeouts and enables progress tracking.
- **Applies to:** `backend/src/api/routers/cmhc.py`, future admin endpoints (graphics generation)
- **Required pattern:** `task_id = tm.submit_task(coro); return 202 {task_id}`
- **Forbidden pattern:** `result = await long_running_task(); return 200 result`
- **Enforced in:** `api/routers/cmhc.py` (CMHC scraping takes 10–30s)

## ARCH-SNAP-001: HTML Snapshot Before Parse
- **Constraint:** Raw HTML from external scrapers must be persisted to storage BEFORE any parsing or validation is attempted.
- **Rationale:** When CMHC changes their DOM structure, we need the original HTML to debug the parser failure. Without snapshots, the data is lost.
- **Applies to:** `services/cmhc/service.py`
- **Required pattern:** `await storage.upload_raw(html, path); parser.validate_structure(html)`
- **Forbidden pattern:** `parser.validate_structure(html); storage.upload_raw(html, path)`
- **Enforced in:** `services/cmhc/service.py` lines 132–139

## ARCH-RSEM-001: Resource Semaphore Isolation
- **Constraint:** All CPU-heavy sync operations must run under appropriate
  semaphore AND `run_in_threadpool`.
- **Rationale:** Prevents event loop blocking in async FastAPI.
- **Applies to:** All services calling Polars, Pandas, CairoSVG, Pillow.
- **Required pattern:** `async with app.state.data_sem: await run_in_threadpool(fn)`
- **Forbidden pattern:** Direct synchronous call in async endpoint.

## ARCH-PLRS-001: Polars/Pandas Boundary
- **Constraint:** New data pipeline code uses Polars only. Legacy StatCan
  code (service.py, schemas.py, client.py) uses Pandas.
- **Rationale:** Prevents Pandas/Polars chimera. One conversion point only.
- **Legacy files:** `services/statcan/service.py`, `schemas.py`, `client.py`
- **Polars files:** `services/statcan/data_fetch.py`, `services/data/workbench.py`
- **Forbidden:** `import pandas` in any Polars-path file.

## ARCH-JOBS-001: Persistent Job Orchestration
- **Constraint:** All long-running operations must be submitted as persistent
  DB-backed jobs, not executed synchronously in HTTP handlers.
- **Rationale:** Jobs survive server restarts. Status visible to operators.
- **Required pattern:** `job_repo.enqueue(type, payload) → 202 Accepted`
- **Forbidden pattern:** `await long_operation()` inside router handler.

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
