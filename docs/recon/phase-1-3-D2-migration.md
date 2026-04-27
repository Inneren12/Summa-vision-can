# Phase 1.3 Pre-Recon Part D2 — Migration & Rollout (Section G)

**Type:** RECON FINALIZATION (2 of 4 micro-splits of original Part D)
**Scope:** Section G only — migration analysis + deploy order.
**Other splits:** D1 (test plan), D3 (DEBT additions), D4 (polish + founder questions).
**Date:** 2026-04-27
**Branch:** `claude/migration-rollout-analysis-JauAD`
**Git remote:** `http://local_proxy@127.0.0.1:36411/git/Inneren12/Summa-vision-can`

**Prereqs read:**
- Part A — `docs/recon/phase-1-3-A-backend-inventory.md` (Publication model column inventory at A §1.2).
- Part C1 — `docs/recon/phase-1-3-C1-etag.md` (ETag derivation: `id` + `updated_at`/`created_at` + `config_hash`).
- Part C2d — `docs/recon/phase-1-3-C2d-backcompat.md` (tolerate-missing policy + DEBT-038).

This document is **READ-ONLY** for production code — no schema changes are
proposed; the section below explicitly closes out the "do we need a migration?"
question.

---

## Section G — Migration & Rollout

### G.1 Column changes

**Decision: NO new column on `publications`.**

Cited from Part A §1.2 (verbatim column list, `backend/src/models/publication.py:80-155`),
the version-relevant columns the ETag will consume already exist:

| Column        | Present per Part A §1.2 | Type / nullability                              | Used by ETag derivation? |
|---------------|-------------------------|--------------------------------------------------|--------------------------|
| `id`          | ✅ A §1.2 line 82       | `int`, PK, `autoincrement=True`, NOT NULL        | ✅ (identity component)  |
| `updated_at`  | ✅ A §1.2 line 117–121  | `DateTime(timezone=True)`, **nullable**, `onupdate=func.now()` | ✅ (primary timestamp) |
| `created_at`  | ✅ A §1.2 line 104–109  | `DateTime(timezone=True)`, NOT NULL, defaulted   | ✅ (fallback when `updated_at IS NULL`) |
| `config_hash` | ✅ A §1.2 line 90       | `String(64)`, **nullable**                       | ✅ (NULL → `""` per C1 §A.2) |

Per Part C1 §A.1 line 33 (verbatim): *"R19 satisfied: derivation reuses
`updated_at` + `config_hash`. **No new column required.**"* The ETag is a
**derived** value — `compute_etag(pub) -> sha256("{id}|{updated_at or created_at}|{config_hash or ''}")[:16]`
(C1 §A.2) — and is computed in a pure helper at `backend/src/services/publications/etag.py`,
never persisted.

**`config_hash` existence check (closes the C1 §A.8 contingency).** Part A §1.2
line 90 confirms `config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)`
is already on the model. The "raise as Q if `config_hash` is missing" branch
from C1 §A.8 #1 therefore does **not** fire, and no follow-up founder Q is
needed for this section.

**No `row_version` / `etag` / `revision` column is being added.** The Part A
§1.2 gloss explicitly notes *"no dedicated optimistic-concurrency `row_version`/
`etag` column exists today"* — and that remains the case after Phase 1.3. The
optimistic-concurrency check is a string compare against the derived ETag, not
a numeric row-version increment.

### G.2 Alembic migration

**Decision: NO Alembic migration needed for Phase 1.3.**

Reasoning:

1. No column added (G.1).
2. No column type change. `updated_at`'s `onupdate=func.now()` trigger is the
   ETag's freshness signal; the trigger already exists per Part A §1.2 line 120.
3. No new index strictly required for the v1 query path. The PATCH handler does
   `repo.get_by_id(publication_id)` (PK lookup, already indexed) followed by a
   single-row UPDATE on the same PK. No new lookup keys are introduced.
4. No new ENUM values. `PublicationStatus` is unchanged.
5. No FK additions or changes.

**If a future v2 ever introduces a dedicated `row_version` integer column** (out
of scope per C1 §A.4 / G.1), the migration would need to follow the Summa-Vision
Alembic conventions already used elsewhere in the project:

- For any **enum-typed** column added or modified, use
  `postgresql.ENUM(..., create_type=False)` together with `checkfirst=True`
  precautions (carry-forward from earlier sprint memory; relevant historical
  reference: `backend/migrations/versions/6e2e939f9cb6_add_publication_versioning.py`
  pattern set).
- Integration test teardown for any new migration must use
  `alembic downgrade base` rather than `Base.metadata.drop_all()`, so that the
  downgrade path is exercised on every CI run (carry-forward from prior sprint
  memory).

These bullets are recorded **defensively** in case a hardening pass later flips
to a numeric `row_version`. They do **not** apply to Phase 1.3 itself, which
ships zero migrations.

### G.3 Backwards-compatibility policy (cite Part C2d)

The Part C2d §E.2 decision is reproduced here only by reference — its full text,
including the DEBT-038 entry and the "tolerate-then-harden" rationale, lives at
`docs/recon/phase-1-3-C2d-backcompat.md`. The migration-section summary:

| Condition (PATCH `/publications/{id}`)             | v1 backend behavior                                              |
|----------------------------------------------------|------------------------------------------------------------------|
| `If-Match` present **and** matches server ETag     | Apply mutation; return new `ETag` header. (Normal path.)         |
| `If-Match` present **and** mismatches              | `412 Precondition Failed` + `PRECONDITION_FAILED` envelope (C2b).|
| `If-Match` **absent**                              | Warn-log; **accept**; proceed without precondition check; return new `ETag`. |

**DEBT-038 (cited from C2d §E.3):** *"PATCH publications tolerates missing
`If-Match` for v1 deploy compat"*. Resolution path: after **two weeks of clean
deploy** with warn-log volume dropped to negligible, flip the absent-header
branch to **`428 Precondition Required`** and update `docs/modules/api.md` to
mark `If-Match` as required.

This document does not re-enumerate DEBT-038's full body — see C2d §E.3 verbatim.

### G.4 Deploy order

Per Part C2d §E.4, the deploy is one-directional and **uncoordinated**:

1. **Backend deploys first.** Ships:
   - `compute_etag(pub)` (`backend/src/services/publications/etag.py`, new pure module).
   - `ETag` header on `GET /api/v1/admin/publications/{id}` and on `PATCH` 200
     responses (C1 §A.5).
   - `If-Match` header acceptance on `PATCH` (C1 §A.6).
   - The tolerate-absent + warn-log branch (C2d §E.2).
   - The `PublicationPreconditionFailedError` exception class wired through
     `register_exception_handlers` (Part C2b envelope).

   At the moment the backend is live, **both** old frontends (no `If-Match`
   echo) and new frontends (echoing `If-Match`) are served correctly. The only
   user-visible effect for old-frontend clients is unchanged behavior; the only
   operator-visible effect is a stream of `warn`-level "PATCH without If-Match"
   log entries that the operator expects and monitors as the rollout progresses.

2. **Frontend deploys second.** Ships:
   - `ETag` capture on `GET` admin/publications responses.
   - `If-Match` echo on every autosave `PATCH` (Part C2c §D.1).
   - The `PRECONDITION_FAILED` branch in `performSave` and the
     `PreconditionFailedModal` (Part C2c §D.5).

   As CDN invalidates and users refresh, the warn-log volume falls.

**No coordinated rollback is needed** — each direction degrades safely (C2d §E.4
table reproduced for the migration audit trail):

| Scenario                                | Behavior                                                                                    |
|-----------------------------------------|---------------------------------------------------------------------------------------------|
| Backend rolled back, frontend new       | New frontend sends `If-Match`; old backend ignores unknown request header per RFC 7230 §3.2.4. PATCH proceeds without precondition check — identical to pre-1.3 behavior. |
| Backend new, frontend rolled back       | Old frontend sends no `If-Match`; new backend takes the tolerate-absent branch. Warn-log fires; PATCH proceeds. (Steady-state rollout window.) |
| Both rolled back                        | Pre-1.3 baseline. No regression.                                                             |
| Both rolled forward                     | Full ETag-guarded path; 412 surfaces only on real concurrent edits (Part C2a §B).            |

### G.5 Why not 428 from day 1

Cited from Part C2d §E.5 — the "strict alternative" was considered and rejected
for v1. The three blockers:

1. **Fleet-wide instantaneous failure.** Per Part C2c §D.1, autosave fires every
   few seconds inside `performSave`. An old tab open across the deploy boundary
   would 428-fail on its very next tick. Multiplied across the open-tab
   population at deploy time, this is a synchronized failure event with no
   genuine conflict driving any of it — a pure rollout artefact.
2. **Modal cannot distinguish rollout from conflict.** The Part C2c modal is
   designed for the conflict case (Reload vs. Save-as-new-draft). Surfacing it
   to a user whose only "sin" is having a pre-deploy tab degrades the modal's
   signal: users trained on rollout-noise modals will dismiss real conflict
   modals reflexively.
3. **428 is a one-way door at the wrong moment.** Once the strict handler is
   live, every pre-deploy tab is broken until manually reloaded. There is no
   operator lever to "soften" the transition — only a backend rollback, which
   throws away the new ETag emission too.

Tolerate-then-harden ships the contract, lets the tab population refresh
naturally, then flips to 428 when the warn-log says it is safe (DEBT-038
resolution path, C2d §E.3 lines 78–80). The eventual end-state is identical to
the strict alternative; only the transition is gentler.

### G.6 Migration audit checklist (closes Section G)

| Item                                                                  | Status     | Source                                          |
|-----------------------------------------------------------------------|------------|-------------------------------------------------|
| New column on `publications`?                                         | ❌ No      | Part A §1.2 (all required columns present); C1 §A.1 line 33 |
| Alembic revision needed for Phase 1.3?                                | ❌ No      | G.2 above                                       |
| Index added/dropped?                                                  | ❌ No      | G.2 #3                                          |
| ENUM modified?                                                        | ❌ No      | G.2 #4                                          |
| Migration teardown convention to remember (if a future v2 needs it)   | ✅ noted   | G.2 (`alembic downgrade base`, `create_type=False`, `checkfirst=True`) |
| Backcompat for missing `If-Match`                                     | ✅ defined | C2d §E.2 / G.3                                  |
| DEBT logged for the eventual hardening                                | ✅ DEBT-038 | C2d §E.3 / G.3                                  |
| Deploy order one-directional, no coordinated rollback                 | ✅ yes     | G.4                                             |
| `docs/modules/api.md` update needed in Phase 1.3?                     | ⚠️ partial | C2d §E.6 — `If-Match` documented as **recommended** in v1; "required + 428" wording lands on DEBT-038 resolution. |
| `docs/MIGRATIONS.md` (or equivalent migration ledger) update needed?  | ❌ No      | G.2 — no migration to record.                   |

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-D2-migration.md
New columns needed: no — id/updated_at/created_at/config_hash all present per A §1.2
Alembic migration needed: no — ETag is derived (C1 §A.1 line 33); no index/enum/FK change
Deploy order: backend first, frontend second
Backcompat: tolerate missing If-Match (warn-log, accept) — DEBT-038 for 2-week hardening to 428
VERDICT: COMPLETE
```

---

**End of Part D2.**
