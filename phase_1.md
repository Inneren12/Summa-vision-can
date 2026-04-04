# Phase 1: Data Extraction (Sprint 1 + Architecture Patches)
Здесь собраны только те PR, которые нужно либо создать с нуля, либо обновить (с учетом того, что базовая структура FastAPI и Timezone Guard у нас уже есть).

## PR-04 (V2): Resilient StatCan HTTP Client

```
Role: Expert Python Backend Engineer.
Task: Execute PR-04 for the "Summa Vision" project.
Context (Human): A robust wrapper around `httpx.AsyncClient` that uses our Rate Limiter and Timezone Guard, now enhanced with structured logging and 503 handling.
```

<ac-block id="Ph1-PR04-AC1">
**Acceptance Criteria for PR04 (Resilient Client):**
- [ ] Create `StatCanClient` accepting `httpx.AsyncClient`, `StatCanMaintenanceGuard`, and `AsyncTokenBucket` via Dependency Injection.
- [ ] Implement exponential backoff retry logic for HTTP 429, HTTP 409, AND HTTP 503.
- [ ] CRITICAL ARCHITECTURE: Integrate the `structlog` logger from PR-00. Log a `WARNING` on every retry attempt containing the attempt number, HTTP status code, and sleep duration.
- [ ] Raise `DataSourceError` (from PR-00) on persistent failures.
- [ ] Unit Tests: Mock a 503 response sequence using `respx` and assert the logger was called with the correct attempt numbers.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/statcan/client.py`
</ac-block>

---

## PR-05 (V2): Bulletproof Pydantic Schemas

```
Role: Expert Python Backend Engineer.
Task: Execute PR-05 for the "Summa Vision" project.
Context (Human): Strict validation of incoming StatCan JSON payloads. The API sometimes sends strings instead of ints, so we must coerce them.
```

<ac-block id="Ph1-PR05-AC1">
**Acceptance Criteria for PR05 (Coercing Schemas):**
- [ ] Create Pydantic V2 models: `ChangedCubeResponse`, `CubeMetadataResponse`, `DimensionSchema`.
- [ ] Use `ConfigDict(populate_by_name=True, alias_generator=to_camel)` to map JSON to snake_case.
- [ ] CRITICAL ARCHITECTURE: Add a Pydantic `field_validator` (or `BeforeValidator`) to `scalar_factor_code` to explicitly coerce string representations (e.g., `"3"`) into integers. Raise `ValidationError` if coercion fails.
- [ ] Unit Tests: Pass a JSON fixture where `scalarFactorCode` is a string to ensure coercion works.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/statcan/schemas.py`
</ac-block>

---

## PR-06 (V2): ETL Service & NaN Validators

```
Role: Data Engineer.
Task: Execute PR-06 for the "Summa Vision" project.
Context (Human): Download CSVs and safely apply scalar factors using Pandas, handling missing data (NaNs) gracefully to prevent pipeline crashes.
```

<ac-block id="Ph1-PR06-AC1">
**Acceptance Criteria for PR06 (Safe Pandas ETL):**
- [ ] Create `StatCanETLService` with `fetch_todays_releases()` and synchronous `normalize_dataset()`.
- [ ] CRITICAL DATA ENG: Inside `normalize_dataset`, explicitly call `pd.to_numeric(df['VALUE'], errors='coerce')` BEFORE multiplying by the scalar factor. Handle cases where `scalar_factor_code` is `None` (default to 0).
- [ ] Add post-validation: Calculate the percentage of NaN values in the 'VALUE' column. Return a `DataQualityReport(total_rows, valid_rows, nan_rows, nan_percentage)` alongside the DataFrame.
- [ ] If NaN percentage > 50%, log a `WARNING` using `structlog`.
- [ ] Unit Tests: Pass a CSV string containing empty values and text like `".."`. Assert the pipeline outputs `NaN` without crashing and returns an accurate `DataQualityReport`.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/statcan/service.py`, `/backend/src/services/statcan/validators.py`
</ac-block>

---

## PR-07 (V2): Multi-Backend Storage Interface

```
Role: Expert Python Backend Engineer.
Task: Execute PR-07 for the "Summa Vision" project.
Context (Human): A storage abstraction allowing us to swap between local disk (for dev) and AWS S3 (for prod) seamlessly.
```

<ac-block id="Ph1-PR07-AC1">
**Acceptance Criteria for PR07 (Storage Abstraction):**
- [ ] Define `StorageInterface` with methods: `upload_dataframe_as_csv()`, `upload_json()`, `download_csv() -> pd.DataFrame`, `list_objects()`, `generate_presigned_url(path, ttl) -> str`.
- [ ] Implement `S3StorageManager` (using `aiobotocore`).
- [ ] Implement `LocalStorageManager` saving to `./data/local_storage/`. Its `generate_presigned_url` should just return a `file://` or local API path.
- [ ] CRITICAL ARCHITECTURE: Create a factory function `get_storage_manager()` that selects the implementation based on `BaseSettings.STORAGE_BACKEND` (`Literal["s3", "local"]`).
- [ ] Unit Tests: Test full cycle (upload -> list -> download) using `LocalStorageManager` without AWS credentials.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/storage.py`
</ac-block>

---

## PR-09 & 10 (V2): Stealth Scraper & HTML Snapshots

```
Role: Python Scraper Engineer.
Task: Execute PR-09 and PR-10 for the "Summa Vision" project.
Context (Human): Scrape CMHC portal using Playwright Stealth. We must save raw HTML snapshots before parsing so we can debug when CMHC inevitably changes their DOM structure.
```

<ac-block id="Ph1-PR09-10-AC1">
**Acceptance Criteria for CMHC Scraper with Snapshots:**
- [ ] Implement `CMHCParser` using `BeautifulSoup4`.
- [ ] CRITICAL ARCHITECTURE: Add `validate_structure(html) -> bool` to check for expected CSS selectors/tables. If False, log `CRITICAL` via `structlog` and raise `DataSourceError`. DO NOT return empty DataFrames silently.
- [ ] Implement `run_cmhc_extraction_pipeline()`. BEFORE passing HTML to the parser, upload the raw HTML string to storage using `StorageInterface` with a key like `cmhc/snapshots/{date}_{city}.html`.
- [ ] Unit Tests: Pass HTML with missing `<table>` tags, assert `validate_structure` fails and raises the error.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/cmhc/parser.py`, `/backend/src/services/cmhc/service.py`
</ac-block>

---

## PR-11 & 44: Universal Task Manager & Async HTTP 202

```
Role: System Architect.
Task: Execute PR-11 for the "Summa Vision" project.
Context (Human): CMHC scraping takes 10-30 seconds. Synchronous HTTP requests will timeout. We need a Task Manager returning HTTP 202 Accepted for polling.
```

<ac-block id="Ph1-PR11-AC1">
**Acceptance Criteria for PR11 (Async Task Engine):**
- [ ] Create `TaskManager` with an in-memory dictionary (UUID keys) to store task status.
- [ ] **[FIX]** Add a code comment `# TODO: migrate to Redis or DB-backed store for production (in-memory state is lost on server restart)`.
- [ ] Methods: `submit_task(coroutine) -> task_id`, `get_task_status(task_id) -> TaskStatus(status: PENDING|RUNNING|COMPLETED|FAILED, result_url: str | None)`.
- [ ] Create router `POST /api/v1/admin/cmhc/sync`. It MUST submit the CMHC extraction coroutine to the TaskManager and return `HTTP 202 Accepted` with `{"task_id": "..."}` instantly.
- [ ] Create router `GET /api/v1/admin/tasks/{task_id}` for clients to poll status.
- [ ] Unit Tests: Submit a mock sleep task, verify 202 response, poll status until `COMPLETED`.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/task_manager.py`, `/backend/src/api/routers/tasks.py`, `/backend/src/api/routers/cmhc.py`
</ac-block>

---

## PR-12 (V2): Persistent Job Scheduler

```
Role: Python Backend Engineer.
Task: Execute PR-12 for the "Summa Vision" project.
Context (Human): Automated daily scraping via APScheduler, backed by a database to survive server restarts.
```

<ac-block id="Ph1-PR12-AC1">
**Acceptance Criteria for PR12 (Persistent APScheduler):**
- [ ] Integrate `AsyncIOScheduler` into FastAPI startup events.
- [ ] CRITICAL ARCHITECTURE: Configure an `SQLAlchemyJobStore` using a local SQLite database (e.g., `sqlite:///jobs.sqlite`). Do not use the default memory store.
- [ ] **[FIX]** The Job Store database URL MUST be configurable via `BaseSettings.SCHEDULER_DB_URL`, separate from the main `DATABASE_URL`. When PostgreSQL is introduced in Phase 1.5, the job store should be migrated to the same PostgreSQL instance.
- [ ] Configure CRON job for `fetch_todays_releases()` at 09:00 EST. Use `replace_existing=True` to avoid duplication on reboots.
- [ ] Wrap tasks in global error handlers logging to `structlog`.
- [ ] Unit Tests: Trigger scheduler programmatically and assert the mock was called.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/scheduler.py`
</ac-block>
