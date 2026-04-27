# Operator Phase Status

**Purpose:** single source of truth for the `OPERATOR_AUTOMATION_ROADMAP.md` phase series (1.x, 2.x, 3.x, 4.x, 5.x). Distinct from `SPRINT_STATUS.md`, which tracks the older PR-numbered phases (Phase 0 ETL, Phase 1 ETL, Phase 1.5 backend persistence PR-39/40/41, etc.).

**This file is the source of truth.** Every roadmap-phase shipping PR must update this file in the same commit. Status cells without a corresponding git anchor (PR# or commit hash) are not valid.

**Maintenance:**
- Status changes happen in the same commit as the shipping code. No separate "update tracker" PRs.
- Founder approves status flips before merge.
- Cross-references with `OPERATOR_AUTOMATION_ROADMAP.md` (the plan), `DEBT.md` (the debt registry), and `ROADMAP_DEPENDENCIES.md` (the dependency map) — but those files do not own status. This file does.

---

## Status legend

- ✅ **Complete** — code merged, tests passing, architecture-MD docs updated. PR# or commit hash recorded.
- 🔄 **In progress** — implementation started, branch open. PR# or branch name recorded.
- ⏳ **Next** — top of queue, not yet started.
- 📅 **Scheduled** — future phase, dependencies not yet met.
- 🚧 **Blocked** — dependency unresolved or external blocker. Reason recorded.
- 📅 **Manual** — non-code task (content population, founder decision, etc.). 0 PRs.
- ❌ **Cancelled** — formally dropped from scope. Reason recorded.

---

## Phase 1 — Immediate leverage

| # | Item | Status | Anchor | Notes |
|---|---|---|---|---|
| 1.1 | Clone from Published | ✅ Complete | PR #165 (merge `02d2532`, branch `codex/implement-clone-from-published-publication`) | Clone endpoint at `cloneAdminPublication` with new lineage + `cloned_from_publication_id` FK. Used as fork-path basis in 1.3. |
| 1.2 | Golden Example drafts | 📅 Manual | — | Stage C content task — founder selects 3 graphics from launch batch, clones via 1.1, renames `TUTORIAL: <template>`. 0 PRs. Gated on launch batch creation. |
| 1.3 | Optimistic Concurrency (ETag + 412) | ✅ Complete | PR #206 impl (`89fd418`); polish PRs #207 (`f92135f`), #208 (`a5f4558`), #209 (`3a8799b`) all merged | Strong ETag + If-Match + 412 PRECONDITION_FAILED + two-button modal (Reload + Save-as-new-draft) + fork-path + 'conflict' save status. ARCHITECTURE_INVARIANTS.md §7 filled. DEBT-041/042/043. Polish round merged via PR #209. |
| 1.4 | Platform Crop Zone overlays | ✅ Complete | PR #167 (merge `6558ff6`, branch `codex/implement-crop-zone-overlays`); commits `8216ce7` (feat), `65347a6` (fix) | Editor preview overlay toggle + `cropZones.ts` config + renderer/overlay.ts + TopBar toggle. DEBT-036 logged for dimension verification follow-up. |
| 1.5 | Visual Data Diffing in Flutter `/data/preview` | ✅ Complete | PR #171 (merge `eb03022`, branch `claude/add-cube-diff-service`); commits `90952ab` (feat), `a672772` (fix), `f968c4c` / `2086af3` (tests) | `cube_diff_service.dart` + `data_preview_providers.dart` + `data_preview_screen.dart` under `frontend/lib/features/data_preview/{application,data,domain,presentation}`. `ROADMAP_DEPENDENCIES.md:36` confirms COMPLETE 2026-04-26 (backend PR-39/40/41 + frontend PR #171, 7-round fix saga). |
| 1.6 | Right-click Context Menus in Editor | 🔄 In progress | branch `claude/add-context-menus-kf2rk` | Right-click on a block in Canvas opens Lock / Hide / Duplicate / Delete menu; matching Cmd/Ctrl+L/H/D + Delete shortcuts; non-empty Delete prompts confirm modal; new `block.locked` instance flag (additive, no schemaVersion bump); reducer actions `TOGGLE_LOCK`, `DUPLICATE_BLOCK`, `REMOVE_BLOCK` integrated with permission gate + 800ms history batching. Awaiting PR# / merge. |

**Phase 1 DoD verification:** see `OPERATOR_AUTOMATION_ROADMAP.md` Phase 1 DoD list. Phase 1 closes when all 6 items above are ✅ or 📅 Manual (per scope).

---

## Phase 2 — Distribution & observability

Per `OPERATOR_AUTOMATION_ROADMAP.md` Phase 2 table. Items will be filled in when Phase 2 work begins. Until then, this section says "Not yet started."

| # | Item | Status | Anchor | Notes |
|---|---|---|---|---|
| 2.1 | Multi-preset ZIP export (client-side fflate) | ⏳ Not yet started | — | — |
| 2.2 | Publish Kit Generator (distribution.json in ZIP) | 📅 Scheduled | — | Depends on 2.1 |
| 2.3 | Post URL ledger | ⏳ Not yet started | — | Phase 2.5b deferred row types depend on this — see DEBT-040 |
| 2.5 | (Already shipped 2.5a — Flutter Exception Inbox) | 🔄 Partial — 2.5a shipped, 2.5b deferred | PR #205 (2.5a) | 2.5b blocked on Phase 2.3 + Phase 3 entities — tracked in DEBT-040 |

(Other Phase 2 items added when their numbering is finalised in subsequent roadmap revisions.)

---

## Phase 3+ — Future phases

Filled in as phases are entered. Currently:

| Phase | High-level scope | Status |
|---|---|---|
| Phase 3 | Binding entity (operator data ↔ block bindings) | 📅 Scheduled |
| Phase 4 | Operational resilience | 📅 Scheduled |
| Phase 5 | Lead funnel scale | 📅 Scheduled |

---

## Cross-reference: legacy phase numbering

The OPERATOR_AUTOMATION_ROADMAP series above is **distinct** from the older PR-numbered system tracked in `SPRINT_STATUS.md` and `summa-vision-handoff-2026-04-24.md`:

- Old "Phase 0" / "Phase 1" — backend ETL (StatCan, CMHC scrapers). Tracked in `SPRINT_STATUS.md`. Status: ✅ Complete.
- Old "Phase 1.5" — backend persistence (PR-39/40/41 — models, repos, public gallery API). Tracked in `summa-vision-handoff-2026-04-24.md` line 20. Status: ✅ Complete.
- Old "Phase 2" — AI Brain & Visual Engine (PR-14/47 LLM Interface). Status: ⏳ Next per old roadmap, but blocked by current operator-roadmap focus.

The numbering collision (operator roadmap "Phase 1.5" = Flutter data diffing; old roadmap "Phase 1.5" = backend persistence) is a known source of confusion. **When in doubt, this file refers to the operator-roadmap series** unless explicitly prefixed `legacy:` (e.g. `legacy: Phase 1.5 PR-41`).

---

## Maintenance log

| Date | Phase touched | Anchor | Notes |
|---|---|---|---|
| 2026-04-27 | initial | — | File created. Initial status determined by git-log + codebase fingerprint scan (per `phase-1-status-check.md`). |
| 2026-04-27 | 1.6 → 🔄 In progress | branch `claude/add-context-menus-kf2rk` | Implementation landed: BlockContextMenu + DeleteConfirmModal components; Block.locked schema field (additive); TOGGLE_LOCK / DUPLICATE_BLOCK / REMOVE_BLOCK reducer actions; Cmd/Ctrl+L/H/D + Delete keyboard wiring through `shouldSkipGlobalShortcut`; reducer + component + integration tests (32 new tests, 800/800 suite green); EN+RU i18n parity preserved at 320 keys each. PR # to be assigned on push. |
