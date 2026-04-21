# Project Status

## Étape 0: Infrastructure Foundation

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| 0-1 | Docker + Compose + Health + MinIO | 🔄 Fixing | — |
| 0-2 | Job Model + Typed Payloads + Repository | 🔄 | 0-1 |
| 0-3 | Job Runner + Dedupe + Retry | ✅ | 0-2 |
| 0-4 | AuditEvent Foundation | 🔄 | 0-2 |
| 0-5 | Backup + Alerting Baseline | 🔄 | 0-1 |

**Étape 0 status:** All PRs merged. Backup script operational.
Infrastructure foundation: Docker, persistent jobs,
audit events, backup, monitoring. Production hardening items tracked in DEBT.md.

## Étape A: Data Engine

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| A-1 | CubeCatalog Model + Bilingual FTS | 🔄 | Étape 0 |
| A-2 | CubeCatalogRepository | 🔄 | A-1 |
| A-3 | CatalogSyncService | 🔄 | A-2 |
| A-4 | Cube Search API | 🔄 | A-2, A-3 |
| A-5 | DataFetchService (Polars-first) | 🔄 | A-1, A-4 |
| A-6 | DataWorkbench (Pure Polars) | 🔄 | — |
| A-7 | Transform API | 🔄 | A-5, A-6 |

**Étape A: all PRs merged.** Production hardening ongoing. Data Engine: catalog search + Polars fetch + workbench transforms + preview API.

## Previously Completed

### Sprint 1: StatCan ETL Pipeline ✅
| PR | Title | Status |
|----|-------|--------|
| PR-1 | FastAPI Base + HealthCheck | ✅ |
| PR-2 | Maintenance Guard (Timezone) | ✅ |
| PR-3 | Rate Limiter (Token Bucket) | ✅ |
| PR-4 | StatCan HTTP Client | ✅ |
| PR-5 | Pydantic Schemas | ✅ |
| PR-6 | ETL Service + NaN Handling | ✅ |

### Phase 1.5: Persistence Layer ✅
| PR | Title | Status |
|----|-------|--------|
| PR-39 | Database Schema & Models | ✅ |
| PR-40 | Repository Layer | ✅ |
| PR-41 | Public Gallery API | ✅ |

### Phase 2.5: Security ✅
| PR | Title | Status |
|----|-------|--------|
| PR-42 | Auth Middleware | ✅ |

### Foundation Fixes ✅
| PR | Title | Status |
|----|-------|--------|
| FIX-01..08 | Foundation repairs | ✅ |
| 0-1 | Docker + Compose + Health + MinIO | ✅ |

## Étape C: Admin Panel (Flutter)

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| C-1 | Cube Search Screen | 🔄 | A-4, PR-20, PR-46 |
| C-2 | Data Preview | 🔄 | C-1, A-5 |
| C-3 | Chart Config + Generation Screen | 🔄 | C-2, B-4 |
| C-4 | Jobs Dashboard Screen | 🔄 | C-3, 0-2, 0-3 |
| C-5 | KPI Dashboard Screen | ✅ | C-3, 0-4 |

**Étape C status:** All PRs complete. ✅

**Étape C-4:** JobsDashboardScreen with filter bar (job type dropdown, status chips), summary stats bar (queued/running/success/failed/stale counts), scrollable job card list, job detail bottom sheet, retry button for retryable failed jobs, stale/zombie warning for jobs running >10 min, auto-refresh every 10s, MockInterceptor fixtures (8 sample jobs), freezed models, Riverpod providers, widget + model tests. Backend `POST /api/v1/admin/jobs/{job_id}/retry` endpoint with 404/409 handling.

**Étape C-1:** CubeSearchScreen with debounced search, CubeSearchTile, CubeDetailScreen stub, MockInterceptor fixtures, AppDrawer navigation, GoRouter routes, freezed models, Riverpod providers, widget + model tests.

**Étape C-3:** ChartConfigScreen with chart type / size preset / background category selectors, title field with validation, async generation flow (submit → poll → result), inline image preview with download button, MockInterceptor polling simulation, widget + model tests. Wires C-2 "Generate Chart" button to /graphics/config route.

**Étape C-5:** KPI Dashboard — backend `GET /api/v1/admin/kpi?days=30` aggregation endpoint (KPIService, KPIResponse schema). Flutter KPIScreen with period selector (7/30/90 days), summary cards (publications, leads, downloads, job success), download funnel visualization, lead breakdown by category, job failure chart, system health row, auto-refresh every 60s. MockInterceptor fixture, freezed model, Riverpod providers, widget + model tests.

## Étape B: Visual Engine

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| B-1 | SVG Generator → Real Data | 🔄 | A-5, A-6 |
| B-2 | Template Backgrounds | 🔄 | — |
| B-3 | End-to-End Pipeline | 🔄 | B-1, B-2 |
| B-4 | Admin Graphics API + Batch CLI | ⬜ | B-3 |
| B-5 | JSON/CSV Upload → Graphic Generation | ✅ | B-4 |

**B-5 status:** Admin can now feed arbitrary JSON/CSV into the same
graphic pipeline without going through a StatCan cube. Backend exposes
`POST /api/v1/admin/graphics/generate-from-data` which serializes rows
to a temporary Parquet under `temp/uploads/` and enqueues the existing
`graphics_generate` job — pipeline is *unchanged*. Flutter admin adds a
"StatCan Cube / Upload Data" toggle, a `DataUploadWidget` (JSON + CSV
parsing, dtype inference), and an editable `EditableDataTable` preview.
Temp Parquet cleanup tracked as DEBT-021.

## Étape D: Lead Capture & Download

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| D-0a | EmailService Interface | ✅ | — |
| D-0b | TurnstileValidator | ✅ | — |
| D-0c | DownloadToken Model | ✅ | Étape 0 |
| D-1 | Public Gallery + Individual Page | ✅ | B-4 |
| D-2 | Lead Capture + Secure Download | ✅ | D-0a, D-0b, D-0c |
| D-3 | B2B Scoring + Slack Notifications | ✅ | D-2 |
| D-4 | Partner Page — Media Kit | ✅ | D-3 |

## Étape E: Editor (Authoring Workflow)

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| E-3-1 | Stage 3 Domain Model Consolidation (`doc.review`, schema v2) | 🔄 | — |
| E-3-2a | Stage 3 Reducer Actions — Workflow State Machine | 🔄 | E-3-1 |
| E-3-2b | Stage 3 Reducer Actions — Comments Subsystem | 🔄 | E-3-2a |
| E-3-3 | Stage 3 Review Panel UI | 🔄 | E-3-2b |
| E-3-4 | Stage 3 Backend Persistence + Cleanup | 🔄 | E-3-3 |
| E-3-5 | Stage 3 End-to-End Tests | ⬜ | E-3-4 |
| E-4-0 | Stage 4 Task 0 — Editor Wire-Up (Next.js admin routes) | ✅ | E-3-4 |
| E-4-1 | Stage 4 Task 1 — Click-to-select + UX polish | ✅ | E-4-0 |
| E-4-2 | Stage 4 Task 2 — Autosave + recovery | ✅ | E-4-0 |
| E-4-3 | Stage 4 Task 3 — Deterministic export (font-load gate) | ✅ | E-4-2 |
| E-4-4 | Stage 4 Task 4 — Debug overlay (dev tooling) | ✅ | E-4-1 |
| E-4-5 | Stage 4 Task 5 — WCAG AA contrast validator | ✅ | E-4-0 |
| E-4-6 | Stage 4 Task 6 — Font lifecycle hardening (late-subset closure) | ✅ | E-4-3 |
| E-4-9a | Stage 4 Task 9a — Perf: instrumentation + editor memoization | ✅ | E-4-6 |
| E-4-10b | Stage 4 Task 10b — Production polish (error boundaries, console, FastAPI docs) | ✅ | E-4-9a |
| E-4-9b | Stage 4 Task 9b — Public gallery perf: DownloadModal dynamic import + InquiryForm deferred hydration | ✅ | E-4-9a |

- E-4-6 follow-up (fonts.load text argument): pending human commit
- E-4-10a (production blockers: admin auth + InquiryForm CAPTCHA): separate PR, may land before or after 10b

**E-4-9b status:** `DownloadModal` split into a trigger
(button + `useState` + `next/dynamic` import) and a deferred
`DownloadModalContent` chunk that owns the form, `react-hook-form`,
the `zod` resolver, and `TurnstileWidget`. Homepage hydration cost
of the heavy form code collapses from per-card to zero until first
open; subsequent opens across any card reuse the chunk. `InquiryForm`
on `/partner-with-us` wrapped in `dynamic(..., { ssr: true })` so the
form still server-renders for SEO / no-JS while client hydration and
the RHF bundle defer off the critical path. `@next/bundle-analyzer`
wired as a devDep; `npm run analyze` runs a webpack build gated on
`ANALYZE=true` (cross-env for Windows portability) and writes reports
to `.next/analyze/`. The `--webpack` flag is required because
`@next/bundle-analyzer` is not yet compatible with Turbopack. No
changes to form logic, submit behaviour, or Turnstile integration.

**E-3-4 status (in flight):** Backend-only persistence PR. Adds a
nullable `Publication.review` Text column (Alembic migration
`f2a7d9c3b481`), a `ReviewPayload` schema, a workflow → status sync
rule in the PATCH router, five new `PUBLICATION_WORKFLOW_*` audit
event types, and augments `publish` / `unpublish` to mirror transitions
into `review.workflow`. Closes DEBT-024 (cosmetic rename
`validateDocumentShape` → `assertCanonicalDocumentV2Shape`) and removes
the demo workflow switcher from `infographic-editor-stage3b-v2.jsx`.
Stage 3 is functionally closed pending a consumer wire-up — no Next.js
admin route or Flutter integration is in scope; PR 4 establishes the
contract, a follow-up wires a consumer.

**E-3-1 status:** Data-layer only. `CanonicalDocument` now carries a `review`
section (workflow + workflow history + comments); root-level `workflow` is
moved under `review.workflow`; `schemaVersion` bumped 1 → 2 with a single
`v1 → v2` migration in `registry/guards.ts`. Renamed legacy `HistoryEntry`
(edit log) to `EditHistoryEntry` so the name is free for the new
`WorkflowHistoryEntry` type. Migration coverage lands in
`src/components/editor/__tests__/migrations.test.ts`. No reducer actions or UI
changed in this PR.

**E-3-2a status:** Workflow state machine landed in the reducer. Seven new
actions (`SUBMIT_FOR_REVIEW`, `APPROVE`, `REQUEST_CHANGES`, `RETURN_TO_DRAFT`,
`MARK_EXPORTED`, `MARK_PUBLISHED`, `DUPLICATE_AS_DRAFT`) gated by
`canTransition` in `store/workflow.ts`. Permission gate is now two-axis:
existing `mode` axis (template|design) AND new `workflow` axis; both must
pass for any mutation to land. Copy-edit lockdown enforced in `in_review`.
Read-only transitions clear undo/redo. Deterministic timestamps via injected
`TimestampProvider`. Closes `DEBT-022` (validator unification) and the
`WorkflowHistoryEntry` half of `DEBT-023` (element shape validation). Adds
`DEBT-024` (cosmetic rename of `validateDocumentShape`). Comments subsystem
deferred to E-3-2b; UI to E-3-3.

**E-3-2b status:** Comments subsystem landed. Six new reducer actions
(`ADD_COMMENT`, `REPLY_TO_COMMENT`, `EDIT_COMMENT`, `RESOLVE_COMMENT`,
`REOPEN_COMMENT`, `DELETE_COMMENT`) implemented in `store/comments.ts` and
delegated from the reducer. Comment mutations live OUTSIDE the undo/redo
timeline — they do not call `push`, do not touch `undoStack`/`redoStack`,
and do not perturb `_lastAction`. Audit trail for ADD/REPLY/RESOLVE/REOPEN/
DELETE lands in `doc.review.history` (EDIT is intentionally unaudited).
New `canComment` dimension in `WORKFLOW_PERMISSIONS` keeps comments open
through `in_review` and freezes them in `approved|exported|published`.
Ownership check gates EDIT/DELETE on `comment.author === actor`; RESOLVE
and REOPEN are open to any commenter. `validateImportStrict` now
deep-validates every `Comment` element and enforces referential integrity
for `parentId`. Closes `DEBT-023`. UI surface (indicators, NoteModal,
Review panel) deferred to E-3-3.

**E-4-0 status (full close):** Wire-up landed on
`claude/wire-infographic-editor-9w3wr` (PR #101, merged) and the four
review blockers closed on follow-up branch
`claude/close-infographic-blockers-wkjVX`. New routes `/admin`
(publication list) and `/admin/editor/[id]` (editor page) under
`frontend-public/src/app/admin/`. Browser code talks to the backend
admin API via a same-origin Next.js proxy at
`src/app/api/admin/publications/[...path]/route.ts`; the proxy injects
`X-API-KEY` server-side from `ADMIN_API_KEY` (server-only env var,
never bundled to client). `InfographicEditor` gains `initialDoc?` and
`publicationId?` props; `initState` accepts an optional seed doc.
Ctrl+S PATCHes through `updateAdminPublication`; the legacy local-JSON
download on save is removed.

**E-4-2 status (full close):** Autosave landed on
`claude/stage4-task2-autosave`; review-fix close on
`claude/stage4-task2-fix-close-sxKZr`. Debounced 2000ms `useEffect` on
`state.doc` reference; navigational actions preserve identity so they
don't reset the timer. Reuses the Task 0 `SAVED_IF_MATCHES` /
`SAVE_FAILED` channel verbatim — no reducer changes. New local
`SaveStatus` enum (`idle | pending | saving | error`) drives a
four-state `SaveStatusIndicator` in TopBar (amber/red dot with CSS
keyframe pulse for `saving`). Exponential-backoff retry (2s/4s/8s/16s,
4 attempts) scheduled via an orthogonal effect watching
`state.saveError` + a `saveFailureGen` counter (required because
identical error strings would otherwise leave the dep array stable).
NotificationBanner save-error branch extended inline with live
countdown + "Retry now" button. `beforeunload` guard covers the 2s
window between an edit and the next scheduled save. Review-fix close
resolves three blockers: **B1** 404s no longer schedule auto-retries
(local `canAutoRetryRef` flag drives the retry-effect guard; zero
reducer changes); **B2** the debounce effect short-circuits while
`state.saveError` is set, so the retry effect is the sole save
orchestrator during error-state and edit-during-error produces a
single scheduled save at `delay[0]=2000ms` instead of two racing
timers; **B4** the debounce callback re-arms itself when `savingRef`
is held by an in-flight PATCH (previously a slow-network PATCH could
leave subsequent edits unsaved until a mutating action or Ctrl+S).
Test files: `autosave.test.tsx` (21 tests; +6 from close, +1 from B5),
`save-status-indicator.test.tsx` (6 tests), `_admin-api-mock.ts`
helper; extended `error-channels.test.tsx` with 5 retry-UX tests.
605 tests passing.

- B5 follow-up (dismiss bypass): debounce effect guard on
  `canAutoRetryRef.current`. Dismissing a 404 banner clears
  `state.saveError` but leaves `dirty = true`; before B5 the debounce
  effect re-ran on the `saveError → null` transition and scheduled a
  fresh 2s PATCH that immediately 404'd. The new guard (after the
  `state.saveError` check, before the `!dirty` check) short-circuits
  when the terminal flag is still set. Zero reducer / schema / API /
  banner changes. +1 test in the terminal-errors describe block.

**E-4-5 status:** WCAG AA contrast validator landed on
`claude/contrast-matrix-validator-thFnP`. New pure-function validator
`validateContrast(doc)` in `src/components/editor/validation/contrast.ts`
implements WCAG 2.1 relative-luminance math from scratch (no library),
maps each text-bearing block type to its renderer's text-colour choice
via `getBlockTextColor`, and iterates visible blocks × document
palette × background base (and gradient lightest-stop where applicable).
`ValidationResult` widened with `contrastIssues: ContrastIssue[]`; the
structured issues feed a new per-block contrast surface in Inspector
while string summaries continue flowing into existing `errors`/`warnings`
buckets → TopBar counts → `canExp` export gate. New `BG_META` registry
parallel to `BGS` exposes data-only `{ base, lightestStop?, isGradient }`
per background id; parity with `BGS` enforced by test. Crude YIQ
heuristic at `validate.ts:115-122` deleted — smoking-gun test ensures
`"Primary color may be too dark on dark bg"` warning can never re-appear.
Large-text WCAG threshold (3:1) applied to `hero_stat` and
`headline_editorial`; everything else uses 4.5:1. Gradient handling
emits error on base-stop failure and warning on lightest-stop failure.
Two design tokens tuned to pass validation: `TK.c.txtM` (#5C6370 →
#7A818C; 3.22:1 → 4.96:1) and `pal.neg` across all six palettes
(#E11D48 → #F43F5E; 4.14:1 → 5.60:1). Historical note filed in DEBT.md.
36 new tests across `contrast.test.ts`, `backgrounds-meta.test.ts`,
`inspector-contrast.test.tsx`, plus 4 contrast-integration cases
appended to `validate.test.ts`. 638 tests passing.

Follow-up close resolves DEBT-026: opaque `document_state` column on
`Publication` (migration `a3e81c0f5d21`) carries the full
`CanonicalDocument` as JSON text; persistence seam
(`src/components/editor/utils/persistence.ts`) prefers it on hydrate
and falls back to the legacy field-level path for rows created before
the column existed. B2 stale-save fixed by snapshot-based
`SAVED_IF_MATCHES` — the reducer clears `dirty` only when
`state.doc === snapshotDoc`. B3 workflow demotion on legacy
PUBLISHED rows fixed by `deriveWorkflowFromStatus`. B4 separates
`saveError` from `importError` in reducer state; NotificationBanner
priority is `saveError > importError > _lastRejection > warnings`.
Entry point established for E-4-1 (click-to-select).

**E-3-3 status (in flight):** Stage 3 UI integration. Six new editor
components: `NoteModal` (the sole modal input surface; replaces any
prospective `window.prompt` for comment text and transition notes;
hand-rolled with focus trap + restore + Escape + Ctrl+Enter),
`StatusBadge` (compact in TopBar, regular in ReviewPanel header),
`RightRail` (tabbed parent for Inspector + Review), `ReviewPanel`
(workflow header with `availableTransitions`, threads with reply /
resolve / edit / delete affordances and tombstone rendering, history
list with reverse-chrono ordering and collapse-after-6), `ReadOnlyBanner`
(above-canvas notice when `isReadOnlyWorkflow(...)`, with one-click
"Return to draft" when allowed), and `NotificationBanner` (priority-
resolved in-app banner consuming `state._lastRejection` and the existing
import error/warning state). TopBar and LeftPanel pick up small
modifications: `<StatusBadge>` after the template chip; `unresolvedByBlock`
memo + count pill in block rows. `index.tsx` now computes
`effectivePerms` (mode × workflow overlay) so disabled buttons never
silently dispatch into a reducer rejection. Canvas stays clean — no
overlay layer (deferred). Editor test suite passes with ≥ 95% line
coverage on every new Stage 3 component (NoteModal, StatusBadge,
RightRail, ReviewPanel, ReadOnlyBanner, NotificationBanner) — see CI
for exact counts.

## Theme #2: Marginal Tax Rate Meatgrinder

| PR | Title | Status | Dependencies |
|----|-------|--------|--------------|
| T2-BE | METR Calculator Backend — Engine, API, Card Data | ✅ | — |
| T2-FE | METR Interactive Calculator (Next.js) | ⬜ | T2-BE |

**T2-BE:** Pure-function METR calculation engine (federal tax, CPP/CPP2, EI, provincial tax for ON/BC/AB/QC, CCB, GST/HST Credit, CWB, OTB/BCF/ACFB/QC solidarity). Three public API endpoints: `/calculate`, `/curve`, `/compare`. Signal card data generator (4 cards: hero KPI, waterfall, provincial bars, slope). 90 tests passing. Tax year: 2025.
