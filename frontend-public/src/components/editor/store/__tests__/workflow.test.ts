import { reducer, initState } from "../reducer";
import type { EditorAction, EditorState, TimestampProvider, WorkflowState } from "../../types";
import {
  TRANSITIONS,
  canTransition,
  availableTransitions,
  transitionTarget,
  systemTimestampProvider,
  isReadOnlyWorkflow,
  WORKFLOW_ACTION_TYPES,
} from "../workflow";
import { WORKFLOW_PERMISSIONS, classifyKey } from "../permissions";
import { validateImportStrict } from "../../registry/guards";

// ────────────────────────────────────────────────────────────────────
// Fixtures
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
    k => state.doc.blocks[k].type === type,
  );
  if (!id) throw new Error(`No block of type ${type} in fixture`);
  return id;
}

// ────────────────────────────────────────────────────────────────────
// 1. Transition machine
// ────────────────────────────────────────────────────────────────────

describe("workflow / transition machine", () => {
  test("canTransition returns true for every legal pair", () => {
    (Object.keys(TRANSITIONS) as WorkflowState[]).forEach(from => {
      for (const to of TRANSITIONS[from]) {
        expect(canTransition(from, to)).toBe(true);
      }
    });
  });

  test("canTransition returns false for known illegal pairs", () => {
    expect(canTransition("draft", "approved")).toBe(false);
    expect(canTransition("draft", "exported")).toBe(false);
    expect(canTransition("draft", "published")).toBe(false);
    expect(canTransition("exported", "draft")).toBe(false);
    expect(canTransition("exported", "approved")).toBe(false);
    expect(canTransition("published", "draft")).toBe(false);
    expect(canTransition("published", "in_review")).toBe(false);
    expect(canTransition("published", "approved")).toBe(false);
    expect(canTransition("published", "exported")).toBe(false);
    expect(canTransition("published", "published")).toBe(false);
  });

  test("availableTransitions('published') is empty (terminal)", () => {
    expect(availableTransitions("published")).toEqual([]);
  });

  test("transitionTarget is null for DUPLICATE_AS_DRAFT (not a transition)", () => {
    expect(transitionTarget("DUPLICATE_AS_DRAFT")).toBeNull();
  });

  test("WORKFLOW_ACTION_TYPES enumerates every workflow action", () => {
    expect(new Set(WORKFLOW_ACTION_TYPES)).toEqual(new Set([
      "SUBMIT_FOR_REVIEW",
      "APPROVE",
      "REQUEST_CHANGES",
      "RETURN_TO_DRAFT",
      "MARK_EXPORTED",
      "MARK_PUBLISHED",
      "DUPLICATE_AS_DRAFT",
    ]));
  });
});

// ────────────────────────────────────────────────────────────────────
// 2. Reducer — happy paths
// ────────────────────────────────────────────────────────────────────

describe("reducer / workflow transitions — happy paths", () => {
  test("4. SUBMIT_FOR_REVIEW from draft appends a 'submitted' history entry", () => {
    const s0 = baseState();
    expect(s0.doc.review.workflow).toBe("draft");
    const s1 = reducer(s0, { type: "SUBMIT_FOR_REVIEW" });
    expect(s1.doc.review.workflow).toBe("in_review");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("submitted");
    expect(entry.summary).toBe("Submitted for review");
    expect(entry.fromWorkflow).toBe("draft");
    expect(entry.toWorkflow).toBe("in_review");
    expect(entry.author).toBe("you");
    expect(entry.ts).toBe(FIXED_TS);
  });

  test("5. APPROVE from in_review transitions to approved", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const s1 = reducer(s0, { type: "APPROVE" });
    expect(s1.doc.review.workflow).toBe("approved");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("approved");
    expect(entry.summary).toBe("Approved for export");
  });

  test("6. REQUEST_CHANGES from in_review with note returns to draft", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const s1 = reducer(s0, { type: "REQUEST_CHANGES", note: "Fix headline" });
    expect(s1.doc.review.workflow).toBe("draft");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("changes_requested");
    expect(entry.summary).toBe("Changes requested: Fix headline");
  });

  test("7. REQUEST_CHANGES without note uses default summary", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const s1 = reducer(s0, { type: "REQUEST_CHANGES" });
    expect(s1.doc.review.workflow).toBe("draft");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.summary).toBe("Changes requested; returned to draft");
  });

  test("8. RETURN_TO_DRAFT from approved uses 'returned_to_draft' action label", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const s1 = reducer(s0, { type: "RETURN_TO_DRAFT", note: "Revoked after review" });
    expect(s1.doc.review.workflow).toBe("draft");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("returned_to_draft");
    expect(entry.action).not.toBe("changes_requested");
    expect(entry.summary).toBe("Returned to draft: Revoked after review");
  });

  test("8b. RETURN_TO_DRAFT without note uses default summary", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const s1 = reducer(s0, { type: "RETURN_TO_DRAFT" });
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.summary).toBe("Approval revoked; returned to draft");
  });

  test("9. MARK_EXPORTED from approved captures filename in summary", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const s1 = reducer(s0, { type: "MARK_EXPORTED", filename: "summa-housing.png" });
    expect(s1.doc.review.workflow).toBe("exported");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("exported");
    expect(entry.summary).toBe("Exported as summa-housing.png");
  });

  test("10. MARK_PUBLISHED from exported captures channel in summary", () => {
    const s0 = setWorkflow(baseState(), "exported");
    const s1 = reducer(s0, { type: "MARK_PUBLISHED", channel: "instagram" });
    expect(s1.doc.review.workflow).toBe("published");
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.action).toBe("published");
    expect(entry.summary).toBe("Published to instagram");
  });

  test("11. DUPLICATE_AS_DRAFT from exported produces a fresh draft", () => {
    const s0 = setWorkflow(baseState(), "exported");
    const s1 = reducer(s0, { type: "DUPLICATE_AS_DRAFT" });
    expect(s1.doc.review.workflow).toBe("draft");
    expect(s1.doc.meta.version).toBe(0);
    expect(s1.doc.meta.history).toEqual([]);
    expect(s1.doc.review.history).toHaveLength(1);
    const entry = s1.doc.review.history[0];
    expect(entry.action).toBe("duplicated");
    expect(entry.summary).toBe("Duplicated from exported document");
    expect(entry.fromWorkflow).toBeNull();
    expect(entry.toWorkflow).toBe("draft");
    // Deep-clone: mutating the duplicate must not affect the original.
    const firstBlockId = Object.keys(s1.doc.blocks)[0];
    s1.doc.blocks[firstBlockId].props.text = "mutated";
    expect(s0.doc.blocks[firstBlockId].props.text).not.toBe("mutated");
  });

  test("12. DUPLICATE_AS_DRAFT from published also produces a fresh draft", () => {
    const s0 = setWorkflow(baseState(), "published");
    const s1 = reducer(s0, { type: "DUPLICATE_AS_DRAFT" });
    expect(s1.doc.review.workflow).toBe("draft");
    expect(s1.doc.review.history[0].summary).toBe("Duplicated from published document");
    expect(s1.doc.meta.version).toBe(0);
  });
});

// ────────────────────────────────────────────────────────────────────
// 3. Reducer — rejection paths
// ────────────────────────────────────────────────────────────────────

describe("reducer / workflow transitions — rejections", () => {
  test("13. SUBMIT_FOR_REVIEW from approved is rejected; state unchanged", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const s1 = reducer(s0, { type: "SUBMIT_FOR_REVIEW" });
    expect(s1.doc.review.workflow).toBe("approved");
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("SUBMIT_FOR_REVIEW");
    expect(s1._lastRejection?.reason).toMatch(/Illegal transition/);
  });

  test("14. APPROVE from draft is rejected", () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: "APPROVE" });
    expect(s1.doc.review.workflow).toBe("draft");
    expect(s1._lastRejection?.reason).toMatch(/Illegal transition: draft → approved/);
  });

  test("15. MARK_PUBLISHED from draft is rejected", () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: "MARK_PUBLISHED", channel: "twitter" });
    expect(s1.doc.review.workflow).toBe("draft");
    expect(s1._lastRejection?.reason).toMatch(/Illegal transition/);
  });

  test("16. DUPLICATE_AS_DRAFT from draft is rejected with helpful reason", () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: "DUPLICATE_AS_DRAFT" });
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.reason).toMatch(/exported or published/);
  });

  test("17. Every workflow action except DUPLICATE_AS_DRAFT is rejected from published", () => {
    const s0 = setWorkflow(baseState(), "published");
    const transitionActions: EditorAction[] = [
      { type: "SUBMIT_FOR_REVIEW" },
      { type: "APPROVE" },
      { type: "REQUEST_CHANGES" },
      { type: "RETURN_TO_DRAFT" },
      { type: "MARK_EXPORTED", filename: "x.png" },
      { type: "MARK_PUBLISHED", channel: "twitter" },
    ];
    for (const a of transitionActions) {
      const next = reducer(s0, a);
      expect(next.doc.review.workflow).toBe("published");
      expect(next._lastRejection).toBeDefined();
    }
    // DUPLICATE_AS_DRAFT from published IS allowed (lifecycle escape hatch).
    const dup = reducer(s0, { type: "DUPLICATE_AS_DRAFT" });
    expect(dup.doc.review.workflow).toBe("draft");
  });
});

// ────────────────────────────────────────────────────────────────────
// 4. Workflow × category permission matrix
// ────────────────────────────────────────────────────────────────────

describe("permissions / workflow × category gate", () => {
  test("18. UPDATE_PROP (text) in draft is allowed", () => {
    const s0 = baseState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "Hello" });
    expect(s1.doc.blocks[bid].props.text).toBe("Hello");
    expect(s1._lastRejection).toBeUndefined();
  });

  test("19. UPDATE_PROP (text) in in_review is allowed", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "Hello" });
    expect(s1.doc.blocks[bid].props.text).toBe("Hello");
  });

  test("20. UPDATE_PROP (data) in in_review is rejected with copy-edit reason", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    // delta_badge exposes a `direction` key (DATA_CONTENT_KEYS), so
    // an attempt to change it in in_review must be rejected.
    const dbid = findBlockIdByType(s0, "delta_badge");
    const before = s0.doc.blocks[dbid].props.direction;
    const targetValue = before === "positive" ? "negative" : "positive";
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: dbid, key: "direction", value: targetValue });
    expect(s1.doc.blocks[dbid].props.direction).toBe(before);
    expect(s1._lastRejection?.reason).toMatch(/Only copy edits allowed/);
  });

  test("21. UPDATE_PROP (style) in in_review is rejected", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "align", value: "center" });
    expect(s1.doc.blocks[bid].props.align).not.toBe("center");
    expect(s1._lastRejection?.reason).toMatch(/Only copy edits allowed/);
  });

  test("22. Any content action in approved is rejected", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "Hello" });
    expect(s1.doc.blocks[bid].props.text).not.toBe("Hello");
    expect(s1._lastRejection?.reason).toMatch(/read-only/i);
  });

  test("23. SELECT in published is allowed (navigation always works)", () => {
    const s0 = setWorkflow(baseState(), "published");
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "SELECT", blockId: bid });
    expect(s1.selectedBlockId).toBe(bid);
  });

  test("24. SET_MODE in published is allowed", () => {
    const s0 = setWorkflow(baseState(), "published");
    const s1 = reducer(s0, { type: "SET_MODE", mode: "template" });
    expect(s1.mode).toBe("template");
  });

  test("25. IMPORT in approved is rejected (read-only guard)", () => {
    const s0 = setWorkflow(baseState(), "approved");
    const s1 = reducer(s0, { type: "IMPORT", doc: baseState().doc });
    expect(s1.doc).toBe(s0.doc); // doc unchanged
    expect(s1._lastRejection?.reason).toMatch(/read-only/i);
  });

  test("WORKFLOW_PERMISSIONS matrix is exported and shaped correctly", () => {
    expect(WORKFLOW_PERMISSIONS.draft.textContent).toBe(true);
    expect(WORKFLOW_PERMISSIONS.draft.structural).toBe(true);
    expect(WORKFLOW_PERMISSIONS.draft.importUndoRedo).toBe(true);
    expect(WORKFLOW_PERMISSIONS.in_review.textContent).toBe(true);
    expect(WORKFLOW_PERMISSIONS.in_review.dataContent).toBe(false);
    expect(WORKFLOW_PERMISSIONS.in_review.structural).toBe(false);
    expect(WORKFLOW_PERMISSIONS.in_review.style).toBe(false);
    // Fix prompt P0: importUndoRedo must be false in in_review — otherwise
    // IMPORT swaps the doc entirely, and UNDO/REDO replay pre-submission
    // structural snapshots, bypassing the copy-edit lockdown.
    expect(WORKFLOW_PERMISSIONS.in_review.importUndoRedo).toBe(false);
    expect(WORKFLOW_PERMISSIONS.approved.importUndoRedo).toBe(false);
    expect(WORKFLOW_PERMISSIONS.published.importUndoRedo).toBe(false);
  });

  test("classifyKey maps known keys to the right category", () => {
    expect(classifyKey("text")).toBe("text");
    expect(classifyKey("value")).toBe("text");
    expect(classifyKey("direction")).toBe("data");
    expect(classifyKey("items")).toBe("structural");
    expect(classifyKey("align")).toBe("style");
    expect(classifyKey("unknown_prop")).toBe("unknown");
  });
});

// ────────────────────────────────────────────────────────────────────
// 5. Determinism
// ────────────────────────────────────────────────────────────────────

describe("reducer / workflow actions — determinism", () => {
  test("26. Identical inputs + mock clock → identical outputs", () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: "SUBMIT_FOR_REVIEW" });
    const s2 = reducer(s0, { type: "SUBMIT_FOR_REVIEW" });
    expect(s1.doc).toEqual(s2.doc);
  });

  test("27. Action.ts overrides the provider clock", () => {
    const s0 = baseState();
    const custom = "2030-12-31T23:59:59.999Z";
    const s1 = reducer(s0, { type: "SUBMIT_FOR_REVIEW", ts: custom });
    const entry = s1.doc.review.history[s1.doc.review.history.length - 1];
    expect(entry.ts).toBe(custom);
    expect(s1.doc.meta.updatedAt).toBe(custom);
  });

  test("systemTimestampProvider returns a valid ISO string", () => {
    const iso = systemTimestampProvider.now();
    expect(Number.isNaN(Date.parse(iso))).toBe(false);
  });
});

// ────────────────────────────────────────────────────────────────────
// 6. Undo/redo behaviour on read-only entry
// ────────────────────────────────────────────────────────────────────

describe("reducer / undo-redo behaviour around workflow transitions", () => {
  test("28. APPROVE clears undoStack and redoStack", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "A" });
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "B" });
    expect(s.undoStack.length).toBeGreaterThan(0);
    s = setWorkflow(s, "in_review");
    const after = reducer(s, { type: "APPROVE" });
    expect(after.undoStack).toEqual([]);
    expect(after.redoStack).toEqual([]);
    expect(isReadOnlyWorkflow(after.doc.review.workflow)).toBe(true);
  });

  test("29. MARK_EXPORTED clears stacks", () => {
    let s = setWorkflow(baseState(), "approved");
    const bid = findBlockIdByType(s, "headline_editorial");
    // Re-allow a write in draft, then push it into approved as stack filler
    s = { ...s, undoStack: [s.doc, s.doc], redoStack: [s.doc] };
    expect(bid).toBeDefined();
    const after = reducer(s, { type: "MARK_EXPORTED", filename: "x.png" });
    expect(after.undoStack).toEqual([]);
    expect(after.redoStack).toEqual([]);
  });

  test("30. RETURN_TO_DRAFT (approved → draft) preserves stacks", () => {
    let s = setWorkflow(baseState(), "approved");
    // Plant non-empty stacks to verify they survive the transition.
    s = { ...s, undoStack: [s.doc], redoStack: [s.doc] };
    const after = reducer(s, { type: "RETURN_TO_DRAFT" });
    expect(after.doc.review.workflow).toBe("draft");
    expect(after.undoStack.length).toBe(1);
    expect(after.redoStack.length).toBe(1);
  });
});

// ────────────────────────────────────────────────────────────────────
// 7. Shape validation (DEBT-023 partial closure)
// ────────────────────────────────────────────────────────────────────

describe("validateImportStrict / review.history element shape", () => {
  test("31. rejects history[0].ts = 'not-iso'", () => {
    const s = baseState();
    const bad: any = JSON.parse(JSON.stringify(s.doc));
    bad.review.history[0].ts = "not-iso";
    expect(() => validateImportStrict(bad)).toThrow(/review\.history\[0\]\.ts/);
  });

  test("32. rejects history[N].fromWorkflow = 'bogus_state'", () => {
    const s = baseState();
    const bad: any = JSON.parse(JSON.stringify(s.doc));
    bad.review.history.push({
      ts: FIXED_TS,
      action: "submitted",
      summary: "Submitted",
      author: "you",
      fromWorkflow: "bogus_state",
      toWorkflow: "in_review",
    });
    expect(() => validateImportStrict(bad)).toThrow(/review\.history\[1\]\.fromWorkflow/);
  });

  test("33. accepts well-formed history", () => {
    const s = baseState();
    const doc: any = JSON.parse(JSON.stringify(s.doc));
    doc.review.history.push({
      ts: FIXED_TS,
      action: "submitted",
      summary: "Submitted for review",
      author: "reviewer-a",
      fromWorkflow: "draft",
      toWorkflow: "in_review",
    });
    expect(() => validateImportStrict(doc)).not.toThrow();
  });
});

// ────────────────────────────────────────────────────────────────────
// 8. DEBT-022 closure
// ────────────────────────────────────────────────────────────────────

describe("DEBT-022 / legacy validateImport is gone", () => {
  test("34. guards.ts exports validateImportStrict but NOT validateImport", () => {
    const guards = require("../../registry/guards") as Record<string, unknown>;
    expect(typeof guards.validateImportStrict).toBe("function");
    expect("validateImport" in guards).toBe(false);
  });

  test("35. reducer module has zero 'validateImport(' call-site references", () => {
    const fs = require("fs");
    const path = require("path");
    const src = fs.readFileSync(
      path.join(__dirname, "..", "reducer.ts"),
      "utf8",
    );
    // Allow `validateImportStrict(` but not bare `validateImport(`.
    const bare = src.match(/validateImport\(/g) || [];
    expect(bare).toHaveLength(0);
    expect(src).toMatch(/validateImportStrict\(/);
  });
});

// ────────────────────────────────────────────────────────────────────
// 9. Fix prompt — P0 bypass closure + P1 dirty/rejection consistency
// ────────────────────────────────────────────────────────────────────

describe("fix prompt / P0 — in_review bypass closure", () => {
  test("IMPORT is rejected in in_review", () => {
    const s0 = setWorkflow(baseState(), "in_review");
    const fresh = JSON.parse(JSON.stringify(baseState().doc));
    const result = reducer(s0, { type: "IMPORT", doc: fresh });
    expect(result.doc).toBe(s0.doc);
    expect(result._lastRejection?.type).toBe("IMPORT");
    expect(result._lastRejection?.reason).toMatch(/read-only/i);
  });

  test("UNDO is rejected in in_review even when undoStack is non-empty", () => {
    // 1. Make an edit in draft so the undo stack has a snapshot.
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "edited" });
    expect(s.undoStack.length).toBeGreaterThan(0);

    // 2. Submit for review.
    s = reducer(s, { type: "SUBMIT_FOR_REVIEW", ts: FIXED_TS });
    expect(s.doc.review.workflow).toBe("in_review");
    // Stack preserved across submit (REQUEST_CHANGES must restore undo).
    expect(s.undoStack.length).toBeGreaterThan(0);

    // 3. UNDO must be rejected — this was the P0 history-stack bypass.
    const result = reducer(s, { type: "UNDO" });
    expect(result.doc).toBe(s.doc);
    expect(result._lastRejection?.type).toBe("UNDO");
    expect(result._lastRejection?.reason).toMatch(/read-only/i);
  });

  test("REDO is rejected in in_review", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "v1" });
    s = reducer(s, { type: "UNDO" });
    expect(s.redoStack.length).toBeGreaterThan(0);

    s = reducer(s, { type: "SUBMIT_FOR_REVIEW", ts: FIXED_TS });
    const result = reducer(s, { type: "REDO" });
    expect(result.doc).toBe(s.doc);
    expect(result._lastRejection?.type).toBe("REDO");
  });

  test("undoStack is preserved across SUBMIT_FOR_REVIEW (available again after REQUEST_CHANGES)", () => {
    let s = baseState();
    const bid = findBlockIdByType(s, "headline_editorial");
    s = reducer(s, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "v1" });
    const stackBefore = s.undoStack.length;
    expect(stackBefore).toBeGreaterThan(0);

    s = reducer(s, { type: "SUBMIT_FOR_REVIEW", ts: FIXED_TS });
    // Not cleared on submit — crucial for the round-trip.
    expect(s.undoStack.length).toBe(stackBefore);

    // Reviewer bounces the document back.
    s = reducer(s, { type: "REQUEST_CHANGES", ts: FIXED_TS });
    expect(s.doc.review.workflow).toBe("draft");
    expect(s.undoStack.length).toBe(stackBefore);

    // UNDO now works again.
    const result = reducer(s, { type: "UNDO" });
    expect(result.doc).not.toBe(s.doc);
    expect(result._lastRejection).toBeUndefined();
  });
});

describe("fix prompt / P1 — workflow transitions mark state as dirty", () => {
  test("SUBMIT_FOR_REVIEW sets dirty: true", () => {
    const s0 = { ...baseState(), dirty: false };
    const r = reducer(s0, { type: "SUBMIT_FOR_REVIEW", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("APPROVE sets dirty: true", () => {
    const s0 = { ...setWorkflow(baseState(), "in_review"), dirty: false };
    const r = reducer(s0, { type: "APPROVE", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("REQUEST_CHANGES sets dirty: true", () => {
    const s0 = { ...setWorkflow(baseState(), "in_review"), dirty: false };
    const r = reducer(s0, { type: "REQUEST_CHANGES", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("RETURN_TO_DRAFT sets dirty: true", () => {
    const s0 = { ...setWorkflow(baseState(), "approved"), dirty: false };
    const r = reducer(s0, { type: "RETURN_TO_DRAFT", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("MARK_EXPORTED sets dirty: true", () => {
    const s0 = { ...setWorkflow(baseState(), "approved"), dirty: false };
    const r = reducer(s0, { type: "MARK_EXPORTED", filename: "out.png", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("MARK_PUBLISHED sets dirty: true", () => {
    const s0 = { ...setWorkflow(baseState(), "exported"), dirty: false };
    const r = reducer(s0, { type: "MARK_PUBLISHED", channel: "twitter", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("DUPLICATE_AS_DRAFT produces a dirty state", () => {
    const s0 = { ...setWorkflow(baseState(), "published"), dirty: false };
    const r = reducer(s0, { type: "DUPLICATE_AS_DRAFT", ts: FIXED_TS });
    expect(r.dirty).toBe(true);
  });

  test("SAVED clears dirty", () => {
    const s0: EditorState = { ...baseState(), dirty: true };
    const r = reducer(s0, { type: "SAVED" });
    expect(r.dirty).toBe(false);
  });
});

describe("fix prompt / P1 — invalid IMPORT flows through _lastRejection", () => {
  test("invalid IMPORT fills _lastRejection (no silent rejection)", () => {
    const s0 = baseState();
    const result = reducer(s0, { type: "IMPORT", doc: { garbage: true } as any });
    expect(result.doc).toBe(s0.doc);
    expect(result._lastRejection?.type).toBe("IMPORT");
    expect(typeof result._lastRejection?.reason).toBe("string");
    expect((result._lastRejection?.reason ?? "").length).toBeGreaterThan(0);
  });

  test("valid IMPORT clears _lastRejection", () => {
    const s0: EditorState = {
      ...baseState(),
      _lastRejection: { type: "PREVIOUS", reason: "old", at: 1 },
    };
    const fresh = JSON.parse(JSON.stringify(baseState().doc));
    const result = reducer(s0, { type: "IMPORT", doc: fresh });
    expect(result._lastRejection).toBeUndefined();
    expect(result.dirty).toBe(false); // fresh import starts clean
  });
});
