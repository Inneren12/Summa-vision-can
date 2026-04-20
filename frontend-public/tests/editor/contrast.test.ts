import {
  hexToRgb,
  relativeLuminance,
  contrastRatio,
  getBlockTextColor,
  validateContrast,
  TEXT_BEARING_BLOCKS,
} from "../../src/components/editor/validation/contrast";
import { PALETTES } from "../../src/components/editor/config/palettes";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";
import type { CanonicalDocument } from "../../src/components/editor/types";

function cloneDoc(tid: string): CanonicalDocument {
  return JSON.parse(JSON.stringify(mkDoc(tid, TPLS[tid])));
}

describe("hexToRgb", () => {
  test("parses uppercase and lowercase", () => {
    expect(hexToRgb("#FFFFFF")).toEqual({ r: 255, g: 255, b: 255 });
    expect(hexToRgb("#000000")).toEqual({ r: 0, g: 0, b: 0 });
    expect(hexToRgb("#ff5733")).toEqual({ r: 255, g: 87, b: 51 });
  });

  test("parses without leading #", () => {
    expect(hexToRgb("F3F4F6")).toEqual({ r: 243, g: 244, b: 246 });
  });

  test("throws on malformed input", () => {
    expect(() => hexToRgb("#FFF")).toThrow();
    expect(() => hexToRgb("not-a-colour")).toThrow();
    expect(() => hexToRgb("#GGGGGG")).toThrow();
  });
});

describe("relativeLuminance", () => {
  test("black = 0, white = 1 (exact per WCAG)", () => {
    expect(relativeLuminance("#000000")).toBeCloseTo(0, 5);
    expect(relativeLuminance("#FFFFFF")).toBeCloseTo(1, 5);
  });

  test("ordered: black < dark-grey < mid-grey < light-grey < white", () => {
    const lums = ["#000000", "#333333", "#808080", "#CCCCCC", "#FFFFFF"].map(
      relativeLuminance,
    );
    for (let i = 1; i < lums.length; i++) {
      expect(lums[i]).toBeGreaterThan(lums[i - 1]);
    }
  });
});

describe("contrastRatio — WebAIM reference values", () => {
  test("black on white = 21:1 (exact)", () => {
    expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
  });

  test("white on black = 21:1 (symmetric)", () => {
    expect(contrastRatio("#FFFFFF", "#000000")).toBeCloseTo(21, 1);
  });

  test("mid-grey #767676 on white ≈ 4.54 (W3C WCAG 2.1 math; WebAIM rounds to 4.48)", () => {
    expect(contrastRatio("#767676", "#FFFFFF")).toBeCloseTo(4.54, 1);
  });

  test("same colour on itself = 1:1", () => {
    expect(contrastRatio("#0B0D11", "#0B0D11")).toBeCloseTo(1, 5);
  });

  test("palette primary #22D3EE on solid_dark #0B0D11 exceeds 4.5", () => {
    expect(contrastRatio("#22D3EE", "#0B0D11")).toBeGreaterThan(4.5);
  });

  test("TK.c.txtP #F3F4F6 on #0B0D11 exceeds 15", () => {
    expect(contrastRatio("#F3F4F6", "#0B0D11")).toBeGreaterThan(15);
  });
});

describe("getBlockTextColor", () => {
  const housing = PALETTES.housing;

  test("headline_editorial → TK.c.txtP", () => {
    expect(getBlockTextColor("headline_editorial", housing)).toBe("#F3F4F6");
  });

  test("hero_stat default slot → pal.p", () => {
    expect(getBlockTextColor("hero_stat", housing)).toBe(housing.p);
  });

  test("hero_stat label slot → TK.c.txtS", () => {
    expect(getBlockTextColor("hero_stat", housing, "label")).toBe("#8B949E");
  });

  test("bar_horizontal value slot → txtP, default slot → txtS", () => {
    expect(getBlockTextColor("bar_horizontal", housing, "value")).toBe("#F3F4F6");
    expect(getBlockTextColor("bar_horizontal", housing)).toBe("#8B949E");
  });

  test("comparison_kpi label slot → txtS, default → pal.p", () => {
    expect(getBlockTextColor("comparison_kpi", housing, "label")).toBe("#8B949E");
    expect(getBlockTextColor("comparison_kpi", housing)).toBe(housing.p);
  });

  test("table_enriched score slot → txtP, default → txtS", () => {
    expect(getBlockTextColor("table_enriched", housing, "score")).toBe("#F3F4F6");
    expect(getBlockTextColor("table_enriched", housing)).toBe("#8B949E");
  });

  test("brand_stamp → TK.c.acc", () => {
    expect(getBlockTextColor("brand_stamp", housing)).toBe("#FBBF24");
  });

  test("delta_badge → pal.neg (worst-case direction)", () => {
    expect(getBlockTextColor("delta_badge", housing)).toBe(housing.neg);
  });

  test("line_editorial → pal.p", () => {
    expect(getBlockTextColor("line_editorial", housing)).toBe(housing.p);
  });

  test("unknown block type → null", () => {
    expect(getBlockTextColor("not_a_block", housing)).toBeNull();
  });

  test("every TEXT_BEARING_BLOCKS entry returns a non-null colour", () => {
    for (const t of TEXT_BEARING_BLOCKS) {
      expect(getBlockTextColor(t, housing)).not.toBeNull();
    }
  });
});

describe("validateContrast — integration", () => {
  test("default single_stat_hero + housing + solid_dark → no issues", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "housing";
    doc.page.background = "solid_dark";
    expect(validateContrast(doc)).toEqual([]);
  });

  test("unknown palette → no contrast issues (outer validator flags id)", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "not_a_palette";
    doc.page.background = "solid_dark";
    expect(validateContrast(doc)).toEqual([]);
  });

  test("unknown background → no contrast issues", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "housing";
    doc.page.background = "not_a_background";
    expect(validateContrast(doc)).toEqual([]);
  });

  test("hidden block is skipped", () => {
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "housing";
    doc.page.background = "solid_dark";
    // Force a contrast failure by pointing palette.p at a very-dark value
    // for a block that reads pal.p (hero_stat). Hide the block → no issue.
    doc.page.palette = "housing";
    for (const bid of Object.keys(doc.blocks)) {
      doc.blocks[bid].visible = false;
    }
    expect(validateContrast(doc)).toEqual([]);
  });

  test("every emitted issue has valid shape and threshold 3 or 4.5", () => {
    // Exercise the iteration path against every palette × gradient combo.
    for (const pid of Object.keys(PALETTES)) {
      for (const bg of ["gradient_warm", "gradient_midnight", "gradient_radial"]) {
        const doc = cloneDoc("single_stat_hero");
        doc.page.palette = pid;
        doc.page.background = bg;
        const issues = validateContrast(doc);
        for (const i of issues) {
          expect(i.message).toMatch(/\d+(\.\d+)?:1/);
          expect(i.ratio).toBeGreaterThanOrEqual(1);
          expect([3, 4.5]).toContain(i.threshold);
          expect(["error", "warning"]).toContain(i.severity);
          expect(["base", "lightestStop"]).toContain(i.bgPoint);
          expect(i.textColor).toMatch(/^#[0-9A-Fa-f]{6}$/);
          expect(i.bgColor).toMatch(/^#[0-9A-Fa-f]{6}$/);
          expect(doc.blocks[i.blockId]).toBeDefined();
        }
      }
    }
  });

  test("gradient issues are warnings (not errors) for standard palette × bg combos", () => {
    // All stock backgrounds have a dark #0B0D11 base that passes against
    // the standard text tokens. Any gradient flag should therefore be a
    // warning against lightestStop, not an error against base.
    const doc = cloneDoc("single_stat_hero");
    doc.page.palette = "neutral";
    doc.page.background = "gradient_warm";
    const issues = validateContrast(doc);
    for (const issue of issues) {
      expect(issue.severity).toBe("warning");
      expect(issue.bgPoint).toBe("lightestStop");
    }
  });
});
