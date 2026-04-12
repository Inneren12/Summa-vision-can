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
- **Applies to:** `backend/src/services/**/*.py`
- **Required pattern:** `def __init__(self, client: AsyncClient):`
- **Forbidden pattern:** `self.client = httpx.AsyncClient()`

## ARCH-ERR-001: Unified Exception Hierarchy
- **Constraint:** All domain exceptions must inherit from `SummaVisionError`. No bare `raise Exception()`.
- **Rationale:** The global error handler (`error_handler.py`) only catches `SummaVisionError` subclasses. Bare exceptions bypass structured logging and return unformatted 500 errors.
- **Applies to:** All `backend/src/` modules
- **Required pattern:** `raise DataSourceError(message="...", error_code="...", context={...})`
- **Forbidden pattern:** `raise Exception("something went wrong")`
- **Enforced in:** `core/error_handler.py`, `services/statcan/client.py`

## ARCH-LOG-001: Structured Logging via structlog
- **Constraint:** All WARNING and CRITICAL logs must use `structlog` bound loggers with context dictionaries. No `print()` or stdlib `logging.warning()`.
- **Rationale:** JSON-structured logs are essential for production observability. Unstructured `print()` calls are invisible to log aggregators.
- **Applies to:** All `backend/src/` modules
- **Required pattern:** `logger.warning("message", key=value, another_key=value)`
- **Forbidden pattern:** `print(...)`, `logging.warning(...)`
- **Enforced in:** `services/statcan/client.py` (retry warnings), `services/statcan/service.py` (NaN warnings)

## ARCH-TASK-001: Async HTTP 202 for Long-Running Operations
- **Constraint:** Any HTTP endpoint performing work that takes >5 seconds must use the persistent Job system and return `HTTP 202 Accepted` with a `job_id`.
- **Rationale:** Synchronous HTTP requests to long-running endpoints will timeout. The 202 + polling pattern prevents client-side timeouts and enables progress tracking.
- **Applies to:** `backend/src/api/routers/admin_cubes.py`, `backend/src/api/routers/admin_graphics.py`
- **Required pattern:** `job_repo.enqueue(type, payload) → 202 Accepted`
- **Forbidden pattern:** `result = await long_running_task(); return 200 result`
- **Enforced in:** `api/routers/admin_cubes.py` (catalog sync), `api/routers/admin_graphics.py` (graphics generation)

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

## ARCH-JOBS-002: Job Handler Idempotency
- **Constraint:** Job handlers MUST be safe for re-execution after
  zombie reaper requeue or retry.
- **Rationale:** Prevents data duplication and side-effect repetition.
- **Required pattern:** Check if output already exists before writing.
- **Forbidden pattern:** Unconditional write without existence check.

## ARCH-AUDT-001: Typed Event Taxonomy
- **Constraint:** Every AuditEvent must use a value from the ``EventType``
  enum. Arbitrary strings are rejected at write time.
- **Rationale:** Prevents taxonomy drift (``job.failed`` vs ``job_failure``
  vs ``job-failed``) which silently breaks KPI queries.
- **Applies to:** All code calling ``AuditWriter.log_event()``.
- **Required pattern:** ``await writer.log_event(EventType.JOB_FAILED, ...)``
- **Forbidden pattern:** ``await writer.log_event("job_error", ...)``

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
