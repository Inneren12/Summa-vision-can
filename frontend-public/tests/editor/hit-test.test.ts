import { hitTest, clientToLogical, type HitAreaEntry } from '../../src/components/editor/utils/hit-test';

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
