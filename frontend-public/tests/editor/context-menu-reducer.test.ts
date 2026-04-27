/**
 * Phase 1.6 — reducer tests for context-menu actions.
 *
 * Verifies the four new dispatches (TOGGLE_LOCK, TOGGLE_VIS gating on lock,
 * DUPLICATE_BLOCK, REMOVE_BLOCK) and their integration with the existing
 * permission gate, history batching, and undo stack.
 */
import { reducer, initState } from "../../src/components/editor/store/reducer";
import type { EditorState } from "../../src/components/editor/types";

function findBlockIdByType(state: EditorState, type: string): string {
  const bid = Object.keys(state.doc.blocks).find(
    id => state.doc.blocks[id].type === type,
  );
  if (!bid) throw new Error(`No block of type ${type} in test fixture`);
  return bid;
}

function setMode(state: EditorState, mode: "design" | "template"): EditorState {
  return reducer(state, { type: "SET_MODE", mode });
}

describe("reducer / TOGGLE_LOCK", () => {
  test("toggles block.locked from undefined to true and back", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    expect(s0.doc.blocks[bid].locked).toBeUndefined();

    const s1 = reducer(s0, { type: "TOGGLE_LOCK", blockId: bid });
    expect(s1.doc.blocks[bid].locked).toBe(true);
    expect(s1.dirty).toBe(true);
    expect(s1.undoStack.length).toBe(1);

    const s2 = reducer(s1, { type: "TOGGLE_LOCK", blockId: bid });
    expect(s2.doc.blocks[bid].locked).toBe(false);
  });

  test("TOGGLE_LOCK on missing block is a no-op", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "TOGGLE_LOCK", blockId: "blk_nope" });
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("TOGGLE_LOCK");
  });
});

describe("reducer / lock blocks UPDATE_PROP", () => {
  test("once locked, UPDATE_PROP no-ops and records rejection", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const original = s0.doc.blocks[bid].props.text;

    const s1 = reducer(s0, { type: "TOGGLE_LOCK", blockId: bid });
    const s2 = reducer(s1, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "BLOCKED" });
    expect(s2.doc.blocks[bid].props.text).toBe(original);
    expect(s2._lastRejection?.type).toBe("UPDATE_PROP");
    expect(s2._lastRejection?.reason).toMatch(/locked/i);

    // Unlock — edits flow again.
    const s3 = reducer(s2, { type: "TOGGLE_LOCK", blockId: bid });
    const s4 = reducer(s3, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "Unlocked Edit" });
    expect(s4.doc.blocks[bid].props.text).toBe("Unlocked Edit");
  });

  test("once locked, TOGGLE_VIS no-ops too (lock blocks movement)", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    const visible0 = s0.doc.blocks[bid].visible;

    const sLocked = reducer(s0, { type: "TOGGLE_LOCK", blockId: bid });
    const sTry = reducer(sLocked, { type: "TOGGLE_VIS", blockId: bid });
    expect(sTry.doc.blocks[bid].visible).toBe(visible0);
    expect(sTry._lastRejection?.type).toBe("TOGGLE_VIS");
  });
});

describe("reducer / DUPLICATE_BLOCK", () => {
  test("inserts a fresh copy directly after the source in the same section", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    // Confirm precondition: maxPerSection for eyebrow_tag is 1 → duplicate
    // should be REJECTED. Sanity-check the rejection path before testing the
    // happy path on a different block.
    const sReject = reducer(s0, { type: "DUPLICATE_BLOCK", blockId: bid });
    expect(sReject._lastRejection?.type).toBe("DUPLICATE_BLOCK");

    // body_annotation: maxPerSection 2, so duplication is allowed when the
    // template ships with 0 or 1 annotation. Use single_stat_note which has
    // one body_annotation in the context section.
    const tplState: EditorState = {
      ...initState(),
    };
    const sSwitch = reducer(tplState, { type: "SWITCH_TPL", tid: "single_stat_note" });
    const annId = findBlockIdByType(sSwitch, "body_annotation");
    const ownerSec = sSwitch.doc.sections.find(s => s.blockIds.includes(annId))!;
    const indexBefore = ownerSec.blockIds.indexOf(annId);

    const s1 = reducer(sSwitch, { type: "DUPLICATE_BLOCK", blockId: annId, newId: "blk_dup_001" });
    const newSec = s1.doc.sections.find(s => s.id === ownerSec.id)!;
    expect(newSec.blockIds.length).toBe(ownerSec.blockIds.length + 1);
    expect(newSec.blockIds[indexBefore + 1]).toBe("blk_dup_001");

    const dup = s1.doc.blocks["blk_dup_001"];
    expect(dup.type).toBe("body_annotation");
    expect(dup.props).toEqual(sSwitch.doc.blocks[annId].props);
    expect(dup.locked).toBeUndefined();
    expect(s1.selectedBlockId).toBe("blk_dup_001");
  });

  test("DUPLICATE_BLOCK rejected in template mode (mode-axis gate)", () => {
    const s0 = setMode(initState(), "template");
    const annId = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "DUPLICATE_BLOCK", blockId: annId });
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("DUPLICATE_BLOCK");
  });

  test("DUPLICATE_BLOCK rejects caller-provided newId collision", () => {
    const s0 = reducer(initState(), { type: "SWITCH_TPL", tid: "single_stat_note" });
    const annId = findBlockIdByType(s0, "body_annotation");
    const existingId = Object.keys(s0.doc.blocks)[0];
    const collisionId = existingId === annId
      ? Object.keys(s0.doc.blocks).find(id => id !== annId)!
      : existingId;

    const s1 = reducer(s0, {
      type: "DUPLICATE_BLOCK",
      blockId: annId,
      newId: collisionId,
    });

    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("DUPLICATE_BLOCK");
    expect(s1._lastRejection?.reason).toMatch(/already exists/i);
  });
});

describe("reducer / REMOVE_BLOCK", () => {
  test("removes optional block from registry and section refs", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    const ownerSec = s0.doc.sections.find(s => s.blockIds.includes(bid))!;

    // Select the target before removing so the selection-clear assertion
    // below tests REMOVE_BLOCK behavior, not initState() defaults.
    const sSelected = reducer(s0, { type: "SELECT", blockId: bid });
    const s1 = reducer(sSelected, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s1.doc.blocks[bid]).toBeUndefined();
    const newSec = s1.doc.sections.find(s => s.id === ownerSec.id)!;
    expect(newSec.blockIds.includes(bid)).toBe(false);
    expect(s1.selectedBlockId).toBeNull();
    expect(s1.dirty).toBe(true);
  });

  test("REMOVE_BLOCK preserves selection when a different block is selected", () => {
    const s0 = initState();
    const targetBid = findBlockIdByType(s0, "eyebrow_tag");
    // Pick any other block to be selected — must not be templateRequired
    // since REMOVE_BLOCK on those gets rejected.
    const keptBid = Object.keys(s0.doc.blocks).find(
      id => id !== targetBid &&
            s0.doc.blocks[id].type !== "source_footer" &&
            s0.doc.blocks[id].type !== "headline_editorial",
    )!;
    expect(keptBid).toBeDefined();

    const sSelected = reducer(s0, { type: "SELECT", blockId: keptBid });
    const s1 = reducer(sSelected, { type: "REMOVE_BLOCK", blockId: targetBid });
    expect(s1.selectedBlockId).toBe(keptBid);
  });

  test("REMOVE_BLOCK on required_locked block is rejected", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "source_footer");
    const s1 = reducer(s0, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s1.doc.blocks[bid]).toBeDefined();
    expect(s1._lastRejection?.type).toBe("REMOVE_BLOCK");
  });

  test("REMOVE_BLOCK on required_editable block is rejected", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s1.doc.blocks[bid]).toBeDefined();
    expect(s1._lastRejection?.type).toBe("REMOVE_BLOCK");
  });

  test("REMOVE_BLOCK rejected in template mode", () => {
    const s0 = setMode(initState(), "template");
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    const s1 = reducer(s0, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s1.doc.blocks[bid]).toBeDefined();
    expect(s1._lastRejection?.type).toBe("REMOVE_BLOCK");
  });
});

describe("reducer / REMOVE_BLOCK comment subtree", () => {
  test("removing a block drops anchored comment AND its replies", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");

    // Seed: 1 comment anchored to bid, 1 reply (parentId = c1.id) anchored
    // to a different block (the harder case — proves parentId-chain
    // closure rather than relying on co-anchoring), 1 unrelated comment
    // anchored to a different block.
    const otherBid = Object.keys(s0.doc.blocks).find(id => id !== bid)!;
    const seeded: EditorState = {
      ...s0,
      doc: {
        ...s0.doc,
        review: {
          ...s0.doc.review,
          comments: [
            {
              id: "c1",
              blockId: bid,
              parentId: null,
              author: "u1",
              text: "parent",
              createdAt: "2026-04-27T00:00:00Z",
              updatedAt: null,
              resolved: false,
              resolvedAt: null,
              resolvedBy: null,
            },
            {
              id: "c2",
              blockId: otherBid,
              parentId: "c1",
              author: "u2",
              text: "reply",
              createdAt: "2026-04-27T00:00:01Z",
              updatedAt: null,
              resolved: false,
              resolvedAt: null,
              resolvedBy: null,
            },
            {
              id: "c3",
              blockId: otherBid,
              parentId: null,
              author: "u3",
              text: "unrelated",
              createdAt: "2026-04-27T00:00:02Z",
              updatedAt: null,
              resolved: false,
              resolvedAt: null,
              resolvedBy: null,
            },
          ],
        },
      },
    };

    const s1 = reducer(seeded, { type: "REMOVE_BLOCK", blockId: bid });
    const remaining = s1.doc.review.comments.map(c => c.id).sort();
    expect(remaining).toEqual(["c3"]);
  });
});

describe("reducer / undo restores after each menu action", () => {
  test("Lock → Undo restores unlocked state", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    const s1 = reducer(s0, { type: "TOGGLE_LOCK", blockId: bid });
    expect(s1.doc.blocks[bid].locked).toBe(true);
    const s2 = reducer(s1, { type: "UNDO" });
    expect(s2.doc.blocks[bid].locked).toBeUndefined();
  });

  test("Duplicate → Undo removes the duplicate", () => {
    const s0 = reducer(initState(), { type: "SWITCH_TPL", tid: "single_stat_note" });
    const annId = findBlockIdByType(s0, "body_annotation");
    const s1 = reducer(s0, { type: "DUPLICATE_BLOCK", blockId: annId, newId: "blk_dup_x" });
    expect(s1.doc.blocks["blk_dup_x"]).toBeDefined();
    const s2 = reducer(s1, { type: "UNDO" });
    expect(s2.doc.blocks["blk_dup_x"]).toBeUndefined();
  });

  test("Remove → Undo restores the block", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");
    const before = s0.doc.blocks[bid];
    const s1 = reducer(s0, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s1.doc.blocks[bid]).toBeUndefined();
    const s2 = reducer(s1, { type: "UNDO" });
    expect(s2.doc.blocks[bid]).toEqual(before);
  });

  test("Hide → Delete → Undo: restored block carries visible=false (no stale-field leak)", () => {
    // Slice 3.8 lesson — undo must restore the exact pre-delete shape, not
    // a stale snapshot from before the Hide action.
    const s0 = initState();
    const bid = findBlockIdByType(s0, "eyebrow_tag");

    const s1 = reducer(s0, { type: "TOGGLE_VIS", blockId: bid });
    expect(s1.doc.blocks[bid].visible).toBe(false);

    const s2 = reducer(s1, { type: "REMOVE_BLOCK", blockId: bid });
    expect(s2.doc.blocks[bid]).toBeUndefined();

    const s3 = reducer(s2, { type: "UNDO" });
    expect(s3.doc.blocks[bid]).toBeDefined();
    expect(s3.doc.blocks[bid].visible).toBe(false);
  });
});
