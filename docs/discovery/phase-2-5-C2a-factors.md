# Phase 2.5 Discovery Part C2a — Q-C Decision Factors

**Type:** ANALYSIS (1 of 2 micro-splits of original Part C2)
**Date:** 2026-04-27
**Branch:** `claude/analyze-qc-decision-factors-1M2Xs`
**Git remote:** `origin  http://local_proxy@127.0.0.1:37817/git/Inneren12/Summa-vision-can` (fetch + push)
**Output:** READ-ONLY discovery document
**Pair:** C2b (recommendation matrix + open questions) follows.

---

## §0 Inputs consumed

| Part | Path | Status |
|---|---|---|
| A — router + screens | `docs/discovery/phase-2-5-A-router.md` | present (283 lines) |
| B — job model + endpoints | `docs/discovery/phase-2-5-B-model.md` | present (414 lines) |
| C1 — row type buckets | `docs/discovery/phase-2-5-C1-sources.md` | present (204 lines) |

All three prerequisites read in full before answering the factors below. (`/mnt/user-data/outputs/` does not exist on this host; canonical location is `docs/discovery/`.) READ-ONLY: no source files inspected directly — every claim below is grounded in cited evidence already captured in A, B, or C1.

---

## §1 Factor 1 — Does `/jobs` exist?

**Answer: YES.**

**Cited evidence — Part A §1.1 (`docs/discovery/phase-2-5-A-router.md`):**

> ```
> /jobs               → JobsDashboardScreen()                          app_router.dart:105-109
> ```
>
> Total routes: 9. Initial location: `/queue`.

**Cited evidence — Part A §1.2:**

> #### `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart`
> - Top-level widget class: `JobsDashboardScreen`
> - Type: `ConsumerStatefulWidget` (with `_JobsDashboardScreenState extends ConsumerState`)

**Cited evidence — Part A §1.1 redirect block:**

> `knownPrefixes = ['/queue', '/editor/', '/preview/', '/cubes/', '/data/', '/graphics/', '/kpi', '/jobs']`

The route is registered, the screen widget compiles and renders, and `/jobs` is in the redirect allow-list. Not partial-unfinished.

**Concrete artefacts:**

| Aspect | Value |
|---|---|
| Route path | `/jobs` |
| Route definition | `frontend/lib/core/routing/app_router.dart:105-109` |
| Route constant | `AppRoutes.jobs` (`app_router.dart:15-27`) |
| Widget class | `JobsDashboardScreen` |
| Widget file | `frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart` |
| Widget kind | `ConsumerStatefulWidget` |
| Supporting widgets | `widgets/job_card.dart`, `widgets/jobs_stats_bar.dart`, `widgets/job_detail_sheet.dart` |

---

## §2 Factor 2 — Does `/jobs` have tab structure?

**Answer: NO (single screen, no tabs).**

**Cited evidence — Part A §1.3 (verbatim grep output):**

> ```
> $ grep -nE 'TabBar|TabBarView|StatefulShellRoute' frontend/lib/features/jobs/presentation/jobs_dashboard_screen.dart
> (no matches)
>
> $ grep -rnE 'TabBar|TabBarView' frontend/lib/features/jobs/
> (no matches)
> ```
>
> - `/jobs` already has a tab structure: **no.**
> - Existing tabs today: **none.**
> - *Gloss: filtering on `/jobs` is done with a `DropdownButtonFormField` + `ChoiceChip` row, not with `TabBar`. Adding tabs would be a structural change, not a refactor of an existing `TabController`.*

**Cited evidence — Part A §1.1 (router shape):**

> `grep -n 'StatefulShellRoute' frontend/lib/core/routing/app_router.dart` → **none.**
> No `StatefulShellRoute`, no `ShellRoute`, no nested `routes:` children. Router is flat.

**What lives on `/jobs` today (Part A §1.2 detail):**

- Single `ListView.separated` of `JobCard` rows (`jobs_dashboard_screen.dart:236`)
- Filter row above the list: a `DropdownButtonFormField` for job type plus `ChoiceChip`s for status
- `JobsStatsBar` (status counts, tap-to-filter) above the filter row
- Refresh `IconButton` in the AppBar

**Implication for inbox-as-tab:**

- Current tab count: **0**
- Adding an "Exceptions" / "Inbox" tab is **not** an incremental change against an existing `TabController` — it requires introducing `TabBar` + `TabBarView` (or `DefaultTabController`) into `JobsDashboardScreen` first, then making the existing list the first tab and the inbox the second.
- Because there is no `StatefulShellRoute` either, the tab structure (if added) would live inside the screen, not in the router.

---

## §3 Factor 3 — How many row types includable in v1?

**Answer: 2 includable, 3 deferred (out of 5 enumerated row types).**

**Cited evidence — Part C1 §2 roll-up (verbatim):**

> | # | Type | Bucket | v1 inclusion |
> |---|---|---|---|
> | 1 | stale bindings | **C** | no |
> | 2 | failed exports | **A** | **yes** |
> | 3 | missing post URLs | **C** | no |
> | 4 | zombie jobs | **A** | **yes** |
> | 5 | validation blockers | **D** | no |
>
> **v1 includable today: 2** (types 2, 4)
> **v1 deferred: 3** (types 1, 3, 5)
> **New backend endpoints required for v1: 0**

**Bucket counts:**

| Bucket | Definition (from C1 §0 legend) | Count | Types |
|---|---|---|---|
| A | available via existing endpoint today | **2** | failed exports (#2), zombie jobs (#4) |
| B | data model exists, new aggregation endpoint required | **0** | — |
| C | depends on a future Phase — defer in 2.5 v1 | **2** | stale bindings (#1), missing post URLs (#3) |
| D | frontend-only state, not inbox-able from Flutter | **1** | validation blockers (#5) |

**Totals:**

- **Total includable (A + B): 2** — failed exports, zombie jobs
- **Total deferred (C + D): 3** — stale bindings, missing post URLs, validation blockers
- **Total enumerated row types: 5**

**Determining citations (per Part C1 per-type sections):**

- Type 1 (stale bindings, C): "No `Binding` model anywhere in `backend/src/models/`; Phase-3 dep" (C1 §1, type 1)
- Type 2 (failed exports, A): "`GET /admin/jobs?status=failed&job_type=graphics_generate`" (C1 §1, type 2 + Part B §1.4)
- Type 3 (missing post URLs, C): "No `post_url`/`post_ledger` anywhere; Phase-2.3 dep" (C1 §1, type 3)
- Type 4 (zombie jobs, A): "`?status=running` + `Job.isStale` (threshold 10 min, matches reaper)" (C1 §1, type 4 + Part B §1.5)
- Type 5 (validation blockers, D): "Validator lives in `frontend-public/.../validation/validate.ts`, never persisted server-side" (C1 §1, type 5)

---

## §4 Factor 4 — Endpoint overlap with `/jobs`

**Answer: HIGH overlap — 100% of v1-includable row types reuse `GET /api/v1/admin/jobs`. Zero new endpoints needed.**

**Cited evidence — Part B §1.4 (verbatim, the only listing endpoint):**

> ```
> GET  /api/v1/admin/jobs:               yes — JobListResponse{items, total}
> GET  /api/v1/admin/jobs/{job_id}:      yes — JobItemResponse (job_id is int)
> POST /api/v1/admin/jobs/{job_id}/retry: yes — 202, RetryJobResponse{job_id, status}
> ```
>
> Other relevant: none (no exceptions/failures/queue/bulk routers exist)

**Cited evidence — Part C1 roll-up:**

> NEW BACKEND ENDPOINTS NEEDED: 0 — both v1 row types reuse the existing `GET /api/v1/admin/jobs` listing with different `status` / `job_type` filter combinations.

**Per-type endpoint mapping:**

| # | Type | v1? | Source query | Endpoint | New endpoint? |
|---|---|---|---|---|---|
| 2 | failed exports | yes | `?status=failed&job_type=graphics_generate&limit=N` | `GET /api/v1/admin/jobs` | NO |
| 4 | zombie jobs | yes | `?status=running&limit=N` then client-side `Job.isStale` filter | `GET /api/v1/admin/jobs` | NO |
| 1 | stale bindings | no | n/a (no `Binding` entity exists) | none | n/a (deferred) |
| 3 | missing post URLs | no | n/a (no post ledger exists) | none | n/a (deferred) |
| 5 | validation blockers | no | n/a (frontend-only Zustand state) | none | n/a (deferred) |

**Includable types whose data already comes from `/api/v1/admin/jobs`:**

- Type 2 — failed exports
- Type 4 — zombie jobs

**Includable types needing new endpoints:**

- *(none)*

**Overlap assessment:**

- 2 of 2 v1 row types are served by the same endpoint that already powers the `/jobs` dashboard.
- The Flutter call site for both is the same repository method already in production: `JobDashboardRepository.listJobs({jobType, status, limit})` (Part B §1.3).
- The backend status enum already accepts `failed` and `running` (Part B §1.2), and `job_type` accepts the registered handler keys including `graphics_generate` (Part C1 §1, type 2).
- Client-side post-fetch refinement is required only for zombie jobs (apply `Job.isStale` over a `?status=running` page); failed exports need none.

**Implication:** the v1 inbox is a filtered view over the same data plane that `/jobs` already consumes — the canonical "high overlap → overlay natural" pattern. The opposite would be true (low/no overlap → new route natural) only if the v1 set required a new endpoint, which Part B §1.4 confirms it does not.

---

## §5 Summary Report

```
DOC PATH: docs/discovery/phase-2-5-C2a-factors.md
INPUTS: A=docs/discovery/phase-2-5-A-router.md
        B=docs/discovery/phase-2-5-B-model.md
        C1=docs/discovery/phase-2-5-C1-sources.md

Factor 1 (/jobs exists):     yes  (app_router.dart:105-109 → JobsDashboardScreen, ConsumerStatefulWidget)
Factor 2 (/jobs has tabs):   no   (no TabBar/TabBarView/TabController anywhere; filter via Dropdown+ChoiceChip)
Factor 3 (v1 row count):     2 includable (types 2,4) ; 3 deferred (types 1,3,5) ; bucket A=2 B=0 C=2 D=1
Factor 4 (endpoint overlap): high (2/2 v1 types reuse GET /api/v1/admin/jobs ; 0 new endpoints needed)

VERDICT: COMPLETE
```

---

**End of Part C2a.** C2b (recommendation matrix + open questions) follows.
