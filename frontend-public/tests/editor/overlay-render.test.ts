import { renderOverlay } from '../../src/components/editor/renderer/overlay';
import type { HitAreaEntry } from '../../src/components/editor/utils/hit-test';
import { TK } from '../../src/components/editor/config/tokens';

function makeCtx() {
  return {
    setTransform: jest.fn(),
    clearRect: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    setLineDash: jest.fn(),
    strokeRect: jest.fn(),
    strokeStyle: '',
    lineWidth: 1,
  } as unknown as CanvasRenderingContext2D & {
    setTransform: jest.Mock;
    clearRect: jest.Mock;
    save: jest.Mock;
    restore: jest.Mock;
    setLineDash: jest.Mock;
    strokeRect: jest.Mock;
  };
}

const areas: HitAreaEntry[] = [
  { blockId: 'a', hitArea: { x: 10, y: 20, w: 100, h: 50 } },
  { blockId: 'b', hitArea: { x: 200, y: 200, w: 100, h: 50 } },
];

describe('renderOverlay', () => {
  test('clears the backing store on every invocation', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: null, hoveredBlockId: null, dpr: 2 });
    expect(ctx.clearRect).toHaveBeenCalledTimes(1);
    expect(ctx.clearRect).toHaveBeenCalledWith(0, 0, 2160, 2160);
  });

  test('no selection + no hover → no strokes', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: null, hoveredBlockId: null, dpr: 1 });
    expect(ctx.strokeRect).not.toHaveBeenCalled();
  });

  test('selection only → one stroke with TK.c.acc', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: 'a', hoveredBlockId: null, dpr: 1 });
    expect(ctx.strokeRect).toHaveBeenCalledTimes(1);
    expect(ctx.strokeStyle).toBe(TK.c.acc);
  });

  test('hover only (different block) → one stroke with TK.c.txtS', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: null, hoveredBlockId: 'b', dpr: 1 });
    expect(ctx.strokeRect).toHaveBeenCalledTimes(1);
    expect(ctx.strokeStyle).toBe(TK.c.txtS);
  });

  test('hover on same block as selection → selection wins, hover skipped', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: 'a', hoveredBlockId: 'a', dpr: 1 });
    expect(ctx.strokeRect).toHaveBeenCalledTimes(1);
    expect(ctx.strokeStyle).toBe(TK.c.acc);
  });

  test('hover + selection on different blocks → two strokes', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: 'a', hoveredBlockId: 'b', dpr: 1 });
    expect(ctx.strokeRect).toHaveBeenCalledTimes(2);
  });

  test('unknown selected/hovered id → no stroke', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: 'missing', hoveredBlockId: 'also-missing', dpr: 1 });
    expect(ctx.strokeRect).not.toHaveBeenCalled();
  });

  test('applies dpr transform after clear', () => {
    const ctx = makeCtx();
    renderOverlay({ ctx, logicalW: 1080, logicalH: 1080, hitAreas: areas, selectedBlockId: null, hoveredBlockId: null, dpr: 2 });
    // First setTransform resets (1,0,0,1), second applies dpr
    expect(ctx.setTransform).toHaveBeenNthCalledWith(1, 1, 0, 0, 1, 0, 0);
    expect(ctx.setTransform).toHaveBeenNthCalledWith(2, 2, 0, 0, 2, 0, 0);
  });
});
