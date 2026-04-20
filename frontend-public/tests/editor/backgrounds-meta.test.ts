import { BGS, BG_META } from "../../src/components/editor/config/backgrounds";

describe("BG_META parity with BGS", () => {
  test("every BGS key has a BG_META entry", () => {
    const bgsKeys = Object.keys(BGS).sort();
    const metaKeys = Object.keys(BG_META).sort();
    expect(metaKeys).toEqual(bgsKeys);
  });

  test("every gradient entry has a lightestStop 6-digit hex", () => {
    for (const [, meta] of Object.entries(BG_META)) {
      if (meta.isGradient) {
        expect(meta.lightestStop).toBeDefined();
        expect(meta.lightestStop).toMatch(/^#[0-9A-Fa-f]{6}$/);
      }
    }
  });

  test("non-gradient entries omit lightestStop", () => {
    for (const [, meta] of Object.entries(BG_META)) {
      if (!meta.isGradient) {
        expect(meta.lightestStop).toBeUndefined();
      }
    }
  });

  test("every base is a 6-digit hex", () => {
    for (const [, meta] of Object.entries(BG_META)) {
      expect(meta.base).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });
});
