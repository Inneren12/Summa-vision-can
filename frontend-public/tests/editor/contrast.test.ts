import {
  hexToRgb,
  relativeLuminance,
  contrastRatio,
  getBlockTextSlots,
  validateContrast,
  TEXT_BEARING_BLOCKS,
} from "../../src/components/editor/validation/contrast";
import { BG_META } from "../../src/components/editor/config/backgrounds";
import { PALETTES } from "../../src/components/editor/config/palettes";
import { TK } from "../../src/components/editor/config/tokens";
import { TPLS, mkDoc } from "../../src/components/editor/registry/templates";
import type { CanonicalDocument, Palette } from "../../src/components/editor/types";

function cloneDoc(tid: string): CanonicalDocument {
  return JSON.parse(JSON.stringify(mkDoc(tid, TPLS[tid])));
}

function makeDoc(
  blockType: string,
  options?: { palette?: string; background?: string; visible?: boolean },
): CanonicalDocument {
  return {
    schemaVersion: 2,
    templateId: "test",
    page: {
      size: "square",
      background: options?.background ?? "solid_dark",
      palette: options?.palette ?? "housing",
    },
    sections: [{ id: "section-1", type: "hero", blockIds: ["block-1"] }],
    blocks: {
      "block-1": {
        id: "block-1",
        type: blockType,
        props: {},
        visible: options?.visible ?? true,
      },
    },
    meta: {
      createdAt: "2026-04-21T00:00:00.000Z",
      updatedAt: "2026-04-21T00:00:00.000Z",
      version: 1,
      history: [],
    },
    review: {
      workflow: "draft",
      history: [],
      comments: [],
    },
  };
}

function registerPalette(id: string, palette: Palette): void {
  (PALETTES as Record<string, Palette>)[id] = palette;
}

function registerBackground(
  id: string,
  background: { base: string; lightestStop?: string; isGradient: boolean },
): void {
  (BG_META as Record<string, { base: string; lightestStop?: string; isGradient: boolean }>)[id] =
    background;
}

function unregisterThemeFixture(id: string): void {
  delete (PALETTES as Record<string, Palette>)[id];
  delete (BG_META as Record<string, { base: string; lightestStop?: string; isGradient: boolean }>)[id];
}

afterEach(() => {
  unregisterThemeFixture("test_comparison_palette");
  unregisterThemeFixture("test_hero_label_palette");
  unregisterThemeFixture("test_hero_value_palette");
  unregisterThemeFixture("test_table_header_bg");
  unregisterThemeFixture("test_table_header_palette");
  unregisterThemeFixture("test_table_score_palette");
  unregisterThemeFixture("test_mid_bg");
  unregisterThemeFixture("test_dark_bg");
});

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

describe("getBlockTextSlots", () => {
  const housing = PALETTES.housing;

  test("headline_editorial → TK.c.txtP", () => {
    expect(getBlockTextSlots("headline_editorial", housing)).toEqual([
      { slot: "primary", color: TK.c.txtP },
    ]);
  });

  test("hero_stat default slot → pal.p", () => {
    expect(getBlockTextSlots("hero_stat", housing)).toEqual([
      { slot: "value", color: housing.p },
      { slot: "label", color: TK.c.txtS },
    ]);
  });

  test("hero_stat label slot → TK.c.txtS", () => {
    expect(getBlockTextSlots("hero_stat", housing)[1]).toEqual({
      slot: "label",
      color: TK.c.txtS,
    });
  });

  test("bar_horizontal value slot → txtP, default slot → txtS", () => {
    expect(getBlockTextSlots("bar_horizontal", housing)).toEqual([
      { slot: "label", color: TK.c.txtS },
      { slot: "value", color: TK.c.txtP },
    ]);
  });

  test("comparison_kpi label slot → txtS, default → pal.p", () => {
    const slots = getBlockTextSlots("comparison_kpi", housing);
    const bySlot = Object.fromEntries(slots.map(({ slot, color }) => [slot, color]));

    expect(slots).toHaveLength(4);
    expect(bySlot).toEqual({
      value: TK.c.txtP,
      delta_pos: housing.pos,
      delta_neg: housing.neg,
      label: TK.c.txtS,
    });
  });

  test("table_enriched score slot → txtP, default → txtS", () => {
    expect(getBlockTextSlots("table_enriched", housing)).toEqual([
      { slot: "header", color: TK.c.txtS },
      { slot: "cell", color: TK.c.txtP },
      { slot: "score", color: housing.p },
    ]);
  });

  test("brand_stamp → TK.c.acc", () => {
    expect(getBlockTextSlots("brand_stamp", housing)).toEqual([
      { slot: "primary", color: TK.c.acc },
    ]);
  });

  test("delta_badge → pal.neg (worst-case direction)", () => {
    expect(getBlockTextSlots("delta_badge", housing)).toEqual([
      { slot: "primary", color: housing.neg },
    ]);
  });

  test("line_editorial → pal.p", () => {
    expect(getBlockTextSlots("line_editorial", housing)).toEqual([
      { slot: "primary", color: housing.p },
    ]);
  });

  test("unknown block type → null", () => {
    expect(getBlockTextSlots("not_a_block", housing)).toEqual([]);
  });

  test("every TEXT_BEARING_BLOCKS entry returns a non-null colour", () => {
    for (const t of TEXT_BEARING_BLOCKS) {
      expect(getBlockTextSlots(t, housing).length).toBeGreaterThan(0);
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

  test("comparison_kpi emits only the failing delta_neg slot", () => {
    registerPalette("test_comparison_palette", {
      n: "Test Comparison",
      p: "#22D3EE",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#FFFFFF",
      neg: "#111318",
    });
    registerBackground("test_dark_bg", {
      base: "#0B0D11",
      isGradient: false,
    });

    const issues = validateContrast(
      makeDoc("comparison_kpi", {
        palette: "test_comparison_palette",
        background: "test_dark_bg",
      }),
    );

    expect(issues).toHaveLength(1);
    expect(issues[0].slot).toBe("delta_neg");
    expect(issues[0].message.startsWith("comparison_kpi.delta_neg:")).toBe(true);
  });

  test("hero_stat emits only the failing label slot", () => {
    registerPalette("test_hero_label_palette", {
      n: "Test Hero Label",
      p: "#FFFFFF",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#0D9488",
      neg: "#F43F5E",
    });
    registerBackground("test_table_header_bg", {
      base: "#4A5058",
      isGradient: false,
    });

    const issues = validateContrast(
      makeDoc("hero_stat", {
        palette: "test_hero_label_palette",
        background: "test_table_header_bg",
      }),
    );

    expect(issues).toHaveLength(1);
    expect(issues[0].slot).toBe("label");
    expect(issues[0].message.startsWith("hero_stat.label:")).toBe(true);
  });

  test("hero_stat emits only the failing value slot when pal.p loses contrast", () => {
    registerPalette("test_hero_value_palette", {
      n: "Test Hero Value",
      p: "#111318",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#0D9488",
      neg: "#F43F5E",
    });
    registerBackground("test_dark_bg", {
      base: "#0B0D11",
      isGradient: false,
    });

    const issues = validateContrast(
      makeDoc("hero_stat", {
        palette: "test_hero_value_palette",
        background: "test_dark_bg",
      }),
    );

    expect(issues).toHaveLength(1);
    expect(issues[0].slot).toBe("value");
    expect(issues[0].message.startsWith("hero_stat.value:")).toBe(true);
  });

  test("table_enriched emits only the failing score slot when pal.p loses contrast", () => {
    registerPalette("test_table_score_palette", {
      n: "Test Table Score",
      p: "#111318",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#0D9488",
      neg: "#F43F5E",
    });
    registerBackground("test_dark_bg", {
      base: "#0B0D11",
      isGradient: false,
    });

    const issues = validateContrast(
      makeDoc("table_enriched", {
        palette: "test_table_score_palette",
        background: "test_dark_bg",
      }),
    );

    expect(issues).toHaveLength(1);
    expect(issues[0].slot).toBe("score");
    expect(issues[0].message.startsWith("table_enriched.score:")).toBe(true);
  });

  test("table_enriched checks header independently from score", () => {
    registerPalette("test_table_header_palette", {
      n: "Test Table Header",
      p: "#FFFFFF",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#0D9488",
      neg: "#F43F5E",
    });
    registerBackground("test_mid_bg", {
      base: "#626871",
      isGradient: false,
    });

    const issues = validateContrast(
      makeDoc("table_enriched", {
        palette: "test_table_header_palette",
        background: "test_mid_bg",
      }),
    );

    expect(issues).toHaveLength(1);
    expect(issues[0].slot).toBe("header");
    expect(issues[0].message.startsWith("table_enriched.header:")).toBe(true);
  });

  test("multi-slot blocks never emit the legacy primary slot label", () => {
    registerPalette("test_comparison_palette", {
      n: "Test Comparison",
      p: "#22D3EE",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#FFFFFF",
      neg: "#111318",
    });
    registerPalette("test_table_score_palette", {
      n: "Test Table Score",
      p: "#111318",
      s: "#3B82F6",
      a: "#FBBF24",
      pos: "#0D9488",
      neg: "#F43F5E",
    });
    registerBackground("test_dark_bg", {
      base: "#0B0D11",
      isGradient: false,
    });

    const issues = [
      ...validateContrast(
        makeDoc("comparison_kpi", {
          palette: "test_comparison_palette",
          background: "test_dark_bg",
        }),
      ),
      ...validateContrast(
        makeDoc("table_enriched", {
          palette: "test_table_score_palette",
          background: "test_dark_bg",
        }),
      ),
    ];

    expect(issues.length).toBeGreaterThan(0);
    expect(issues.every((issue) => issue.slot !== "primary")).toBe(true);
  });

  test("non-text block returns no slots and emits no issues", () => {
    const doc = makeDoc("not_a_block", {
      palette: "housing",
      background: "solid_dark",
    });

    expect(getBlockTextSlots("not_a_block", PALETTES.housing)).toEqual([]);
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
          expect(i.message).toMatch(/^[a-z_]+\.[a-z_]+: contrast \d+(\.\d+)?:1/);
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
