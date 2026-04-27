# Phase 2.5 Discovery Part B — Job Model + Backend Endpoints

**Type:** READ-ONLY discovery (2 of 3 — paired with 2.5-A router and 2.5-C Inbox SoT)
**Repo:** `Inneren12/Summa-vision-can`
**Branch:** `claude/discover-job-model-endpoints-zl1pw`
**Git remote:** `http://local_proxy@127.0.0.1:39517/git/Inneren12/Summa-vision-can` (origin, fetch+push)

---

## §1.1 Job model in Flutter

**Search:**

```
$ grep -rn 'class Job\b\|enum JobStatus\|class JobRecord\|class JobModel' frontend/lib --include='*.dart'
frontend/lib/features/jobs/domain/job.dart:7:class Job with _$Job {
```

Single hit. No `JobRecord`, `JobModel`, or frontend `JobStatus` enum.

**Verbatim — `frontend/lib/features/jobs/domain/job.dart` (header through fields):**

```dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'job.freezed.dart';
part 'job.g.dart';

@freezed
class Job with _$Job {
  const factory Job({
    required String id,
    @JsonKey(name: 'job_type') required String jobType,
    required String status,
    @JsonKey(name: 'payload_json') String? payloadJson,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'attempt_count') required int attemptCount,
    @JsonKey(name: 'max_attempts') required int maxAttempts,
    @JsonKey(name: 'created_at') required DateTime createdAt,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'finished_at') DateTime? finishedAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @JsonKey(name: 'dedupe_key') String? dedupeKey,
  }) = _Job;
```

**Field inventory (Flutter `Job`):**

| Field | Dart type | JSON key |
|---|---|---|
| `id` | `String` (required) | `id` |
| `jobType` | `String` (required) | `job_type` |
| `status` | `String` (required) | `status` |
| `payloadJson` | `String?` | `payload_json` |
| `resultJson` | `String?` | `result_json` |
| `errorCode` | `String?` | `error_code` |
| `errorMessage` | `String?` | `error_message` |
| `attemptCount` | `int` (required) | `attempt_count` |
| `maxAttempts` | `int` (required) | `max_attempts` |
| `createdAt` | `DateTime` (required) | `created_at` |
| `startedAt` | `DateTime?` | `started_at` |
| `finishedAt` | `DateTime?` | `finished_at` |
| `createdBy` | `String?` | `created_by` |
| `dedupeKey` | `String?` | `dedupe_key` |

`subject_key` (present in backend model — see §1.5) is **not** mapped on the Flutter side.

**Helper extension — `JobHelpers` (lines 28–57):**

- `isRetryable` ⇒ `status == 'failed' && attemptCount < maxAttempts`
- `isStale` ⇒ `status == 'running' && startedAt != null && now - startedAt > 10 min`
- `duration` ⇒ `finishedAt - startedAt` (nullable)
- `jobTypeDisplay` ⇒ `catalog_sync` → "Catalog Sync", `cube_fetch` → "Data Fetch", `graphics_generate` → "Chart Generation"
- `statusDisplay` ⇒ first-letter-cap

**Error info per DEBT-030 pattern:**

- `errorCode`: **YES** (`String?`, JSON key `error_code`)
- `errorMessage`: **YES** (`String?`, JSON key `error_message`)

---

## §1.2 JobStatus enum

**Search:**

```
$ grep -rn 'enum JobStatus' frontend/lib --include='*.dart'
(no output)

$ grep -rn 'enum JobStatus' backend/src
backend/src/models/job.py:30:class JobStatus(str, enum.Enum):
```

**Frontend:** No `enum JobStatus`. The `Job.status` field is a plain `String` (line 11 of `job.dart`); status values are compared as string literals throughout the UI (e.g., `jobs_stats_bar.dart` lines 23–26: `'queued'`, `'running'`, `'success'`, `'failed'`; `job.dart:30`: `'failed'`; `job.dart:33`: `'running'`).

**Backend — verbatim `backend/src/models/job.py:30-37`:**

```python
class JobStatus(str, enum.Enum):
    """Lifecycle status of a job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Match:**

- Backend canonical set: `{QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED}` — matches the memory item exactly.
- Frontend literals observed in source: `queued`, `running`, `success`, `failed`. **`cancelled` is never referenced in Flutter** (no UI code path handles a cancelled status; `jobs_stats_bar.dart` only counts the four states above).
- The Flutter enum is implicit (string-typed), so there is no compile-time guarantee that the frontend stays in sync with backend `JobStatus`.

---

## §1.3 JobRepository / providers / filters

**Search:**

```
$ grep -rn 'class.*JobRepository\|class.*JobsNotifier\|jobsProvider\|jobRepositoryProvider' frontend/lib --include='*.dart'
(no output)
```

The literal patterns above produce no match — the frontend uses different names. The repository is `JobDashboardRepository`, providers are `jobDashboardRepositoryProvider`, `jobsListProvider`, `jobFilterProvider`, `autoRefreshProvider`. There is **no Notifier class** (no `JobsNotifier` / `StateNotifier` / `AsyncNotifier`).

**Repository — `frontend/lib/features/jobs/data/job_dashboard_repository.dart`:**

```dart
class JobDashboardRepository {
  final Dio _dio;
  JobDashboardRepository(this._dio);

  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  });

  Future<Job> getJob(String jobId);

  Future<String> retryJob(String jobId);  // returns new job_id
}

final jobDashboardRepositoryProvider = Provider<JobDashboardRepository>(
  (ref) => JobDashboardRepository(ref.watch(dioProvider)),
);
```

Public methods: **3** — `listJobs({jobType, status, limit})`, `getJob(jobId)`, `retryJob(jobId)`. No `cancelJob`, no `enqueueJob`.

**Providers — `frontend/lib/features/jobs/application/jobs_providers.dart`:**

```dart
final jobFilterProvider = StateProvider<JobFilter>((ref) => const JobFilter());

final jobsListProvider =
    FutureProvider.autoDispose<JobListResponse>((ref) async {
  final filter = ref.watch(jobFilterProvider);
  final repo = ref.read(jobDashboardRepositoryProvider);
  return repo.listJobs(
    jobType: filter.jobType,
    status: filter.status,
    limit: filter.limit,
  );
});

final autoRefreshProvider = Provider.autoDispose<void>((ref) {
  final timer = Timer.periodic(const Duration(seconds: 10), (_) {
    ref.invalidate(jobsListProvider);
  });
  ref.onDispose(timer.cancel);
});
```

**Notifier mutations:** none — there is no `Notifier` / `StateNotifier`. Mutations route through `ref.invalidate(jobsListProvider)` after `repo.retryJob(...)` calls (see `jobs_dashboard_screen.dart:45-53`).

**Filter shape — `frontend/lib/features/jobs/domain/job_filter.dart`:**

```dart
@freezed
class JobFilter with _$JobFilter {
  const factory JobFilter({
    String? jobType,
    String? status,
    @Default(50) int limit,
  }) = _JobFilter;
}
```

**List response — `frontend/lib/features/jobs/domain/job_list_response.dart`:**

```dart
@freezed
class JobListResponse with _$JobListResponse {
  const factory JobListResponse({
    required List<Job> items,
    required int total,
  }) = _JobListResponse;
}
```

**Filter location:** **server-side** for the primary cut. `JobFilter.{jobType, status, limit}` becomes `query_parameters` on `GET /api/v1/admin/jobs` inside `listJobs()` (lines 18–25 of repository). The dashboard widgets do a small amount of **client-side aggregation only** for the stats bar (`jobs_stats_bar.dart:23-27` counts `queued/running/success/failed/stale` over the already-fetched page), but no client-side filtering of which rows display.

---

## §1.4 Backend job endpoints

**Search:**

```
$ grep -rn 'router\..*\(jobs\|exceptions\|failures\|retry\|cancel\)' backend/app/api/
(no output — backend lives in backend/src, not backend/app)

$ find backend/src/api -name '*job*.py' -o -name '*queue*.py' -o -name '*exception*.py'
backend/src/api/routers/admin_jobs.py

$ grep -n '@router\.\(get\|post\|put\|delete\|patch\)' backend/src/api/routers/admin_jobs.py
92:@router.get(
159:@router.get(
204:@router.post(
```

Only one router file: `backend/src/api/routers/admin_jobs.py`. No exceptions/failures/queue router exists. Endpoints are mounted under `prefix="/api/v1/admin"` (line 34).

### Endpoint 1 — `GET /api/v1/admin/jobs` (line 92)

```python
@router.get(
    "/jobs",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List jobs with optional filters",
)
async def list_jobs(
    job_type: str | None = Query(default=None, description="Filter by job type"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    job_repo: JobRepository = Depends(_get_job_repo),
) -> JobListResponse:
```

- **Method/path:** `GET /api/v1/admin/jobs`
- **Query params:** `job_type` (str, optional), `status` (str, optional — aliased from `status_filter`), `limit` (int, 1..200, default 50)
- **Response shape:** `JobListResponse{ items: list[JobItemResponse], total: int }` (router-level Pydantic, lines 63–67) where `JobItemResponse` mirrors the Flutter `Job` field-for-field plus carries `id` as `str` (lines 42–60).
- **Pagination:** `limit` only — **no `offset` / no `cursor`**. Order is `created_at DESC` (`job_repository.py:190`).
- **Status validation:** invalid `status_filter` ⇒ 422 (lines 110–118); the only accepted values are the five `JobStatus` enum values.

### Endpoint 2 — `GET /api/v1/admin/jobs/{job_id}` (line 159)

```python
@router.get(
    "/jobs/{job_id}",
    response_model=JobItemResponse,
)
async def get_job(
    job_id: int,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> JobItemResponse:
```

- **Method/path:** `GET /api/v1/admin/jobs/{job_id}` (path param is `int`)
- **Response shape:** single `JobItemResponse`
- **Errors:** `404 Job not found` (lines 175–179)

### Endpoint 3 — `POST /api/v1/admin/jobs/{job_id}/retry` (line 204)

```python
@router.post(
    "/jobs/{job_id}/retry",
    response_model=RetryJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_job(
    job_id: int,
    job_repo: JobRepository = Depends(_get_job_repo),
) -> RetryJobResponse:
```

- **Method/path:** `POST /api/v1/admin/jobs/{job_id}/retry`
- **Status code:** `202 ACCEPTED`
- **Response shape:** `RetryJobResponse{ job_id: str, status: str }` (lines 70–74). Note: response carries the **same** job's id and updated status, not a new id, despite the Flutter side typing it as a "new" id (`retryJob` returns `response.data['job_id']`).
- **Errors:** `404 Job not found` (NotFoundError ⇒ 404), `409 Job is not retryable` (ConflictError ⇒ 409). Validation/state mutation lives in `JobRepository.retry_failed_job` (line 250 of repo).

### Other relevant backend endpoints

None. No `cancel`, no `bulk-retry`, no `exceptions`, no `failures`, no `enqueue`. The only mounted router file in `backend/src/api/routers/` matching the search is `admin_jobs.py`.

### Pagination & filter summary

| Aspect | Value |
|---|---|
| Pagination scheme | `limit` only (1..200, default 50) — **no offset, no cursor** |
| Ordering | `created_at DESC` (server-fixed) |
| Filter params | `job_type` (str), `status` (str — must parse to `JobStatus`) |
| Total count | Yes — `total` field returned alongside `items` (computed by `JobRepository.count_jobs`) |

---

## §1.5 Backend job model (sanity check)

**File:** `backend/src/models/job.py` (single hit from `find backend/src/domain` returns nothing — domain dir does not exist; canonical path is `backend/src/models/`).

**Status enum (verbatim, lines 30–37):** `QUEUED="queued"`, `RUNNING="running"`, `SUCCESS="success"`, `FAILED="failed"`, `CANCELLED="cancelled"` — **matches the memory item exactly**.

**Field inventory (`Job` ORM, `__tablename__ = "jobs"`):**

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | `int` PK | no | autoincrement | |
| `job_type` | `String(50)` | no | — | indexed |
| `status` | `Enum(JobStatus)` | no | `QUEUED` (`"queued"`) | |
| `payload_json` | `Text` | no | — | typed payload, see `job_payloads.py` |
| `result_json` | `Text` | yes | — | |
| `error_code` | `String(100)` | yes | — | **present** — DEBT-030 pattern |
| `error_message` | `Text` | yes | — | **present** |
| `attempt_count` | `Integer` | no | `0` | |
| `max_attempts` | `Integer` | no | `3` | |
| `created_at` | `DateTime(tz)` | no | `now(utc)` | |
| `started_at` | `DateTime(tz)` | yes | — | timestamp for stale detection |
| `finished_at` | `DateTime(tz)` | yes | — | terminal timestamp |
| `created_by` | `String(100)` | yes | — | operator/system id |
| `dedupe_key` | `String(255)` | yes | — | indexed; partial unique index `ix_jobs_dedupe_active` per docstring |
| `subject_key` | `String(255)` | yes | — | indexed — **NOT mapped in Flutter** |

**Indices (line 65–68):** `ix_jobs_type_status (job_type, status)`, `ix_jobs_created_at (created_at)`.

**Stale detection timestamps:** **YES** — `started_at` + `finished_at` are present; the zombie reaper `JobRepository.requeue_stale_running` (lines 202–234) uses `started_at < now - 10min AND status == RUNNING AND attempt_count < max_attempts` to requeue stuck jobs. The Flutter `Job.isStale` mirrors the same threshold (`> 10 min`).

**Relationship to Publication or other entities:** **None.** The `Job` model has no `ForeignKey` and no `relationship(...)`. Jobs are loosely coupled to other entities only through the opaque `payload_json` blob and the optional `dedupe_key` / `subject_key` strings.

---

## §1.6 Existing retry / cancel actions

**Search:**

```
$ grep -rn 'retryJob\|cancelJob\|jobRetry\|jobCancel' frontend/lib backend/src
frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart:45:  Future<void> _retryJob(Job job) async {
frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart:48:      final newJobId = await repo.retryJob(job.id);
frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart:245:                      onRetry: () => _retryJob(job),
frontend/lib/features/jobs/data/job_dashboard_repository.dart:34:  Future<String> retryJob(String jobId) async {
```

**Retry — frontend:** **YES.** `JobDashboardRepository.retryJob(jobId)` ⇒ `POST /api/v1/admin/jobs/{job_id}/retry`. UI integration: `jobs_dashboard_screen.dart:45-53` shows a snackbar then `ref.invalidate(jobsListProvider)`; the retry button is wired via `onRetry: () => _retryJob(job)` on each `JobCard` (line 245).

**Retry — backend:** **YES.** `POST /api/v1/admin/jobs/{job_id}/retry` (router line 204) ⇒ `JobRepository.retry_failed_job` (repo line 250). Returns 202 + `RetryJobResponse{ job_id, status }`; raises 404 / 409.

**Cancel — frontend:** **NO.** `cancelJob` / `jobCancel` produce zero hits. `'cancelled'` literal is also never referenced in `frontend/lib`.

**Cancel — backend:** **NO endpoint exists.** No `POST /jobs/{id}/cancel`, no `cancel` keyword in `admin_jobs.py` or `job_repository.py`. The `JobStatus.CANCELLED` value is defined in the enum but **no code path writes it** — confirmed by:

```
$ grep -rn 'cancel' backend/src/api/routers/admin_jobs.py backend/src/repositories/job_repository.py
(no output)
```

`JobStatus.CANCELLED` is a dead value at the API surface today.

---

## §3 Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:39517/git/Inneren12/Summa-vision-can
DOC PATH: docs/discovery/phase-2-5-B-model.md

§1.1 Job model: frontend/lib/features/jobs/domain/job.dart
  Has errorCode field: yes (String?, JsonKey 'error_code')
  Has errorMessage field: yes (String?, JsonKey 'error_message')

§1.2 JobStatus values:
  Frontend enum: NOT FOUND — status is a plain String; literals used in UI: queued, running, success, failed (cancelled never referenced)
  Backend enum: QUEUED='queued', RUNNING='running', SUCCESS='success', FAILED='failed', CANCELLED='cancelled'
  Match: partial — backend has CANCELLED, frontend has no UI path for it; no compile-time sync (string-typed on Flutter side)

§1.3 Job providers: frontend/lib/features/jobs/application/jobs_providers.dart (+ data/job_dashboard_repository.dart)
  Repository methods: 3 — listJobs({jobType, status, limit}), getJob(jobId), retryJob(jobId) — class is JobDashboardRepository (not JobRepository)
  Notifier mutations: 0 — no Notifier; mutations done via ref.invalidate(jobsListProvider) after repo call
  Filter location: server-side (jobType/status/limit ⇒ query params); client-side ONLY for stats-bar aggregation

§1.4 Backend endpoints (prefix /api/v1/admin):
  GET  /api/v1/admin/jobs:               yes — JobListResponse{items, total}
  GET  /api/v1/admin/jobs/{job_id}:      yes — JobItemResponse (job_id is int)
  POST /api/v1/admin/jobs/{job_id}/retry: yes — 202, RetryJobResponse{job_id, status}; 404/409
  POST /.../jobs/{id}/cancel:            NO
  Other relevant: none (no exceptions/failures/queue/bulk routers exist)
  Pagination: limit only (1..200, default 50) — NO offset, NO cursor; total count returned
  Filter params: job_type, status (validated against JobStatus enum, 422 on bad value)

§1.5 Backend Job model: backend/src/models/job.py
  Status enum: QUEUED, RUNNING, SUCCESS, FAILED, CANCELLED
  Has error_code: yes (String(100), nullable) — also error_message (Text, nullable)
  Has timestamps for stale detection: yes (started_at + finished_at; 10-min reaper in repo)
  Extra: subject_key field exists in backend but is NOT mapped in Flutter Job model
  Publication/FK relationship: NONE — Job is standalone (only loose coupling via payload_json + dedupe_key/subject_key)

§1.6 Retry/cancel actions:
  Frontend: retry yes (repo.retryJob + dashboard button) | cancel NO
  Backend:  retry yes (POST .../retry, 202) | cancel NO (CANCELLED enum value is unused at API surface)

VERDICT: COMPLETE
```

---

**End of Part B.**
