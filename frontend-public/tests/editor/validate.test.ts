import { validate } from "../../src/components/editor/validation/validate";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";
import type { CanonicalDocument } from "../../src/components/editor/types";
import type { ValidationMessage } from "../../src/components/editor/validation/types";
import { validateImportStrict } from "../../src/components/editor/registry/guards";

function importMessage(doc: unknown): string | null {
  try {
    validateImportStrict(doc);
    return null;
  } catch (err) {
    return err instanceof Error ? err.message : String(err);
  }
}

function hasValidationKey(messages: ValidationMessage[], key: string): boolean {
  return messages.some(m => m.key === key);
}

function cloneDoc(tid: keyof typeof TPLS): CanonicalDocument {
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
    expect(hasValidationKey(r.errors, 'validation.page.unknown_palette')).toBe(true);
  });

  test("flags unknown background", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.background = "not_a_bg";
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.page.unknown_background')).toBe(true);
  });

  test("flags unknown size", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.size = "not_a_size";
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.page.unknown_size')).toBe(true);
  });
});

describe("validate / duplicate ids", () => {
  test("flags duplicate section id", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.sections[1].id = doc.sections[0].id;
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.section.duplicate_id')).toBe(true);
  });

  test("flags duplicate blockId within a single section", () => {
    const doc = cloneDoc("single_stat_hero");
    const sec = doc.sections[0];
    sec.blockIds.push(sec.blockIds[0]);
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.section.duplicate_block_id')).toBe(true);
  });
});

describe("validate / delegates to validateBlockData", () => {
  test("surfaces invalid line chart data via the shared validator", () => {
    const doc = cloneDoc("line_area");
    const bid = findBlockIdByType(doc, "line_editorial");
    doc.blocks[bid].props.series = [{ label: "X", role: "primary", data: [1, 2] }];
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.series.points_mismatch')).toBe(true);
  });

  test("surfaces invalid bar data (empty items) via the shared validator", () => {
    const doc = cloneDoc("ranked_bar_simple");
    const bid = findBlockIdByType(doc, "bar_horizontal");
    doc.blocks[bid].props.items = [];
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.items.min_one')).toBe(true);
  });

  test("validateImportStrict and validate agree on block-data rules", () => {
    const doc = cloneDoc("line_area");
    const bid = findBlockIdByType(doc, "line_editorial");
    doc.blocks[bid].props.series[0].data = [1];
    const importErr = importMessage(doc);
    const validation = validate(doc);
    expect(importErr).toMatch(/Invalid props for line_editorial/);
    expect(hasValidationKey(validation.errors, 'validation.series.points_mismatch')).toBe(true);
  });
});

describe("validate / required blocks + empty content", () => {
  test("flags empty headline", () => {
    const doc = cloneDoc("single_stat_hero");
    const bid = findBlockIdByType(doc, "headline_editorial");
    doc.blocks[bid].props.text = "";
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.headline.empty')).toBe(true);
  });

  test("flags empty hero number", () => {
    const doc = cloneDoc("single_stat_hero");
    const bid = findBlockIdByType(doc, "hero_stat");
    doc.blocks[bid].props.value = "";
    const r = validate(doc);
    expect(hasValidationKey(r.errors, 'validation.hero_number.empty')).toBe(true);
  });
});

describe("validate / contrast integration", () => {
  test("ValidationResult.contrastIssues is always an array", () => {
    const doc = cloneDoc("single_stat_hero");
    const r = validate(doc);
    expect(Array.isArray(r.contrastIssues)).toBe(true);
  });

  test("every contrast error is mirrored into the errors bucket", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "housing";
    doc.page.background = "solid_dark";
    const r = validate(doc);
    for (const issue of r.contrastIssues.filter(i => i.severity === "error")) {
      expect(r.errors).toContainEqual(issue.message);
    }
  });

  test("every contrast warning is mirrored into the warnings bucket", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "neutral";
    doc.page.background = "gradient_warm";
    const r = validate(doc);
    for (const issue of r.contrastIssues.filter(i => i.severity === "warning")) {
      expect(r.warnings).toContainEqual(issue.message);
    }
  });

  test("crude YIQ 'Primary color may be too dark' warning is gone", () => {
    for (const pid of ["housing", "government", "energy", "society", "economy", "neutral"]) {
      const doc = cloneDoc("single_stat_hero");
      doc.page.palette = pid;
      const r = validate(doc);
      expect(r.warnings.some(w => w.key === 'validation.primary_too_dark')).toBe(false);
    }
  });
});
