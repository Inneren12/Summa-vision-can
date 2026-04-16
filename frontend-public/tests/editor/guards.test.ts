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
