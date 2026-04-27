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

---

**End of Part 1. Sections 3-8 added by Part 2.**
