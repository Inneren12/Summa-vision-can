# Phase 2.5 Discovery Part C1 — Source-of-Truth for 5 Inbox Row Types

**Type:** ANALYSIS (1 of 2 splits of original Part C; pair with C2 risk analysis)
**Date:** 2026-04-27
**Branch:** `claude/inbox-row-types-discovery-c5pCi`
**Git remote:** `origin  http://local_proxy@127.0.0.1:33089/git/Inneren12/Summa-vision-can` (fetch + push)
**Output:** READ-ONLY discovery document

---

## §0 Inputs consumed

| Part | Path | Status |
|---|---|---|
| A — router + screens | `docs/discovery/phase-2-5-A-router.md` | present |
| B — job model + endpoints | `docs/discovery/phase-2-5-B-model.md` | present |

Both prerequisites read in full before classification below. (`/mnt/user-data/outputs/` does not exist on this host; the canonical location is `docs/discovery/`.)

**Bucket legend:**
- **A** — available via existing endpoint today
- **B** — data model exists, but a new aggregation endpoint is required
- **C** — depends on a future Phase — defer in 2.5 v1
- **D** — frontend-only state, not inbox-able from Flutter

---

## §1 Per-type classification

### Type 1 — Stale bindings

**Bucket: C** (Phase-3-only, defer)

**Evidence (greps over `backend/src`, `frontend/lib`, `frontend-public/src`):**

```
$ grep -rn 'binding.*stale\|stale.*binding\|snapshotValue\|resolvedAt' backend/src frontend/lib frontend-public/src
backend/src/core/logging.py:92:  def get_logger(**initial_bindings: object)        # structlog kwarg, unrelated
frontend/lib/main.dart:18:  WidgetsFlutterBinding.ensureInitialized();              # Flutter framework
frontend-public/src/components/editor/types.ts:84:  resolvedAt: string | null;     # review COMMENT, not a binding
```

```
$ grep -rni 'class.*Binding\|hybrid.binding\|binding_id' backend/src frontend/lib
(zero matches — no Binding entity / table / class exists)
```

- No `Binding` model in `backend/src/models/` (only `audit_event`, `cube_catalog`, `download_token`, `job`, `lead`, `publication`).
- No `bindings` router in `backend/src/api/routers/`.
- Every `binding` hit traces to either structlog kwargs, Flutter framework `WidgetsBinding`, or editor review-comment `resolvedAt` (which is a comment-resolution timestamp, not a binding-resolution timestamp).
- Memory + roadmap call hybrid binding a **Phase 3** deliverable. The data model does not exist today.

**v1 inclusion: NO** — defer until Phase 3 ships the binding entity. There is nothing for the inbox to query.

---

### Type 2 — Failed exports

**Bucket: A** (available via existing `GET /api/v1/admin/jobs?status=failed&job_type=graphics_generate`)

**Evidence — Part B §1.4 verbatim:**

> `GET /api/v1/admin/jobs` (admin_jobs.py:92)
> Query params: `job_type` (str, optional), `status` (str, optional — aliased from `status_filter`), `limit` (int, 1..200, default 50)
> Status validation: invalid `status_filter` ⇒ 422 (lines 110–118); only the five `JobStatus` enum values are accepted.

**Evidence — handler registry (`backend/src/services/jobs/handlers.py`):**

```
register_handler("catalog_sync",      handle_catalog_sync)        # line 101
register_handler("cube_fetch",        handle_cube_fetch)          # line 182
register_handler("graphics_generate", handle_graphics_generate)   # line 235  ← export equivalent
```

The "export" surface in this codebase is the `graphics_generate` job type, which runs the end-to-end graphic pipeline (`handlers.py:194`). The `approved → exported` workflow event in `admin_publications.py:64,79` confirms the same vocabulary at the publication layer.

**Filterability today:**
- Status filter: ✅ `?status=failed` (validated against `JobStatus` enum)
- Job type filter: ✅ `?job_type=graphics_generate`
- Combined query returns the exact list of failed export jobs ordered by `created_at DESC` (Part B §1.4) with `total` count.

**v1 inclusion: YES** — zero new backend work. Flutter just composes the query in `JobDashboardRepository.listJobs(jobType: 'graphics_generate', status: 'failed', limit)`.

---

### Type 3 — Missing post URLs

**Bucket: C** (Phase-2.3-dep, defer)

**Evidence:**

```
$ grep -rn 'post_url\|posted_at\|post_ledger\|distribution_package' backend/src frontend/lib
(zero matches)
```

- No `post_url` / `posted_at` column on `Publication` (full field list at `backend/src/models/publication.py:80-155` shows `s3_key_lowres`, `s3_key_highres`, `published_at`, but **no** `post_url` / posting-distribution fields).
- No `post_ledger` / `distribution_package` table in `backend/src/models/__init__.py`.
- Roadmap places the post ledger at item 2.3, which has not shipped.

**v1 inclusion: NO** — defer until Phase 2.3 introduces the ledger. There is no posting record to flag as "missing URL" today.

---

### Type 4 — Zombie jobs

**Bucket: A** (available via existing `GET /api/v1/admin/jobs?status=running` + Flutter's existing `Job.isStale` helper)

**Evidence — reaper exists but is write-side only:**

```
backend/src/main.py:72            # Zombie reaper (R8) — runs once on startup
backend/src/main.py:79            requeued = await job_repo.requeue_stale_running(stale_threshold_minutes=10)
backend/src/repositories/job_repository.py:202   async def requeue_stale_running(stale_threshold_minutes=10)
```

The reaper *requeues* stale running jobs — it does not expose a listing endpoint. There is no `?stale_only=true` query parameter and no dedicated `/zombies` route (`grep -n '@router' admin_jobs.py` returns 3 routes only — list, get, retry).

**However, the listing path exists and the threshold logic is already mirrored client-side:**

- Server endpoint: `GET /api/v1/admin/jobs?status=running` (Part B §1.4) returns running jobs ordered `created_at DESC` with `started_at` populated.
- Flutter helper (Part B §1.1, `frontend/lib/features/jobs/domain/job.dart` `JobHelpers`):
  > `isStale` ⇒ `status == 'running' && startedAt != null && now - startedAt > 10 min`
- Threshold (10 min) matches the reaper exactly (`requeue_stale_running` default = 10 min).

So the inbox can today: fetch `?status=running&limit=200`, filter rows where `Job.isStale == true`. No new backend.

**Caveat:** post-fetch filtering scales fine while running-job count fits within `limit ≤ 200`. A server-side `?stale_only=true` filter would be a future optimization, not a v1 blocker.

**v1 inclusion: YES** — bucket A on the strict criterion (listing endpoint + status filter exists; age threshold already implemented in Flutter domain layer).

---

### Type 5 — Unresolved validation blockers

**Bucket: D** (frontend-only Zustand state, not inbox-able from Flutter today)

**Evidence — validator lives in the Next.js editor app, not the backend:**

```
$ grep -rn 'validation_blocker\|validator.*blocker\|blocked_by_validator' backend/src frontend/lib frontend-public/src
(zero matches)
```

```
$ grep -rn 'errors\.push' frontend-public/src/components/editor/validation/validate.ts
validate.ts:20-159   # 14 R.errors.push() callsites with keys 'validation.page.unknown_palette',
                     # 'validation.headline.empty', 'validation.section.duplicate_id', etc.
```

- Validator output is built per-render from `validate(doc)` returning `{errors, warnings}` — purely in-memory React/Zustand state inside `frontend-public/src/components/editor/`. It is **not persisted**.
- TopBar gates exports on it: `tExport('disabled.validation_errors', { count: errs })` (`TopBar.tsx:94`) — again, runtime-only.
- Backend `Publication.review` is a Text JSON blob; the model docstring (`backend/src/models/publication.py:128-130`) states explicitly:
  > "The backend stores the payload verbatim and does not deep-validate nested entries; the frontend's `assertCanonicalDocumentV2Shape` owns shape validation."
- No `validation_status` / `validation_blocked` column on `Publication`. No queryable flag exists.
- The Flutter app does not run the validator (it lives in `frontend-public/`, the Next.js editor — not `frontend/`, the Flutter admin shell), so there is nothing for the Flutter inbox to surface.

**v1 inclusion: NO** — surfacing this requires either (a) backend persistence of validation status on `Publication`, or (b) the editor pushing validation results into a backend record on save. Both are scope additions, not 2.5 work.

---

## §2 Roll-up

| # | Type | Bucket | v1 inclusion | Determining citation |
|---|---|---|---|---|
| 1 | stale bindings | **C** | no | No `Binding` model anywhere in `backend/src/models/`; Phase-3 dep |
| 2 | failed exports | **A** | **yes** | Part B §1.4 `GET /admin/jobs?status=failed&job_type=graphics_generate` |
| 3 | missing post URLs | **C** | no | No `post_url`/`post_ledger` anywhere; Phase-2.3 dep |
| 4 | zombie jobs | **A** | **yes** | Part B §1.4 `?status=running` + `Job.isStale` (threshold 10 min, matches reaper) |
| 5 | validation blockers | **D** | no | Validator lives in `frontend-public/.../validation/validate.ts`, never persisted server-side |

**v1 includable today: 2** (types 2, 4)
**v1 deferred: 3** (types 1, 3, 5)
**New backend endpoints required for v1: 0** — both v1 row types reuse the existing `GET /api/v1/admin/jobs` listing with different `status` / `job_type` filter combinations.

---

## §3 Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:33089/git/Inneren12/Summa-vision-can
DOC PATH: docs/discovery/phase-2-5-C1-sources.md

INPUTS CONSUMED:
  Part A: docs/discovery/phase-2-5-A-router.md
  Part B: docs/discovery/phase-2-5-B-model.md

§ Per-type buckets:
  1. stale bindings:        C  (Phase-3 dep, no Binding entity)
  2. failed exports:        A  (existing /admin/jobs ?status=failed&job_type=graphics_generate)
  3. missing post URLs:     C  (Phase-2.3 dep, no post ledger)
  4. zombie jobs:           A  (existing /admin/jobs ?status=running + Flutter Job.isStale)
  5. validation blockers:   D  (frontend-only validate.ts, never persisted)

V1 ROW TYPES INCLUDABLE: 2  (types 2, 4)
V1 ROW TYPES DEFERRED:   3  (types 1, 3, 5)
NEW BACKEND ENDPOINTS NEEDED: 0

VERDICT: READY-FOR-C2
```

---

**End of Part C1.** C2 (Q-C overlay vs new route risk analysis) follows.
