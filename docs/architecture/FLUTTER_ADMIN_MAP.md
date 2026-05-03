# Flutter Admin App — Architecture Map

**Status:** Living document — update on every Flutter admin impl PR
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Source:** Phase 2.5 discovery Parts A + B
**Related architecture:**
- `BACKEND_API_INVENTORY.md` §1 (job endpoints consumed by Flutter)
- `TEST_INFRASTRUCTURE.md` §3 (Flutter testing patterns)

**Maintenance rule:** any PR that adds/modifies a Flutter admin route, screen, provider, or Job model field requires update to this file in the same commit. Drift signal: if memory items reference Flutter routes, providers, or JobStatus values not listed here, this file is stale.

## How to use this file

- Pre-recon and recon prompts SHOULD read this file FIRST when scope touches the Flutter admin app.
- Sections track: routes, screens, Job/JobStatus model, repositories and providers, retry/cancel actions, i18n status.
- For backend job endpoints consumed by these screens, see BACKEND_API_INVENTORY.md §1.
- For testing patterns (especially `tester.runAsync`, Hive lifecycle), see TEST_INFRASTRUCTURE.md §3.

## 1. Router

**Definition file:** `frontend/lib/core/routing/app_router.dart` (128 lines; Riverpod-provided `GoRouter`)

### All routes

| Path | Screen widget | File | Notes |
|---|---|---|---|
| / | NOT FOUND | n/a | No explicit route; unknown-path redirect → `/queue` (initial location) |
| /queue | `QueueScreen()` | `frontend/lib/features/queue/presentation/queue_screen.dart` | `app_router.dart:62-66`; initial location |
| /jobs | `JobsDashboardScreen()` | `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart` | `app_router.dart:105-109` |
| /exceptions | NOT FOUND | n/a | No route, no screen, no `exceptions/` directory |
| /cubes/search | `CubeSearchScreen()` | (cube search screen) | `app_router.dart:67-71` |
| /cubes/:productId | `CubeDetailScreen(productId: …)` | (cube detail screen) | `app_router.dart:72-79` |
| /data/preview | `DataPreviewScreen(storageKey: query['key'])` | (data preview screen) | `app_router.dart:80-87` |
| /graphics/config | `ChartConfigScreen(storageKey, productId)` | (chart config screen) | `app_router.dart:88-99` |
| /kpi | `KPIScreen()` | (KPI screen) | `app_router.dart:100-104` |
| /editor/:briefId | `EditorScreen(briefId: …)` | (editor screen) | `app_router.dart:110-117` |
| /preview/:taskId | `PreviewScreen(taskId: …)` | (preview screen) | `app_router.dart:118-125` |
| /semantic-mappings | `SemanticMappingsListScreen()` | `frontend/lib/features/semantic_mappings/screens/semantic_mappings_list_screen.dart` | Phase 3.1b |
| /semantic-mappings/new | `SemanticMappingFormScreen(mappingId: null)` | `frontend/lib/features/semantic_mappings/screens/semantic_mapping_form_screen.dart` | Phase 3.1b |
| /semantic-mappings/:id | `SemanticMappingFormScreen(mappingId: int)` | same | Phase 3.1b |

### Phase 3.1b additions

* Drawer tile: `Icons.dataset_linked` → `loc.navSemanticMappings` (`/semantic-mappings`).
* Repository: `SemanticMappingsRepository` (`frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart`) wraps `Dio` with the four admin endpoints + the cube-metadata read endpoint.
* Riverpod providers (`providers/semantic_mappings_providers.dart`):
  * `semanticMappingsRepositoryProvider` (Provider)
  * `semanticMappingsFilterProvider` (StateProvider for filters)
  * `semanticMappingsListProvider` (FutureProvider.autoDispose)
  * `semanticMappingProvider(id)` (FutureProvider.autoDispose.family)
  * `cubeMetadataProvider(cubeId)` (FutureProvider.autoDispose.family)
* Widgets: `DimensionFiltersEditor` (key/value editor — see DEBT-055 for missing reorder UX) and `VersionConflictModal` (412 reload prompt).
* Backend error envelope helper: `frontend/lib/core/network/backend_error_envelope.dart` parses both nested (`{detail: {error_code, ...}}`) and flat envelopes for inline form rendering.
* `frontend/lib/l10n/backend_errors.dart` now maps the seven semantic-mapping codes (5 from 3.1ab + 2 new in 3.1b: `VERSION_CONFLICT`, `BULK_VALIDATION_FAILED`). DEBT-056 tracks a comprehensive sweep of the rest.


Total routes: `9` (flat — no `StatefulShellRoute`, no `ShellRoute`, no nested `routes:` children).

Route constants live in `AppRoutes` (`app_router.dart:15-27`).

### Route guards / redirects
(From A.1.1, `app_router.dart:39-60`)
- Bare `/cubes` rewrites to `AppRoutes.cubeSearch` (`/cubes/search`).
- Any unknown path that does not start with one of the known prefixes (`/queue`, `/editor/`, `/preview/`, `/cubes/`, `/data/`, `/graphics/`, `/kpi`, `/jobs`) and is not `/queue` falls back to `AppRoutes.queue`.
- No auth guard.
- `/exceptions` is NOT in the known-prefix list — any link to it would be redirected to `/queue`.

### Tab structures
(From A.1.3)
- `/jobs` has tabs: **no** (filter row uses `DropdownButtonFormField` + `ChoiceChip`s instead of `TabBar`).
- `/queue` has tabs: **no**.
- Other routes with tab structures: **none** (no `TabBar`, `TabBarView`, `TabController`, `StatefulShellRoute`, or `ShellRoute` anywhere in `frontend/lib/features/jobs/` or `frontend/lib/features/queue/`).

## 2. Job/queue/exception screens

(From A.1.2)

### JobsDashboardScreen
- **File:** `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart`
- **Widget class:** `JobsDashboardScreen` (`ConsumerStatefulWidget`, with `_JobsDashboardScreenState extends ConsumerState`)
- **Providers watched:** `3` (`autoRefreshProvider`, `jobFilterProvider`, `jobsListProvider` — lines 70, 72, 73). Plus `ref.read` ×4 (`jobDashboardRepositoryProvider` line 47; `jobFilterProvider.notifier` lines 97, 137, 165).
- **List/table widget:** `ListView.separated` (line 236), rendering `JobCard` rows; no `DataTable`.
- **Action surfaces:** AppBar refresh `IconButton` (lines 80–85, hard-coded English tooltip `'Refresh jobs'`); no FAB; no bottom action bar. Drawer (`AppDrawer`), `JobsStatsBar` (status counts → tap-to-filter), filter row (job-type `DropdownButtonFormField` + status `ChoiceChip`s with literal English maps `_jobTypes` / `_statuses`), `'No jobs found…'` empty state, error state with retry button.

### QueueScreen
- **File:** `frontend/lib/features/queue/presentation/queue_screen.dart`
- **Widget class:** `QueueScreen` (`ConsumerWidget` — plain stateless consumer)
- **Providers watched:** `1` (`queueProvider` line 18). Plus 2 invalidations of `queueProvider` (lines 28, 65).
- **List/table widget:** `ListView.separated` (line 55), rendering `_BriefCard` rows; no `DataTable`.
- **Action surfaces:** AppBar refresh `IconButton` (lines 25–30, l10n tooltip `l10n.queueRefreshTooltip`); no FAB; no bottom action bar. Drawer (`AppDrawer`), `_EmptyQueueView`, error state with retry button, `_BriefCard` with virality badge / chart-type chip / Approve & Reject buttons.

### Exceptions screen
- **NONE FOUND.** No `exceptions/` directory under `frontend/lib/features/`, no `*exception*.dart` file, no `/exceptions` route, no `exception.*` ARB keys. Adding an exceptions surface would be a greenfield feature, not a refactor.

### Sister screens (related but not job-specific)
(From A.1.2 "Other relevant")
- `frontend/lib/features/jobs/presentation/widgets/job_detail_sheet.dart` — detail bottom-sheet helper (`showJobDetailSheet`).
- `frontend/lib/features/jobs/presentation/widgets/jobs_stats_bar.dart` — status-count chips above the jobs list.
- `frontend/lib/features/jobs/presentation/widgets/job_card.dart` — single job row card with retry / view-detail.
- `frontend/lib/features/kpi/presentation/widgets/job_failure_chart.dart` — KPI tile (not a screen).
- `frontend/lib/features/graphics/domain/job_status.dart` (+ generated `.freezed.dart` / `.g.dart`) — chart-generation task status; lives in `graphics/`, distinct from the `jobs/` feature.

## 3. Job model (Flutter side)

**File:** `frontend/lib/features/jobs/domain/job.dart`

### Class definition
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

### Key fields
| Field | Type | Purpose |
|---|---|---|
| `id` | `String` (required, JSON `id`) | Job identifier (server returns `int`, deserialized to string on Flutter side). |
| `jobType` | `String` (required, JSON `job_type`) | Discriminator: `catalog_sync`, `cube_fetch`, `graphics_generate`. |
| `status` | `String` (required) | Lifecycle state — plain `String`, no enum (see §3 JobStatus). |
| `payloadJson` | `String?` (JSON `payload_json`) | Opaque per-type payload blob. |
| `resultJson` | `String?` (JSON `result_json`) | Opaque per-type result blob (success only). |
| `errorCode` | `String?` (JSON `error_code`) | DEBT-030 envelope mapping — backend stable error code. |
| `errorMessage` | `String?` (JSON `error_message`) | DEBT-030 envelope mapping — human-readable error detail. |
| `attemptCount` | `int` (required, JSON `attempt_count`) | Drives `isRetryable` together with `maxAttempts`. |
| `maxAttempts` | `int` (required, JSON `max_attempts`) | Retry ceiling. |
| `createdAt` | `DateTime` (required, JSON `created_at`) | Server-assigned creation timestamp. |
| `startedAt` | `DateTime?` (JSON `started_at`) | Drives `isStale` (>10 min while `running`). |
| `finishedAt` | `DateTime?` (JSON `finished_at`) | Terminal-state timestamp. |
| `createdBy` | `String?` (JSON `created_by`) | Operator/system id. |
| `dedupeKey` | `String?` (JSON `dedupe_key`) | Idempotency key (partial unique index server-side). |

`subject_key` (present in backend ORM) is **NOT** mapped on the Flutter side.

### JobStatus enum
**File:** Frontend: none — `Job.status` is a plain `String`. Backend: `backend/src/models/job.py:30-37`.
**Frontend values:** `queued`, `running`, `success`, `failed` (string literals in `jobs_stats_bar.dart` and `JobHelpers`; `cancelled` is never referenced anywhere in `frontend/lib`).
**Backend values:** `QUEUED="queued"`, `RUNNING="running"`, `SUCCESS="success"`, `FAILED="failed"`, `CANCELLED="cancelled"`.
**Match:** partial — backend exposes `CANCELLED` but no Flutter UI path handles it; because `Job.status` is string-typed there is no compile-time guarantee that the frontend stays in sync with backend `JobStatus`.

### freezed copyWith caveat (memory)
For nullable error fields on terminal state transitions (failed/timeout), use fresh constructor not `copyWith`. Pattern `field ?? this.field` preserves old value when new is null. Slice 3.8 lesson: `CHART_EMPTY_DF` leaked from first failure to second where backend omitted code. Always add stale-field regression test for terminal transitions.

## 4. Job repositories and providers

### JobRepository
**File:** `frontend/lib/features/jobs/data/job_dashboard_repository.dart` (actual class is `JobDashboardRepository` — no `JobRepository` exists in `frontend/lib`).

Public methods (signatures only):
- `listJobs({String? jobType, String? status, int limit = 50}) → Future<JobListResponse>` — `GET /api/v1/admin/jobs` with filters as query params.
- `getJob(String jobId) → Future<Job>` — `GET /api/v1/admin/jobs/{job_id}`.
- `retryJob(String jobId) → Future<String>` — `POST /api/v1/admin/jobs/{job_id}/retry`; returns `response.data['job_id']`.

No `cancelJob`, no `enqueueJob`.

### JobsNotifier (or equivalent)
**File:** none — there is no `JobsNotifier`, `StateNotifier`, or `AsyncNotifier` in `frontend/lib/features/jobs/`.

Public mutations: `0`
- Mutations route through `ref.invalidate(jobsListProvider)` after `repo.retryJob(...)` calls (`jobs_dashboard_screen.dart:45-53`).

### Provider definitions
**File:** `frontend/lib/features/jobs/application/jobs_providers.dart` (plus `jobDashboardRepositoryProvider` defined in the repository file).

| Provider | Type | Watches | Notes |
|---|---|---|---|
| `jobFilterProvider` | `StateProvider<JobFilter>` | — | Filter shape: `{ jobType?, status?, limit=50 }` (`job_filter.dart`). |
| `jobsListProvider` | `FutureProvider.autoDispose<JobListResponse>` | `jobFilterProvider` | Reads `jobDashboardRepositoryProvider`; calls `repo.listJobs(...)` with filter values. |
| `autoRefreshProvider` | `Provider.autoDispose<void>` | — | 10-second `Timer.periodic` that invalidates `jobsListProvider`; `ref.onDispose(timer.cancel)`. |
| `jobDashboardRepositoryProvider` | `Provider<JobDashboardRepository>` | `dioProvider` | Defined in `job_dashboard_repository.dart`. |

### Filter location
Filters applied: **server-side** for the primary cut — `JobFilter.{jobType, status, limit}` becomes `query_parameters` on `GET /api/v1/admin/jobs`. Client-side aggregation is used **only** by `jobs_stats_bar.dart:23-27` (counts `queued/running/success/failed/stale` over the already-fetched page); no client-side filtering of which rows display.

### State sync pattern (memory)
Notifier `_poll` (or equivalent state-sync method) MUST copy ALL response fields to state. Slice 3.8 lesson: mapper tested + widget tests with synthetic state passed; notifier `_poll` never copied `errorCode` from response → 285+ tests green, dead plumbing caught only post-merge. For any new response field, integration test (mocked HTTP → notifier → state → UI) required, not just unit + widget tests.

## 5. Retry / cancel actions

### Frontend
(From B.1.6)
- Retry action exists: **yes**
- Cancel action exists: **no**
- Implementation file(s): `frontend/lib/features/jobs/data/job_dashboard_repository.dart:34` (`retryJob`), `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart:45-53` (`_retryJob` UI handler), `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart:245` (`onRetry` wiring on each `JobCard`). For cancel: none.

### Backend endpoints
(From B.1.4 — see also BACKEND_API_INVENTORY.md §1)
- `POST .../jobs/{id}/retry`: **yes** — `backend/src/api/routers/admin_jobs.py:204`, returns `202 ACCEPTED` with `RetryJobResponse{job_id, status}`; raises `404` (not found) / `409` (not retryable).
- `POST .../jobs/{id}/cancel`: **no** — endpoint does not exist; `JobStatus.CANCELLED` is defined in the enum but no code path writes it.
- Other relevant: `GET /api/v1/admin/jobs` (list), `GET /api/v1/admin/jobs/{job_id}` (detail). No `bulk-retry`, no `exceptions`, no `failures`, no `enqueue`.

### Bulk actions
Phase 4.1 / 4.2 (roadmap) plan bulk retry with jitter and Shift-click range select. Not yet implemented as of inputs date.

## 6. i18n status

### Source files
- ARB files location: `frontend/lib/l10n/app_en.arb` (additional locale ARBs colocated in `frontend/lib/l10n/`).
- Generated localization files: not captured in 2.5-A discovery (path follows the project's `l10n.yaml`; consult `flutter gen-l10n` output directory).

### Existing job/queue/exception keys
(From A.1.4)

| Namespace | Key count | Status |
|---|---|---|
| `job.*` | 0 | TBD — jobs dashboard uses hard-coded English literals throughout (`'Jobs Dashboard'`, `'Refresh jobs'`, `'All Types'`, `'Catalog Sync'`, `'Queued'`, `'Running'`, `'No jobs found…'`, etc.). |
| `queue.*` | 6 | complete — `queueTitle`, `queueRefreshTooltip`, `queueLoadError`, `queueEmptyState`, `queueRejectVerb`, `queueApproveVerb`. |
| `exception.*` | 0 | TBD — no exceptions namespace, no exceptions screen exists. |
| `errorJob*` | 0 | TBD — DEBT-030 backend error codes have no l10n keys yet. |

### Existing screens use AppLocalizations
(From A.1.4)
- All job/queue screens wired to `AppLocalizations.of(context)`: **mixed** — `queue_screen.dart` is fully wired (10 `l10n.` callsites against 6 ARB keys); `jobs_dashboard_screen.dart` and the `jobs/presentation/widgets/*` files have **no** `AppLocalizations` references and rely on hard-coded English.

### CRITICAL test rule (memory P3-004)
Tests for any localized widget MUST include `localizationsDelegates: AppLocalizations.localizationsDelegates` and `supportedLocales: AppLocalizations.supportedLocales` in MaterialApp setup, AND assert via `final l10n = AppLocalizations.of(context)!` against generated keys, NOT against hardcoded EN strings. Production code must NOT use `AppLocalizations.of(context)?.X ?? 'EN fallback'` — that pattern lets tests pass against fallback while localization is silently broken.

## 7. Flutter test runner conventions

### `flutter test` invocation
- CI runs: default — no `--concurrency=1` flag
- Concurrency: multi-isolate on CI (typically 2-4 parallel on 2-CPU GitHub runner)

### Critical patterns (memory — Phase 1.5 saga)
- **`tester.runAsync` is mandatory** for `dart:io` and Hive operations inside `testWidgets` body. The fake-async zone blocks completers from real I/O. Symptom of violation: TimeoutException after 0:10:00.000000 with stack trace `dart:isolate _RawReceivePort._handleMessage` only (no package frame).
- **`tester.runAsync` cannot be nested.** If a provider body does I/O (e.g. Hive `box.put`), wrapping `container.read(provider.future)` in `tester.runAsync` gives "Reentrant call to runAsync() denied". Solution: override the provider in tests with synchronous body.
- **Hive setup pattern:** wrap `Hive.init` + `Hive.openBox` in `tester.runAsync`. Teardown also wrapped. Always call `Hive.close()` before `box.deleteFromDisk()`. Memory P3-006 proposes a `openTempHiveBox` helper.
- **Diagnostic-first rule:** when 2 fix rounds fail to converge on the same test symptom, STOP guessing — round 3+ must be diagnostic-only (breadcrumb prints at every async checkpoint). Speculative structural changes without data waste cycles.

(For full details see TEST_INFRASTRUCTURE.md §3.)

## 8. Maintenance log

| Date | PR | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from Phase 2.5 discovery Parts A + B |
