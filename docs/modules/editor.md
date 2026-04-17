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
- `doc.meta` must not contain a `schemaVersion` field. `validateImport` rejects
  documents that do.
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
  v2 invariant. Throws with a precise message on any violation.

The legacy string-returning `validateImport(doc): string | null` is preserved
for existing call sites (reducer, `index.tsx`); Stage 3 PR 2 migrates them to
the throwing API. Tracked as `DEBT-022`.

### Stage 3 artifact history

The long-term intent for the review subsystem was sketched across two artifact
files kept under `docs/editor/` (`infographic-editor-stage3a-v2.jsx`,
`infographic-editor-stage3b-v2.jsx`). Those artifacts split review state across
three fields (`doc.meta.workflow`, `doc.meta.history`, `doc.comments`) as a
compromise during incremental artifact development. Stage 3 PR 1 consolidates
all three into `doc.review` and removes the dual-write of `schemaVersion`.
