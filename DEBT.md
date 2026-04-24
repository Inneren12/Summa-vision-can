# Technical Debt Registry

> Source of truth for known technical debt.
> Maintained per-PR: creating debt -> add entry; resolving -> move to Resolved.

## Format

| Field | Description |
|-------|-------------|
| **ID** | `DEBT-NNN` (sequential, never reused) |
| **Source** | PR number or review that identified it (e.g. `PR #16 review`, `Roadmap R18`) |
| **Added** | Date added (YYYY-MM-DD) |
| **Severity** | `critical` / `high` / `medium` / `low` |
| **Category** | `architecture` / `testing` / `security` / `ops` / `code-quality` |
| **Status** | `active` -> confirmed, needs work; `accepted` -> known, deferred intentionally; `in-progress` -> being fixed |
| **Description** | Factual statement of what the debt IS (not hypotheses) |
| **Impact** | What breaks or degrades if not fixed |
| **Resolution** | Concrete action to resolve |
| **Target** | Specific PR, etape, or milestone |

Rules:
- Every entry must be a **verified fact**, not a hypothesis.
- Do NOT add speculative or unverified items -> verify first, then add.
- Backlog features and future enhancements go in ROADMAP, not here.
- When resolving: move entry to Resolved table with PR link and date.
- When updating severity/target: edit in-place and append a changelog
  line at the bottom of the entry:
  `> Updated YYYY-MM-DD: severity high->medium, moved target to B-3.`

---

## Active Debt



### DEBT-031: Unify generation phase enums across preview and chart config stacks

- **Source:** Phase 3 Slice 3.7 recon (`docs/phase-3-slice-7-recon.md` §4 Decision 4)
- **Added:** 2026-04-24
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** Two parallel generation notifier stacks exist:
  - `frontend/lib/features/graphics/domain/generation_notifier.dart` + `generation_state.dart` use `GenerationPhase { idle, submitting, polling, completed, timeout, failed }`
  - `frontend/lib/features/graphics/application/generation_state_notifier.dart` uses `GenerationPhase { idle, submitting, polling, success, failed, timeout }`
  The semantic difference `completed` vs `success` causes both screens to maintain local phase→ARB-key switches in Slice 3.8 impl, duplicating mapping logic.
- **Impact:** Minor code duplication in 3.8 impl (2 switch statements, 5-7 lines each). No runtime issue, no user-facing bug.
- **Resolution:** Refactor to a single shared `GenerationPhase` enum used by both notifier stacks. Update all consumers. Delete the duplicate.
- **Target:** Opportunistic — during a future graphics refactor or when the chart config flow is re-architected for backend Phase 2 integration.

> Updated 2026-04-24: errorCode plumbing in both notifier stacks completed in Slice 3.8 Fix Round 1 (GitHub review caught dead mapper). DEBT-031 remains open for the phase enum unification proper.

### DEBT-029: Locale-aware bootstrap-error fallback in Flutter admin app

- **Source:** Phase 3 Slice 3.3+3.4 recon (`docs/phase-3-slice-3-recon.md` §6)
- **Added:** 2026-04-23
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** `_BootstrapError` in `frontend/lib/main.dart` renders hardcoded EN text (`App bootstrap failed: $error`) as an EN-kept Category B diagnostic path.
- **Impact:** In rare bootstrap-failure sessions, RU operators see an untranslated diagnostic message.
- **Resolution:** Add locale-aware pre-localization fallback using `PlatformDispatcher.instance.locale` with a tiny EN/RU const map, defaulting to EN for unsupported locales.
- **Target:** Opportunistic fix during future Flutter bootstrap refactor.

### DEBT-030: Editor endpoints lack structured error codes for localized operator messaging

- **Source:** Phase 3 Slice 3.5+3.6 recon (`docs/phase-3-slice-5-recon.md` §5/§9)
- **Added:** 2026-04-24
- **Severity:** medium
- **Category:** architecture
- **Status:** accepted
- **Description:** Editor-facing backend flows (`PATCH /api/v1/admin/publications/{id}`, `POST /api/v1/admin/publications/{id}/publish`, `POST /api/v1/admin/publications/{id}/unpublish`) do not currently expose a stable, documented `error_code` contract for client-side localization; UI must rely on a generic localized wrapper (`editorActionError`) with raw backend detail passthrough.
- **Impact:** RU operators receive partially localized failure messaging (localized wrapper + backend detail that may remain EN), reducing precision and consistency across error cases.
- **Resolution:** Introduce endpoint-level structured `error_code` values and mapping docs for admin_publications flows; add Flutter mapper (`lib/l10n/backend_errors.dart`) from code → specific ARB messages; keep generic wrapper only as fallback for unknown codes.
- **Target:** Slice 3.7/3.8 backend-error mapping alignment PR (or earlier backend contract PR if scheduled).

### DEBT-027: Autosave retry-reset effect uses exhaustive-deps exception

- **Source:** Stage 4 Task 2 implementation (`claude/stage4-task2-autosave`)
- **Added:** 2026-04-20
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** In `frontend-public/src/components/editor/index.tsx` a
  `useEffect(() => { if (state.saveError) retryAttemptRef.current = 0; },
  [doc])` uses `// eslint-disable-next-line react-hooks/exhaustive-deps`
  to avoid including `state.saveError` in its dependency array.
  Including it would cause the effect to re-run on every `SAVE_FAILED`
  dispatch, resetting the attempt counter and defeating the exponential
  backoff progression. The effect is intended to reset retries only
  when the user edits the doc during error state.
- **Impact:** One ESLint disable directive. No runtime consequence ->
  the behaviour is correct and fully covered by the autosave test
  "user edit during error resets retry budget".
- **Resolution:** Refactor autosave orchestration into a small reducer
  (or a hand-rolled state machine) where attempt count lives alongside
  saveError, replacing the pair of effect + ref with a single state
  transition table. Out of scope for Task 2.
- **Target:** Future autosave refactor (no concrete milestone).
### DEBT-021: Temp upload Parquet files not cleaned up

- **Source:** JSON/CSV upload PR (`claude/add-data-upload-graphics-i8IWc`)
- **Added:** 2026-04-14
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `POST /api/v1/admin/graphics/generate-from-data` writes a
  temporary Parquet to S3 under `temp/uploads/{uuid}.parquet` before
  enqueuing the existing `graphics_generate` job. The `GraphicPipeline`
  does not delete its input object, and no cleanup cron exists yet,
  so these temp Parquet files accumulate indefinitely.
- **Impact:** Low — individual objects are small (≤ 10 000 rows × columns
  of CSV/JSON data). Growth is proportional to upload volume; eventually
  increases storage cost and clutters bucket listings.
- **Resolution:** Add a scheduled task that deletes objects under
  `temp/uploads/` with a `LastModified` older than
  `settings.temp_upload_ttl_hours` (default 24 h).
- **Target:** Follow-up PR (not blocking for the upload feature).

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
| DEBT-010 | No audit event retention cleanup | Final Debts | 2026-04-12 |
| DEBT-015 | GraphicPipeline generate() method is monolithic | Final Debts | 2026-04-12 |
| DEBT-001 | Cooldown query uses text match on JSON | Docs & Quality | 2026-04-12 |
| DEBT-002 | Integration tests use metadata.create_all | Docs & Quality | 2026-04-12 |
| DEBT-003 | Dockerfile doesn't run migrations on startup | Pre-deploy Hardening | 2026-04-12 |
| DEBT-004 | Old in-memory TaskManager not yet removed | Dead Code Cleanup | 2026-04-12 |
| DEBT-005 | StorageInterface upload_bytes/download_bytes | PR B-3 | 2026-04-09 |
| DEBT-006 | Dead code in services/cmhc/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-007 | Dead code in services/ai/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-008 | No startup validation for required secrets | Pre-deploy Hardening | 2026-04-12 |
| DEBT-012 | Admin graphics API uses placeholder data | PR B-3 | 2026-04-09 |
| DEBT-013 | Admin graphics uploads same file for high-res variant | PR B-3 | 2026-04-09 |
| DEBT-014 | database.py creates engine at module level | PR A-1 fix | 2026-04-06 |
| DEBT-016 | ARCHITECTURE.md references removed MVP features | Docs & Quality | 2026-04-12 |
| DEBT-017 | Job handlers violate ARCH-DPEN-001 with inline httpx | Docs & Quality | 2026-04-12 |
| DEBT-018 | TESTING.md coverage table is stale | Docs & Quality | 2026-04-12 |
| DEBT-019 | Orphaned LLM infrastructure outside services/ai/ | Dead Code Cleanup | 2026-04-12 |
| DEBT-020 | CMHC and Tasks routers still mounted for deferred features | Dead Code Cleanup | 2026-04-12 |
| DEBT-021 | Temp upload Parquet files not cleaned up | codex/fix-contrast-slot-validation | 2026-04-20 |
| DEBT-028 | Contrast validator only checks 'primary' slot per block | Stage 4 post-merge fix | 2026-04-21 |
| DEBT-027 | Autosave retry-reset effect uses exhaustive-deps exception | claude/fix-autosave-deps-warning-NoqvL | 2026-04-21 |
| DEBT-022 | `validateImport` dual-signature (string + throwing) | Stage 3 PR 2a (`claude/add-workflow-state-machine-mUM3P`) | 2026-04-17 |
| DEBT-023 | `validateImportStrict` does not deep-validate `Comment` entries | Stage 3 PR 2b (`claude/recon-comments-subsystem-HwvB1`) | 2026-04-17 |
| DEBT-024 | Rename `validateDocumentShape` -> `assertCanonicalDocumentV2Shape` | Stage 3 PR 4 (`claude/reconnaissance-persistence-cleanup-EJ4uX`) | 2026-04-19 |
| DEBT-026 | Lossy round-trip between `CanonicalDocument` and `AdminPublicationResponse` | Stage 4 Task 0 full close (`claude/close-infographic-blockers-wkjVX`) | 2026-04-19 |

### DEBT-026: Lossy round-trip between CanonicalDocument and AdminPublicationResponse

- **Source:** PR review of `claude/wire-infographic-editor-9w3wr` (Stage 4 Task 0 initial commit `550c336`)
- **Added:** 2026-04-19
- **Severity:** high
- **Category:** architecture
- **Status:** resolved
- **Description:** `buildUpdatePayload` emitted only editorial / text / review fields; `hydrateDoc` reconstructed from a template and overlaid the narrow subset. Block-level props, chart data, and layout fields did not survive a save -> reload cycle. Size mapping (`instagram_1080` / `instagram_port` -> backend `instagram`) was additionally lossy on the inverse.
- **Impact:** Opening an existing publication, pressing Ctrl+S, and reloading silently reset block props and chart data to template defaults. Effective data loss on every save of any doc whose state exceeded the mapped subset.
- **Resolution:** Added opaque `document_state` JSON column on `Publication` (nullable, Alembic `a3e81c0f5d21`). Frontend sends the full canonical document as a JSON string in every PATCH; backend stores verbatim with no parsing or shape validation. Derived editorial columns (`headline`, `chart_type`, `visual_config`, `review`, `eyebrow`, `description`, `source_text`, `footnote`) are kept in sync for search indexing and the public gallery. `hydrateDoc` prefers `document_state` when present (parse + `validateImportStrict`); falls back to the legacy field-level hydrate with `deriveWorkflowFromStatus` for rows predating this column (those rows become lossless on first subsequent PATCH). `HydrationError` surfaces malformed `document_state` through `error.tsx`.
- **Target:** Stage 4 Task 0 full close (`claude/close-infographic-blockers-wkjVX`)
- **Resolved:** 2026-04-19
- **Resolution PR:** `claude/close-infographic-blockers-wkjVX` (fix commit `d46edf6`)
