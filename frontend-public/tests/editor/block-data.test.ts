import {
  validateBarHorizontalData,
  validateLineEditorialData,
  validateComparisonKpiData,
  validateTableEnrichedData,
  validateSmallMultipleData,
  validateBlockData,
} from "../../src/components/editor/validation/block-data";

describe("validateBarHorizontalData", () => {
  const ok = {
    items: [
      { label: "A", value: 1, flag: "", highlight: false },
      { label: "B", value: 2, flag: "", highlight: false },
    ],
    unit: "%",
  };

  test("accepts a well-formed payload", () => {
    expect(validateBarHorizontalData(ok).valid).toBe(true);
  });

  test("rejects non-array items", () => {
    const r = validateBarHorizontalData({ items: "x" });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch(/items must be an array/);
  });

  test("rejects empty items", () => {
    const r = validateBarHorizontalData({ items: [] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /at least one/i.test(e))).toBe(true);
  });

  test("rejects more than 30 items", () => {
    const items = Array.from({ length: 31 }, (_, i) => ({ label: `L${i}`, value: i, flag: "", highlight: false }));
    const r = validateBarHorizontalData({ items });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /too many items/i.test(e))).toBe(true);
  });

  test("rejects items with empty label", () => {
    const r = validateBarHorizontalData({ items: [{ label: "", value: 1, flag: "", highlight: false }] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /label/i.test(e))).toBe(true);
  });

  test("rejects non-finite values", () => {
    const r = validateBarHorizontalData({ items: [{ label: "A", value: NaN, flag: "", highlight: false }] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /finite/i.test(e))).toBe(true);
  });

  test("requires finite benchmarkValue when showBenchmark is true", () => {
    const r = validateBarHorizontalData({ ...ok, showBenchmark: true });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /benchmarkValue/.test(e))).toBe(true);
    expect(validateBarHorizontalData({ ...ok, showBenchmark: true, benchmarkValue: 5 }).valid).toBe(true);
  });
});

describe("validateLineEditorialData", () => {
  const ok = {
    series: [{ label: "A", role: "primary", data: [1, 2, 3] }],
    xLabels: ["2020", "2021", "2022"],
    yUnit: "%",
  };

  test("accepts a well-formed payload", () => {
    expect(validateLineEditorialData(ok).valid).toBe(true);
  });

  test("rejects non-array series", () => {
    const r = validateLineEditorialData({ series: "x", xLabels: [] });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch(/series must be an array/);
  });

  test("rejects non-array xLabels", () => {
    const r = validateLineEditorialData({ series: [], xLabels: "x" });
    expect(r.valid).toBe(false);
    expect(r.errors[0]).toMatch(/xLabels must be an array/);
  });

  test("rejects series.data length mismatch with xLabels", () => {
    const r = validateLineEditorialData({
      series: [{ label: "A", role: "primary", data: [1, 2] }],
      xLabels: ["2020", "2021", "2022"],
    });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /points but/.test(e))).toBe(true);
  });

  test("rejects invalid series role", () => {
    const r = validateLineEditorialData({
      series: [{ label: "A", role: "not_a_role", data: [1, 2, 3] }],
      xLabels: ["2020", "2021", "2022"],
    });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /role must be/.test(e))).toBe(true);
  });

  test("rejects non-finite data values", () => {
    const r = validateLineEditorialData({
      series: [{ label: "A", role: "primary", data: [1, Infinity, 3] }],
      xLabels: ["2020", "2021", "2022"],
    });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /non-finite/.test(e))).toBe(true);
  });
});

describe("validateComparisonKpiData", () => {
  const ok = {
    items: [
      { label: "A", value: "1", delta: "", direction: "positive" },
      { label: "B", value: "2", delta: "", direction: "neutral" },
    ],
  };

  test("accepts a well-formed payload", () => {
    expect(validateComparisonKpiData(ok).valid).toBe(true);
  });

  test("rejects fewer than 2 items", () => {
    const r = validateComparisonKpiData({ items: [ok.items[0]] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /at least 2/.test(e))).toBe(true);
  });

  test("rejects more than 4 items", () => {
    const items = Array.from({ length: 5 }, (_, i) => ({ label: `L${i}`, value: "1", delta: "", direction: "neutral" }));
    const r = validateComparisonKpiData({ items });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /too many/.test(e))).toBe(true);
  });

  test("rejects invalid direction", () => {
    const r = validateComparisonKpiData({
      items: [ok.items[0], { label: "B", value: "2", delta: "", direction: "up" }],
    });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /direction/.test(e))).toBe(true);
  });
});

describe("validateTableEnrichedData", () => {
  const ok = {
    columns: ["Country", "A", "B"],
    rows: [
      { country: "Canada", flag: "", vals: [1, 2], rank: 1 },
      { country: "U.S.", flag: "", vals: [3, 4], rank: 2 },
    ],
  };

  test("accepts a well-formed payload", () => {
    expect(validateTableEnrichedData(ok).valid).toBe(true);
  });

  test("rejects vals length mismatch with columns", () => {
    const r = validateTableEnrichedData({
      columns: ["Country", "A", "B", "C"],
      rows: [{ country: "Canada", flag: "", vals: [1], rank: 1 }],
    });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /vals but/.test(e))).toBe(true);
  });

  test("rejects fewer than 2 columns", () => {
    const r = validateTableEnrichedData({ columns: ["Country"], rows: [{ country: "Canada", flag: "", vals: [], rank: 1 }] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /columns/.test(e))).toBe(true);
  });

  test("rejects empty rows", () => {
    const r = validateTableEnrichedData({ columns: ["Country", "A"], rows: [] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /row required/.test(e))).toBe(true);
  });
});

describe("validateSmallMultipleData", () => {
  const ok = {
    items: [
      { label: "A", flag: "", data: [1, 2, 3] },
      { label: "B", flag: "", data: [4, 5, 6] },
    ],
    yUnit: "%",
  };

  test("accepts a well-formed payload", () => {
    expect(validateSmallMultipleData(ok).valid).toBe(true);
  });

  test("rejects empty items", () => {
    expect(validateSmallMultipleData({ items: [] }).valid).toBe(false);
  });

  test("rejects empty per-item data", () => {
    const r = validateSmallMultipleData({ items: [{ label: "A", flag: "", data: [] }] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /data is empty/.test(e))).toBe(true);
  });

  test("rejects non-finite per-item values", () => {
    const r = validateSmallMultipleData({ items: [{ label: "A", flag: "", data: [1, NaN] }] });
    expect(r.valid).toBe(false);
    expect(r.errors.some(e => /non-finite/.test(e))).toBe(true);
  });
});

describe("validateBlockData dispatcher", () => {
  test("dispatches to the correct per-type validator", () => {
    expect(validateBlockData("bar_horizontal", { items: [] }).valid).toBe(false);
    expect(validateBlockData("line_editorial", { series: [], xLabels: [] }).valid).toBe(false);
  });

  test("unknown types are treated as valid (registry handles unknown-type rejection)", () => {
    expect(validateBlockData("eyebrow_tag", {}).valid).toBe(true);
    expect(validateBlockData("not_a_real_block", {}).valid).toBe(true);
  });
});
