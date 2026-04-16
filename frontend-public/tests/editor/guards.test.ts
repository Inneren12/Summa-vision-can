import {
  validateImport,
  hydrateImportedDoc,
  SUPPORTED_SCHEMA_VERSIONS,
  CURRENT_SCHEMA,
} from "../../src/components/editor/registry/guards";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";

function goodDoc() {
  // Baseline valid doc, deep-cloned each call so mutating it in one test
  // doesn't leak into others.
  return JSON.parse(JSON.stringify(mkDoc("single_stat_hero", TPLS.single_stat_hero)));
}

function docForTemplate(tid: keyof typeof TPLS) {
  return JSON.parse(JSON.stringify(mkDoc(tid, TPLS[tid])));
}

describe("hydrateImportedDoc", () => {
  test("returns { doc, warnings } with no warnings for a clean input", () => {
    const d = goodDoc();
    const result = hydrateImportedDoc(d);
    expect(result.doc.schemaVersion).toBe(CURRENT_SCHEMA);
    expect(result.doc.templateId).toBe("single_stat_hero");
    expect(Array.isArray(result.warnings)).toBe(true);
    expect(result.warnings).toEqual([]);
  });

  test("fills page defaults for a missing page config and records warnings", () => {
    const d: any = goodDoc();
    delete d.page;
    const result = hydrateImportedDoc(d);
    expect(result.doc.page.size).toBeDefined();
    expect(result.doc.page.background).toBeDefined();
    expect(result.doc.page.palette).toBeDefined();
    expect(result.warnings.some(w => /page config/i.test(w))).toBe(true);
  });

  test("warns when a partial page config is filled", () => {
    const d: any = goodDoc();
    delete d.page.size;
    const result = hydrateImportedDoc(d);
    expect(result.doc.page.size).toBe("instagram_1080");
    expect(result.warnings.some(w => /page\.size/.test(w))).toBe(true);
  });

  test("rejects unsupported schemaVersion (throws)", () => {
    const d: any = goodDoc();
    d.schemaVersion = 99;
    expect(() => hydrateImportedDoc(d)).toThrow(/Unsupported schemaVersion/);
  });

  test("throws on non-object input", () => {
    expect(() => hydrateImportedDoc(null as any)).toThrow();
    expect(() => hydrateImportedDoc("string" as any)).toThrow();
  });

  test("forces block.id to match object key and records realignment warning", () => {
    const d: any = goodDoc();
    const firstKey = Object.keys(d.blocks)[0];
    d.blocks[firstKey].id = "MISMATCHED_ID";
    const result = hydrateImportedDoc(d);
    expect(result.doc.blocks[firstKey].id).toBe(firstKey);
    expect(result.warnings.some(w => /Realigned/.test(w))).toBe(true);
  });

  test("defaults workflow to 'draft' when invalid and records warning", () => {
    const d: any = goodDoc();
    d.workflow = "not_a_real_state";
    const result = hydrateImportedDoc(d);
    expect(result.doc.workflow).toBe("draft");
    expect(result.warnings.some(w => /workflow/i.test(w))).toBe(true);
  });

  test("warns about unknown block types but keeps them in doc", () => {
    const d: any = goodDoc();
    const firstKey = Object.keys(d.blocks)[0];
    d.blocks[firstKey].type = "not_a_real_block_type";
    const result = hydrateImportedDoc(d);
    expect(result.warnings.some(w => /unknown type/i.test(w))).toBe(true);
  });

  test("passes through supported schemaVersion list", () => {
    expect(Array.from(SUPPORTED_SCHEMA_VERSIONS)).toContain(CURRENT_SCHEMA);
  });

  test("missing schemaVersion becomes CURRENT_SCHEMA with warning", () => {
    const d: any = goodDoc();
    delete d.schemaVersion;
    const result = hydrateImportedDoc(d);
    expect(result.doc.schemaVersion).toBe(CURRENT_SCHEMA);
    expect(result.warnings.some(w => /schemaVersion/i.test(w))).toBe(true);
  });

  test("normalizes deterministic nested _id for legacy bar/line/kpi data", () => {
    const barDoc: any = docForTemplate("ranked_bar_simple");
    const lineDoc: any = docForTemplate("line_area");
    const kpiDoc: any = docForTemplate("single_stat_hero");
    const barId = Object.keys(barDoc.blocks).find(id => barDoc.blocks[id].type === "bar_horizontal");
    const lineId = Object.keys(lineDoc.blocks).find(id => lineDoc.blocks[id].type === "line_editorial");
    const kpiId = Object.keys(kpiDoc.blocks)[0];
    kpiDoc.blocks[kpiId].type = "comparison_kpi";
    kpiDoc.blocks[kpiId].props = {
      items: [
        { label: "A", value: "1", delta: "+1", direction: "positive" },
        { label: "B", value: "2", delta: "+2", direction: "neutral" },
      ],
    };
    if (!barId || !lineId || !kpiId) throw new Error("missing fixture blocks");
    barDoc.blocks[barId].props.items.forEach((it: any) => { delete it._id; });
    lineDoc.blocks[lineId].props.series.forEach((it: any) => { delete it._id; });
    kpiDoc.blocks[kpiId].props.items.forEach((it: any) => { delete it._id; });

    const barResult = hydrateImportedDoc(barDoc);
    const lineResult = hydrateImportedDoc(lineDoc);
    const kpiResult = hydrateImportedDoc(kpiDoc);

    expect(barResult.doc.blocks[barId].props.items[0]._id).toBe(`${barId}_items_0`);
    expect(lineResult.doc.blocks[lineId].props.series[0]._id).toBe(`${lineId}_series_0`);
    expect(kpiResult.doc.blocks[kpiId].props.items[0]._id).toBe(`${kpiId}_items_0`);
    expect(barResult.warnings.some(w => /missing _id/.test(w))).toBe(true);
  });

  test("re-importing same legacy JSON keeps deterministic nested ids stable", () => {
    const d: any = docForTemplate("ranked_bar_simple");
    const barId = Object.keys(d.blocks).find(id => d.blocks[id].type === "bar_horizontal");
    if (!barId) throw new Error("missing bar block");
    d.blocks[barId].props.items.forEach((it: any) => { delete it._id; });

    const first = hydrateImportedDoc(JSON.parse(JSON.stringify(d)));
    const second = hydrateImportedDoc(JSON.parse(JSON.stringify(d)));

    const firstIds = first.doc.blocks[barId].props.items.map((it: any) => it._id);
    const secondIds = second.doc.blocks[barId].props.items.map((it: any) => it._id);
    expect(firstIds).toEqual(secondIds);
  });

  test("normalizes malformed scalar props and emits warnings", () => {
    const d: any = docForTemplate("ranked_bar_simple");
    const barId = Object.keys(d.blocks).find(id => d.blocks[id].type === "bar_horizontal");
    if (!barId) throw new Error("missing bar block");
    d.blocks[barId].props.showBenchmark = "yes";
    d.blocks[barId].props.benchmarkValue = "5";

    const result = hydrateImportedDoc(d);

    expect(result.doc.blocks[barId].props.showBenchmark).toBe(true);
    expect(result.doc.blocks[barId].props.benchmarkValue).toBe(5);
    expect(result.warnings.some(w => /showBenchmark expected boolean/.test(w))).toBe(true);
    expect(result.warnings.some(w => /benchmarkValue expected finite number/.test(w))).toBe(true);
  });

  test("normalizes defaults + deterministic ids when chart props are null or non-object", () => {
    const dNull: any = docForTemplate("ranked_bar_simple");
    const barId = Object.keys(dNull.blocks).find(id => dNull.blocks[id].type === "bar_horizontal");
    if (!barId) throw new Error("missing bar block");
    dNull.blocks[barId].props = null;

    const nullResult = hydrateImportedDoc(dNull);
    expect(nullResult.doc.blocks[barId].props.items[0]._id).toBe(`${barId}_items_0`);

    const dGarbage: any = docForTemplate("ranked_bar_simple");
    dGarbage.blocks[barId].props = "garbage";
    const garbageResult = hydrateImportedDoc(dGarbage);
    expect(garbageResult.doc.blocks[barId].props.items[0]._id).toBe(`${barId}_items_0`);
  });
});

describe("mkDoc nested _id synthesis", () => {
  test("bar_horizontal items get deterministic _id from mkDoc", () => {
    const doc = mkDoc("ranked_bar_simple", TPLS.ranked_bar_simple);
    const barBlock = Object.values(doc.blocks).find(b => b.type === "bar_horizontal");
    expect(barBlock).toBeDefined();
    const items = barBlock!.props.items as any[];
    expect(items.length).toBeGreaterThan(0);
    items.forEach((it, i) => {
      expect(it._id).toBe(`${barBlock!.id}_items_${i}`);
    });
  });

  test("line_editorial series get deterministic _id from mkDoc", () => {
    const doc = mkDoc("line_area", TPLS.line_area);
    const lineBlock = Object.values(doc.blocks).find(b => b.type === "line_editorial");
    expect(lineBlock).toBeDefined();
    const series = lineBlock!.props.series as any[];
    expect(series.length).toBeGreaterThan(0);
    series.forEach((s, i) => {
      expect(s._id).toBe(`${lineBlock!.id}_series_${i}`);
    });
  });

  test("comparison_kpi items get deterministic _id from mkDoc", () => {
    const doc = mkDoc("comparison_3kpi", TPLS.comparison_3kpi);
    const kpiBlock = Object.values(doc.blocks).find(b => b.type === "comparison_kpi");
    expect(kpiBlock).toBeDefined();
    const items = kpiBlock!.props.items as any[];
    expect(items.length).toBeGreaterThan(0);
    items.forEach((it, i) => {
      expect(it._id).toBe(`${kpiBlock!.id}_items_${i}`);
    });
  });

  test("template switch produces stable ids across calls", () => {
    const doc1 = mkDoc("ranked_bar_simple", TPLS.ranked_bar_simple);
    const doc2 = mkDoc("ranked_bar_simple", TPLS.ranked_bar_simple);
    const bar1 = Object.values(doc1.blocks).find(b => b.type === "bar_horizontal");
    const bar2 = Object.values(doc2.blocks).find(b => b.type === "bar_horizontal");
    const ids1 = (bar1!.props.items as any[]).map(it => it._id);
    const ids2 = (bar2!.props.items as any[]).map(it => it._id);
    expect(ids1).toEqual(ids2);
  });
});

describe("validateImport", () => {
  test("accepts a freshly-built doc", () => {
    expect(validateImport(goodDoc())).toBeNull();
  });

  test("rejects non-object", () => {
    expect(validateImport(null)).toMatch(/Not an object/);
  });

  test("rejects missing schemaVersion", () => {
    const d: any = goodDoc();
    delete d.schemaVersion;
    expect(validateImport(d)).toMatch(/Missing schemaVersion/);
  });

  test("rejects unsupported schemaVersion", () => {
    const d: any = goodDoc();
    d.schemaVersion = 42;
    expect(validateImport(d)).toMatch(/Unsupported schemaVersion/);
  });

  test("rejects missing sections array", () => {
    const d: any = goodDoc();
    d.sections = "not-an-array";
    expect(validateImport(d)).toMatch(/Missing sections array/);
  });

  test("rejects section referencing missing block", () => {
    const d: any = goodDoc();
    d.sections[0].blockIds.push("nonexistent_block_id");
    expect(validateImport(d)).toMatch(/references missing block/);
  });

  test("rejects block referenced from multiple sections", () => {
    const d: any = goodDoc();
    const bid = d.sections[0].blockIds[0];
    d.sections[1].blockIds.push(bid);
    expect(validateImport(d)).toMatch(/referenced in multiple sections/);
  });

  test("rejects orphan block (present in blocks, unreferenced by any section)", () => {
    const d: any = goodDoc();
    d.blocks["blk_orphan"] = {
      id: "blk_orphan",
      type: "eyebrow_tag",
      props: { text: "x" },
      visible: true,
    };
    expect(validateImport(d)).toMatch(/Orphan block/);
  });

  test("rejects block.id that doesn't match its key", () => {
    const d: any = goodDoc();
    const key = Object.keys(d.blocks)[0];
    d.blocks[key].id = "WRONG";
    expect(validateImport(d)).toMatch(/Block id mismatch/);
  });

  test("rejects unknown block type", () => {
    const d: any = goodDoc();
    const key = Object.keys(d.blocks)[0];
    d.blocks[key].type = "this_type_does_not_exist";
    expect(validateImport(d)).toMatch(/Unknown block type/);
  });

  test("rejects duplicate section id", () => {
    const d: any = goodDoc();
    d.sections[1].id = d.sections[0].id;
    expect(validateImport(d)).toMatch(/Duplicate section id/);
  });
});
