# Editor Module

> Infographic authoring tree under `frontend-public/src/components/editor/`.

## Document schema v2

`CanonicalDocument` is the authoritative document shape for the infographic
editor. As of Stage 3 PR 1 it is at schema version **2**.

### Final shape

```ts
interface CanonicalDocument {
  schemaVersion: 2;
  templateId: string;
  page: PageConfig;                      // { size, background, palette }
  sections: Section[];                   // ordered; each holds blockIds: string[]
  blocks: Record<string, Block>;         // keyed by id
  meta: DocMeta;                         // edit log + timestamps
  review: Review;                        // workflow lifecycle + comments
}

interface DocMeta {
  createdAt: string;
  updatedAt: string;
  version: number;                       // edit-snapshot counter
  history: EditHistoryEntry[];           // { version, savedAt, summary }
}

interface Review {
  workflow: WorkflowState;               // draft | in_review | approved | exported | published
  history: WorkflowHistoryEntry[];       // { ts, action, summary, author, fromWorkflow, toWorkflow }
  comments: Comment[];                   // { id, blockId, parentId, author, text, ... }
}
```

### Two histories, two purposes

`meta.history` and `review.history` look similar but are semantically different
and must not be merged.

| Field | Purpose | Entry type | Written by |
|-------|---------|------------|------------|
| `meta.history` | Save-snapshot / undo log. One entry per edit action. | `EditHistoryEntry` (`{ version, savedAt, summary }`) | Reducer's `push` helper on every document-mutating action |
| `review.history` | Review lifecycle audit log. One entry per workflow transition or comment event. | `WorkflowHistoryEntry` (`{ ts, action, summary, author, fromWorkflow, toWorkflow }`) | Stage 3 PR 2 reducer actions (`SUBMIT_FOR_REVIEW`, `APPROVE`, `ADD_COMMENT`, …) |

### `schemaVersion` policy

- `doc.schemaVersion` at the root is the **single source of truth**.
- `doc.meta` must not contain a `schemaVersion` field. `validateImportStrict`
  rejects documents that do.
- `doc.meta` must not contain `workflow`. Workflow lives in `doc.review.workflow`.
- Root must not contain `workflow` or `comments`. Both live in `doc.review`.

### Migration chain

Storage contains only v1 documents, so the chain is a single step:

```
v1  ──(MIGRATIONS[1])──►  v2
```

`v1 → v2` moves `doc.workflow` (root) into `doc.review.workflow`, adds
`doc.review.history` with a single `"migrated"` audit entry, initialises
`doc.review.comments = []`, and bumps `doc.schemaVersion` to 2.

Migration is orchestrated by two functions in `registry/guards.ts`:

- `migrateDoc(raw): MigrationResult` — pure, throwing. Returns `{ doc,
  appliedMigrations }` and is idempotent on already-current documents.
- `validateImportStrict(raw): CanonicalDocument` — migrates, then asserts every
  v2 invariant. Throws with a precise message on any violation. **Sole import
  entry point as of Stage 3 PR 2a** — the legacy string-returning
  `validateImport(doc): string | null` was removed (DEBT-022 closed).

## Workflow state machine (Stage 3 PR 2a)

The reducer enforces permissions along **two orthogonal axes**:

1. **Mode axis** — `template` vs `design`. Controls structural vs content
   editing. Unchanged from Stage 2.
2. **Workflow axis** — `draft | in_review | approved | exported | published`.
   Controls the review lifecycle. Added in PR 2a.

An action must pass **both gates** to mutate the document. See
`store/reducer.ts#isActionAllowed`.

### Legal transitions

```
draft     → in_review
in_review → approved | draft   (approve OR changes requested)
approved  → exported | draft   (export OR revoke approval)
exported  → published
published → ∅                  (terminal)
```

`DUPLICATE_AS_DRAFT` is a lifecycle action (not a transition); it produces
a fresh draft and is legal only from `exported` or `published`. Source of
truth: `TRANSITIONS` in `store/workflow.ts`.

### Workflow × category matrix

| Action category              | draft | in_review | approved | exported | published |
|------------------------------|:-----:|:---------:|:--------:|:--------:|:---------:|
| TEXT_CONTENT                 |   ✓   |     ✓     |    ✗     |    ✗     |     ✗     |
| DATA_CONTENT                 |   ✓   |     ✗     |    ✗     |    ✗     |     ✗     |
| STRUCTURAL (add/remove)      |   ✓   |     ✗     |    ✗     |    ✗     |     ✗     |
| STYLE (bg, theme, size, tpl) |   ✓   |     ✗     |    ✗     |    ✗     |     ✗     |
| IMPORT / UNDO / REDO         |   ✓   |     ✗     |    ✗     |    ✗     |     ✗     |
| SELECT / SET_MODE / SAVED    |   ✓   |     ✓     |    ✓     |    ✓     |     ✓     |
| Workflow transitions         | governed by transition table above                 |

In `in_review` only copy edits land; attempting a data/structural/style
edit returns *"Only copy edits allowed during review — return to draft
first"*.

**History-stack bypass note.** `in_review` blocks not only content
edits but also `IMPORT`, `UNDO`, and `REDO`. Two bypass paths motivate
that rule:

- **IMPORT** — `validateImportStrict` is workflow-blind; allowing
  IMPORT in review would let the user swap the entire document and
  bypass every per-key lock.
- **UNDO / REDO** — stacks are PRESERVED across `SUBMIT_FOR_REVIEW`
  (so `REQUEST_CHANGES` can restore undo once the document is back in
  draft). If UNDO were allowed in `in_review`, a single dispatch would
  replay a pre-submission structural snapshot in a state that is
  supposed to permit only copy edits.

Blocking these three actions while preserving the stacks is the
minimum-surface fix — no extra stack-clearing heuristics needed.

### Determinism

All workflow transitions accept an optional `ts?: string` (ISO 8601).
When absent, the reducer reads from `state._timestampProvider` (defaults
to `systemTimestampProvider` in `initState`). Tests inject a mock clock
for deterministic output. No `new Date().toISOString()` calls live
inside the reducer body.

### Read-only transitions clear undo/redo

Crossing into `approved | exported | published` clears `undoStack` and
`redoStack`. Rationale: an undo after APPROVE would silently revert
approval state. Transitions back to `draft` (`REQUEST_CHANGES`,
`RETURN_TO_DRAFT`) preserve stacks.

### Transitions mark the document as dirty

Every workflow transition mutates the document — it appends a
`WorkflowHistoryEntry`, flips `review.workflow`, and advances
`meta.updatedAt`. These are unsaved changes by definition, so the
reducer sets `dirty: true` on every transition (including
`DUPLICATE_AS_DRAFT`, where the new document identity has not been
persisted anywhere yet). Only `SAVED` or a successful persistence
round-trip clears the dirty flag.

Reference artifact: `docs/editor/infographic-editor-stage3a-v2.jsx`.

### Stage 3 artifact history

The long-term intent for the review subsystem was sketched across two artifact
files kept under `docs/editor/` (`infographic-editor-stage3a-v2.jsx`,
`infographic-editor-stage3b-v2.jsx`). Those artifacts split review state across
three fields (`doc.meta.workflow`, `doc.meta.history`, `doc.comments`) as a
compromise during incremental artifact development. Stage 3 PR 1 consolidates
all three into `doc.review` and removes the dual-write of `schemaVersion`.
