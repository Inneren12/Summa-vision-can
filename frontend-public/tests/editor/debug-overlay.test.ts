import {
  renderDebugOverlay,
  type DebugSectionEntry,
  type DebugBlockEntry,
} from '../../src/components/editor/renderer/debug-overlay';

function makeDebugCtx() {
  const calls: Array<{ method: string; args: unknown[] }> = [];
  const track = (method: string) =>
    jest.fn((...args: unknown[]) => {
      calls.push({ method, args });
    });

  const ctx = {
    setTransform: track('setTransform'),
    clearRect: track('clearRect'),
    save: track('save'),
    restore: track('restore'),
    setLineDash: track('setLineDash'),
    strokeRect: track('strokeRect'),
    fillRect: track('fillRect'),
    fillText: track('fillText'),
    measureText: jest.fn((text: string) => ({ width: text.length * 6 })),
    strokeStyle: '',
    fillStyle: '',
    font: '',
    lineWidth: 1,
    textBaseline: 'alphabetic' as CanvasTextBaseline,
    globalAlpha: 1,
  } as unknown as CanvasRenderingContext2D;

  return { ctx, calls };
}

const solidSection = (
  type: string,
  x: number,
  y: number,
  w: number,
  h: number,
): DebugSectionEntry => ({
  type,
  rect: { x, y, w, h },
});

const solidEntry = (
  blockId: string,
  overflow: boolean,
): DebugBlockEntry => {
  const raw = { x: 10, y: 10, w: overflow ? 200 : 80, h: overflow ? 200 : 40 };
  const sec = { x: 0, y: 0, w: 100, h: 100 };
  return {
    blockId,
    blockType: 'headline_editorial',
    rawHitArea: raw,
    clampedHitArea: {
      x: raw.x,
      y: raw.y,
      w: Math.min(raw.w, sec.w - (raw.x - sec.x)),
      h: Math.min(raw.h, sec.h - (raw.y - sec.y)),
    },
    sectionRect: sec,
    overflow,
  };
};

describe('renderDebugOverlay', () => {
  test('clears canvas and applies DPR transform', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 2,
      sections: [],
      entries: [],
    });
    const first = calls.slice(0, 3).map((c) => c.method);
    expect(first).toEqual(['setTransform', 'clearRect', 'setTransform']);
    expect(calls[1].args).toEqual([0, 0, 2160, 2160]);
    expect(calls[2].args).toEqual([2, 0, 0, 2, 0, 0]);
  });

  test('draws one fill + one stroke + one label per known section type', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 1,
      sections: [
        solidSection('header', 64, 64, 952, 130),
        solidSection('footer', 64, 970, 952, 40),
      ],
      entries: [],
    });
    const fillRects = calls.filter((c) => c.method === 'fillRect');
    const strokeRects = calls.filter((c) => c.method === 'strokeRect');
    // 2 section fills + 2 label background rects
    expect(fillRects.length).toBe(4);
    // 2 section stroke outlines
    expect(strokeRects.length).toBe(2);
  });

  test('unknown section type is skipped silently', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 1,
      sections: [solidSection('not_a_section', 0, 0, 100, 100)],
      entries: [],
    });
    expect(calls.filter((c) => c.method === 'strokeRect').length).toBe(0);
    expect(calls.filter((c) => c.method === 'fillRect').length).toBe(0);
  });

  test('non-overflow block draws one stroke (clamped) and one label', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 1,
      sections: [],
      entries: [solidEntry('b1', false)],
    });
    const strokeRects = calls.filter((c) => c.method === 'strokeRect');
    expect(strokeRects.length).toBe(1); // clamped only, no dashed overflow
    const setDashCalls = calls.filter((c) => c.method === 'setLineDash');
    // Every setLineDash call should be empty ([]) — no dashed outlines.
    expect(
      setDashCalls.every(
        (c) => Array.isArray(c.args[0]) && (c.args[0] as unknown[]).length === 0,
      ),
    ).toBe(true);
  });

  test('overflow block draws two strokes (clamped + dashed raw) and one label', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 1,
      sections: [],
      entries: [solidEntry('b1', true)],
    });
    const strokeRects = calls.filter((c) => c.method === 'strokeRect');
    expect(strokeRects.length).toBe(2); // clamped + raw

    const dashedCalls = calls.filter(
      (c) =>
        c.method === 'setLineDash' &&
        Array.isArray(c.args[0]) &&
        (c.args[0] as unknown[]).length > 0,
    );
    expect(dashedCalls.length).toBe(1); // one dashed setLineDash for the raw rect
  });

  test('label text contains blockType prefix and blockId slice', () => {
    const { ctx, calls } = makeDebugCtx();
    renderDebugOverlay({
      ctx,
      logicalW: 1080,
      logicalH: 1080,
      dpr: 1,
      sections: [],
      entries: [solidEntry('abcdef1234567890', false)],
    });
    const textCalls = calls.filter((c) => c.method === 'fillText');
    expect(textCalls.length).toBeGreaterThan(0);
    const text = textCalls[0].args[0] as string;
    expect(text).toContain('headline_editorial');
    expect(text).toContain('abcdef'); // first 6 chars of blockId
  });
});
