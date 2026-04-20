import {
  hitTest,
  clientToLogical,
  clampRectToSection,
  type HitAreaEntry,
} from '../../src/components/editor/utils/hit-test';

function rect(blockId: string, x: number, y: number, w: number, h: number): HitAreaEntry {
  return { blockId, hitArea: { x, y, w, h } };
}

describe('hitTest', () => {
  test('returns null on empty entries', () => {
    expect(hitTest([], 10, 10)).toBeNull();
  });

  test('returns block id when point is inside a rect', () => {
    const entries = [rect('a', 0, 0, 100, 100)];
    expect(hitTest(entries, 50, 50)).toBe('a');
  });

  test('returns null when point is outside all rects', () => {
    const entries = [rect('a', 0, 0, 100, 100)];
    expect(hitTest(entries, 200, 200)).toBeNull();
  });

  test('returns null when point is negative relative to rect', () => {
    const entries = [rect('a', 10, 10, 100, 100)];
    expect(hitTest(entries, 5, 5)).toBeNull();
  });

  test('point exactly on rect edge hits inclusively (top-left corner)', () => {
    const entries = [rect('a', 10, 20, 100, 100)];
    expect(hitTest(entries, 10, 20)).toBe('a');
  });

  test('point exactly on rect edge hits inclusively (bottom-right corner)', () => {
    const entries = [rect('a', 10, 20, 100, 100)];
    expect(hitTest(entries, 110, 120)).toBe('a');
  });

  test('point 1px outside right edge misses', () => {
    const entries = [rect('a', 10, 20, 100, 100)];
    expect(hitTest(entries, 111, 70)).toBeNull();
  });

  test('overlap: returns the last-drawn (topmost) block', () => {
    // 'a' drawn first, 'b' drawn second, both covering (50, 50).
    const entries = [
      rect('a', 0, 0, 100, 100),
      rect('b', 25, 25, 75, 75),
    ];
    expect(hitTest(entries, 50, 50)).toBe('b');
  });

  test('overlap: picks first rect when only first covers the point', () => {
    const entries = [
      rect('a', 0, 0, 100, 100),
      rect('b', 200, 200, 50, 50),
    ];
    expect(hitTest(entries, 10, 10)).toBe('a');
  });

  test('three-way overlap returns the last one', () => {
    const entries = [
      rect('a', 0, 0, 200, 200),
      rect('b', 10, 10, 180, 180),
      rect('c', 20, 20, 160, 160),
    ];
    expect(hitTest(entries, 100, 100)).toBe('c');
  });
});

describe('clientToLogical', () => {
  function stubCanvas(rectProps: Partial<DOMRect>): HTMLCanvasElement {
    const defaults = { left: 0, top: 0, right: 720, bottom: 720, width: 720, height: 720, x: 0, y: 0 };
    const merged = { ...defaults, ...rectProps };
    return {
      getBoundingClientRect: () => ({ ...merged, toJSON: () => merged }),
    } as unknown as HTMLCanvasElement;
  }

  test('720px display → 1080 logical: middle of rect maps to logical center', () => {
    const canvas = stubCanvas({ width: 720, height: 720, left: 0, top: 0 });
    expect(clientToLogical(canvas, 360, 360, 1080, 1080)).toEqual({ x: 540, y: 540 });
  });

  test('offset rect: subtracts rect.left / rect.top', () => {
    const canvas = stubCanvas({ width: 720, height: 720, left: 100, top: 50 });
    expect(clientToLogical(canvas, 460, 410, 1080, 1080)).toEqual({ x: 540, y: 540 });
  });

  test('asymmetric scale (portrait): width and height scale independently', () => {
    const canvas = stubCanvas({ width: 720, height: 900, left: 0, top: 0 });
    // logical 1080×1350 → scaleX=1.5, scaleY=1.5
    expect(clientToLogical(canvas, 100, 200, 1080, 1350)).toEqual({ x: 150, y: 300 });
  });

  test('zero-size rect returns {0, 0} rather than NaN', () => {
    const canvas = stubCanvas({ width: 0, height: 0, left: 0, top: 0 });
    expect(clientToLogical(canvas, 100, 100, 1080, 1080)).toEqual({ x: 0, y: 0 });
  });

  test('click at rect origin maps to logical (0, 0)', () => {
    const canvas = stubCanvas({ width: 720, height: 720, left: 10, top: 20 });
    expect(clientToLogical(canvas, 10, 20, 1080, 1080)).toEqual({ x: 0, y: 0 });
  });
});

describe('clampRectToSection', () => {
  const section = { x: 10, y: 20, w: 100, h: 50 };

  test('rect fully inside section → unchanged', () => {
    const rect = { x: 20, y: 30, w: 40, h: 20 };
    expect(clampRectToSection(rect, section)).toEqual(rect);
  });

  test('rect overflows bottom → clamped to section bottom', () => {
    const rect = { x: 20, y: 30, w: 40, h: 200 };
    expect(clampRectToSection(rect, section)).toEqual({ x: 20, y: 30, w: 40, h: 40 });
  });

  test('rect overflows right → clamped to section right', () => {
    const rect = { x: 20, y: 30, w: 200, h: 10 };
    expect(clampRectToSection(rect, section)).toEqual({ x: 20, y: 30, w: 90, h: 10 });
  });

  test('rect starts above section → top clamped, height reduced', () => {
    const rect = { x: 20, y: 0, w: 40, h: 40 };
    expect(clampRectToSection(rect, section)).toEqual({ x: 20, y: 20, w: 40, h: 20 });
  });

  test('rect fully outside section (below) → zero-area at origin', () => {
    const rect = { x: 20, y: 200, w: 40, h: 10 };
    const result = clampRectToSection(rect, section);
    expect(result.w).toBe(0);
    expect(result.h).toBe(0);
  });

  test('rect fully outside section (right) → zero-area at origin', () => {
    const rect = { x: 500, y: 30, w: 40, h: 10 };
    const result = clampRectToSection(rect, section);
    expect(result.w).toBe(0);
    expect(result.h).toBe(0);
  });

  test('hitTest with zero-area rect → never matches', () => {
    const entries = [{ blockId: 'a', hitArea: { x: 10, y: 20, w: 0, h: 0 } }];
    expect(hitTest(entries, 10, 20)).toBeNull();
    expect(hitTest(entries, 5, 5)).toBeNull();
  });

  test('two-block overlap scenario — clamping prevents adjacent-section steal', () => {
    // Simulate an overflowing hero block and an adjacent context block.
    // Without clamping, hero's hit area reaches into context's section.
    // With clamping, hero is confined to its section and context wins.
    const heroSection = { x: 0, y: 0, w: 1080, h: 400 };
    // contextSection (x:0, y:400, w:1080, h:400) is implicit — the context
    // block's raw hit rect is already within bounds so clamping is a no-op.

    const rawHero = { x: 100, y: 100, w: 800, h: 500 }; // overflows!
    const contextBlock = { x: 100, y: 450, w: 800, h: 100 };

    const clampedHero = clampRectToSection(rawHero, heroSection);
    expect(clampedHero.h).toBe(300); // clamped to section bottom

    // Build entries in draw order (hero first, context later = topmost).
    const entries = [
      { blockId: 'hero', hitArea: clampedHero },
      { blockId: 'context', hitArea: contextBlock },
    ];

    // Point at y=500 is in context's section, not hero's.
    // Without clamping, raw hero (y+h=600) would match and steal selection.
    expect(hitTest(entries, 500, 500)).toBe('context');
  });
});
