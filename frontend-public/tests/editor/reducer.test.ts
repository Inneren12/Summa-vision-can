import { reducer, initState } from "../../src/components/editor/store/reducer";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";
import type { EditorState, EditorAction } from "../../src/components/editor/types";

function firstBlockId(state: EditorState): string {
  return Object.keys(state.doc.blocks)[0];
}

function findBlockIdByType(state: EditorState, type: string): string {
  const bid = Object.keys(state.doc.blocks).find(
    id => state.doc.blocks[id].type === type,
  );
  if (!bid) throw new Error(`No block of type ${type} in test fixture`);
  return bid;
}

describe("reducer / initState", () => {
  test("initState yields a document with sections + blocks", () => {
    const s = initState();
    expect(s.doc.templateId).toBe("single_stat_hero");
    expect(s.doc.sections.length).toBeGreaterThan(0);
    expect(Object.keys(s.doc.blocks).length).toBeGreaterThan(0);
    expect(s.undoStack).toEqual([]);
    expect(s.redoStack).toEqual([]);
    expect(s.dirty).toBe(false);
    expect(s.mode).toBe("design");
  });
});

describe("reducer / UPDATE_PROP", () => {
  test("mutates the target block's props and pushes to undo", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "New Headline" });
    expect(s1.doc.blocks[bid].props.text).toBe("New Headline");
    expect(s1.undoStack.length).toBe(1);
    expect(s1.dirty).toBe(true);
  });

  test("no-op when blockId does not exist", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: "blk_nope", key: "text", value: "x" });
    // Permission gate rejects. Doc reference unchanged; rejection recorded
    // on `_lastRejection` (PR 2a — was `s1 === s0` before the field existed).
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("UPDATE_PROP");
  });
});

describe("reducer / UNDO + REDO", () => {
  test("undo restores prior state; redo reapplies it", () => {
    const s0 = initState();
    const bid = findBlockIdByType(s0, "headline_editorial");
    const originalText = s0.doc.blocks[bid].props.text;

    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: bid, key: "text", value: "Changed" });
    expect(s1.doc.blocks[bid].props.text).toBe("Changed");

    const s2 = reducer(s1, { type: "UNDO" });
    expect(s2.doc.blocks[bid].props.text).toBe(originalText);
    expect(s2.redoStack.length).toBe(1);

    const s3 = reducer(s2, { type: "REDO" });
    expect(s3.doc.blocks[bid].props.text).toBe("Changed");
  });

  test("undo with empty undoStack is a no-op", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "UNDO" });
    expect(s1).toBe(s0);
  });
});

describe("reducer / SWITCH_TPL", () => {
  test("switches document to the new template and clears undo stack", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: firstBlockId(s0), key: "text", value: "x" });
    const s2 = reducer(s1, { type: "SWITCH_TPL", tid: "ranked_bar_simple" });
    expect(s2.doc.templateId).toBe("ranked_bar_simple");
    // Undo stack grows by one (snapshot of pre-switch doc); redo cleared.
    expect(s2.redoStack).toEqual([]);
    expect(s2.selectedBlockId).toBeNull();
  });

  test("unknown templateId is a no-op", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "SWITCH_TPL", tid: "not_a_template" });
    expect(s1).toBe(s0);
  });
});

describe("reducer / SET_MODE", () => {
  test("switches mode between design and template", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "SET_MODE", mode: "template" });
    expect(s1.mode).toBe("template");
    const s2 = reducer(s1, { type: "SET_MODE", mode: "design" });
    expect(s2.mode).toBe("design");
  });
});

describe("reducer / permission gate", () => {
  test("template mode blocks palette change", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "SET_MODE", mode: "template" });
    const originalPal = s1.doc.page.palette;
    const s2 = reducer(s1, { type: "CHANGE_PAGE", key: "palette", value: "neutral" });
    expect(s2.doc.page.palette).toBe(originalPal);
  });

  test("template mode blocks switch template", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "SET_MODE", mode: "template" });
    const s2 = reducer(s1, { type: "SWITCH_TPL", tid: "ranked_bar_simple" });
    expect(s2.doc.templateId).toBe(s1.doc.templateId);
  });

  test("design mode allows palette change", () => {
    const s0 = initState(); // design by default
    const s1 = reducer(s0, { type: "CHANGE_PAGE", key: "palette", value: "neutral" });
    expect(s1.doc.page.palette).toBe("neutral");
  });

  test("template mode blocks editing structural keys like 'items'", () => {
    const s0 = initState();
    // ranked_bar_simple has bar_horizontal so we can exercise items editing
    const withBars = reducer(s0, { type: "SWITCH_TPL", tid: "ranked_bar_simple" });
    const inTemplate = reducer(withBars, { type: "SET_MODE", mode: "template" });
    const barId = findBlockIdByType(inTemplate, "bar_horizontal");
    const originalItems = inTemplate.doc.blocks[barId].props.items;
    const after = reducer(inTemplate, {
      type: "UPDATE_PROP", blockId: barId, key: "items", value: [],
    } as EditorAction);
    // Structural key blocked — items unchanged
    expect(after.doc.blocks[barId].props.items).toEqual(originalItems);
  });
});

describe("reducer / IMPORT", () => {
  test("accepts a valid hydrated doc and resets undo/redo", () => {
    const s0 = initState();
    const s1 = reducer(s0, { type: "UPDATE_PROP", blockId: firstBlockId(s0), key: "text", value: "x" });
    const freshDoc = mkDoc("insight_card", TPLS.insight_card);
    const s2 = reducer(s1, { type: "IMPORT", doc: freshDoc });
    expect(s2.doc.templateId).toBe("insight_card");
    expect(s2.undoStack).toEqual([]);
    expect(s2.redoStack).toEqual([]);
    expect(s2.dirty).toBe(false);
  });

  test("rejects a malformed doc (defense in depth)", () => {
    const s0 = initState();
    const bad: any = { schemaVersion: 1, templateId: "x", page: { size: "a", background: "b", palette: "c" }, sections: "bad", blocks: {} };
    const s1 = reducer(s0, { type: "IMPORT", doc: bad });
    // Doc unchanged; rejection now flows through withRejection so UI has a
    // uniform signal (PR 2a fix prompt — Issue 4).
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe("IMPORT");
    expect(s1._lastRejection?.reason.length).toBeGreaterThan(0);
  });
});
