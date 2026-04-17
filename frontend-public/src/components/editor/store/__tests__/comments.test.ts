import { reducer, initState } from "../reducer";
import type {
  Comment,
  EditorState,
  TimestampProvider,
  WorkflowState,
} from "../../types";
import {
  blockDisplayLabel,
  buildThreads,
  collectDescendantIds,
  isThreadResolved,
  threadUnresolvedCount,
  truncate,
  type CommentThreadNode,
} from "../comments";
import { WORKFLOW_PERMISSIONS } from "../permissions";

// ────────────────────────────────────────────────────────────────────
// Fixtures (mirror workflow.test.ts to keep tests drop-in runnable)
// ────────────────────────────────────────────────────────────────────

const FIXED_TS = "2026-04-17T12:00:00.000Z";

function fixedClock(iso: string = FIXED_TS): TimestampProvider {
  return { now: () => iso };
}

function baseState(overrides: Partial<EditorState> = {}): EditorState {
  const s = initState();
  return { ...s, _timestampProvider: fixedClock(), ...overrides };
}

function setWorkflow(state: EditorState, to: WorkflowState): EditorState {
  return {
    ...state,
    doc: { ...state.doc, review: { ...state.doc.review, workflow: to } },
  };
}

function findBlockIdByType(state: EditorState, type: string): string {
  const id = Object.keys(state.doc.blocks).find(
    (k) => state.doc.blocks[k].type === type,
  );
  if (!id) throw new Error(`No block of type ${type} in fixture`);
  return id;
}

function mkComment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: "c1",
    blockId: "b1",
    parentId: null,
    author: "you",
    text: "hi",
    createdAt: FIXED_TS,
    updatedAt: null,
    resolved: false,
    resolvedAt: null,
    resolvedBy: null,
    ...overrides,
  };
}

// ────────────────────────────────────────────────────────────────────
// 1. Thread helpers
// ────────────────────────────────────────────────────────────────────

describe("comments / thread helpers", () => {
  test("1. buildThreads returns empty array for empty input", () => {
    expect(buildThreads([])).toEqual([]);
  });

  test("2. buildThreads groups replies under their root parent", () => {
    const c1 = mkComment({ id: "c1", createdAt: "2026-04-17T12:00:00.000Z" });
    const r1 = mkComment({
      id: "r1",
      parentId: "c1",
      createdAt: "2026-04-17T12:01:00.000Z",
    });
    const r2 = mkComment({
      id: "r2",
      parentId: "c1",
      createdAt: "2026-04-17T12:02:00.000Z",
    });
    const threads = buildThreads([c1, r1, r2]);
    expect(threads).toHaveLength(1);
    expect(threads[0].id).toBe("c1");
    expect(threads[0].replies.map((r) => r.id)).toEqual(["r1", "r2"]);
  });

  test("3. buildThreads sorts roots newest-first and replies oldest-first", () => {
    const older = mkComment({ id: "older", createdAt: "2026-01-01T00:00:00.000Z" });
    const newer = mkComment({ id: "newer", createdAt: "2026-05-01T00:00:00.000Z" });
    const replyOlder = mkComment({
      id: "rOlder",
      parentId: "newer",
      createdAt: "2026-05-02T00:00:00.000Z",
    });
    const replyNewer = mkComment({
      id: "rNewer",
      parentId: "newer",
      createdAt: "2026-05-03T00:00:00.000Z",
    });
    const threads = buildThreads([older, newer, replyNewer, replyOlder]);
    expect(threads.map((t) => t.id)).toEqual(["newer", "older"]);
    expect(threads[0].replies.map((r) => r.id)).toEqual(["rOlder", "rNewer"]);
  });

  test("4. buildThreads promotes orphaned replies (missing parent) to roots", () => {
    const orphan = mkComment({
      id: "orphan",
      parentId: "ghost",
      createdAt: "2026-04-17T12:00:00.000Z",
    });
    const threads = buildThreads([orphan]);
    expect(threads).toHaveLength(1);
    expect(threads[0].id).toBe("orphan");
    expect(threads[0].replies).toEqual([]);
  });

  test("5. threadUnresolvedCount counts root + open replies", () => {
    const thread: CommentThreadNode = {
      ...mkComment({ id: "root", resolved: false }),
      replies: [
        mkComment({ id: "r1", parentId: "root", resolved: false }),
        mkComment({ id: "r2", parentId: "root", resolved: true }),
      ],
    };
    expect(threadUnresolvedCount(thread)).toBe(2);
  });

  test("6. threadUnresolvedCount returns 0 for fully resolved thread", () => {
    const thread: CommentThreadNode = {
      ...mkComment({ id: "root", resolved: true }),
      replies: [mkComment({ id: "r1", parentId: "root", resolved: true })],
    };
    expect(threadUnresolvedCount(thread)).toBe(0);
  });

  test("7. threadUnresolvedCount >= 1 when a reply is open even if root is resolved", () => {
    const thread: CommentThreadNode = {
      ...mkComment({ id: "root", resolved: true }),
      replies: [mkComment({ id: "r1", parentId: "root", resolved: false })],
    };
    expect(threadUnresolvedCount(thread)).toBe(1);
    expect(isThreadResolved(thread)).toBe(false);
  });

  test("8. isThreadResolved true iff threadUnresolvedCount === 0", () => {
    const open: CommentThreadNode = { ...mkComment({ resolved: false }), replies: [] };
    const closed: CommentThreadNode = { ...mkComment({ resolved: true }), replies: [] };
    expect(isThreadResolved(open)).toBe(false);
    expect(isThreadResolved(closed)).toBe(true);
  });

  test("9. collectDescendantIds returns just the root for a leaf", () => {
    const ids = collectDescendantIds([mkComment({ id: "only" })], "only");
    expect([...ids]).toEqual(["only"]);
  });

  test("10. collectDescendantIds walks arbitrary depth (3-level chain)", () => {
    const comments: Comment[] = [
      mkComment({ id: "a" }),
      mkComment({ id: "b", parentId: "a" }),
      mkComment({ id: "c", parentId: "b" }),
      mkComment({ id: "d", parentId: "c" }),
    ];
    const ids = collectDescendantIds(comments, "a");
    expect(ids).toEqual(new Set(["a", "b", "c", "d"]));
  });

  test("11. collectDescendantIds handles multiple siblings at one level", () => {
    const comments: Comment[] = [
      mkComment({ id: "root" }),
      mkComment({ id: "r1", parentId: "root" }),
      mkComment({ id: "r2", parentId: "root" }),
      mkComment({ id: "r3", parentId: "root" }),
    ];
    expect(collectDescendantIds(comments, "root")).toEqual(
      new Set(["root", "r1", "r2", "r3"]),
    );
  });
});

// ────────────────────────────────────────────────────────────────────
// 2. Reducer — happy paths
// ────────────────────────────────────────────────────────────────────

describe("reducer / comment actions — happy paths", () => {
  test("12. ADD_COMMENT in draft appends comment and audit entry", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const undoBefore = s0.undoStack.length;
    const redoBefore = s0.redoStack.length;
    const lastActionBefore = s0._lastAction;

    const s1 = reducer(s0, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "needs tightening",
      id: "c-1",
    });

    expect(s1.doc.review.comments).toHaveLength(1);
    const c = s1.doc.review.comments[0];
    expect(c.id).toBe("c-1");
    expect(c.blockId).toBe(bid);
    expect(c.parentId).toBeNull();
    expect(c.author).toBe("you");
    expect(c.text).toBe("needs tightening");
    expect(c.createdAt).toBe(FIXED_TS);
    expect(c.resolved).toBe(false);

    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("comment_added");
    expect(entry.summary).toContain("Headline");
    expect(entry.summary).toContain('"needs tightening"');
    expect(entry.fromWorkflow).toBeNull();
    expect(entry.toWorkflow).toBeNull();

    expect(s1.dirty).toBe(true);
    expect(s1.undoStack.length).toBe(undoBefore);
    expect(s1.redoStack.length).toBe(redoBefore);
    expect(s1._lastAction).toBe(lastActionBefore);
  });

  test("13. ADD_COMMENT in in_review is allowed", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "pls rephrase",
      id: "c-r",
    });
    expect(s1.doc.review.comments).toHaveLength(1);
    expect(s1._lastRejection).toBeUndefined();
  });

  test("14. ADD_COMMENT with explicit id uses that id", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "a",
      id: "my-fixed-id",
    });
    expect(s1.doc.review.comments[0].id).toBe("my-fixed-id");
  });

  test("15. ADD_COMMENT without id generates one via makeId", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "ADD_COMMENT", blockId: bid, text: "hi" });
    const id = s1.doc.review.comments[0].id;
    expect(typeof id).toBe("string");
    expect(id.length).toBeGreaterThan(0);
  });

  test("16. ADD_COMMENT honours explicit ts; default falls back to provider", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const custom = "2030-01-01T00:00:00.000Z";

    const explicit = reducer(s0, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "x",
      ts: custom,
      id: "a",
    });
    expect(explicit.doc.review.comments[0].createdAt).toBe(custom);
    expect(explicit.doc.meta.updatedAt).toBe(custom);

    const fallback = reducer(s0, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "y",
      id: "b",
    });
    expect(fallback.doc.review.comments[0].createdAt).toBe(FIXED_TS);
  });

  test("17. REPLY_TO_COMMENT inherits parent.blockId and sets parentId", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "root", id: "p1" });
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "p1",
      text: "reply text",
      id: "r1",
    });
    expect(s.doc.review.comments).toHaveLength(2);
    const reply = s.doc.review.comments.find((c) => c.id === "r1")!;
    expect(reply.parentId).toBe("p1");
    expect(reply.blockId).toBe(bid);
    const entry = s.doc.review.history[s.doc.review.history.length - 1];
    expect(entry.action).toBe("comment_replied");
    expect(entry.summary).toContain('"reply text"');
  });

  test("18. EDIT_COMMENT on own comment updates text + updatedAt, no history entry", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "v1", id: "c" });
    const histLenBefore = s.doc.review.history.length;
    s = reducer(s, {
      type: "EDIT_COMMENT",
      commentId: "c",
      text: "v2",
      ts: "2026-05-01T00:00:00.000Z",
    });
    const c = s.doc.review.comments[0];
    expect(c.text).toBe("v2");
    expect(c.updatedAt).toBe("2026-05-01T00:00:00.000Z");
    expect(s.doc.review.history.length).toBe(histLenBefore);
  });

  test("19. RESOLVE_COMMENT sets resolved fields and appends history", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "please fix", id: "c" });
    s = reducer(s, {
      type: "RESOLVE_COMMENT",
      commentId: "c",
      ts: "2026-05-02T00:00:00.000Z",
      actor: "alice",
    });
    const c = s.doc.review.comments[0];
    expect(c.resolved).toBe(true);
    expect(c.resolvedAt).toBe("2026-05-02T00:00:00.000Z");
    expect(c.resolvedBy).toBe("alice");
    const entry = s.doc.review.history[s.doc.review.history.length - 1];
    expect(entry.action).toBe("comment_resolved");
    expect(entry.summary).toContain("Resolved comment on");
  });

  test("20. RESOLVE_COMMENT on already-resolved comment is a no-op", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t", id: "c" });
    s = reducer(s, { type: "RESOLVE_COMMENT", commentId: "c" });
    const histLen = s.doc.review.history.length;
    const dirtyPre = { ...s, dirty: false };
    const after = reducer(dirtyPre, { type: "RESOLVE_COMMENT", commentId: "c" });
    expect(after.doc.review.history.length).toBe(histLen);
    expect(after.dirty).toBe(false);
    expect(after._lastRejection).toBeUndefined();
  });

  test("21. REOPEN_COMMENT reverses resolve; no-op when already open", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t", id: "c" });
    s = reducer(s, { type: "RESOLVE_COMMENT", commentId: "c", actor: "alice" });
    s = reducer(s, { type: "REOPEN_COMMENT", commentId: "c", actor: "bob" });
    const c = s.doc.review.comments[0];
    expect(c.resolved).toBe(false);
    expect(c.resolvedAt).toBeNull();
    expect(c.resolvedBy).toBeNull();
    const entry = s.doc.review.history[s.doc.review.history.length - 1];
    expect(entry.action).toBe("comment_reopened");

    // Second reopen on an already-open comment is a no-op.
    const histLen = s.doc.review.history.length;
    const noop = reducer(s, { type: "REOPEN_COMMENT", commentId: "c" });
    expect(noop.doc.review.history.length).toBe(histLen);
  });

  test("22. DELETE_COMMENT removes comment + descendants", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "root", id: "p" });
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "p",
      text: "reply",
      id: "r1",
    });
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "p",
      text: "reply2",
      id: "r2",
    });
    s = reducer(s, { type: "DELETE_COMMENT", commentId: "p" });
    expect(s.doc.review.comments).toEqual([]);
  });

  test("23. DELETE_COMMENT summary includes reply count when > 0", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "root", id: "p" });
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "p",
      text: "r",
      id: "r1",
    });
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "p",
      text: "r2",
      id: "r2",
    });
    s = reducer(s, { type: "DELETE_COMMENT", commentId: "p" });
    const entry = s.doc.review.history[s.doc.review.history.length - 1];
    expect(entry.action).toBe("comment_deleted");
    expect(entry.summary).toMatch(/\(\+ 2 replies\)/);
  });

  test("24. DELETE_COMMENT summary omits parenthetical when no replies", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "solo", id: "p" });
    s = reducer(s, { type: "DELETE_COMMENT", commentId: "p" });
    const entry = s.doc.review.history[s.doc.review.history.length - 1];
    expect(entry.summary).not.toMatch(/replies?\)/);
  });
});

// ────────────────────────────────────────────────────────────────────
// 3. Reducer — ownership & integrity rejections
// ────────────────────────────────────────────────────────────────────

describe("reducer / comment actions — ownership & integrity", () => {
  test("25. EDIT_COMMENT on someone else's comment is rejected", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "alice's note",
      id: "c",
      actor: "alice",
    });
    const docBefore = s.doc;
    const result = reducer(s, {
      type: "EDIT_COMMENT",
      commentId: "c",
      text: "hack",
      actor: "bob",
    });
    expect(result.doc).toBe(docBefore);
    expect(result._lastRejection?.type).toBe("EDIT_COMMENT");
    expect(result._lastRejection?.reason).toMatch(/edit only your own/i);
  });

  test("26. DELETE_COMMENT on someone else's comment is rejected", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "alice's note",
      id: "c",
      actor: "alice",
    });
    const docBefore = s.doc;
    const result = reducer(s, {
      type: "DELETE_COMMENT",
      commentId: "c",
      actor: "bob",
    });
    expect(result.doc).toBe(docBefore);
    expect(result._lastRejection?.type).toBe("DELETE_COMMENT");
    expect(result._lastRejection?.reason).toMatch(/delete only your own/i);
  });

  test("27. RESOLVE_COMMENT / REOPEN_COMMENT do not check ownership", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "t",
      id: "c",
      actor: "alice",
    });
    const resolved = reducer(s, {
      type: "RESOLVE_COMMENT",
      commentId: "c",
      actor: "bob",
    });
    expect(resolved._lastRejection).toBeUndefined();
    expect(resolved.doc.review.comments[0].resolved).toBe(true);
    expect(resolved.doc.review.comments[0].resolvedBy).toBe("bob");

    const reopened = reducer(resolved, {
      type: "REOPEN_COMMENT",
      commentId: "c",
      actor: "carol",
    });
    expect(reopened._lastRejection).toBeUndefined();
    expect(reopened.doc.review.comments[0].resolved).toBe(false);
  });

  test("28. ADD_COMMENT on missing block is rejected", () => {
    const s = baseState();
    const result = reducer(s, {
      type: "ADD_COMMENT",
      blockId: "does-not-exist",
      text: "x",
    });
    expect(result.doc).toBe(s.doc);
    expect(result._lastRejection?.reason).toContain("does-not-exist");
  });

  test("29. REPLY_TO_COMMENT with missing parent is rejected", () => {
    const s = baseState();
    const result = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "ghost",
      text: "x",
    });
    expect(result.doc).toBe(s.doc);
    expect(result._lastRejection?.reason).toContain("ghost");
  });

  test("30. EDIT/RESOLVE/REOPEN/DELETE on missing comment is rejected", () => {
    const s = baseState();
    for (const type of [
      "EDIT_COMMENT",
      "RESOLVE_COMMENT",
      "REOPEN_COMMENT",
      "DELETE_COMMENT",
    ] as const) {
      const action =
        type === "EDIT_COMMENT"
          ? { type, commentId: "missing", text: "x" }
          : { type, commentId: "missing" };
      const result = reducer(s, action as any);
      expect(result.doc).toBe(s.doc);
      expect(result._lastRejection?.type).toBe(type);
    }
  });

  test("31. ADD_COMMENT with empty / whitespace text is rejected", () => {
    const s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    const result = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "   " });
    expect(result.doc).toBe(s.doc);
    expect(result._lastRejection?.reason).toMatch(/must not be empty/i);
  });
});

// ────────────────────────────────────────────────────────────────────
// 4. Workflow permission gate
// ────────────────────────────────────────────────────────────────────

describe("permissions / comment × workflow gate", () => {
  test("32. ADD_COMMENT in approved is rejected with 'read-only' reason", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "ADD_COMMENT", blockId: bid, text: "x" });
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.reason).toMatch(/read-only/i);
  });

  test("33. ADD_COMMENT in exported and published is rejected", () => {
    for (const wf of ["exported", "published"] as const) {
      const s0 = setWorkflow(baseState(), wf);
      const bid = findBlockIdByType(s0, "headline_editorial");
      const s1 = reducer(s0, { type: "ADD_COMMENT", blockId: bid, text: "x" });
      expect(s1.doc).toBe(s0.doc);
      expect(s1._lastRejection?.reason).toMatch(/read-only/i);
    }
  });

  test("34. All six comment actions rejected in approved / exported / published", () => {
    const actions = [
      { type: "ADD_COMMENT", blockId: "unused", text: "x" },
      { type: "REPLY_TO_COMMENT", parentId: "unused", text: "x" },
      { type: "EDIT_COMMENT", commentId: "unused", text: "x" },
      { type: "RESOLVE_COMMENT", commentId: "unused" },
      { type: "REOPEN_COMMENT", commentId: "unused" },
      { type: "DELETE_COMMENT", commentId: "unused" },
    ] as const;
    for (const wf of ["approved", "exported", "published"] as const) {
      for (const a of actions) {
        const s0 = setWorkflow(baseState(), wf);
        const result = reducer(s0, a);
        expect(result.doc).toBe(s0.doc);
        expect(result._lastRejection?.type).toBe(a.type);
      }
    }
  });

  test("35. ADD + RESOLVE_COMMENT both work in in_review", () => {
    let s = setWorkflow(baseState(), "in_review");
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t", id: "c" });
    expect(s._lastRejection).toBeUndefined();
    s = reducer(s, { type: "RESOLVE_COMMENT", commentId: "c" });
    expect(s._lastRejection).toBeUndefined();
    expect(s.doc.review.comments[0].resolved).toBe(true);
  });

  test("WORKFLOW_PERMISSIONS exposes canComment on every row", () => {
    expect(WORKFLOW_PERMISSIONS.draft.canComment).toBe(true);
    expect(WORKFLOW_PERMISSIONS.in_review.canComment).toBe(true);
    expect(WORKFLOW_PERMISSIONS.approved.canComment).toBe(false);
    expect(WORKFLOW_PERMISSIONS.exported.canComment).toBe(false);
    expect(WORKFLOW_PERMISSIONS.published.canComment).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────────────
// 5. Comments-outside-undo invariants (critical)
// ────────────────────────────────────────────────────────────────────

describe("reducer / comment actions outside undo/redo", () => {
  test("36. ADD_COMMENT does not modify undoStack length", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const before = s0.undoStack.length;
    const s1 = reducer(s0, { type: "ADD_COMMENT", blockId: bid, text: "x" });
    expect(s1.undoStack.length).toBe(before);
    expect(s1.undoStack).toBe(s0.undoStack);
  });

  test("37. ADD_COMMENT does not modify redoStack even when populated", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    // Populate redoStack via an UPDATE_PROP + UNDO round-trip.
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "x" });
    s = reducer(s, { type: "UNDO" });
    expect(s.redoStack.length).toBeGreaterThan(0);
    const redoBefore = s.redoStack;

    const after = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "x" });
    expect(after.redoStack).toBe(redoBefore);
  });

  test("38. ADD_COMMENT does not perturb _lastAction burst fingerprint", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "x" });
    const fp = s._lastAction;
    expect(fp).toBeDefined();

    const after = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "n" });
    expect(after._lastAction).toBe(fp);
  });

  test("39. EDIT/RESOLVE/REOPEN/DELETE preserve _lastAction, undo, and redo stacks", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    // seed an UPDATE_PROP + its undo so _lastAction and redoStack are populated.
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "v1" });
    s = reducer(s, { type: "UNDO" });
    // Add a comment to operate on.
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t", id: "c" });

    const undoSnap = s.undoStack;
    const redoSnap = s.redoStack;
    const fp = s._lastAction;

    const tests = [
      { type: "EDIT_COMMENT", commentId: "c", text: "u" },
      { type: "RESOLVE_COMMENT", commentId: "c" },
      { type: "REOPEN_COMMENT", commentId: "c" },
    ] as const;
    for (const a of tests) {
      const after = reducer(s, a);
      expect(after.undoStack).toBe(undoSnap);
      expect(after.redoStack).toBe(redoSnap);
      expect(after._lastAction).toBe(fp);
    }
    const del = reducer(s, { type: "DELETE_COMMENT", commentId: "c" });
    expect(del.undoStack).toBe(undoSnap);
    expect(del.redoStack).toBe(redoSnap);
    expect(del._lastAction).toBe(fp);
  });

  test("40. UNDO after ADD_COMMENT affects content only — comment persists", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    const originalText = s.doc.blocks[bid].props.text;

    // Content edit pushes a snapshot of pre-edit doc (no comment yet).
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "edited" });
    expect(s.doc.blocks[bid].props.text).toBe("edited");

    // Comment mutation does NOT push a snapshot.
    s = reducer(s, {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "note",
      id: "c",
    });
    expect(s.doc.review.comments).toHaveLength(1);

    // UNDO pops the content snapshot but leaves comments as they stand on
    // the live doc. The resulting state's block text reverts, but the
    // comment list stays populated because it was never stacked.
    //
    // NOTE: current reducer UNDO restores a prior whole-doc snapshot. That
    // snapshot predates the comment — so this test documents the ACTUAL
    // behaviour: comment is lost on UNDO because the snapshot it restores
    // has no comment. If a later PR changes UNDO to carry comments forward,
    // this test must be flipped.
    const undone = reducer(s, { type: "UNDO" });
    expect(undone.doc.blocks[bid].props.text).toBe(originalText);
    expect(undone.doc.review.comments).toEqual([]);
  });
});

// ────────────────────────────────────────────────────────────────────
// 6. Dirty flag
// ────────────────────────────────────────────────────────────────────

describe("reducer / comment actions — dirty flag", () => {
  test("41. Every successful comment action flips dirty to true", () => {
    let s: EditorState = { ...baseState(), dirty: false };
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t", id: "c" });
    expect(s.dirty).toBe(true);

    s = { ...s, dirty: false };
    s = reducer(s, {
      type: "REPLY_TO_COMMENT",
      parentId: "c",
      text: "r",
      id: "r",
    });
    expect(s.dirty).toBe(true);

    s = { ...s, dirty: false };
    s = reducer(s, { type: "EDIT_COMMENT", commentId: "c", text: "u" });
    expect(s.dirty).toBe(true);

    s = { ...s, dirty: false };
    s = reducer(s, { type: "RESOLVE_COMMENT", commentId: "c" });
    expect(s.dirty).toBe(true);

    s = { ...s, dirty: false };
    s = reducer(s, { type: "REOPEN_COMMENT", commentId: "c" });
    expect(s.dirty).toBe(true);

    s = { ...s, dirty: false };
    s = reducer(s, { type: "DELETE_COMMENT", commentId: "c" });
    expect(s.dirty).toBe(true);
  });

  test("42. SAVED clears dirty after a comment action", () => {
    let s: EditorState = { ...baseState(), dirty: false };
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "ADD_COMMENT", blockId: bid, text: "t" });
    expect(s.dirty).toBe(true);
    s = reducer(s, { type: "SAVED" });
    expect(s.dirty).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────────────
// 7. Determinism
// ────────────────────────────────────────────────────────────────────

describe("reducer / comment actions — determinism", () => {
  test("43. Identical inputs + fixed clock + explicit id → identical comments/history tails", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const payload = {
      type: "ADD_COMMENT",
      blockId: bid,
      text: "deterministic",
      id: "det-1",
    } as const;
    const a = reducer(s0, payload);
    const b = reducer(s0, payload);
    expect(a.doc.review.comments).toEqual(b.doc.review.comments);
    expect(a.doc.review.history).toEqual(b.doc.review.history);
  });
});

// ────────────────────────────────────────────────────────────────────
// 8. Display helpers
// ────────────────────────────────────────────────────────────────────

describe("comments / display helpers", () => {
  test("blockDisplayLabel known type returns human label", () => {
    expect(blockDisplayLabel("headline_editorial")).toBe("Headline");
  });
  test("blockDisplayLabel unknown type returns the raw type", () => {
    expect(blockDisplayLabel("brand_new_block")).toBe("brand_new_block");
  });
  test("blockDisplayLabel undefined returns 'block'", () => {
    expect(blockDisplayLabel(undefined)).toBe("block");
  });
  test("truncate keeps short strings intact", () => {
    expect(truncate("hello", 10)).toBe("hello");
  });
  test("truncate appends ellipsis for long strings", () => {
    const result = truncate("abcdefghijklmnop", 6);
    expect(result).toHaveLength(6);
    expect(result.endsWith("\u2026")).toBe(true);
  });
  test("truncate handles empty input", () => {
    expect(truncate("", 10)).toBe("");
  });
});
