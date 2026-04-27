# Phase 2.5 Discovery Part A — Flutter Router + Screens

**Type:** READ-ONLY DISCOVERY
**Date:** 2026-04-27
**Branch:** `claude/discover-flutter-routes-nOtoJ`
**Git remote:** `origin  http://local_proxy@127.0.0.1:41253/git/Inneren12/Summa-vision-can`

---

## §1.1 Router definition

### Find command output

```
$ find frontend/lib -name '*.dart' | xargs grep -l 'GoRouter\|GoRoute' 2>/dev/null | head -5
frontend/lib/core/routing/app_drawer.dart
frontend/lib/core/routing/app_router.dart
```

**Router file:** `frontend/lib/core/routing/app_router.dart` (128 lines)
*Gloss: Riverpod-provided `GoRouter`; `app_drawer.dart` matches because it imports `GoRouter` types for navigation, not because it defines routes.*

### Route constants (`AppRoutes`, lines 15–27)

| Const                  | Path                       |
|------------------------|----------------------------|
| `queue`                | `/queue`                   |
| `editor`               | `/editor/:briefId`         |
| `preview`              | `/preview/:taskId`         |
| `cubeSearch`           | `/cubes/search`            |
| `cubeDetail`           | `/cubes/:productId`        |
| `dataPreview`          | `/data/preview`            |
| `graphicsConfig`       | `/graphics/config`         |
| `kpi`                  | `/kpi`                     |
| `jobs`                 | `/jobs`                    |

### `GoRoute` definitions verbatim (path → screen widget)

```
/queue              → QueueScreen()                                  app_router.dart:62-66
/cubes/search       → CubeSearchScreen()                             app_router.dart:67-71
/cubes/:productId   → CubeDetailScreen(productId: …)                 app_router.dart:72-79
/data/preview       → DataPreviewScreen(storageKey: query['key'])    app_router.dart:80-87
/graphics/config    → ChartConfigScreen(storageKey, productId)       app_router.dart:88-99
/kpi                → KPIScreen()                                    app_router.dart:100-104
/jobs               → JobsDashboardScreen()                          app_router.dart:105-109
/editor/:briefId    → EditorScreen(briefId: …)                       app_router.dart:110-117
/preview/:taskId    → PreviewScreen(taskId: …)                       app_router.dart:118-125
```

**Total routes:** 9. **Initial location:** `/queue`.

### Tab structures (StatefulShellRoute / nested routes)

`grep -n 'StatefulShellRoute' frontend/lib/core/routing/app_router.dart` → **none.**
No `StatefulShellRoute`, no `ShellRoute`, no nested `routes:` children. Router is flat.

### Redirects / guards (`app_router.dart:39-60`)

```dart
redirect: (context, state) {
  final knownPrefixes = [
    '/queue', '/editor/', '/preview/', '/cubes/',
    '/data/', '/graphics/', '/kpi', '/jobs',
  ];
  final path = state.matchedLocation;

  if (path == '/cubes') return AppRoutes.cubeSearch;

  final isKnown = knownPrefixes.any((p) => path.startsWith(p));
  if (!isKnown && path != AppRoutes.queue) {
    return AppRoutes.queue;
  }
  return null;
},
```

*Gloss: bare `/cubes` rewrites to `/cubes/search`; any unknown path falls back to `/queue`. No auth guard. No `/exceptions` prefix in the known list.*

---

## §1.2 Job/queue/exception screen files

### Directory find output

```
$ find frontend/lib -type d \( -name '*job*' -o -name '*queue*' -o -name '*exception*' \) 2>/dev/null
frontend/lib/features/jobs
frontend/lib/features/queue
```

*Gloss: `jobs/` and `queue/` exist; **no `exceptions/` directory.***

### File find output

```
$ find frontend/lib \( -name '*job*.dart' -o -name '*queue*.dart' -o -name '*exception*.dart' \) 2>/dev/null
frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart
frontend/lib/features/jobs/application/jobs_providers.dart
frontend/lib/features/jobs/data/job_dashboard_repository.dart
frontend/lib/features/jobs/domain/job_filter.dart
frontend/lib/features/jobs/domain/job.freezed.dart
frontend/lib/features/jobs/domain/job.g.dart
frontend/lib/features/jobs/domain/job_list_response.g.dart
frontend/lib/features/jobs/domain/job_filter.freezed.dart
frontend/lib/features/jobs/domain/job.dart
frontend/lib/features/jobs/domain/job_list_response.dart
frontend/lib/features/jobs/domain/job_list_response.freezed.dart
frontend/lib/features/queue/presentation/queue_screen.dart
frontend/lib/features/queue/data/queue_repository.dart
frontend/lib/features/graphics/domain/job_status.g.dart       # graphics-task status, not jobs feature
frontend/lib/features/graphics/domain/job_status.freezed.dart # graphics-task status, not jobs feature
frontend/lib/features/graphics/domain/job_status.dart         # graphics-task status, not jobs feature
frontend/lib/features/jobs/presentation/widgets/job_detail_sheet.dart
frontend/lib/features/jobs/presentation/widgets/jobs_stats_bar.dart
frontend/lib/features/jobs/presentation/widgets/job_card.dart
frontend/lib/features/kpi/presentation/widgets/job_failure_chart.dart        # KPI tile
```

*No `*exception*.dart` matches.*

### Per-screen detail

#### `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart`

- Top-level widget class: `JobsDashboardScreen`
- Type: `ConsumerStatefulWidget` (with `_JobsDashboardScreenState extends ConsumerState`)
- `ref.watch(...)` calls: **3** (`autoRefreshProvider`, `jobFilterProvider`, `jobsListProvider` — lines 70, 72, 73)
- `ref.read(...)` calls: **4** (`jobDashboardRepositoryProvider` line 47; `jobFilterProvider.notifier` lines 97, 137, 165)
- List widget: **`ListView.separated`** (line 236) rendering `JobCard` rows; no `DataTable`
- AppBar actions: refresh `IconButton` (line 80–85) — *hard-coded English tooltip `'Refresh jobs'`*
- FAB / bottom bar: **none**
- Other UI: drawer (`AppDrawer`), `JobsStatsBar` (status counts → tap-to-filter), filter row with job-type `DropdownButtonFormField` + status `ChoiceChip`s (literal English maps `_jobTypes`/`_statuses`), `'No jobs found…'` empty state, error state with retry button

#### `frontend/lib/features/queue/presentation/queue_screen.dart`

- Top-level widget class: `QueueScreen`
- Type: `ConsumerWidget` (plain stateless consumer)
- `ref.watch(...)` calls: **1** (`queueProvider` line 18)
- `ref.read/.invalidate` calls: 2 invalidations of `queueProvider` (lines 28, 65)
- List widget: **`ListView.separated`** (line 55) rendering `_BriefCard` rows; no `DataTable`
- AppBar actions: refresh `IconButton` (line 25–30) — *l10n-wired tooltip `l10n.queueRefreshTooltip`*
- FAB / bottom bar: **none**
- Other UI: drawer (`AppDrawer`), `_EmptyQueueView`, error state with retry button, `_BriefCard` with virality badge / chart-type chip / Approve & Reject buttons

#### Other relevant

- `frontend/lib/features/jobs/presentation/widgets/job_detail_sheet.dart` — detail bottom-sheet helper (`showJobDetailSheet`)
- `frontend/lib/features/jobs/presentation/widgets/jobs_stats_bar.dart` — status-count chips above the list
- `frontend/lib/features/jobs/presentation/widgets/job_card.dart` — single job row card with retry / view-detail
- `frontend/lib/features/kpi/presentation/widgets/job_failure_chart.dart` — KPI tile, not a screen
- `frontend/lib/features/graphics/domain/job_status.dart` (+ generated) — chart-generation task status; **lives in `graphics/`, distinct from the `jobs/` feature**

**No exceptions screen, exceptions widget, or exceptions feature directory exists.**

---

## §1.3 Sub-tabs and overlays

### Grep output

```
$ grep -nE 'TabBar|TabBarView|StatefulShellRoute' frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart
(no matches)

$ grep -rnE 'TabBar|TabBarView' frontend/lib/features/jobs/
(no matches)

$ grep -rnE 'TabBar|TabBarView' frontend/lib/features/queue/
(no matches)
```

- `/jobs` already has a tab structure: **no.**
- Existing tabs today: **none.**
- `/queue` already has a tab structure: **no.**
- *Gloss: filtering on `/jobs` is done with a `DropdownButtonFormField` + `ChoiceChip` row, not with `TabBar`. Adding tabs would be a structural change, not a refactor of an existing `TabController`.*

---

## §1.4 i18n status of existing job/queue screens

### Find of files calling `AppLocalizations.of` / `l10n.`

```
$ find frontend/lib -name '*.dart' \( -path '*job*' -o -path '*queue*' \) -exec grep -l 'AppLocalizations\.of\|l10n\.' {} \;
frontend/lib/features/queue/presentation/queue_screen.dart
```

*Only one match: queue is l10n-wired, jobs is not.*

### `l10n.` usages by feature

```
features/queue/presentation/queue_screen.dart:
  16: final l10n = AppLocalizations.of(context)!;
  23:   title: Text(l10n.queueTitle),
  27:   tooltip: l10n.queueRefreshTooltip,
  41:   l10n.queueLoadError(err.toString()),
  48:   child: Text(l10n.commonRetryVerb),
  79: final l10n = AppLocalizations.of(context)!;
  83:   l10n.queueEmptyState,
  104: final l10n = AppLocalizations.of(context)!;
  183:  child: Text(l10n.queueRejectVerb),
  188:  child: Text(l10n.queueApproveVerb),

features/jobs/**:
  (no l10n. or AppLocalizations.of references)
```

### ARB keys under `job.*` / `queue.*` / `exception.*`

```
$ grep -nE '"(job|queue|jobs|exception)[A-Za-z]*"' frontend/lib/l10n/app_en.arb
47:  "queueTitle": "Brief Queue",
51:  "queueRefreshTooltip": "Refresh queue",
55:  "queueLoadError": "Failed to load queue\n{error}",
65:  "queueEmptyState": "No briefs in queue.\nTap refresh to fetch new ones.",
69:  "queueRejectVerb": "Reject",
73:  "queueApproveVerb": "Approve",
```

| Namespace        | Key count |
|------------------|-----------|
| `queue*`         | 6         |
| `job*` / `jobs*` | 0         |
| `exception*`     | 0         |

*Gloss: jobs dashboard uses **hard-coded English literals** throughout (`'Jobs Dashboard'`, `'Refresh jobs'`, `'All Types'`, `'Catalog Sync'`, `'Queued'`, `'Running'`, `'No jobs found…'`, `'Job retried (new job: $newJobId)'`, `'Retry failed: …'`, `'Job is not retryable'`, `'Failed to load jobs'`, `'Retry'`). Queue screen is fully wired to `AppLocalizations` against 6 ARB keys. No exception namespace exists.*

---

## Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:41253/git/Inneren12/Summa-vision-can
DOC PATH: docs/discovery/phase-2-5-A-router.md

§1.1 Router: frontend/lib/core/routing/app_router.dart:34
  Total routes: 9 (flat — no StatefulShellRoute / ShellRoute / nesting)
  Routes verbatim:
    /queue              → QueueScreen          (initialLocation)
    /jobs               → JobsDashboardScreen
    /exceptions         → NOT FOUND
    /cubes/search       → CubeSearchScreen
    /cubes/:productId   → CubeDetailScreen
    /data/preview       → DataPreviewScreen
    /graphics/config    → ChartConfigScreen
    /kpi                → KPIScreen
    /editor/:briefId    → EditorScreen
    /preview/:taskId    → PreviewScreen
  Redirects: bare '/cubes'→/cubes/search; any unknown path→/queue. No auth guard.

§1.2 Screen files:
  jobs:        frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart
    widget class: JobsDashboardScreen (ConsumerStatefulWidget)
    list type: ListView.separated (JobCard rows)
    ref.watch×3, ref.read×4 (filter notifier + repo)
    AppBar: refresh IconButton (hard-coded EN); FAB: none
  queue:       frontend/lib/features/queue/presentation/queue_screen.dart
    widget class: QueueScreen (ConsumerWidget)
    list type: ListView.separated (_BriefCard rows)
    ref.watch×1; AppBar: refresh IconButton (l10n); FAB: none
  exceptions:  NOT FOUND (no dir, no file, no route)
  other relevant: jobs/presentation/widgets/{job_card,job_detail_sheet,jobs_stats_bar}.dart;
                  graphics/domain/job_status.dart (chart task status, not jobs feature);
                  kpi/presentation/widgets/job_failure_chart.dart (KPI tile)

§1.3 Sub-tab structure on /jobs: no
  Existing tabs: none (no TabBar/TabBarView/TabController anywhere in jobs/ or queue/)
  Filtering on /jobs is done with DropdownButtonFormField + ChoiceChip row.

§1.4 i18n:
  Existing job/queue screens use AppLocalizations: mixed
    — queue_screen.dart: yes (10 l10n. callsites)
    — jobs_dashboard_screen.dart + jobs widgets: no (hard-coded English)
  ARB keys under queue.*: 6 ; job.*/jobs.*: 0 ; exception.*: 0

VERDICT: COMPLETE
```

---

**End of Part A.**
