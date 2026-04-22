import type {
  CanonicalDocument,
  Comment,
  CommentAction,
  EditorState,
  WorkflowHistoryEntry,
} from '../types';
import { makeId } from '../utils/ids';
import { getProvider, resolveActor, withRejection } from './reducer';

// ────────────────────────────────────────────────────────────────────
// Comments subsystem
//
// Comment actions live OUTSIDE undo/redo. Rationale:
//   • Ownership: an EDIT/DELETE gated on `author === actor` becomes
//     meaningless if an UNDO can silently restore or obliterate another
//     user's note.
//   • Audit integrity: comment events are audited via doc.review.history
//     entries, which must not be rewindable by a content-stack UNDO.
//   • Convention: Figma, Linear, and Google Docs all keep review comments
//     off the document-content undo timeline.
//
// The invariant "comment actions do not push snapshots" is enforced at
// each `applyXxx` below — they never call the reducer's `push` helper and
// never touch `undoStack`, `redoStack`, or `_lastAction`. `dirty` flips to
// true so the SAVED clear path still works.
// ────────────────────────────────────────────────────────────────────

/** Derived thread node: a root comment plus its flat reply list. */
export interface CommentThreadNode extends Comment {
  replies: Comment[];
}

/**
 * Group a flat comment list into root-and-reply threads.
 * one-level invariant — see `threadUnresolvedCount` for details.
 *
 * Roots sorted newest-first by `createdAt`; replies sorted oldest-first
 * within each thread. Orphaned replies (parentId points to missing comment)
 * are promoted to roots so they remain visible in the UI.
 */
export function buildThreads(comments: readonly Comment[]): CommentThreadNode[] {
  const byId = new Map<string, CommentThreadNode>();
  for (const c of comments) byId.set(c.id, { ...c, replies: [] });

  const roots: CommentThreadNode[] = [];
  for (const node of byId.values()) {
    if (node.parentId && byId.has(node.parentId)) {
      byId.get(node.parentId)!.replies.push(node);
    } else {
      roots.push(node);
    }
  }
  for (const node of byId.values()) {
    node.replies.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }
  roots.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return roots;
}

/**
 * Counts unresolved nodes in a thread (root + direct replies).
 *
 * ONE-LEVEL INVARIANT: This function assumes the thread is at most one level
 * deep (root + replies). This matches the current data model, which is
 * enforced by:
 *   - `applyReplyToComment` (rejects reply-to-reply in the reducer)
 *   - `assertCanonicalDocumentV2Shape` (rejects reply-to-reply in imported docs)
 *
 * If multi-level threading is ever permitted, this function must be made
 * recursive. Do not change it in isolation — the enforcement in the reducer
 * and validator, plus the `CommentThreadNode` shape, and the UI layer all
 * assume flat one-level threads.
 */
export function threadUnresolvedCount(thread: CommentThreadNode): number {
  const root = thread.resolved ? 0 : 1;
  const replies = thread.replies.filter((r) => !r.resolved).length;
  return root + replies;
}

/**
 * Derived status: thread is resolved iff every node in it is resolved.
 * one-level invariant — see `threadUnresolvedCount` for details.
 */
export function isThreadResolved(thread: CommentThreadNode): boolean {
  return threadUnresolvedCount(thread) === 0;
}

/**
 * Collect the full subtree of descendant ids rooted at `rootId` (inclusive).
 * BFS over `parentId` edges so DELETE_COMMENT can remove a root plus every
 * reply, even if the UI ever grows beyond single-level nesting.
 */
export function collectDescendantIds(
  comments: readonly Comment[],
  rootId: string,
): Set<string> {
  const ids = new Set<string>([rootId]);
  const queue: string[] = [rootId];
  while (queue.length) {
    const parent = queue.shift()!;
    for (const c of comments) {
      if (c.parentId === parent && !ids.has(c.id)) {
        ids.add(c.id);
        queue.push(c.id);
      }
    }
  }
  return ids;
}

// ────────────────────────────────────────────────────────────────────
// Display helpers (pure)
// ────────────────────────────────────────────────────────────────────

const BLOCK_LABELS: Record<string, string> = {
  eyebrow_tag: "Eyebrow",
  headline_editorial: "Headline",
  subtitle_descriptor: "Subtitle",
  hero_stat: "Hero stat",
  delta_badge: "Delta badge",
  body_annotation: "Annotation",
  source_footer: "Source",
  brand_stamp: "Brand stamp",
  bar_horizontal: "Ranked bars",
  line_editorial: "Line chart",
  comparison_kpi: "KPI compare",
  table_enriched: "Visual table",
  small_multiple: "Small multiples",
};

/**
 * @deprecated Dev-only helper for reducer-level audit/log text.
 * Use `useTranslations('block.type')(\`${type}.name\`)` for user-visible labels.
 */
export function blockDisplayLabel(blockType: string | undefined): string {
  if (!blockType) return "block";
  return BLOCK_LABELS[blockType] ?? blockType;
}

export function truncate(s: string, n: number): string {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "\u2026" : s;
}

// ────────────────────────────────────────────────────────────────────
// Internal shared helpers
// ────────────────────────────────────────────────────────────────────

const TEXT_TRUNCATE_LEN = 60;

function labelFor(doc: CanonicalDocument, blockId: string): string {
  const block = doc.blocks[blockId];
  return block ? blockDisplayLabel(block.type) : blockId;
}

function appendHistory(
  doc: CanonicalDocument,
  entry: WorkflowHistoryEntry,
): CanonicalDocument {
  return {
    ...doc,
    review: {
      ...doc.review,
      history: [...doc.review.history, entry],
    },
  };
}

function historyEntry(
  action: string,
  summary: string,
  ts: string,
  author: string,
): WorkflowHistoryEntry {
  return {
    ts,
    action,
    summary,
    author,
    fromWorkflow: null,
    toWorkflow: null,
  };
}

/**
 * Wrap a new doc with meta.updatedAt refreshed and stamp the editor state
 * without touching undoStack / redoStack / _lastAction. Shared shape for every
 * successful comment mutation.
 */
function commitCommentMutation(
  state: EditorState,
  nextDoc: CanonicalDocument,
  ts: string,
): EditorState {
  return {
    ...state,
    doc: { ...nextDoc, meta: { ...nextDoc.meta, updatedAt: ts } },
    dirty: true,
    _lastRejection: undefined,
  };
}

function findComment(doc: CanonicalDocument, id: string): Comment | undefined {
  return doc.review.comments.find((c) => c.id === id);
}

function replaceComment(
  comments: readonly Comment[],
  id: string,
  patch: Partial<Comment>,
): Comment[] {
  return comments.map((c) => (c.id === id ? { ...c, ...patch } : c));
}

// ────────────────────────────────────────────────────────────────────
// Reducer applyXxx entry points
// ────────────────────────────────────────────────────────────────────

export function applyAddComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'ADD_COMMENT' }>,
): EditorState {
  if (!state.doc.blocks[action.blockId]) {
    return withRejection(state, action.type, `Block "${action.blockId}" not found.`);
  }
  const text = action.text.trim();
  if (text.length === 0) {
    return withRejection(state, action.type, "Comment text must not be empty.");
  }

  const id = action.id ?? makeId();
  const ts = action.ts ?? getProvider(state).now();
  const author = resolveActor(action);

  const comment: Comment = {
    id,
    blockId: action.blockId,
    parentId: null,
    author,
    text,
    createdAt: ts,
    updatedAt: null,
    resolved: false,
    resolvedAt: null,
    resolvedBy: null,
  };

  const label = labelFor(state.doc, action.blockId);
  const summary = `Comment on ${label}: "${truncate(text, TEXT_TRUNCATE_LEN)}"`;
  const entry = historyEntry("comment_added", summary, ts, author);

  let nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: [...state.doc.review.comments, comment],
    },
  };
  nextDoc = appendHistory(nextDoc, entry);

  return commitCommentMutation(state, nextDoc, ts);
}

export function applyReplyToComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'REPLY_TO_COMMENT' }>,
): EditorState {
  const parent = findComment(state.doc, action.parentId);
  if (!parent) {
    return withRejection(state, action.type, `Parent comment "${action.parentId}" not found.`);
  }
  // One-level threading: replies can only be posted on root comments.
  // `buildThreads` / `threadUnresolvedCount` / `isThreadResolved` are flat by
  // design; allowing reply-to-reply would silently misrepresent thread shape.
  if (parent.parentId !== null) {
    return withRejection(
      state,
      action.type,
      "Replies can only be posted on root comments (threading depth is one level).",
    );
  }
  const text = action.text.trim();
  if (text.length === 0) {
    return withRejection(state, action.type, "Comment text must not be empty.");
  }

  const id = action.id ?? makeId();
  const ts = action.ts ?? getProvider(state).now();
  const author = resolveActor(action);

  const comment: Comment = {
    id,
    blockId: parent.blockId,
    parentId: parent.id,
    author,
    text,
    createdAt: ts,
    updatedAt: null,
    resolved: false,
    resolvedAt: null,
    resolvedBy: null,
  };

  const label = labelFor(state.doc, parent.blockId);
  const summary = `Replied on ${label}: "${truncate(text, TEXT_TRUNCATE_LEN)}"`;
  const entry = historyEntry("comment_replied", summary, ts, author);

  let nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: [...state.doc.review.comments, comment],
    },
  };
  nextDoc = appendHistory(nextDoc, entry);

  return commitCommentMutation(state, nextDoc, ts);
}

export function applyEditComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'EDIT_COMMENT' }>,
): EditorState {
  const target = findComment(state.doc, action.commentId);
  if (!target) {
    return withRejection(state, action.type, `Comment "${action.commentId}" not found.`);
  }
  const actor = resolveActor(action);
  if (target.author !== actor) {
    return withRejection(state, action.type, "You can edit only your own comments.");
  }
  const text = action.text.trim();
  if (text.length === 0) {
    return withRejection(state, action.type, "Comment text must not be empty.");
  }

  const ts = action.ts ?? getProvider(state).now();

  // Lean audit: EDIT does not write to review.history.
  const nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: replaceComment(state.doc.review.comments, action.commentId, {
        text,
        updatedAt: ts,
      }),
    },
  };

  return commitCommentMutation(state, nextDoc, ts);
}

export function applyResolveComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'RESOLVE_COMMENT' }>,
): EditorState {
  const target = findComment(state.doc, action.commentId);
  if (!target) {
    return withRejection(state, action.type, `Comment "${action.commentId}" not found.`);
  }
  // No-op: resolving an already-resolved comment does not error.
  if (target.resolved) {
    return { ...state, _lastRejection: undefined };
  }

  const ts = action.ts ?? getProvider(state).now();
  const author = resolveActor(action);

  const label = labelFor(state.doc, target.blockId);
  const entry = historyEntry(
    "comment_resolved",
    `Resolved comment on ${label}`,
    ts,
    author,
  );

  let nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: replaceComment(state.doc.review.comments, action.commentId, {
        resolved: true,
        resolvedAt: ts,
        resolvedBy: author,
      }),
    },
  };
  nextDoc = appendHistory(nextDoc, entry);

  return commitCommentMutation(state, nextDoc, ts);
}

export function applyReopenComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'REOPEN_COMMENT' }>,
): EditorState {
  const target = findComment(state.doc, action.commentId);
  if (!target) {
    return withRejection(state, action.type, `Comment "${action.commentId}" not found.`);
  }
  if (!target.resolved) {
    return { ...state, _lastRejection: undefined };
  }

  const ts = action.ts ?? getProvider(state).now();
  const author = resolveActor(action);

  const label = labelFor(state.doc, target.blockId);
  const entry = historyEntry(
    "comment_reopened",
    `Reopened comment on ${label}`,
    ts,
    author,
  );

  let nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: replaceComment(state.doc.review.comments, action.commentId, {
        resolved: false,
        resolvedAt: null,
        resolvedBy: null,
      }),
    },
  };
  nextDoc = appendHistory(nextDoc, entry);

  return commitCommentMutation(state, nextDoc, ts);
}

/** Tombstone marker used when a delete cannot physically remove a comment
 *  because the subtree contains foreign-authored replies. The marker shape
 *  preserves every field except `text` / `author` / `updatedAt` so threading,
 *  resolution status, and block anchoring remain intact. */
export const TOMBSTONE_AUTHOR = "[deleted]";
export const TOMBSTONE_TEXT = "[deleted]";

export function applyDeleteComment(
  state: EditorState,
  action: Extract<CommentAction, { type: 'DELETE_COMMENT' }>,
): EditorState {
  const target = findComment(state.doc, action.commentId);
  if (!target) {
    return withRejection(state, action.type, `Comment "${action.commentId}" not found.`);
  }
  const actor = resolveActor(action);
  if (target.author !== actor) {
    return withRejection(state, action.type, "You can delete only your own comments.");
  }

  const ts = action.ts ?? getProvider(state).now();
  const subtreeIds = collectDescendantIds(state.doc.review.comments, action.commentId);
  const hasReplies = subtreeIds.size > 1;
  const subtreeComments = state.doc.review.comments.filter((c) => subtreeIds.has(c.id));
  // Physical delete is safe iff every node in the subtree is authored by the
  // actor (or is already a tombstone from a prior delete). Otherwise the
  // delete would obliterate another user's note, violating the ownership
  // contract. Previously-tombstoned nodes count as actor-owned because no
  // live author is losing content.
  const actorOwnsEntireSubtree = subtreeComments.every(
    (c) => c.author === actor || c.author === TOMBSTONE_AUTHOR,
  );

  const label = labelFor(state.doc, target.blockId);
  let nextComments: Comment[];
  let summary: string;

  if (!hasReplies || actorOwnsEntireSubtree) {
    // Physical removal — safe: nothing foreign is being dropped.
    nextComments = state.doc.review.comments.filter((c) => !subtreeIds.has(c.id));
    const extraCount = subtreeIds.size - 1;
    summary =
      extraCount > 0
        ? `Deleted comment on ${label} (+ ${extraCount} repl${extraCount === 1 ? "y" : "ies"})`
        : `Deleted comment on ${label}`;
  } else {
    // Tombstone the target in place so foreign replies remain visible and
    // threaded. Preserve id / blockId / parentId / createdAt / resolved state.
    nextComments = state.doc.review.comments.map((c) =>
      c.id === action.commentId
        ? { ...c, text: TOMBSTONE_TEXT, author: TOMBSTONE_AUTHOR, updatedAt: ts }
        : c,
    );
    summary = `Deleted comment on ${label} (tombstoned — has replies from other authors)`;
  }

  const entry = historyEntry("comment_deleted", summary, ts, actor);

  let nextDoc: CanonicalDocument = {
    ...state.doc,
    review: {
      ...state.doc.review,
      comments: nextComments,
    },
  };
  nextDoc = appendHistory(nextDoc, entry);

  return commitCommentMutation(state, nextDoc, ts);
}

/** Discriminator set used by the reducer + permission gate to recognise
 *  comment-lifecycle action types. */
export const COMMENT_ACTION_TYPES = [
  "ADD_COMMENT",
  "REPLY_TO_COMMENT",
  "EDIT_COMMENT",
  "RESOLVE_COMMENT",
  "REOPEN_COMMENT",
  "DELETE_COMMENT",
] as const;

export type CommentActionType = typeof COMMENT_ACTION_TYPES[number];

export function isCommentAction(action: { type: string }): action is CommentAction {
  return (COMMENT_ACTION_TYPES as readonly string[]).includes(action.type);
}
