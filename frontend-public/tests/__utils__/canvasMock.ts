/**
 * Shared jsdom canvas-mock helpers.
 *
 * jsdom's HTMLCanvasElement.getContext returns null and HTMLCanvasElement.toBlob
 * is unimplemented, so any test that drives the editor renderer or the export
 * blob path must override both. Reuse across:
 *   - tests/components/editor/export/renderToBlob.test.ts
 *   - tests/components/editor/export/renderToBlob.integration.test.tsx
 *   - tests/components/editor/context-menu-integration.test.tsx (future migration)
 *   - tests/editor/renderer-contract.test.ts (`makeCtx()` was the original
 *     in-file copy)
 *
 * Keep field names and the no-op behaviour aligned with renderer-contract's
 * original `makeCtx()` to avoid contract drift.
 */

export interface MockCtx {
  font: string;
  fillStyle: string | CanvasGradient | CanvasPattern;
  strokeStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
  textAlign: string;
  globalAlpha: number;
  setLineDash: jest.Mock;
  beginPath: jest.Mock;
  moveTo: jest.Mock;
  lineTo: jest.Mock;
  stroke: jest.Mock;
  fill: jest.Mock;
  fillRect: jest.Mock;
  roundRect: jest.Mock;
  fillText: jest.Mock;
  strokeRect: jest.Mock;
  rect: jest.Mock;
  clip: jest.Mock;
  save: jest.Mock;
  restore: jest.Mock;
  closePath: jest.Mock;
  arc: jest.Mock;
  ellipse: jest.Mock;
  measureText: jest.Mock;
  createLinearGradient: jest.Mock;
  createRadialGradient: jest.Mock;
  createPattern: jest.Mock;
}

export function makeCtx(): MockCtx {
  const gradient = { addColorStop: jest.fn() };
  return {
    font: '',
    fillStyle: '',
    strokeStyle: '',
    lineWidth: 1,
    textAlign: 'left',
    globalAlpha: 1,
    setLineDash: jest.fn(),
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(),
    fill: jest.fn(),
    fillRect: jest.fn(),
    roundRect: jest.fn(),
    fillText: jest.fn(),
    strokeRect: jest.fn(),
    rect: jest.fn(),
    clip: jest.fn(),
    save: jest.fn(),
    restore: jest.fn(),
    closePath: jest.fn(),
    arc: jest.fn(),
    ellipse: jest.fn(),
    measureText: jest.fn((text: string) => ({ width: (text || '').length * 7 })),
    createLinearGradient: jest.fn(() => gradient),
    createRadialGradient: jest.fn(() => gradient),
    createPattern: jest.fn(() => null),
  };
}

interface InstallOptions {
  /**
   * Custom byte sequence for the synthesised PNG blob. Defaults to a fixed
   * non-empty buffer so size assertions are stable across runs.
   */
  toBlobBytes?: Uint8Array;
  /**
   * If set, simulates a `toBlob` failure by passing `null` to the callback.
   * Used by the rejection-path test.
   */
  forceToBlobNull?: boolean;
}

/**
 * Install canvas mocks on HTMLCanvasElement.prototype. Returns a teardown
 * function to restore the originals; tests should call it in afterEach to
 * keep environments isolated.
 *
 * The mock returns a fresh `MockCtx` per `getContext('2d')` call, mirroring
 * the real browser behaviour where each canvas has its own context.
 */
export function installCanvasMocks(options: InstallOptions = {}): () => void {
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  const originalToBlob = HTMLCanvasElement.prototype.toBlob;

  const ctxByCanvas = new WeakMap<HTMLCanvasElement, MockCtx>();

  HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string) {
    if (kind !== '2d') return null;
    let ctx = ctxByCanvas.get(this);
    if (!ctx) {
      ctx = makeCtx();
      ctxByCanvas.set(this, ctx);
    }
    return ctx as unknown as CanvasRenderingContext2D;
  } as typeof HTMLCanvasElement.prototype.getContext;

  HTMLCanvasElement.prototype.toBlob = function (
    this: HTMLCanvasElement,
    callback: BlobCallback,
    type?: string,
  ) {
    if (options.forceToBlobNull) {
      callback(null);
      return;
    }
    const bytes = options.toBlobBytes ?? new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    const blob = new Blob([bytes], { type: type ?? 'image/png' });
    callback(blob);
  };

  return () => {
    HTMLCanvasElement.prototype.getContext = originalGetContext;
    HTMLCanvasElement.prototype.toBlob = originalToBlob;
  };
}
