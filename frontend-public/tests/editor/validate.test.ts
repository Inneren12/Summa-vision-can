import { validate } from "../../src/components/editor/validation/validate";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";
import type { CanonicalDocument } from "../../src/components/editor/types";

function cloneDoc(tid: keyof typeof TPLS): CanonicalDocument {
  // Deep clone a fresh template doc so test mutations don't leak.
  return JSON.parse(JSON.stringify(mkDoc(tid as string, TPLS[tid as string])));
}

function findBlockIdByType(doc: CanonicalDocument, type: string): string {
  const bid = Object.keys(doc.blocks).find(id => doc.blocks[id].type === type);
  if (!bid) throw new Error(`No block of type ${type} in fixture`);
  return bid;
}

describe("validate / baseline", () => {
  test("accepts a freshly built single_stat_hero doc (no errors)", () => {
    const doc = cloneDoc("single_stat_hero");
    const r = validate(doc);
    expect(r.errors).toEqual([]);
  });

  test("accepts a freshly built ranked_bar_simple doc", () => {
    const doc = cloneDoc("ranked_bar_simple");
    const r = validate(doc);
    expect(r.errors).toEqual([]);
  });
});

describe("validate / page config unknown checks", () => {
  test("flags unknown palette", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "not_a_palette";
    const r = validate(doc);
    expect(r.errors.some(e => /Unknown palette/.test(e))).toBe(true);
  });

  test("flags unknown background", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.background = "not_a_bg";
    const r = validate(doc);
    expect(r.errors.some(e => /Unknown background/.test(e))).toBe(true);
  });

  test("flags unknown size", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.size = "not_a_size";
    const r = validate(doc);
    expect(r.errors.some(e => /Unknown size/.test(e))).toBe(true);
  });
});

describe("validate / duplicate ids", () => {
  test("flags duplicate section id", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.sections[1].id = doc.sections[0].id;
    const r = validate(doc);
    expect(r.errors.some(e => /Duplicate section id/.test(e))).toBe(true);
  });

  test("flags duplicate blockId within a single section", () => {
    const doc = cloneDoc("single_stat_hero");
    const sec = doc.sections[0];
    sec.blockIds.push(sec.blockIds[0]);
    const r = validate(doc);
    expect(r.errors.some(e => /duplicate blockId/.test(e))).toBe(true);
  });
});

describe("validate / delegates to validateBlockData", () => {
  test("surfaces invalid line chart data via the shared validator", () => {
    const doc = cloneDoc("line_area");
    const bid = findBlockIdByType(doc, "line_editorial");
    // Corrupt the series so length !== xLabels.length
    doc.blocks[bid].props.series = [
      { label: "X", role: "primary", data: [1, 2] },
    ];
    const r = validate(doc);
    expect(r.errors.some(e => /Line Chart.*points but/.test(e))).toBe(true);
  });

  test("surfaces invalid bar data (empty items) via the shared validator", () => {
    const doc = cloneDoc("ranked_bar_simple");
    const bid = findBlockIdByType(doc, "bar_horizontal");
    doc.blocks[bid].props.items = [];
    const r = validate(doc);
    expect(r.errors.some(e => /Ranked Bars.*at least one item/.test(e))).toBe(true);
  });
});

describe("validate / required blocks + empty content", () => {
  test("flags empty headline", () => {
    const doc = cloneDoc("single_stat_hero");
    const bid = findBlockIdByType(doc, "headline_editorial");
    doc.blocks[bid].props.text = "";
    const r = validate(doc);
    expect(r.errors.some(e => /Headline is empty/.test(e))).toBe(true);
  });

  test("flags empty hero number", () => {
    const doc = cloneDoc("single_stat_hero");
    const bid = findBlockIdByType(doc, "hero_stat");
    doc.blocks[bid].props.value = "";
    const r = validate(doc);
    expect(r.errors.some(e => /Hero number is empty/.test(e))).toBe(true);
  });
});
