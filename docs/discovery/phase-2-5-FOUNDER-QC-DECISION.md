# Phase 2.5 Discovery — Founder Q-C Decision Block

**Type:** FOUNDER DECISION SUMMARY (consolidates pre-recon Parts A, B, C1, C2a, C2b)
**Date:** 2026-04-27
**Status:** READY-FOR-FOUNDER-Q-C-DECISION
**Output:** READ-ONLY summary — does NOT modify any pre-recon part; consumed by recon-proper prompt after founder answers.

---

## §1 What's being decided

Phase 2.5 ships an **operator inbox** for surfacing exception-flavoured rows (failed exports, zombie jobs in v1; stale bindings, missing post URLs, validation blockers in vNext). The pre-recon set is complete and self-consistent — no cross-Part drift, no contradictions to reconcile (unlike Phase 1.3).

**One hard block remains: founder picks Q-C** — where the inbox lives in the Flutter admin shell.

| Q-C option        | One-line description                                                                |
|-------------------|--------------------------------------------------------------------------------------|
| **(α) OVERLAY**   | Inbox is a **new tab inside `/jobs`**, alongside the existing `JobsDashboardScreen`. |
| **(β) NEW ROUTE** | Inbox is a **separate top-level route `/exceptions`** alongside `/jobs`, `/queue`, `/cubes`, etc. |

Both options are technically viable. The choice is a **workflow / discoverability call**, not a technical-correctness call. C2b §3 explicitly does not pick a side.

---

## §2 What we know going in (zero drift)

Pre-recon facts that hold regardless of Q-C outcome:

| Fact                                                  | Source           |
|--------------------------------------------------------|------------------|
| `/jobs` route exists today (`JobsDashboardScreen`, `ConsumerStatefulWidget`) | A §1.1, A §1.2 + C2a F1 |
| `/jobs` has **NO tab structure** today (no `TabBar`/`TabBarView`/`TabController` anywhere in `frontend/lib/features/jobs/`) | A §1.3 + C2a F2 |
| Router is **flat** — no `StatefulShellRoute`, no `ShellRoute`, no nested children | A §1.1 |
| `/exceptions` route does **NOT exist** — no dir, no file, no router entry | A §1.2 |
| 5 row types enumerated; **2 includable in v1**: failed exports + zombie jobs | C1 §2 |
| 3 deferred row types: stale bindings (Phase 3), missing post URLs (Phase 2.3), validation blockers (frontend-only state) | C1 §2 |
| **0 new backend endpoints needed** — both v1 row types reuse `GET /api/v1/admin/jobs` with different `?status=` / `?job_type=` filters | C1 §2 + C2a F4 |
| `/jobs` is fully unlocalized (hard-coded EN); `/queue` is fully l10n-wired — pattern split already exists | A §1.4 |

---

## §3 Q-C decision matrix (verbatim recall from C2b §1)

| Factor              | (α) OVERLAY                                        | (β) NEW ROUTE                                       |
|---------------------|-----------------------------------------------------|------------------------------------------------------|
| **Files touched**   | ~4–6 files: structural refactor of `jobs_dashboard_screen.dart` (wrap body in `TabBarView`, hoist AppBar to host `TabBar`), 1 new tab body widget, 1 new provider, optional row widget | ~3–5 files: 1 new screen `exceptions_screen.dart`, 1 new provider, 1 router entry in `app_router.dart`, optional row widget |
| **Existing tests at risk** | All `JobsDashboardScreen` tests anchored by `find.byType` / position (filter row, `JobsStatsBar`, `ListView.separated`, AppBar refresh) | None — `JobsDashboardScreen` untouched, new screen has no prior tests |
| **Tab refactor needed** | YES — introduces `TabBar`/`TabBarView` infrastructure into a screen with zero existing tabs (structural change, not a refactor of existing `TabController`) | n/a — new screen owns its own scaffold; tabs are an optional later choice local to that screen |
| **Aligns with v1 row types** | High data-layer fit (2/2 v1 types reuse `GET /api/v1/admin/jobs`); tight conceptual fit IF inbox stays a job-status filter forever | Same data-layer fit; **tighter conceptual fit if inbox eventually broadens** beyond jobs (binding rows, post-URL rows are NOT `?job_type=` filters) |
| **Discoverability** | Secondary surface (2 hops: navigate to `/jobs`, then notice tab strip); only visible to operators already on jobs surface | Top-level (1 hop, equal footing with `/jobs`/`/queue`/`/cubes`/`/data`/`/graphics`/`/kpi`) |
| **Future expansion** | Tab strip on `/jobs` accumulates pressure as 3 deferred row types arrive — none of them are `job_type` filters → either crowded tab strip or sub-router inside `/jobs` | Dedicated surface; `/exceptions` grows internal structure without touching `/jobs`; deferred rows attach naturally |

---

## §4 The workflow question Q-C resolves

C2b §3 frames the decision as a **workflow call**:

> *"overlay if `/jobs` is daily-driven, new route if Exceptions warrants separate operator focus."*

Restated as the question the founder is actually answering:

**"Is the inbox a sub-task that operators reach while already working on jobs (overlay), or a peer surface that earns its own top-level focus (new route)?"**

The matrix doesn't answer this. The pre-recon set deliberately stops here.

---

## §5 What each answer triggers

### §5.1 If Q-C = (α) OVERLAY

**Recon-proper additions required:**

- Sub-recon on `JobsDashboardScreen` structural refactor: which widgets stay in the AppBar, which move into the tab body, how `JobsStatsBar` interacts with tab switching, whether the job-type filter row applies per-tab or globally.
- Test re-anchoring strategy for existing `JobsDashboardScreen` widget tests — likely Key-based, not position-based.
- Decision: should the existing list become tab "All Jobs" with the inbox as tab "Inbox", or should "Failed Exports" + "Zombie Jobs" each get its own tab (i.e., does v1 ship 2 tabs or 3+)?
- l10n: jobs surface goes from hard-coded EN (A §1.4) to localized — does the overlay PR also wire `AppLocalizations` for the existing jobs literals, or only the new tab? (Pre-existing tech-debt question made acute by the refactor touching the same file.)

**Implementation cost:** higher than (β). Structural edit to a live screen + test re-anchoring.

### §5.2 If Q-C = (β) NEW ROUTE

**Recon-proper additions required:**

- Decide on `app_router.dart` route shape: `/exceptions` flat top-level (matches existing pattern), or `/exceptions/:typeId` for future drill-in (e.g., `/exceptions/failed-exports`).
- Update redirect allow-list `knownPrefixes` (A §1.1, line 41–47) to include `/exceptions`.
- Decide: does the new screen reuse `JobCard` widget verbatim, or get a row widget tailored to "exception" framing (different actions, different visual treatment)?
- l10n: new screen ships fully l10n-wired from day 1 (matching `/queue` pattern, not the `/jobs` hard-coded-EN debt).
- AppDrawer entry: where does `/exceptions` slot in the drawer ordering?

**Implementation cost:** lower than (α). Pure additive change, no live-screen edit, no existing tests to re-anchor.

---

## §6 Secondary questions (NOT blockers; answered at recon-proper)

Per C2b §4 — these belong in the recon-proper open-questions block but do NOT block Q-C. They land regardless of (α)/(β):

| #     | Question                                                                                              | C2b ref |
|-------|-------------------------------------------------------------------------------------------------------|---------|
| Q-C.1 | **Daily-driver question** — is `/jobs` checked daily, or only on incidents? Affects whether overlay's "where the eyes already are" is real, but does NOT change what gets built once Q-C is picked. | C2b §4.1 |
| Q-C.2 | **Action parity** — do retry/cancel actions in inbox match `/jobs` behavior (`POST /api/v1/admin/jobs/{id}/retry` per B §1.4) or have specialized affordances (bulk retry, dismiss, snooze)? | C2b §4.2 |
| Q-C.3 | **Architectural placeholders for deferred types** — does Inbox v1 leave reserved structure (stub tabs/sections, router enums, named provider families) for the 3 deferred row types, or wait for Phase 2.3/3 to land first? | C2b §4.3 |
| Q-C.4 | **Page-size posture for zombie jobs** — ship `limit=200` + client-side `Job.isStale` filter permanently, or accept this as steady-state v1 with no follow-up? Server-side `?stale_only=true` is out of scope either way. | C2b §4.4 |

These are filed for recon-proper, not the Q-C answer. Answering them now is fine but not required.

---

## §7 Recommendation (pre-recon does not pick a side)

This summary deliberately mirrors C2b's stance: **no recommendation**.

Two pre-recon observations bear on the decision but do not collapse it:

1. **Future expansion favors (β).** 3 of 5 enumerated row types (stale bindings, missing post URLs, validation blockers) are NOT `?job_type=` filters. Under (α), they pressure the tab strip toward "tabs of mixed conceptual provenance" once Phase 2.3/3 ship. Under (β), they attach as additional sections of an already-scoped exceptions surface.

2. **Implementation cost favors (β) for v1.** (α) requires structural edit + test re-anchoring on a live screen that currently has zero tabs. (β) is purely additive: 1 new screen file, 1 new provider, 1 router entry. **However** — neither cost is high in absolute terms. Both ship in a single PR.

If the operator workflow is: *"I open `/jobs` daily, scan for failures, retry the actionable ones"* → overlay reduces hops.
If the workflow is: *"I check exceptions when something feels off, often without context on running jobs"* → new route gives the surface its own front door.

**Founder picks Q-C based on which sentence above more accurately describes operator reality.**

---

## §8 Reading order if founder wants the source-of-truth

Recommended sequence to re-read before answering:

1. **C2b §1 matrix** (`docs/discovery/[phase-2-5-C2b-matrix.md](http://phase-2-5-C2b-matrix.md)`) — full factor-by-factor table.
2. **C2a F4** (`docs/discovery/[phase-2-5-C2a-factors.md](http://phase-2-5-C2a-factors.md)` §4) — endpoint overlap analysis (the "high overlap → overlay natural" pattern, viewed from both sides).
3. **C1 §2** (`docs/discovery/[phase-2-5-C1-sources.md](http://phase-2-5-C1-sources.md)`) — 5-row-type bucket roll-up; specifically the deferred types (1, 3, 5) and why their non-`job_type` semantics matter for tab-strip pressure.
4. **A §1.1 + §1.3** (`docs/discovery/[phase-2-5-A-router.md](http://phase-2-5-A-router.md)`) — router shape (flat, no shell route) + confirmation that `/jobs` has zero tabs today.

Total reading time: ~15 min for the source-of-truth path; this summary is sufficient for a quick decision.

---

## §9 What to send back

When the founder is ready to answer Q-C, the message back to me can be as short as:

- **"Q-C = α (overlay)"** — I generate recon-proper prompt for Phase 2.5 with the (α) sub-recon scope from §5.1.
- **"Q-C = β (new route)"** — I generate recon-proper prompt for Phase 2.5 with the (β) sub-recon scope from §5.2.

Q-C.1–Q-C.4 (secondary) can be answered in the same message or deferred to recon-proper output.

If anything in §3 / §5 / §7 is ambiguous, point at the row and I clarify against the source-of-truth parts before recon-proper kicks off.

---

End of decision block. Phase 2.5 pre-recon set: COMPLETE — awaiting founder Q-C.
