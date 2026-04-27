import { isBlockEmpty } from "../../src/components/editor/utils/empty-block";
import { BREG } from "../../src/components/editor/registry/blocks";
import type { Block } from "../../src/components/editor/types";

function blockOfType(type: string, props?: Record<string, unknown>): Block {
  const reg = BREG[type];
  return {
    id: "blk_test",
    type,
    props: props ?? { ...reg.dp },
    visible: true,
  };
}

describe("isBlockEmpty", () => {
  test("returns true for a default-state block", () => {
    expect(isBlockEmpty(blockOfType("headline_editorial"))).toBe(true);
  });

  test("returns false when at least one prop differs from the default", () => {
    const b = blockOfType("headline_editorial", {
      ...BREG["headline_editorial"].dp,
      text: "User wrote something here",
    });
    expect(isBlockEmpty(b)).toBe(false);
  });

  test("returns false when nested array prop differs", () => {
    const reg = BREG["bar_horizontal"];
    const newItems = [
      { label: "A", value: 1, flag: "🍁", highlight: false },
    ];
    const b = blockOfType("bar_horizontal", { ...reg.dp, items: newItems });
    expect(isBlockEmpty(b)).toBe(false);
  });

  test("unknown block type returns false (conservative)", () => {
    expect(isBlockEmpty({ id: "x", type: "ghost_block", props: {}, visible: true })).toBe(false);
  });
});
