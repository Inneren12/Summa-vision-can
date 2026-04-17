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

**Implementation notes.** Category flags are checked before iterating
payload keys. Empty payloads (e.g. `UPDATE_DATA` with `data: {}`) are
rejected in read-only workflows by the category check, not by the loop
body — preventing a zero-iteration bypass where `Object.keys({}).length
=== 0` would run no rejection logic and fall through to
`{ allowed: true }`. The same default-deny shape is used for
`UPDATE_PROP`, `CHANGE_PAGE`, `TOGGLE_VIS`, and `SWITCH_TPL`: the
category flag is consulted once, and the action is only permitted if
that flag is set in the current workflow's `WORKFLOW_PERMISSIONS` row.

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

## Comments subsystem (Stage 3 PR 2b)

The comments subsystem lives in `store/comments.ts` and feeds six new action
types through the reducer: `ADD_COMMENT`, `REPLY_TO_COMMENT`, `EDIT_COMMENT`,
`RESOLVE_COMMENT`, `REOPEN_COMMENT`, `DELETE_COMMENT`.

### `Comment` shape

```ts
interface Comment {
  id: string;
  blockId: string;          // comment anchors to a single block
  parentId: string | null;  // null for root; string for a reply
  author: string;
  text: string;
  createdAt: string;        // ISO 8601
  updatedAt: string | null; // set by EDIT_COMMENT
  resolved: boolean;
  resolvedAt: string | null;
  resolvedBy: string | null;
}
```

`validateImportStrict` deep-validates every comment element (shape + nullability
rules) and enforces referential integrity: every non-null `parentId` must
resolve to a comment id in the same document. This closes DEBT-023.

### Action semantics

| Action              | Ownership check | Logs to `review.history` | History `action` label |
|---------------------|:---------------:|:------------------------:|------------------------|
| `ADD_COMMENT`       | no              | yes                      | `comment_added`        |
| `REPLY_TO_COMMENT`  | no              | yes                      | `comment_replied`      |
| `EDIT_COMMENT`      | **yes**         | no (lean audit)          | —                      |
| `RESOLVE_COMMENT`   | no              | yes                      | `comment_resolved`     |
| `REOPEN_COMMENT`    | no              | yes                      | `comment_reopened`     |
| `DELETE_COMMENT`    | **yes**         | yes                      | `comment_deleted`      |

- **Ownership**: `EDIT` and `DELETE` require `comment.author === resolveActor(action)`.
  `RESOLVE` / `REOPEN` are deliberately open — any commenter can clear a thread.
- **No-op resolve / reopen**: dispatching `RESOLVE_COMMENT` on an already-resolved
  comment (and symmetrically for `REOPEN_COMMENT`) returns the state unchanged,
  without a history entry and without touching the `dirty` flag.
- **One-level threading**: replies may only target root comments (`parent.parentId
  === null`). The reducer rejects reply-to-reply dispatches and `validateImportStrict`
  rejects imports that carry nested threads. Helpers in `store/comments.ts`
  (`buildThreads`, `threadUnresolvedCount`, `isThreadResolved`) are flat by design;
  allowing deeper nesting would silently misrepresent thread shape in the UI.
- **Delete semantics — tombstone on foreign replies**: `DELETE_COMMENT` runs an
  ownership check on the target and a subtree check before removing anything.
  - *Leaf (no replies)* → physical removal.
  - *Subtree fully authored by the actor (or tombstones)* → physical removal
    of the whole subtree.
  - *Subtree contains a reply from a different author* → **tombstone** only.
    The target's `text` and `author` are replaced with the literal `"[deleted]"`
    and `updatedAt` is set; `id`, `blockId`, `parentId`, `createdAt`, and
    `resolved*` fields are preserved so threading and stats stay intact.
    Foreign-authored replies remain untouched and visible.

  History summary reflects the path taken: `(+ N replies)` when replies were
  physically removed, `(tombstoned — has replies from other authors)` when the
  subtree was soft-deleted.

### `canComment` permission dimension

`WorkflowPermission` gains a sixth flag:

| State       | textContent | dataContent | structural | style | importUndoRedo | canComment |
|-------------|:-----------:|:-----------:|:----------:|:-----:|:--------------:|:----------:|
| `draft`     | ✓           | ✓           | ✓          | ✓     | ✓              | ✓          |
| `in_review` | ✓           | ✗           | ✗          | ✗     | ✗              | ✓          |
| `approved`  | ✗           | ✗           | ✗          | ✗     | ✗              | ✗          |
| `exported`  | ✗           | ✗           | ✗          | ✗     | ✗              | ✗          |
| `published` | ✗           | ✗           | ✗          | ✗     | ✗              | ✗          |

`canComment` is orthogonal to the content-edit categories: reviewers can still
annotate during `in_review` even though every non-text content path is locked.
The mode axis never restricts comments — a `template`-mode reviewer has the
same comment surface as a `design`-mode editor.

### Comments are outside undo/redo

Comment mutations **do not participate in the undo/redo timeline**. They:

- do not call the reducer's `push` helper
- do not modify `undoStack`
- do not clear `redoStack`
- do not touch the `_lastAction` burst-batching fingerprint

They do flip `dirty: true` (comments are persisted state) and clear
`_lastRejection`. Rationale:

- **Ownership**: an EDIT/DELETE gated on the actor being the author becomes
  meaningless if UNDO can silently restore or obliterate another user's note.
- **Audit integrity**: comment events are logged in `doc.review.history`,
  which must not be rewindable by a content-stack UNDO.
- **Convention**: Figma, Linear, and Google Docs all keep review comments off
  the document-content undo timeline.

### Undo/redo overlay policy

Undo snapshots are whole-document clones captured by the reducer's `push`
helper. A naive UNDO that reassigned `state.doc = snapshot` would rewind
`review.comments`, `review.history`, and `review.workflow` along with the
content — destroying reviewer annotations, audit trail, and workflow state
on every content undo.

The reducer solves this by **overlaying the live `review` section onto the
restored snapshot**. In both `UNDO` and `REDO`:

```ts
const restored: CanonicalDocument = {
  ...snapshot,
  review: {
    // Preserve the live, non-content timeline.
    workflow: state.doc.review.workflow,
    history:  state.doc.review.history,
    comments: state.doc.review.comments,
  },
  meta: { ...snapshot.meta, updatedAt: getProvider(state).now() },
};
```

Consequences:

- UNDO rewinds `page`, `sections`, `blocks` (content). Comments, workflow
  transitions, and the audit trail are preserved.
- REDO re-applies the content edit while keeping any comments added or
  resolved while the document was rewound.
- `meta.updatedAt` advances to the UNDO/REDO event time — the mutation is
  real, even if the content payload reverts to an earlier state.

Workflow state is explicitly in the overlay so that a content UNDO cannot
silently revert a `SUBMIT_FOR_REVIEW` or `APPROVE`. Workflow transitions
move only through the workflow action set (`canTransition` in
`store/workflow.ts`).

### Thread helpers

`store/comments.ts` also exports pure derivation helpers consumed by the PR 3
UI layer:

- `buildThreads(comments) → CommentThreadNode[]` — groups flat comments into
  root-and-reply threads. Roots newest-first by `createdAt`; replies oldest-first.
  Orphaned replies (parent missing) are promoted to roots so they remain visible.
- `threadUnresolvedCount(thread) → number` — open items across the thread.
- `isThreadResolved(thread) → boolean` — `threadUnresolvedCount === 0`.
- `collectDescendantIds(comments, rootId) → Set<string>` — BFS over `parentId`
  edges; used by `applyDeleteComment` for recursive delete.

Reference artifact: `docs/editor/infographic-editor-stage3b-v2.jsx`.
