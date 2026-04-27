# Phase 2.5 Discovery Part C2b — Q-C Recommendation Matrix

**Type:** ANALYSIS (2 of 2 micro-splits of original Part C2)
**Date:** 2026-04-27
**Branch:** `claude/qc-recommendation-matrix-zIN0u`
**Git remote:** `origin  http://local_proxy@127.0.0.1:44353/git/Inneren12/Summa-vision-can` (fetch + push)
**Output:** READ-ONLY discovery document
**Pair:** C2a (Q-C decision factors) precedes.

---

## §0 Inputs consumed

| Part | Path | Status |
|---|---|---|
| A — router + screens | `docs/discovery/phase-2-5-A-router.md` | present (referenced via C2a) |
| B — job model + endpoints | `docs/discovery/phase-2-5-B-model.md` | present (referenced via C2a) |
| C1 — row type buckets | `docs/discovery/phase-2-5-C1-sources.md` | present (204 lines) |
| C2a — Q-C decision factors | `docs/discovery/phase-2-5-C2a-factors.md` | present (209 lines) |

C2a read in full — every cell in the matrix below is grounded in a C2a factor citation. **No source files inspected directly.** **No side picked.**

---

## §1 Recommendation matrix

DO NOT pick a side. Founder picks Q-C.

| Factor | OVERLAY (tab on `/jobs`) | NEW ROUTE (`/exceptions`) |
|---|---|---|
| **Files touched** | ~4–6 files: `jobs_dashboard_screen.dart` (structural refactor — wrap existing body in `TabBarView`, hoist `AppBar` to host `TabBar`), 1 new tab-body widget (e.g. `inbox_tab.dart`), 1 new `Provider` composing two `listJobs` queries, optional new row widget if `JobCard` is reused unchanged. *(Source: C2a F1 + F2 — `JobsDashboardScreen` is `ConsumerStatefulWidget` with no existing `TabController`, so the tab scaffold has to be introduced before the inbox body can be added.)* | ~3–5 files: 1 new screen `exceptions_screen.dart`, 1 new `Provider` composing two `listJobs` queries, 1 router entry in `app_router.dart` (path + redirect prefix), optional new row widget. *(Source: C2a F1 — router is flat, no `StatefulShellRoute`; `app_router.dart:105-109` shows the existing pattern of a single screen-per-route mapping.)* |
| **Existing tests at risk** | All tests covering `JobsDashboardScreen`'s current single-body shape: filter row (`DropdownButtonFormField` + `ChoiceChip`), `JobsStatsBar` stat-tap-to-filter, `ListView.separated` of `JobCard`s, AppBar refresh `IconButton`. Any widget test that pumps `JobsDashboardScreen` and looks up these by `find.byType` / `find.byKey` will need re-anchoring under the new tab. *(Source: C2a F1 supporting-widgets list + F2 "current screen contents".)* | none — `JobsDashboardScreen` is not modified; new screen has no prior tests. *(Source: C2a F1 — file untouched under this option.)* |
| **Tab refactor needed** | YES — `JobsDashboardScreen` has zero tabs today (C2a F2: "current tab count: 0"; "no `TabBar` / `TabBarView` / `TabController` anywhere in `frontend/lib/features/jobs/`"). Adding "Inbox" requires introducing `TabBar` + `TabBarView` (or `DefaultTabController`) into the screen first, then making the existing list tab 1 and inbox tab 2. This is a **structural change**, not a refactor of an existing `TabController`. | n/a — new screen owns its own scaffold; no tab structure required at all (could be added later inside `/exceptions` independently). |
| **Aligns with v1 row types** | High data-layer fit: 2/2 v1 row types (failed exports, zombie jobs) are served by `GET /api/v1/admin/jobs` with `status` / `job_type` filters — the same endpoint that already powers `/jobs`. Inbox is literally a saved-filter view of the same data plane. *(Source: C2a F3 — A=2, and F4 — "100% endpoint overlap; 0 new endpoints".)* | Same data-layer fit (the endpoint is the same regardless of where the screen lives), but the **conceptual** fit is looser for v1 only and tighter for vNext: deferred row types 1/3/5 (stale bindings, missing post URLs, validation blockers — C2a F3 buckets C, C, D) are **not** job-status filters and would not naturally belong under a `/jobs` tab once they ship. *(Source: C2a F3 deferred list + F4 "the opposite would be true [low/no overlap → new route natural] only if the v1 set required a new endpoint, which Part B §1.4 confirms it does not".)* |
| **Discoverability** | Tab inside `/jobs` — secondary surface; reachable only after the operator navigates to `/jobs` and notices the tab strip. Less prominent. | Top-level route in `app_router.dart` alongside `/queue`, `/jobs`, `/cubes`, `/data`, `/graphics`, `/kpi` — appears in nav menus on equal footing with other dashboards. More prominent. *(Source: C2a F1 redirect-prefix list `['/queue', '/editor/', '/preview/', '/cubes/', '/data/', '/graphics/', '/kpi', '/jobs']` shows the current top-level surface set.)* |
| **Future expansion** | Tab strip on `/jobs` accumulates pressure: Phase-3 stale bindings (C1 type 1), Phase-2.3 missing post URLs (C1 type 3), and any later validation-blocker surfacing (C1 type 5) all want a home. None of those are `job_type` filters, so each would either become its own tab (crowded) or force a sub-router inside `/jobs`. *(Source: C1 §2 deferred list + C2a F3 bucket C/D = 3 deferred types.)* | Dedicated surface — `/exceptions` can grow internal structure (sub-tabs, sections, separate providers per row family) without touching `/jobs`. Phase-3 binding rows and Phase-2.3 post-URL rows can attach here naturally when they ship. *(Source: same C1/C2a deferred list, viewed from the opposite vantage.)* |

---

## §2 Per-factor reasoning paragraphs

**Files touched.** Both options sit in the same order of magnitude (3–6 files), but the *kind* of change differs. OVERLAY's churn includes one structural edit to a live screen (`jobs_dashboard_screen.dart`) — wrapping its body in a `TabBarView` and hoisting the `AppBar` to host a `TabBar` — alongside the new tab content. NEW ROUTE's churn is purely additive: a new screen file, a new provider, and one route registration in `app_router.dart`. The file count is similar; the change profile is "edit + add" vs. "add only".

**Existing tests at risk.** This factor follows directly from C2a F1's listing of `JobsDashboardScreen`'s current widget tree. OVERLAY rewires that tree (filter row and `JobsStatsBar` get pushed into a tab body), so any widget test that locates them by ancestor/position rather than by `Key` becomes brittle. NEW ROUTE leaves that tree untouched, so prior `JobsDashboardScreen` tests keep passing as-is.

**Tab refactor needed.** C2a F2 is unambiguous: zero `TabBar` / `TabBarView` / `TabController` matches across `frontend/lib/features/jobs/`. OVERLAY therefore does not "add a tab" — it *introduces tab infrastructure* into a screen that has none. NEW ROUTE sidesteps the question entirely; whether `/exceptions` ever uses tabs is a future decision local to that screen.

**Aligns with v1 row types.** At the data layer the two options are equivalent: both call `JobDashboardRepository.listJobs(...)` against `GET /api/v1/admin/jobs`, and C2a F4 confirms that 2/2 v1 row types are endpoint-overlapping. Where they diverge is conceptual scope. C2a F3 documents that 3 of 5 enumerated row types are deferred (stale bindings, missing post URLs, validation blockers); none of those three are reachable as `?status=...&job_type=...` filters because the underlying entities (`Binding`, post ledger, persisted validation state) do not exist as queryable records (per C1 §1 buckets C, C, D). OVERLAY is tightest when "Inbox" remains permanently a job-status filter; NEW ROUTE is tightest when "Exceptions" eventually broadens beyond jobs.

**Discoverability.** A top-level route appears in the same place as `/jobs`, `/queue`, `/cubes`, etc., per the C2a F1 redirect-prefix list, and is reachable in one navigation hop. A tab inside `/jobs` is reachable in two — `/jobs` first, then the tab — and is only visible to operators who already work on the jobs surface. Whether the extra hop matters depends on whether Inbox is a sub-task of jobs work or a peer of it; this is the workflow question Q-C resolves.

**Future expansion.** C1 §2 enumerates 3 deferred row types (1: stale bindings, Phase 3; 3: missing post URLs, Phase 2.3; 5: validation blockers, frontend-only state requiring backend persistence). When Phase 3 and Phase 2.3 ship, those row types arrive without `job_type` semantics. Under OVERLAY they pressure the `/jobs` tab strip toward 3+ tabs of mixed conceptual provenance; under NEW ROUTE they attach to `/exceptions` as additional sections of a surface that already advertises itself as the cross-cutting exceptions home. This factor weighs on the Phase-3 horizon, not on v1.

---

## §3 Explicit non-recommendation

This analysis does not pick a side. Both options are technically viable. Founder Q-C resolves the choice based on team workflow preference: overlay if `/jobs` is daily-driven, new route if Exceptions warrants separate operator focus.

---

## §4 Open questions beyond Q-C

The inventory raised the following ambiguities that are **not** Q-C blockers but should be answered at recon-proper so they are not forgotten:

1. **Daily-driver question.** Does the operator currently use `/jobs` daily? Affects which surface deserves real estate. If `/jobs` is a high-traffic dashboard, an overlay tab is "where the eyes already are"; if `/jobs` is checked only when something has gone wrong, then either option needs a separate signal (notification badge, top-level link) regardless.

2. **Action parity.** Should retry/cancel actions in Inbox match `/jobs` behaviour (existing `POST /api/v1/admin/jobs/{job_id}/retry` per Part B §1.4), or have specialised affordances (e.g. bulk retry, dismiss-without-action, snooze)? Q-C does not constrain this — both placements support either choice — but the answer affects the v1 widget/provider surface area regardless of where the screen lives.

3. **Architectural placeholder for deferred row types.** For Phase-3 stale bindings (C1 type 1), Phase-2.3 missing post URLs (C1 type 3), and unresolved validation blockers (C1 type 5) — does Inbox v1 need to leave **architectural room** today (placeholder tabs/sections, slot in a router-level enum, named `Provider` family), or wait for those phases to land before reserving any structure? This is independent of Q-C: a NEW ROUTE can choose to ship empty section headers or not; an OVERLAY tab can choose to ship a single tab or pre-stub the strip.

4. **Page-size posture for zombie jobs.** C1 §1 (type 4 caveat) notes that zombie detection in v1 is post-fetch (`?status=running&limit=200` then client-side `Job.isStale`). Does v1 want to ship with `limit=200` permanently, or is the founder comfortable that "running-job count fits within 200" is a steady-state assumption? A future server-side `?stale_only=true` filter is out of scope for 2.5 either way; this is a "what do we tolerate today" question.

These four are listed so they are not lost; they can be answered any time before v1 implementation begins.

---

## §5 Summary Report

```
DOC PATH: docs/discovery/phase-2-5-C2b-matrix.md
Matrix produced: yes
Sides picked: NO (founder decides Q-C)
Overlay possible: yes — C2a Factor 1 (/jobs exists) + Factor 2 (no tabs today, so structural refactor required but viable)
Endpoint overlap: high — C2a Factor 4 (2/2 v1 row types reuse GET /api/v1/admin/jobs; 0 new endpoints)
Additional founder questions: 4 (daily-driver use, action parity, deferred-type placeholders, zombie page-size posture)
VERDICT: READY-FOR-FOUNDER-Q-C-DECISION
```

---

**End of Part C2b.**
