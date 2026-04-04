# Module: Core Infrastructure

**Package:** `backend.src.core`
**Purpose:** Shared infrastructure components used by all service modules — configuration, logging, exceptions, rate limiting, storage, task management, and database access.

## Package Structure

```
core/
├── __init__.py
├── config.py          ← Pydantic BaseSettings (.env reader)
├── exceptions.py      ← SummaVisionError hierarchy
├── logging.py         ← structlog configuration (JSON/console)
├── error_handler.py   ← Global FastAPI exception handler
├── rate_limit.py      ← AsyncTokenBucket
├── storage.py         ← StorageInterface + S3/Local backends
├── task_manager.py    ← Async task engine (HTTP 202 pattern)
├── scheduler.py       ← APScheduler CRON integration
└── database.py        ← SQLAlchemy async engine + session factory
```

## Classes

### `Settings` (config.py)
Pydantic `BaseSettings` subclass for reading environment variables.
- Loaded via FastAPI `Depends(get_settings)` (no global state).
- Reads from `.env` file.
- Key settings: `storage_backend` (`Literal["s3", "local"]`), `database_url`, S3 config fields.

### `SummaVisionError` (exceptions.py) — ✅ Complete
Base exception with fields: `message: str`, `error_code: str`, `context: dict[str, object]`.
- **Subclasses:** `DataSourceError`, `AIServiceError`, `StorageError`, `ValidationError`, `AuthError`.
- All subclasses provide sensible defaults for `error_code`.

### `setup_logging()` / `get_logger()` (logging.py) — ✅ Complete
Configures structlog with JSON rendering (prod) or console rendering (local dev).
- `setup_logging(force_json=False)` — Call once at app startup.
- `get_logger(**bindings)` — Returns a `structlog.stdlib.BoundLogger`.

### `register_exception_handlers(app)` (error_handler.py) — ✅ Complete
Global FastAPI exception handler for `SummaVisionError`.
- Maps `error_code` to HTTP status codes (AUTH→401, VALIDATION→422, DATASOURCE/AI→502, STORAGE→500).
- Logs every exception via structlog with traceback and context.

### `AsyncTokenBucket` (rate_limit.py) — ✅ Complete
Rate limiter implementing the Token Bucket algorithm.
- `__init__(self, capacity: int = 10, refill_rate: float = 10.0)`.
- `acquire()` — Async method that waits until a token is available.
- Thread-safe/async-safe via `asyncio.Lock`.

### `StorageInterface` (storage.py) — ✅ Complete
Abstract base class defining the storage contract.
- `upload_dataframe_as_csv(df, path)` — Serialize DataFrame to CSV.
- `upload_raw(data, path, content_type)` — Persist arbitrary content (HTML snapshots, JSON, etc.).
- `download_csv(path) -> pd.DataFrame` — Download and parse CSV.
- `list_objects(prefix) -> list[str]` — List object keys by prefix.
- `generate_presigned_url(path, ttl) -> str` — Time-limited download URL.

### `S3StorageManager(StorageInterface)` (storage.py) — ✅ Complete
AWS S3 backend using `aiobotocore`. Configurable via `Settings`.

### `LocalStorageManager(StorageInterface)` (storage.py) — ✅ Complete
Filesystem backend saving to `./data/local_storage/`. Returns `file://` URIs for presigned URLs.

### `get_storage_manager(settings)` (storage.py) — ✅ Complete
Factory selecting implementation based on `settings.storage_backend`.

### `TaskManager` (task_manager.py) — ✅ Complete
In-memory async task engine for HTTP 202 pattern.
- `submit_task(coro) -> str` — Wraps coroutine in `asyncio.create_task`, returns UUID.
- `get_task_status(task_id) -> TaskStatusResponse` — Returns PENDING/RUNNING/COMPLETED/FAILED.
- `TaskStatusResponse` — Pydantic model with `task_id`, `status`, `result_url`, `detail`.
- Module-level singleton via `get_task_manager()`.

### `AsyncSession` / `get_db()` (database.py) — ✅ Complete
SQLAlchemy 2.0 async engine and session factory.
- `get_db()` — FastAPI dependency yielding `AsyncSession`.
- Supports both `aiosqlite` (dev) and `asyncpg` (prod).

### Scheduler (scheduler.py) — ✅ Complete
Persistent job scheduler backed by APScheduler with SQLAlchemy job store.
- **`_create_scheduler(settings)`** — Factory that builds an `AsyncIOScheduler` with `SQLAlchemyJobStore` from `settings.scheduler_db_url`.
- **`start_scheduler(settings=None)`** — Creates, configures, and starts the scheduler. Registers `fetch_todays_releases()` CRON at 09:00 EST Mon–Fri with `replace_existing=True`. Skips start if `settings.scheduler_enabled` is `False`.
- **`shutdown_scheduler()`** — Gracefully stops the scheduler; resilient to closed event loops.
- **`get_scheduler()`** — Returns the module-level singleton (or `None`).
- **`scheduled_fetch_todays_releases()`** — Async wrapper executed by APScheduler. Lazy-imports `StatCanETLService` and runs `fetch_todays_releases()`. All exceptions are caught and logged via structlog.
- Config: `SCHEDULER_DB_URL` (default: `sqlite:///data/jobs.sqlite`), `SCHEDULER_ENABLED` (default: `True`).

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `asyncio` | `services/statcan/client.py` |
| `pydantic-settings` | `main.py` |
| `structlog` | All modules |
| `aiobotocore` | `services/cmhc/service.py` |
| `sqlalchemy` + `alembic` | `repositories/*.py` |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
