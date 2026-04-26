import type { CropZone } from '@/components/editor/config/cropZones';
import {
  drawCropZone,
  getScaledCropRect,
  isFullCanvasCropZone,
} from '@/components/editor/renderer/overlay';

function makeMockCtx() {
  return {
    save: jest.fn(),
    restore: jest.fn(),
    strokeRect: jest.fn(),
    fillRect: jest.fn(),
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    quadraticCurveTo: jest.fn(),
    closePath: jest.fn(),
    fill: jest.fn(),
    fillText: jest.fn(),
    measureText: jest.fn(() => ({ width: 48 } as TextMetrics)),
    set strokeStyle(_v: string) {},
    set lineWidth(_v: number) {},
    set fillStyle(_v: string) {},
    set font(_v: string) {},
    set textBaseline(_v: CanvasTextBaseline) {},
  } as unknown as CanvasRenderingContext2D;
}

describe('crop-zone overlay helpers', () => {
  test('scales coordinates correctly at 0.5 scale', () => {
    const zone: CropZone = { x: 100, y: 200, w: 400, h: 300, platform: 'twitter' };
    expect(getScaledCropRect(zone, 540)).toEqual({ x: 50, y: 100, w: 200, h: 150 });
  });

  test('detects full-canvas crop rect', () => {
    expect(isFullCanvasCropZone({ x: 0, y: 0, w: 1200, h: 900 }, 1200, 900)).toBe(true);
    expect(isFullCanvasCropZone({ x: 0, y: 1, w: 1080, h: 810 }, 1080, 1080)).toBe(false);
  });

  test('strokes rect when zone is partial', () => {
    const ctx = makeMockCtx();
    const zone: CropZone = { x: 0, y: 135, w: 1080, h: 810, platform: 'reddit' };
    drawCropZone(ctx, zone, 1080, 1080);
    expect(ctx.strokeRect).toHaveBeenCalledTimes(1);
  });

  test('skips stroke when zone equals full canvas and still draws label', () => {
    const ctx = makeMockCtx();
    const zone: CropZone = { x: 0, y: 0, w: 1080, h: 810, platform: 'reddit' };
    drawCropZone(ctx, zone, 1080, 810);
    expect(ctx.strokeRect).not.toHaveBeenCalled();
    expect(ctx.fillText).toHaveBeenCalledWith('Reddit', expect.any(Number), expect.any(Number));
  });
});
