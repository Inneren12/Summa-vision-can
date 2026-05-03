# Roadmap Dependencies — Phase/PR DAG and Sprint Planning

**Status:** Living document — update on every roadmap change, phase reorder, or new dependency discovered
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Sources:** OPERATOR_AUTOMATION_ROADMAP.md, ROADMAP_v8_FINAL.md, memory items
**Related:**
- `OPERATOR_AUTOMATION_ROADMAP.md` (in repo root) — full phase definitions
- `ROADMAP_v8_FINAL.md` (in repo root) — original roadmap with infrastructure context
- `BACKEND_API_INVENTORY.md`, `FLUTTER_ADMIN_MAP.md`, etc. (in `docs/architecture/`) — what each PR will touch

**Maintenance rule:** any PR completion, phase reorder, or new dependency discovered MUST update this file in the same commit. Drift signal: if memory items reference parallel-track decisions or phase dependencies not reflected here, this file is stale.

## How to use this file

- **Sprint planning:** read §2 status, §3 DAG, §5 parallel opportunities. Pick next item by checking what's unblocked.
- **Parallel work decisions:** §5 lists which PRs can run in parallel. §6 lists merge conflict risk zones.
- **Critical path:** §4 shows shortest sequence to launch. Items off critical path can flex on timing.
- **Cross-references to architecture MD:** when a PR touches an area covered by an architecture MD, the table cell links there.

## 2. Phase status (as of 2026-04-26)

### Completed phases

| Phase | Status | Notes |
|---|---|---|
| 0 | ✓ COMPLETE | Foundation, dev environment, CI |
| A (Stage A) | ✓ COMPLETE 2026-04-26 | All launch-blocker DEBTs resolved (008/016/019/020/007/021) |
| B (B-2 → B-4) | ✓ COMPLETE | With fix rounds |
| C (C-1 → C-5) | ✓ COMPLETE | With fix rounds |
| D (D-1 → D-4) | ✓ COMPLETE | With fix rounds |
| Design System v3.2 | ✓ COMPLETE | Next.js CSS tokens + Flutter SummaTheme |
| METR Calculator | ✓ COMPLETE | Backend + D3.js frontend |
| D-5 verification | ✓ COMPLETE | Pre-launch scripts |
| Editor Stages 1-2 | ✓ COMPLETE | Strict-template architecture, 13 blocks, 11 templates |
| 1.5 Visual Data Diffing | ✓ COMPLETE 2026-04-26 | Backend (PR-39/40/41) + frontend (PR #171, 7-round fix saga) |

### Active / next

| Phase | Status | Effort | PRs | Notes |
|---|---|---|---|---|
| 1.3 Optimistic Concurrency (ETag+412) | IN-PROGRESS — pre-recon | S | 1 | No deps; pre-recon split 11 micro-prompts |
| 2.5a Exception Inbox v1 (Flutter — failed exports + zombie jobs) | IN-PROGRESS — discovery | M | 2 | No deps; discovery split 5 micro-prompts; blocked on Q-C decision |
| 2.5b Exception Inbox deferred (stale bindings + missing post URLs + validation blockers) | DEFERRED | S | 1+ | Blocked on Phase 2.3 (post_ledger) + Phase 3 (Binding entity); see DEBT-040 |
| 3.1c Singular admin resolve endpoint | IN-PROGRESS | S | 1 | Builds on 3.1aaa (value cache) + 3.1b (mappings CRUD); BLOCKER-1 Option B (service-derived coord); F-fix-3 missing-observation contract. Drift docs: `docs/api.md`, `BACKEND_API_INVENTORY.md`. |
| 3.1d Snapshot persistence + staleness | PENDING | S | 1 | Depends on 3.1c — uses `mapping_version` echo on `ResolvedValueResponse` for staleness comparison on bound publication blocks. |

### Pending

| Phase | Effort | PRs | Depends on |
|---|---|---|---|
| 2.1 Multi-preset ZIP export | M | 2-3 | none |
| 2.2.0.5 Backend slug infrastructure (column, generator, migration, schema, immutability) | S | 1 | 2.2.0 (lineage_key) |
| 2.2 Publish Kit Generator | M | 2 | 2.1, 2.2.0.5 |
| 2.3 UTM-to-lineage attribution | S | 1 | 2.2 |
| 2.4 Draft Social Text (Gemini Flash) | S | 1 | 2.2 |
| Editor Stage 3 | M | 2-3 | none (parallel to 1.x) |
| Editor Stage 4 | L | 5-8 | Stage 3 |
| Phase 3 (AI Brain & Visual Engine) | L | many | Phase 2 complete |
| Phase 4 (operational resilience) | M | several | Phase 3 critical paths |
| Phase 5 (lead funnel scale) | M | several | Phase 4 |

## 3. Dependency DAG

ASCII DAG (top → bottom = ordering; arrows show "depends on"):

```
1.3 Optimistic Concurrency  (no deps)
  └─→ Phase 1.x integration tests harden after 1.3 lands

2.5a Exception Inbox v1      (no deps; failed exports + zombie jobs)
  └─→ Phase 4 operational dashboard reuses

2.5b Exception Inbox deferred (stale bindings + missing post URLs + validation blockers)
  └─ blocked by: Phase 2.3 (post_ledger) + Phase 3 (Binding entity)
  └─ validation-blocker entity ownership TBD (see DEBT-040)

2.1 Multi-preset ZIP         (no deps)
  └─→ 2.2 Publish Kit Generator
        ├─→ 2.3 UTM-to-lineage attribution
        └─→ 2.4 Draft Social Text (Gemini Flash)

Editor Stage 3               (no deps)
  └─→ Editor Stage 4         (large, multi-PR)

Phase 3 (AI Brain & Visual Engine)
  └─ blocked by: Phase 2.1-2.4 complete
  └─→ Phase 4

Phase 4 (operational resilience)
  └─ blocked by: Phase 3 critical paths
  └─→ Phase 5

Phase 5 (lead funnel scale)
  └─ blocked by: Phase 4
```

### Key facts

- **No cycles.** All dependencies are forward-only.
- **No hidden deps.** Roadmap §6 explicitly defers items that don't fit (CRDT, command palette, cross-family auto-resize) — they are NOT silent prerequisites.
- **Editor Stage 3 + 1.x phases are parallel-safe** at the tier-2 level (different code zones), but `meta.history` schema may evolve.
- **Phase 1.3 → Phase 2 ETag-inheritance rule** (added by Phase 1.3 impl): any Phase 2 admin PATCH endpoint that mutates `Publication` rows MUST inherit the ETag-guard contract from `ARCHITECTURE_INVARIANTS.md` §7 OR document an explicit exemption in that section. New admin PATCH endpoints on other versioned ORM models are encouraged (not yet required) to inherit the same contract — see `_DRIFT_DETECTION_TEMPLATE.md` Section D2 for the parity check.

## 4. Critical path

### Shortest sequence to launch (after Stage A)

```
1.3 (S, 1 PR)
  → 2.1 (M, 2-3 PR)
  → 2.2 (M, 2 PR)
  → 2.3 (S, 1 PR) + 2.4 (S, 1 PR)  [parallel after 2.2]
```

Estimated PR count on critical path: **6-8 PRs minimum**.

### Off-critical-path opportunities

- **2.5a Exception Inbox** — operational quality but not launch-blocking
- **Editor Stage 3 + 4** — improves authoring UX, not launch-blocking
- **Phase 4 + 5** — post-launch hardening and growth

If timeline matters, focus on critical path first. Stage 3/4 and 2.5 can flex.

## 5. Parallel opportunities

### Currently safe to run in parallel

| Track A | Track B | Why safe |
|---|---|---|
| 1.3 (backend PATCH + Next.js editor autosave) | 2.5 (Flutter admin) | Different code zones — no merge conflicts |
| 1.3 | Editor Stage 3 | Editor S3 is review/comments, separate from autosave error path |
| 2.5 | Editor Stage 3 | Flutter admin vs Next.js editor — disjoint |
| 2.1 | 2.5 | Editor export pipeline vs Flutter — disjoint |
| 2.1 | Editor Stage 3 | Same Next.js editor — RISK, see §6 |

### Currently NOT safe to run in parallel

- **2.1 + 2.2:** 2.2 depends on 2.1 ZIP foundation
- **2.3 + 2.4 vs 2.2:** both depend on 2.2 publish kit
- **Editor Stage 4 vs anything in Stage 3:** Stage 4 builds on Stage 3 architecture; concurrent work has high merge conflict risk
- **Phase 3 vs Phase 2 anything:** Phase 3 binding/AI work assumes 2.x is settled

### Two-agent rule

**No more than 2 active agents** working on the project simultaneously. Memory item: duplicate PR anti-pattern (parallel agents both completing same task → conflict on second). Even with disjoint zones, coordination overhead grows quadratically with agent count.

## 6. Merge conflict risk zones

When two PRs target the SAME area, conflicts are likely. Currently identified zones:

### Editor (Next.js `frontend-public/src/components/editor/`)
- Stage 3 + Stage 4 concurrent work → high risk
- Stage 3 + 2.1 export pipeline → moderate (export is in same module tree, but separate files)
- 1.3 (autosave error UX) + Stage 3 (review state) → low (different concerns)

### Backend admin endpoints (`backend/app/api/admin/`)
- 1.3 PATCH + 2.5a Exception Inbox endpoint additions → low (different endpoints)
- Phase 1.x + Phase 2.x → low while disjoint, watch when 2.5 needs aggregation endpoint

### Flutter admin (`frontend/`)
- 2.5a Exception Inbox + future Phase 4 ops dashboard → moderate (overlap on /jobs surface)

### Architecture MD (`docs/architecture/`)
- Multiple PRs updating same MD in same time window → trivial conflicts (resolve quickly)
- Drift detection per architecture MD maintenance rules will catch these

## 7. Sprint planning checklist

When picking next sprint, walk this checklist:

1. **Refresh state.** Re-read DEBT.md + this file's §2 status. Memory drifts.
2. **Identify candidates.** §5 unblocked items.
3. **Critical path priority.** Items on §4 critical path > off-path items.
4. **Parallel decision.** If founder has bandwidth for 2 tracks, pick from §5 safe pairs. Otherwise serial.
5. **Architecture MD review.** Each candidate PR — what architecture MD will be updated? List it before sprint starts.
6. **Discovery first.** Items with no recent discovery require pre-recon read of relevant architecture MD + targeted code grep where MD has gaps.
7. **Open questions.** Surface founder questions before pre-recon, not in middle.

Memory item: "Always re-verify DEBT.md state at sprint planning, not just handoff/memory. handoff_doc + memory drift quietly."

## 8. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from OPERATOR_AUTOMATION_ROADMAP.md + memory |
| 2026-04-27 | Phase 1.3 impl | §3 Key facts | Added Phase 1.3 → Phase 2 ETag-inheritance rule. |
