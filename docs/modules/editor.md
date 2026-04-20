# Editor Module

> Infographic authoring tree under `frontend-public/src/components/editor/`.

## Persistence (backend side)

Stage 3 PR 4 wires the review subtree into the backend:

- **`Publication.review`** — a nullable `Text` column on the `publications`
  table (`backend/src/models/publication.py`). Stores the frontend
  `CanonicalDocument.review` subtree verbatim as a JSON string
  (SQLite-compat pattern, matches `visual_config`). The backend does
  **not** deep-validate nested `history` / `comments` entries; the
  frontend's `assertCanonicalDocumentV2Shape` owns shape validation.
- **`PATCH /api/v1/admin/publications/{id}`** accepts a top-level
  `review` field of type `ReviewPayload` (`backend/src/schemas/publication.py`).
  Round-trip preserves the frontend structure — the backend does not
  re-shape or migrate; an unknown top-level key causes `422`.
- **Workflow → status sync rule.** `review.workflow` is the single
  source of truth for editorial state; `Publication.status` remains
  as a coarse gallery-visibility flag derived from it:
  - `review.workflow == "published"` → `Publication.status = PUBLISHED`
    (and `published_at` stamped if not already set).
  - A transition out of `"published"` demotes `status` to `DRAFT`;
    `published_at` is deliberately preserved for historical audit.
- **`POST /publish`** and **`POST /unpublish`** still flip `status` but
  now also mirror the change into `review.workflow` and append a
  `"system"`-authored entry to `review.history` so the editor timeline
  reflects admin-driven transitions. Rows without a `review` payload
  are published by status alone (no synthesis by the backend).
- **Audit events.** Workflow transitions emit one of
  `PUBLICATION_WORKFLOW_{SUBMITTED, APPROVED, CHANGES_REQUESTED,
  RETURNED_TO_DRAFT, EXPORTED}` (see `backend/src/schemas/events.py`).
  The event is classified by `_classify_workflow_event(previous, target)`
  so business semantics are preserved:
  - `draft → in_review`  → `SUBMITTED`
  - `in_review → approved` → `APPROVED`
  - `in_review → draft`  → `CHANGES_REQUESTED` (reviewer pushback,
    distinct from an approval revocation)
  - other `* → draft`    → `RETURNED_TO_DRAFT` (approval revocation)
  - `approved → exported` → `EXPORTED`

  A transition into `"published"` additionally emits
  `PUBLICATION_PUBLISHED`; the two event types carry distinct
  meaning — content-workflow vs. admin-visibility.
- **Public leak prevention.** `PublicationPublicResponse` does **not**
  expose `review`. Workflow state, history and comments are admin-only
  editorial data and must never leave the admin namespace.
- **Consumer status.** PR 4 establishes the persistence contract only.
  The React `InfographicEditor` is not yet mounted by a Next.js route;
  Flutter has its own narrow brief-edit widget. A follow-up PR wires a
  consumer (admin route, WebView embed, or other).

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

## UI surface for Stage 3 (PR 3)

PR 3 wires the Stage 3 reducer surface (workflow, comments, `_lastRejection`)
into the editor UI. It is a pure UI layer; no reducer/registry/renderer changes.

### Right rail — tabbed Inspector | Review

The right column is owned by `components/RightRail.tsx`. It hosts two
sibling tabs:

- **Inspector** (existing `components/Inspector.tsx`, now width-flexible) —
  per-block prop editor.
- **Review** (`components/ReviewPanel.tsx`) — workflow header with current
  badge and available transitions, comment threads, workflow history.

Tab semantics use `role="tablist" / role="tab" / role="tabpanel"` with
`aria-selected` and `aria-controls`. Inactive panels are kept unmounted so
heavy children (Inspector's per-block data editors) do not run while hidden.

**Keyboard navigation** follows the W3C ARIA Authoring Practices tabs
pattern:

- `ArrowLeft` / `ArrowRight` move between tabs (circular).
- `Home` / `End` jump to first / last tab.
- **Roving tabIndex**: the active tab has `tabIndex={0}`, inactive tabs
  have `tabIndex={-1}`. This removes inactive tabs from the sequential
  tab order, so `Tab` from outside the tablist lands on the currently
  active tab, and subsequent `Tab` jumps into the active tabpanel rather
  than cycling every tab.
- Focus moves to the newly active tab on activation (`tabRefs.current[nextIdx]?.focus()`).

A count pill on the Review tab shows `unresolvedTotal` derived from
`buildThreads(state.doc.review.comments)` and `threadUnresolvedCount(...)`.
Pill is hidden when zero.

### `<NoteModal>` — single input surface, single ownership

`components/NoteModal.tsx` is the only modal in the editor. Hand-rolled
(no portal, no library), state-gated conditional render with an inline
`TK`-token style. It is the sole route for free-text input that previously
would have used `window.prompt` — both for comment composition (add / reply
/ edit) and for workflow transition notes (`REQUEST_CHANGES`,
`RETURN_TO_DRAFT`).

**Ownership: `index.tsx`.** There is exactly one `<NoteModal>` instance
in the editor tree, driven by a `noteRequest: NoteRequestConfig | null`
state in `index.tsx`. Surfaces that need to collect free-text input
(ReviewPanel, ReadOnlyBanner) receive an `onRequestNote(config)` callback;
calling it opens the shared modal with the supplied title/label/submit
handler. This guarantees the audit path is identical regardless of which
UI surface initiated the transition — `RETURN_TO_DRAFT` dispatched from
ReadOnlyBanner is indistinguishable from the same transition dispatched
from ReviewPanel, both routing through `NoteModal.onSubmit → dispatch`.

The shared config shape lives at `components/noteRequest.ts`:

```ts
interface NoteRequestConfig {
  title: string;
  label: string;
  placeholder?: string;
  initialValue?: string;
  required: boolean;
  submitLabel: string;
  onSubmit: (note: string) => void;
}
```

Behaviour invariants:

- `role="dialog"` + `aria-modal="true"` + `aria-labelledby` heading +
  `aria-describedby` label.
- Backdrop click → `onCancel`. Inside-dialog clicks do not propagate.
- `Escape` → `onCancel`. `Ctrl/Meta+Enter` → submit if not disabled.
- **Keyboard handling via document-level listener** (`document.addEventListener('keydown', ...)`)
  inside a `useEffect` with explicit `removeEventListener` cleanup.
  Covered by a test that spies on `document.removeEventListener` and
  asserts a `"keydown"` removal fires on unmount.
- **Focus trap**: Tab / Shift+Tab wrap inside the dialog using a
  per-event `querySelectorAll` of focusable nodes (no mutation observer).
- Focuses the textarea on open.
- **DOM-safe focus restore** on close: the previously active element is
  refocused only if it still lives in the document
  (`document.contains(previous)`). Guards against the common case where
  the opener unmounted during the modal session.
- **Body scroll lock** while open: `document.body.style.overflow = 'hidden'`
  on mount, original value restored on unmount. Covered by two tests
  (unmount path and `isOpen → false` prop-change path).
- Submit disabled when `required && trimmed.length === 0`, or when
  `value.length > maxLength`. Counter turns `TK.c.err` past the limit.
- `id` for new comments is **never** generated client-side; the reducer
  produces ids via `makeId()` so persistence + audit history get one
  source of truth.

### Workflow status badge

`components/StatusBadge.tsx` (`compact` for TopBar, `regular` for the
ReviewPanel header). Compact instance lives in TopBar's left cluster,
immediately after the template chip. There are **no workflow transition
buttons in TopBar** — transitions live in ReviewPanel where context
(notes, history) is colocated.

### LeftPanel comment-count pill

`components/LeftPanel.tsx` derives `unresolvedByBlock` once per render via
`useMemo` over `state.doc.review.comments`, summing
`threadUnresolvedCount` per `blockId` for non-resolved threads. Block rows
in the Blocks tab render a small `data-testid="block-unresolved-pill"`
when the block has unresolved comments. The same `accM`/`acc` palette is
used as the Review tab pill for visual consistency.

### `<ReadOnlyBanner>`

`components/ReadOnlyBanner.tsx` shows above the canvas when
`isReadOnlyWorkflow(state.doc.review.workflow)` is true. Not
dismissable — the banner reflects the truth of the read-only state.

**Per-state CTA mapping**:

| Workflow    | Primary CTA          | Secondary CTA        | Note prompt?                     |
|-------------|----------------------|----------------------|----------------------------------|
| `approved`  | Return to draft      | —                    | Yes — NoteModal (reason optional) |
| `exported`  | Duplicate as draft   | Return to draft      | Primary: No (direct dispatch); secondary: Yes |
| `published` | Duplicate as draft   | —                    | No (terminal state; duplication only) |

Rationale: `approved` is pre-export editorial review where returning to
draft with a reason is a normal revision flow. `exported` has produced
an artifact but is not yet publicly visible — duplication preserves the
exported snapshot while returning to draft remains legal. `published` is
public-facing and terminal; editing would rewrite history, so only
duplication is offered.

**Audit parity**: `Return to draft` is **always** routed through the
shared NoteModal via `onRequestNote`. Direct dispatches from the banner
are reserved for `DUPLICATE_AS_DRAFT`, which produces a fresh document
and carries no note.

### `<NotificationBanner>`

`components/NotificationBanner.tsx` consolidates three signals into one
in-app banner positioned directly under TopBar:

| Priority | Source            | role     | Tone               |
|----------|-------------------|----------|--------------------|
| 1        | `importError`     | `alert`  | error tint         |
| 2        | `state._lastRejection` | `status` | error tint        |
| 3        | `importWarnings`  | `status` | accent (warn) tint |

Only the top-priority active signal is rendered. `_lastRejection` reset
behaviour: a local `rejectionDismissed` flag is reset to `false` whenever
`_lastRejection.at` changes, so a fresh rejection always re-surfaces even
after the user dismissed the previous one. The reducer already clears
`_lastRejection` on any successful action, so the banner disappears
automatically once the next action lands. **No toast provider** —
intentional; the in-app banner is the project's convention.

### Effective permissions (mode × workflow overlay)

`PERMS[mode]` is mode-axis only. The reducer's `checkWorkflowPermission`
runs orthogonally on the workflow axis. To prevent buttons looking
enabled then dispatching into a silent rejection, `index.tsx` computes
`effectivePerms = useMemo(...)` that overlays `WORKFLOW_PERMISSIONS[wf]`
onto the mode perms:

- `switchTemplate`, `changePalette`, `changeBackground`, `changeSize`
  → ANDed with `workflowPerms.style`.
- `editBlock(reg, key)` is the combination of three gates:
  block-registry editability (registry-level), mode-axis permission
  (`PERMS[mode].editBlock`), and workflow-key-category
  (`canEditKeyInWorkflow(workflow, key)`). All three must return `true`.
  This mirrors the reducer's `checkModePermission` +
  `checkWorkflowPermission` pair so UI affordances and reducer
  decisions stay in sync.
- `toggleVisibility(reg)` → ANDed with `workflowPerms.structural`
  (structural is `false` in every non-draft workflow, so this covers
  both read-only states and `in_review`).

`in_review` is a copy-edits-only state: text-category keys remain
editable, data/style/structural keys are disabled. Without the
`canEditKeyInWorkflow` gate the Inspector would show every field as
editable and the reducer would silently reject non-text
`UPDATE_PROP` actions, surfacing a rejection banner instead of a
correctly-disabled input.

LeftPanel and Inspector receive `effectivePerms`; in `approved` /
`exported` / `published` the Theme tab buttons disable visibly.
`canEdit` is derived from `effectivePerms.editBlock` so Inspector
property fields disable too.

### Canvas stays clean — no overlay (Stage 3 PR 3)

PR 3 did not introduce a canvas overlay layer. Comment indicators
appeared only in (a) the LeftPanel block-row pills and (b) the Review
panel. The rationale was to preserve export/PNG fidelity and avoid
reflowing the PR 3 scope into the renderer engine.

**Revised in Stage 4 Task 1** — see the "Canvas interaction" section
below. The canvas now has a separate overlay canvas used strictly for
hover/selection outlines. PNG export still reads from the content
canvas only, so the PR 3 export-fidelity constraint is preserved.

### Component file map

| File                                              | Purpose                                          |
|---------------------------------------------------|--------------------------------------------------|
| `components/NoteModal.tsx`                        | Modal text input (replaces `window.prompt`)      |
| `components/StatusBadge.tsx`                      | Workflow state pill (compact / regular)          |
| `components/RightRail.tsx`                        | Tabbed parent for Inspector + Review             |
| `components/ReviewPanel.tsx`                      | Workflow header + threads + history              |
| `components/ReadOnlyBanner.tsx`                   | Above-canvas banner when workflow is read-only   |
| `components/NotificationBanner.tsx`               | Priority-resolved in-app notice surface          |
| `components/Inspector.tsx`                        | Modified — drops outer width/border              |
| `components/LeftPanel.tsx`                        | Modified — adds `unresolvedByBlock` count pills  |
| `components/TopBar.tsx`                           | Modified — inserts `<StatusBadge size="compact">` |
| `index.tsx`                                       | Modified — `effectivePerms`, RightRail wiring    |

## Production consumer (Stage 4 Task 0)

Stage 4 Task 0 wires `InfographicEditor` into Next.js admin routes so
it is reachable from a URL with working backend persistence.

### Editor props

```ts
export interface InfographicEditorProps {
  initialDoc?: CanonicalDocument;
  publicationId?: string;
}
```

- **`initialDoc`**. Optional seed document. Synchronously validated via
  `validateImportStrict` at mount. Invalid → fallback to the default
  `single_stat_hero` template and surface the error through the
  existing `NotificationBanner` import-error state. `initState` accepts
  a corresponding optional doc (pure constructor — does not validate).
- **`publicationId`**. When present, Ctrl+S PATCHes the document to
  the backend through the admin proxy. When absent, Ctrl+S is a
  dev-warn no-op.

### Save behaviour

- Ctrl+S → `buildUpdatePayload(doc)` → `updateAdminPublication(id, payload)`.
- Re-entrancy is blocked by `savingRef`: a second Ctrl+S while a PATCH
  is in flight is discarded.
- **Snapshot-based clear** (B2 fix): on save start, `index.tsx`
  captures `state.doc` by reference and dispatches
  `SAVED_IF_MATCHES { snapshotDoc }` on resolve. The reducer clears
  `dirty` only when `state.doc === snapshotDoc` — i.e. the user did
  not edit during the in-flight PATCH. If they did, `dirty` stays set
  and `saveError` is also cleared (the save itself succeeded; only the
  clean-flag is withheld). Reference equality is sufficient because
  the reducer treats `doc` as immutable — every mutation produces a
  new object.
- Errors dispatch `SAVE_FAILED { error }` (populates `state.saveError`,
  leaves `dirty` untouched). `AdminPublicationNotFoundError` surfaces
  as `"Publication not found — reload the page"`.
- **Error channels** (B4 fix): save failures land on
  `state.saveError` — distinct from the load-side `importError`.
  NotificationBanner priority:
  `saveError > importError > _lastRejection > warnings`.
  Dismiss dispatches `DISMISS_SAVE_ERROR` (clears `saveError`, leaves
  `dirty` untouched).
- **Autosave is out of scope for Task 0** and will be added in
  Stage 4 Task 2.

### Persistence seam (DEBT-026 closed)

`src/components/editor/utils/persistence.ts` owns the mapping between
the editor's `CanonicalDocument` and the backend's admin publication
contract. `document_state` is the source of truth: the editor sends
the full doc as JSON text on every PATCH and rehydrates from it on
load. Derived editorial columns (headline / chart_type / eyebrow /
description / source_text / footnote / visual_config / review) are
kept in sync for backend indexing and the public gallery.

Public functions:

- **`buildUpdatePayload(doc): UpdateAdminPublicationPayload`** — emits
  `document_state: JSON.stringify(doc)` plus all derived fields.
  `chart_type` and `visual_config.layout` are derived from
  `doc.templateId`; editorial text fields are extracted from the
  matching template blocks. `review` is forwarded verbatim.
- **`hydrateDoc(pub): CanonicalDocument`** — prefers
  `pub.document_state` (lossless: `JSON.parse` + `validateImportStrict`);
  when absent, falls back to the legacy field-level hydrate. Throws
  `HydrationError` when `document_state` is present but malformed —
  `src/app/admin/editor/[id]/page.tsx` logs server-side and re-throws
  into Next.js `error.tsx`.
- **`HydrationError`** (exported class). `publicationId` field lets
  the server page log which row failed to rehydrate.
- **Legacy path** rebuilds from scalar columns (template defaults for
  block-level props), with a workflow fallback derived from
  `publication.status` via `deriveWorkflowFromStatus` so legacy
  PUBLISHED rows are not silently demoted to DRAFT on first save
  (B3 fix). A dev-mode `console.warn` records each legacy hit.

### Routes

- `/admin` — publication list (server component; fetches with
  `fetchAdminPublicationListServer`).
- `/admin/editor/[id]` — edit page. Server component fetches the
  publication, hydrates the doc, and hands off to
  `AdminEditorClient` (a thin `'use client'` wrapper around
  `<InfographicEditor>`).
- `/admin/editor/[id]/error.tsx` and `.../not-found.tsx` provide the
  boundaries for unexpected errors and missing publications.

### Legacy JSON download

The previous Ctrl+S / TopBar SAVE behaviour wrote a local JSON file
via `URL.createObjectURL`. Stage 4 Task 0 removes that path for the
`publicationId` case. `exportJSON` (TopBar "Export JSON") is
unchanged — it remains a manual checkpoint tool.

## Canvas interaction (Stage 4 Task 1)

Stage 4 Task 1 adds click-to-select and hover outlines on the canvas,
replacing the PR-3 deferred note in "Canvas stays clean — no overlay".
The PR-3 decision is explicitly revised: the canvas now has an overlay
layer, but it is **separate** from the content canvas and never
participates in PNG export.

### Two-canvas layered architecture

`components/Canvas.tsx` renders two sibling `<canvas>` elements inside
a shared `position: relative` wrapper:

- **Content canvas** — the existing rendering surface. Background + all
  block renderers draw here. PNG export still reads from this canvas.
- **Overlay canvas** — absolutely positioned on top, same CSS size,
  `pointer-events: none`. Hover + selection outlines draw here. The
  overlay never touches the content canvas's backing store, so export
  fidelity is preserved.

Pointer events land on the content canvas (overlay is
`pointer-events: none` so events pass through). `onMouseDown`,
`onMouseMove`, and `onMouseLeave` are wired from `index.tsx`.

### Hit areas

`renderDoc` has always returned
`Array<{ blockId, result: RenderResult }>` where
`result.hitArea = { x, y, w, h }` is populated by each block renderer
(`renderer/blocks.ts` → `rr()` helper). The Task 0 content-render
effect discarded this value; Task 1 captures it into
`hitAreasRef: useRef<HitAreaEntry[]>` immediately after each render.

Storing hit areas in a ref (not reducer state) avoids polluting undo
history with derived render data. The ref is refreshed on every
`doc/pal/sz` change, so hover/click handlers always read the latest
geometry.

### Coordinate transform

`utils/hit-test.ts` exposes two pure helpers:

- `hitTest(entries, x, y)` — iterates `entries` in **reverse** so the
  last-drawn block wins on overlap (matches the engine's draw order).
- `clientToLogical(canvas, clientX, clientY, logicalW, logicalH)` —
  maps pointer-event client coordinates to canvas logical units using
  `getBoundingClientRect` + `logicalW / rect.width` scale. DPR is not
  part of the transform because `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`
  already maps logical → backing-store, and hit areas live in logical
  space.

### Selection + hover semantics

- **Click a block** → `dispatch({ type: "SELECT", blockId })`. Mirrors
  the existing LeftPanel pathway exactly.
- **Click empty canvas** → `dispatch({ type: "SELECT", blockId: null })`.
  This is new behaviour (LeftPanel never deselects) but matches the
  implicit deselect path that `SWITCH_TPL` / `IMPORT` already take and
  is the standard canvas-editor interaction.
- **Hover** → `setHoveredBlockId(hit)` with an identity-check bail-out
  so mousemove inside the same block does not trigger overlay redraws.
- **Hover state is component-local `useState`**, not in the reducer.
  It is ephemeral UI: never persisted, never audited, never permission-
  gated.
- **`SELECT` is always allowed** by both the mode-axis and workflow
  gates (`permissions.ts`, `workflow.test.ts` case 23) — canvas
  click-to-select works even in `published`, `approved`, `exported`,
  and `in_review`. Selection is navigation, not mutation.

### Overlay rendering

`renderer/overlay.ts` (pure function) draws outlines:

- **Selection**: `TK.c.acc`, 2px solid. Matches the accent colour
  LeftPanel uses for its selected row border.
- **Hover**: `TK.c.txtS`, 1px dashed. Subtle mid-grey, distinct from
  selection.

When the hover target equals the selected block, the hover outline is
suppressed so outlines do not stack. When they differ, hover is drawn
first and selection on top. The overlay effect reads from
`hitAreasRef.current` and depends on `[selId, hoveredBlockId, sz, doc,
pal]`; `doc`/`pal` appear in the dep array so the overlay reconciles
after a content change that shifts block rects.

### Read-only / published behaviour

Click-to-select and hover remain functional in every read-only
workflow state. This is intentional: review and approval flows need
selection to drive the Inspector and Review panel even when edits are
disabled.

### Outline colour tokens

The overlay canvas uses two distinct tokens for its two outline states:

| State    | Token        | Value (at time of writing) | Rationale |
|----------|--------------|----------------------------|-----------|
| Hover    | `TK.c.txtS`  | `#8B949E` (secondary grey) | Subtle, doesn't compete visually with selection |
| Selected | `TK.c.acc`   | `#FBBF24` (yellow accent)  | Matches LeftPanel selection highlight semantics |

Historical note: an earlier iteration of the Task 1 spec referenced
`TK.c.fgSec` and `TK.c.bgAct`. Neither is usable:

- `fgSec` does not exist in `config/tokens.ts`.
- `bgAct` is a background fill (`#22252D`, dark grey), not viable as a
  stroke on a dark canvas.

`txtS` and `acc` are the confirmed equivalents in use. Both
definitions live in `renderer/overlay.ts#OVERLAY_STYLE` as the single
source of truth; changing outline colours means editing that one
const.

### Hit area clamping to section bounds

Each block's `hitArea` (from `RenderResult.hitArea`) is clamped to its
owning section's rect before being stored in `hitAreasRef`. This closes
a theoretical cross-section hit-steal scenario where an overflowing
block renderer returns a `hitArea.h` that extends past the visible
section — the content canvas clips draws to the section rect, but raw
hit areas don't, so uncovered pixels in an adjacent section could
match the overflowing block and steal selection from its actual
occupant.

Mechanics:

- `renderer/engine.ts#renderDoc` now returns
  `Array<RenderedBlockEntry>` where each entry carries the block's
  `sectionRect` alongside its `RenderResult`.
- `index.tsx` calls
  `clampRectToSection(entry.result.hitArea, entry.sectionRect)` before
  writing into `hitAreasRef`.
- `utils/hit-test.ts#clampRectToSection` is a pure function that
  returns the rectangle intersection; an empty intersection collapses
  to a zero-area rect that `hitTest` can never match.

Clamping is per-section (not canvas-wide) because two overflowing
blocks in different sections could otherwise still fight for the same
pixels through the canvas-wide clamp.

### Input scope: mouse events only

Task 1 wires `onMouseDown`, `onMouseMove`, and `onMouseLeave` on the
content canvas. Touch and stylus events are **not** handled.

This is a conscious scope choice for Stage 4:

- The admin surface is desktop-only.
- Touch/stylus would require `onPointerDown` / `onPointerMove` with
  pointer-capture semantics, plus consideration for long-press vs tap
  vs drag.
- Adding pointer events in a follow-up is a small change (swap the
  four event names, adjust the type) with no architectural impact.

If admin use on tablets becomes a requirement, migrate to the unified
pointer model in a dedicated PR. Until then, mouse events are
sufficient.

## Autosave (Stage 4 Task 2)

Task 2 adds automatic persistence on top of the manual Ctrl+S path from
Task 0. There is no `localStorage` backup and no offline queue — the
autosave operates directly against the admin proxy, same as Ctrl+S.

### Trigger

- Debounce: `AUTOSAVE_DEBOUNCE_MS = 2000` quiet milliseconds after the
  last mutating reducer action.
- Implementation: a `useEffect` with `[state.doc, state.dirty,
  publicationId, performSave]` in its dependency array. Every mutating
  reducer action returns a new `state.doc` reference; navigational
  actions (`SELECT`, `SET_MODE`, `SAVED_IF_MATCHES`, `SAVE_FAILED`,
  `DISMISS_SAVE_ERROR`) preserve reference. Watching `doc` alone is
  therefore a clean "did content change" signal — no new reducer
  actions or fields were added.
- A new edit cancels and reschedules the pending timer via the effect's
  cleanup function.
- Ctrl+S cancels any pending timer and fires an immediate save. Same
  code path as autosave (both call `performSave`); the Ctrl+S handler
  additionally clears `autosaveTimerRef.current` before invoking
  `performSave` so the scheduled PATCH does not fire redundantly.

### Status indicator

`SaveStatus = 'idle' | 'pending' | 'saving' | 'error'` is local
component state, not reducer state. It exists only for the TopBar
`SaveStatusIndicator`; storing it in the reducer would pollute undo
history and serialisation.

| saveStatus | dirty | TopBar glyph                            |
|------------|-------|-----------------------------------------|
| idle       | false | nothing (fully saved)                   |
| idle       | true  | amber dot, "Unsaved changes"            |
| pending    | true  | amber dot, "Unsaved changes"            |
| saving     | true  | amber dot pulsing, "Saving…"            |
| error      | any   | red dot, "Save failed"                  |

The pulse uses `@keyframes summa-save-pulse` in `app/globals.css` (50%
opacity dip). Token palette: amber = `TK.c.acc`, red = `TK.c.err`.

### Failure handling — exponential backoff

- `SAVE_FAILED` populates `state.saveError` (unchanged from Task 0 fix).
- An orthogonal `useEffect` watches `state.saveError` AND a monotonic
  `saveFailureGen` counter, scheduling auto-retries via setTimeout at
  `RETRY_DELAYS_MS = [2000, 4000, 8000, 16000]`. The failure-generation
  counter is required because React dep comparison uses `Object.is`;
  without it, successive failures with the same error string would
  leave the dep array unchanged and the effect would not re-run.

**Auto-retry applies only to retryable failures.** Terminal errors
(404 — `AdminPublicationNotFoundError`) bypass the retry schedule
entirely; the banner shows with a manual "Retry now" button that the
user can invoke explicitly. Retryability is tracked via a local
`canAutoRetryRef` (not a reducer field): `performSave.catch` flips it
to `false` on 404 and `true` on any other failure, and the retry
effect short-circuits when the flag is `false`. Any new user edit
resets the flag back to `true`, so subsequent failures are eligible
for the full backoff cycle again. Manual "Retry now" also resets it.

After four failed auto-retries on a retryable error, the banner
persists with "Retry now" until the user acts or edits.

**Single-scheduler invariant.** While `saveError` is set, the debounce
effect no-ops. The retry effect is the sole save orchestrator during
error-state. A new user edit resets retry state, and the retry effect
schedules the next attempt at `RETRY_DELAYS_MS[0] = 2000ms` —
functionally identical to the debounce window, but emitted by one
effect instead of two racing. The edit-reset effect is declared
before the retry effect so `retryAttemptRef` is zeroed before the
retry effect body reads it.

**Terminal-error dismiss.** Dismissing a 404 banner clears `saveError`
but does NOT re-enable auto-retry. The debounce effect checks
`canAutoRetryRef.current` in addition to `state.saveError` and
short-circuits while the terminal flag is `false`. Auto-scheduling
resumes only when the user makes a new edit (which resets the flag via
the edit-reset effect) or clicks "Retry now" (which resets it
explicitly). `canAutoRetryRef` is read from the effect body, not
added to the dependency array — the existing `state.saveError`
transition to `null` on dismiss already re-runs the effect and lets
it observe the current ref value.

**Slow-PATCH re-arm.** The debounce callback checks `savingRef.current`
before invoking `performSave`. If a previous PATCH is still in flight
the callback would otherwise no-op (performSave's own guard) and
silently drop any pending edits until the next mutating action or
Ctrl+S. Instead, the callback recursively re-arms itself one
`AUTOSAVE_DEBOUNCE_MS` cycle later. The re-arm is bounded: each
iteration waits the full debounce window, and re-arm only triggers
while `savingRef` is set, so a healthy save loop does not spin.

- A new mutating user edit resets `retryAttemptRef.current` to 0 and
  `canAutoRetryRef.current` to `true` so the next failure re-enters
  the delay schedule from `delay[0]` and auto-retry is eligible.
- The retry schedule is driven by an effect, not by `performSave`'s
  `.catch`, so the save function stays pure and reusable from the
  debounce path and the Ctrl+S / Retry-now paths.

### NotificationBanner extension

The save-error branch now renders:
- "Retrying in Xs…" (live countdown, ticks every 250ms) when
  `retryCountdownMs != null`.
- "Retry now" button when `onManualRetry` is provided.
- Existing Dismiss button (dispatches `DISMISS_SAVE_ERROR`).

The other three tiers (import-error, rejection, warnings) are
untouched.

### `beforeunload` guard

While `state.dirty === true`, a `beforeunload` listener is attached to
`window`. It calls `preventDefault()` + assigns `returnValue = ''` to
trigger the native "leave site?" prompt. Modern browsers ignore custom
messages; the guard is only concerned with triggering the prompt at
all. This covers the 2-second window between an edit and the next
scheduled save.

### What this task deliberately does NOT include

- No `localStorage` backup. If the backend is unreachable and the tab
  closes, the current 2s window of edits is lost. Acceptable for
  Stage 4 scope.
- No pause-on-tab-hidden behaviour. Timers continue to fire when the
  tab is backgrounded.
- No permission gate inside `performSave` — workflow gating is already
  enforced at the reducer layer, so dirty/non-dirty is a sufficient
  signal for whether a PATCH should fire.
- Pointer/touch input for debounce reset (covered by the mouse-events
  scope note for Task 1 above).

## Debug overlay (Stage 4 Task 4)

Dev-only visualization layer that makes `SECTION_LAYOUT` rects and
per-block hit areas visible. The whole point is to surface what
`clampRectToSection` silently fixes — a block returning a raw
`hitArea` that extends past its owning section is invisible during
normal rendering and only shows up here.

### What it shows

- **Section boundaries** — translucent fill + stroke + label per
  section type (cyan header, magenta hero, lime context, amber chart,
  orange footer). All 5 `SECTION_LAYOUT` keys are covered; unknown
  types are skipped silently.
- **Block bounding boxes** — white outline for each block's clamped
  `hitArea`, with a `<blockType>·<blockIdPrefix>` label rendered in
  JetBrains Mono.
- **Overflow markers** — when a block's raw `hitArea` extends beyond
  its `sectionRect`, a dashed red outline is drawn around the raw
  rect alongside the white clamped outline. This is the signal that
  the Task 1 clamping fix is actively clipping.

### When it's available

- **Development** (`NODE_ENV !== 'production'`): always. Toggle via
  the TopBar `DBG` button or `Ctrl+Shift+D`.
- **Production**: only when `?debug=1` is present in the URL. The
  toggle becomes visible; the user still has to click or shortcut to
  enable. The query param controls *availability*, not *state*,
  so accidentally sharing a link with `?debug=1` does not leak the
  overlay to the next viewer.

The `?debug=1` check runs once on mount via a `useEffect` that reads
`window.location.search`. `useSearchParams` from `next/navigation` is
deliberately avoided — the plain browser API requires no Suspense
boundary and keeps the editor component framework-lean.

### Architecture

- **Third canvas sibling** in `components/Canvas.tsx`, conditionally
  rendered on the truthiness of the `debugRef` prop. When
  `debugEnabled === false`, `InfographicEditor` passes `undefined`
  and React unmounts the canvas entirely — no backing store, no
  draw cost. Render order: content canvas → hover/selection
  overlay → debug overlay (LAST, so labels render on top).
- **`debugEntriesRef` and `debugSectionsRef`** populated inside the
  same content-render callback that writes `hitAreasRef`. Populated
  only when `debugEnabled === true`; zero cost when off. Both refs
  derive from the same `RenderedBlockEntry[]` array so they cannot
  drift.
- **`renderDebugOverlay`** in `renderer/debug-overlay.ts` mirrors
  the API shape of `renderer/overlay.ts` (DPR handling, transform
  preamble, small `draw*` helpers) but shares no code. Debug and
  selection-overlay have independent lifecycles — one is dev-only,
  the other is always on.
- **`DEBUG_PALETTE`** is a module-local constant using `rgba()`
  literals. Not part of `TK` tokens — debug colours are developer
  tooling, not design-system output.

### Shortcut behaviour

`Ctrl+Shift+D` (or `Cmd+Shift+D` on macOS) toggles `debugEnabled`.
The branch is evaluated *before* the `isEditable` gate in the
keydown handler because the shortcut is never a meaningful text
editing combo — it must work from inside Inspector inputs too. The
branch bails when `debugAvailable === false`, so production users
without `?debug=1` cannot flip it.

### Independence from permissions

The toggle has no interaction with `effectivePerms` / workflow
state. A `published` document that is otherwise read-only still
shows the DBG button to a developer in dev or a `?debug=1` session
— debug is diagnostic, not authoring.

### Coordination with font gating

Debug-overlay labels use `TK.font.data` (JetBrains Mono). Once the
forthcoming font gate (Stage 4 Task 3) lands, the debug render
effect will need the same `fontsReady` gate as content rendering to
avoid fallback-font labels during the first-load window. Until
then, labels may render briefly with system monospace on a cold
cache. Non-blocking for dev tooling.

### Explicit non-goals

- Safe-zone overlay for export presets. Deferred to a later Stage 4
  task.
- Performance metrics (render timings, draw-call counts). Out of
  scope.
- Interactive picks on the debug overlay. Read-only visualization
  only; the hover/selection canvas continues to own pointer
  affordances.

