import { reducer, initState } from "../reducer";
import { BREG } from "../../registry/blocks";
import type { EditorState } from "../../types";
import type { Binding, SingleValueBinding } from "../../binding/types";

/**
 * Build a state containing a single duplicatable block. `body_annotation`
 * has maxPerSection: 2 in the registry; one instance leaves room for one
 * duplicate. Keeping the fixture minimal sidesteps template-default
 * maxPerSection caps.
 */
function baseState(): EditorState {
  const s = initState();
  const reg = BREG.body_annotation;
  if (!reg) throw new Error("body_annotation missing from registry");
  const blockId = "blk_dup_src";
  return {
    ...s,
    doc: {
      ...s.doc,
      sections: [{ id: "sec_test", type: "context", blockIds: [blockId] }],
      blocks: {
        [blockId]: {
          id: blockId,
          type: "body_annotation",
          props: { ...reg.dp },
          visible: true,
        },
      },
    },
  };
}

const SOURCE_ID = "blk_dup_src";

function attachBinding(state: EditorState, blockId: string, binding: Binding): EditorState {
  return {
    ...state,
    doc: {
      ...state.doc,
      blocks: {
        ...state.doc.blocks,
        [blockId]: { ...state.doc.blocks[blockId], binding },
      },
    },
  };
}

describe("reducer / DUPLICATE_BLOCK — binding (Phase 3.1d Slice 2)", () => {
  it("clones binding deeply on a bound source block", () => {
    const binding: SingleValueBinding = {
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
    };
    const s0 = baseState();
    const blockId = SOURCE_ID;
    const s1 = attachBinding(s0, blockId, binding);
    const s2 = reducer(s1, { type: "DUPLICATE_BLOCK", blockId, newId: "blk_dup_1" });

    const dup = s2.doc.blocks["blk_dup_1"];
    expect(dup).toBeDefined();
    expect(dup.binding).toEqual(binding);
    // Reference identity: cloned, not aliased.
    expect(dup.binding).not.toBe(s1.doc.blocks[blockId].binding);
    expect(dup.binding!.filters).not.toBe(s1.doc.blocks[blockId].binding!.filters);
  });

  it("does not introduce binding on a source block without one", () => {
    const s0 = baseState();
    const blockId = SOURCE_ID;
    const s1 = reducer(s0, { type: "DUPLICATE_BLOCK", blockId, newId: "blk_dup_2" });
    expect(s1.doc.blocks["blk_dup_2"]).toBeDefined();
    expect(s1.doc.blocks["blk_dup_2"]).not.toHaveProperty("binding");
  });

  it("mutating the duplicate's binding does not mutate the source binding", () => {
    const binding: SingleValueBinding = {
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
    };
    const s0 = baseState();
    const blockId = SOURCE_ID;
    const s1 = attachBinding(s0, blockId, binding);
    const s2 = reducer(s1, { type: "DUPLICATE_BLOCK", blockId, newId: "blk_dup_3" });

    const dupBinding = s2.doc.blocks["blk_dup_3"].binding as SingleValueBinding;
    dupBinding.filters.geo = "QC";

    const sourceBinding = s2.doc.blocks[blockId].binding as SingleValueBinding;
    expect(sourceBinding.filters.geo).toBe("ON");
  });
});
