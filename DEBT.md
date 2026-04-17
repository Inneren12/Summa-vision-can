# Technical Debt Registry

> Source of truth for known technical debt.
> Maintained per-PR: creating debt → add entry; resolving → move to Resolved.

## Format

| Field | Description |
|-------|-------------|
| **ID** | `DEBT-NNN` (sequential, never reused) |
| **Source** | PR number or review that identified it (e.g. `PR #16 review`, `Roadmap R18`) |
| **Added** | Date added (YYYY-MM-DD) |
| **Severity** | `critical` / `high` / `medium` / `low` |
| **Category** | `architecture` / `testing` / `security` / `ops` / `code-quality` |
| **Status** | `active` — confirmed, needs work; `accepted` — known, deferred intentionally; `in-progress` — being fixed |
| **Description** | Factual statement of what the debt IS (not hypotheses) |
| **Impact** | What breaks or degrades if not fixed |
| **Resolution** | Concrete action to resolve |
| **Target** | Specific PR, étape, or milestone |

Rules:
- Every entry must be a **verified fact**, not a hypothesis.
- Do NOT add speculative or unverified items — verify first, then add.
- Backlog features and future enhancements go in ROADMAP, not here.
- When resolving: move entry to Resolved table with PR link and date.
- When updating severity/target: edit in-place and append a changelog
  line at the bottom of the entry:
  `> Updated YYYY-MM-DD: severity high→medium, moved target to B-3.`

---

## Active Debt

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

### DEBT-023: `validateImportStrict` does not deep-validate `Comment` entries

- **Source:** Stage 3 PR 1 review (`claude/add-review-section-IL0pl`)
- **Added:** 2026-04-17
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** `validateImportStrict` does not deep-validate
  `review.comments[]` element shape. Currently only array-ness is checked.
  Element-level checks for `WorkflowHistoryEntry` were added in Stage 3
  PR 2a; the parallel `Comment` validator (required: `id`, `blockId`,
  `parentId` nullable, `author`, `text`, `createdAt`, `resolved` boolean,
  `updatedAt` nullable, `resolvedAt` nullable, `resolvedBy` nullable)
  lands in PR 2b alongside the comment reducer actions.
- **Impact:** Low — `mkDoc` seeds `comments: []` and PR 2a does not
  introduce any reducer action that adds comments. Risk surfaces only
  when PR 2b lands user-authored comment entries.
- **Resolution:** Add `validateCommentEntry` in `guards.ts` alongside
  the new comment reducer actions.
- **Target:** Stage 3 PR 2b (comment reducer actions).
> Updated 2026-04-17: scope narrowed to `Comment` only — `WorkflowHistoryEntry`
> element validation closed by PR 2a.

---

### DEBT-024: Rename `validateDocumentShape` → `assertCanonicalDocumentV2Shape`

- **Source:** Stage 3 PR 2a (`claude/add-workflow-state-machine-mUM3P`)
- **Added:** 2026-04-17
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** The single shape validator in
  `frontend-public/src/components/editor/registry/guards.ts` is named
  `validateDocumentShape` but only accepts v2-shaped documents (every
  v2 invariant is asserted: `meta.workflow` forbidden, `review.workflow`
  required, `review.history` element shape, etc.). PR 2a's prompt
  referenced it as `assertCanonicalDocumentV2Shape`, which is the more
  honest name. Kept as-is in PR 2a to avoid scope churn (rename would
  touch every test that asserts on its message strings indirectly).
- **Impact:** Cosmetic. Function works correctly; only the name is
  imprecise.
- **Resolution:** Rename function + every reference (no behavior change).
- **Target:** Future cleanup PR.
> Updated 2026-04-17 (PR 2a follow-up): `validateDocumentShape` is now
> module-internal again (the temporary `export` was removed to preserve
> the single-entry-point contract). Only `validateImportStrict` is
> exposed. Remaining scope for DEBT-024 is the cosmetic rename.


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
| DEBT-022 | `validateImport` dual-signature (string + throwing) | Stage 3 PR 2a (`claude/add-workflow-state-machine-mUM3P`) | 2026-04-17 |
