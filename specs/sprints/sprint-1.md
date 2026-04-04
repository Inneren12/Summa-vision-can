# Sprint 1: Project Skeleton & StatCan Ingestion

**Status:** In Progress
**Dates:** 2026-03-12 — 2026-03-26
**Duration:** 2 weeks
**Goal:** Establish project skeleton, base StatCan API ETL data ingestion, CMHC scraping pipeline, and REST endpoints with scheduling.

**Key Deliverables:**
- FastAPI base with health check and DI config
- StatCan maintenance guard, rate limiter, HTTP client, schemas, and ETL service
- S3 storage abstraction layer
- CMHC stealth browser, DOM parser, and orchestrator service
- REST endpoints for ETL pipelines
- APScheduler integration for automated data collection

**Critical Architecture Applied:**
- ARCH-PURA-001: Data processing must be pure functions
- ARCH-DPEN-001: Strict Dependency Injection

---

## Pack A: Base Infrastructure

### PR-1: Базовая структура FastAPI и HealthCheck

**Context (Human):** Инициализация бэкенда, настройка логгера и создание минимального эндпоинта для проверки жизнеспособности сервера (важно для CI/CD и AWS ALB).

<ac-block id="S1-PR01-AC1">
**Acceptance Criteria for PR01 (FastAPI Base)**:
- [ ] Инициализировать FastAPI app с базовыми настройками CORS и Pydantic BaseSettings (для чтения .env).
- [ ] Создать эндпоинт GET /api/health, возвращающий {"status": "ok", "timestamp": <isoformat>}.
- [ ] CRITICAL ARCHITECTURE: Use Dependency Injection for settings parsing. No global state for configs.
- [ ] Unit Tests: Test /api/health using TestClient from fastapi.testclient.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/main.py`, `/backend/src/core/config.py`
- [ ] Test location: `/backend/tests/api/test_health.py`
</ac-block>

---

### PR-2: Изолированный модуль проверки таймзоны (Maintenance Guard)

**Context (Human):** StatCan API недоступен с 00:00 до 08:30 по EST. Нам нужен чистый математический модуль для проверки времени, чтобы не отправлять запросы и не ловить баны в этот период.

<ac-block id="S1-PR02-AC1">
**Acceptance Criteria for PR02 (Timezone Guard)**:
- [ ] Создать класс/функцию StatCanMaintenanceGuard с использованием встроенного модуля zoneinfo (America/Toronto).
- [ ] Реализовать метод is_maintenance_window(current_time: datetime) -> bool.
- [ ] CRITICAL ARCHITECTURE: Do not hardcode datetime.now() inside the logic; inject the time to make it 100% pure and testable.
- [ ] Unit Tests: Mock current times (e.g., 01:00 EST = True, 08:29 EST = True, 08:31 EST = False, timezone edge cases like DST transitions).
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/statcan/maintenance.py`
- [ ] Test location: `/backend/tests/services/statcan/test_maintenance.py`
</ac-block>

---

### PR-3: Изолированный модуль Rate Limiter (Token Bucket)

**Context (Human):** StatCan банит IP при >25 req/sec. Мы должны аппаратно ограничить наш пайплайн до 10 запросов в секунду (асинхронно).

<ac-block id="S1-PR03-AC1">
**Acceptance Criteria for PR03 (Async Rate Limiter)**:
- [ ] Реализовать алгоритм Token Bucket (AsyncTokenBucket) с поддержкой asyncio.sleep().
- [ ] Настроить capacity = 10, refill_rate = 10 токенов/сек.
- [ ] CRITICAL ARCHITECTURE: Must be thread-safe/async-safe using asyncio.Lock.
- [ ] Unit Tests: Use asyncio.gather with 30 simulated requests and assert the total execution time is ~3 seconds. Mock asyncio.sleep to speed up tests.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/core/rate_limit.py`
- [ ] Test location: `/backend/tests/core/test_rate_limit.py`
</ac-block>

---

## Pack B: StatCan Data Pipeline

### PR-4: Базовый HTTP-клиент StatCan (Интеграция Guard и Limiter)

**Context (Human):** Обвязка вокруг httpx.AsyncClient, которая использует Rate Limiter и Maintenance Guard перед выполнением любого запроса к StatCan.

<ac-block id="S1-PR04-AC1">
**Acceptance Criteria for PR04 (StatCan HTTP Client)**:
- [ ] Создать класс StatCanClient оборачивающий httpx.AsyncClient.
- [ ] Внедрить StatCanMaintenanceGuard (выбрасывать кастомный MaintenanceWindowError если сейчас ночь).
- [ ] Внедрить AsyncTokenBucket перед вызовом httpx.get / httpx.post.
- [ ] Реализовать обработку ошибок: retry при HTTP 429 и HTTP 409, рейз APIConnectionError при таймаутах.
- [ ] CRITICAL ARCHITECTURE: Use Dependency Injection for the HTTP Client to allow mocking in upper layers.
- [ ] Unit Tests: Use respx or httpx-mock to intercept network calls. Test 429 retries and MaintenanceError raising.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/statcan/client.py`
- [ ] Test location: `/backend/tests/services/statcan/test_client.py`
</ac-block>

---

### PR-5: Pydantic схемы для метаданных StatCan

**Context (Human):** Строгая валидация входящих данных от API StatCan, чтобы отлавливать изменения форматов на лету.

<ac-block id="S1-PR05-AC1">
**Acceptance Criteria for PR05 (StatCan Schemas)**:
- [ ] Создать схемы ChangedCubeResponse, CubeMetadataResponse, DimensionSchema.
- [ ] Обязательное поле: scalar_factor_code (для последующего умножения значений "в тысячах/миллионах").
- [ ] CRITICAL ARCHITECTURE: Use Field(alias="...") to map ugly StatCan JSON keys to clean Python snake_case variables.
- [ ] Unit Tests: Pass valid and invalid JSON fixtures (missing fields, wrong types) and assert ValidationError triggers.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/statcan/schemas.py`
- [ ] Test location: `/backend/tests/services/statcan/test_schemas.py`
</ac-block>

---

### PR-6: Логика извлечения и нормализации данных StatCan

**Context (Human):** Сервисный слой, который вызывает клиент, забирает CSV, читает метаданные и умножает сырые значения на их scalar factor.

<ac-block id="S1-PR06-AC1">
**Acceptance Criteria for PR06 (StatCan ETL Service)**:
- [ ] Создать метод fetch_todays_releases() (использует getChangedCubeList).
- [ ] Создать метод normalize_dataset() с использованием Pandas, который применяет скалярный фактор к значениям в датафрейме.
- [ ] CRITICAL ARCHITECTURE: Decouple data fetching from data processing. Service layer must yield cleaned Pandas DataFrames.
- [ ] Unit Tests: Pass a mocked raw CSV string and mocked scalar metadata, assert the Pandas DataFrame output has correctly multiplied values (e.g., 5 * 1000 = 5000).
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/statcan/service.py`
- [ ] Test location: `/backend/tests/services/statcan/test_service.py`
</ac-block>

---

## Pack C: Cloud Storage

### PR-7: Интерфейс облачного хранилища (S3 Manager)

**Context (Human):** Сохранение очищенных CSV/JSON файлов в S3, чтобы наш LLM-гейт (Спринт 2) мог их прочитать.

<ac-block id="S1-PR07-AC1">
**Acceptance Criteria for PR07 (S3 Storage)**:
- [ ] Создать класс S3StorageManager используя aiobotocore (асинхронный клиент AWS).
- [ ] Реализовать методы upload_dataframe_as_csv(df, path) и upload_json(data, path).
- [ ] CRITICAL ARCHITECTURE: Work against an abstract StorageInterface so we can easily swap S3 for local files during local development.
- [ ] Unit Tests: Use moto (specifically moto.aiobotocore) to mock S3 buckets and assert files are "uploaded" correctly.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/core/storage.py`
- [ ] Test location: `/backend/tests/core/test_storage.py`
</ac-block>

---

## Pack D: CMHC Scraping Pipeline

### PR-8: Инициализация Playwright Stealth (База для CMHC)

**Context (Human):** CMHC жестко блокирует ботов (Cloudflare). Нам нужен корректно настроенный инстанс браузера перед парсингом.

<ac-block id="S1-PR08-AC1">
**Acceptance Criteria for PR08 (Playwright Base)**:
- [ ] Настроить инициализацию async_playwright().
- [ ] Внедрить библиотеку playwright-stealth (подмена navigator.webdriver, WebGL fingerprints, User-Agent).
- [ ] Реализовать функцию get_stealth_context() -> BrowserContext.
- [ ] CRITICAL ARCHITECTURE: Context manager pattern (async with) must be strictly used to prevent zombie browser processes and memory leaks.
- [ ] Unit Tests: Run against a local dummy HTML file or httpbin.org/user-agent to assert User-Agent and webdriver flag are spoofed.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/cmhc/browser.py`
- [ ] Test location: `/backend/tests/services/cmhc/test_browser.py`
</ac-block>

---

### PR-9: Логика парсинга таблиц CMHC

**Context (Human):** Извлечение конкретных данных (аренда, вакантность) из DOM-дерева на портале CMHC.

<ac-block id="S1-PR09-AC1">
**Acceptance Criteria for PR09 (CMHC DOM Parser)**:
- [ ] Создать класс CMHCParser, принимающий HTML (строку).
- [ ] Использовать BeautifulSoup4 для извлечения данных из нужных таблиц (table -> tr -> td).
- [ ] Возвращать структурированный Pydantic объект или Pandas DataFrame.
- [ ] CRITICAL ARCHITECTURE: Parser must be completely decoupled from the Browser/Network logic. It strictly takes HTML string in, Data out.
- [ ] Unit Tests: Feed static HTML fixture files containing real CMHC historical table layouts. Assert the output DataFrame matches expected row/column counts.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/cmhc/parser.py`
- [ ] Test location: `/backend/tests/services/cmhc/test_parser.py`
</ac-block>

---

### PR-10: CMHC Оркестратор (Stealth + Parser + S3)

**Context (Human):** Сведение компонентов PR-07, PR-08 и PR-09 в единый сервис сбора жилищных данных.

<ac-block id="S1-PR10-AC1">
**Acceptance Criteria for PR10 (CMHC Service)**:
- [ ] Реализовать метод run_cmhc_extraction_pipeline().
- [ ] Открыть stealth browser -> загрузить страницу -> дождаться рендера JS таблиц -> передать HTML в парсер -> загрузить DataFrame в S3StorageManager.
- [ ] Реализовать логику экспоненциальной задержки (exponential backoff) при обнаружении Cloudflare капчи.
- [ ] CRITICAL ARCHITECTURE: Service layer acts as a Facade. No low-level HTML parsing or socket operations here.
- [ ] Unit Tests: Mock get_stealth_context, CMHCParser, and S3StorageManager. Assert they are called in the correct sequence.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/services/cmhc/service.py`
- [ ] Test location: `/backend/tests/services/cmhc/test_service.py`
</ac-block>

---

## Pack E: API & Automation

### PR-11: FastAPI REST Endpoints для конвейера

**Context (Human):** Создание API-ручек, через которые будущая админка (или внешний планировщик) будет запрашивать данные и запускать сбор.

<ac-block id="S1-PR11-AC1">
**Acceptance Criteria for PR11 (ETL Endpoints)**:
- [ ] Создать роутеры GET /api/v1/statcan/releases и POST /api/v1/cmhc/sync.
- [ ] Интегрировать сервисные слои (StatCan Service и CMHC Service) в эндпоинты через FastAPI Depends.
- [ ] Обеспечить возврат Pydantic-схем с метаданными.
- [ ] CRITICAL ARCHITECTURE: HTTP controllers must only handle Request/Response mapping. No business logic in routing files.
- [ ] Unit Tests: Mock the service layer, call endpoints using TestClient, assert HTTP 200 and JSON structure.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/api/routers/statcan.py`, `/backend/src/api/routers/cmhc.py`
- [ ] Test location: `/backend/tests/api/test_routers.py`
</ac-block>

---

### PR-12: Настройка планировщика фоновых задач (APScheduler)

**Context (Human):** Автоматизация пайплайна без участия человека: сервер должен сам ходить за данными по CRON-расписанию.

<ac-block id="S1-PR12-AC1">
**Acceptance Criteria for PR12 (Task Scheduler)**:
- [ ] Интегрировать APScheduler (AsyncIOScheduler) в жизненный цикл FastAPI (startup/shutdown events).
- [ ] Настроить CRON-job для fetch_todays_releases() каждый будний день в 09:00 EST (сразу после окна обслуживания).
- [ ] CRITICAL ARCHITECTURE: Scheduler tasks must be wrapped in error handlers that log exceptions, preventing the scheduler thread from crashing on failed jobs.
- [ ] Unit Tests: Mock the target job functions. Trigger the scheduler programmatically and assert the mocked job was called.
- [ ] Code coverage >90%
- [ ] File location: `/backend/src/core/scheduler.py`
- [ ] Test location: `/backend/tests/core/test_scheduler.py`
</ac-block>

---

## Success Metrics

- All 12 PRs merged with ✅ status
- Every module has >90% test coverage
- Full end-to-end data flow: StatCan API → ETL → S3 storage
- CMHC scraping pipeline operational with anti-bot measures
- Automated scheduling via APScheduler

## Technical Debt

- [ ] Consolidate error handling into a shared exception hierarchy
- [ ] Add structured logging (JSON format) for production observability
- [ ] Consider adding integration tests with real StatCan sandbox (if available)
- [ ] Evaluate migration from APScheduler to Celery if job complexity grows
