import type { CanonicalDocument, Palette } from '../types';
import { SIZES } from '../config/sizes';
import { BGS } from '../config/backgrounds';
import { renderDoc } from '../renderer/engine';
import { measureLayout } from '../renderer/measure';

/**
 * Hard cap (in CSS px) on the rendered height of `long_infographic`. Exceeding
 * this throws `RenderCapExceededError`; orchestrator (PR#3) catches and marks
 * the preset `qa_status: "skipped"` while continuing with other presets.
 */
export const LONG_INFOGRAPHIC_HEIGHT_CAP = 4000;

/**
 * Pure async helper that renders a document to a PNG blob for a single preset.
 *
 * Constraints:
 * - main-thread-only, rAF-bound. Must NOT be called from a Web Worker.
 * - Caller must ensure `document.fonts.ready` has resolved before invoking.
 *   The helper does NOT re-check fonts. For sequential per-preset rendering,
 *   check fonts ONCE at loop entry to avoid the 5-second stall the B1 fix
 *   removed (`index.tsx:1218-1223`).
 * - Re-entrant: safe to invoke N times back-to-back in a single tick with
 *   different `presetId` values. Each invocation creates a fresh detached
 *   canvas; `renderDoc` reads no module-scope mutable state.
 *
 * For the `long_infographic` preset the canvas height is computed from
 * `measureLayout` summation; if the measured height exceeds
 * `LONG_INFOGRAPHIC_HEIGHT_CAP` the helper throws `RenderCapExceededError`
 * before allocating the canvas (no render pass burned).
 */
export async function renderDocumentToBlob(
  doc: CanonicalDocument,
  pal: Palette,
  presetId: string,
): Promise<Blob> {
  const sz = SIZES[presetId];
  if (!sz) {
    throw new Error(`Unknown preset id: ${presetId}`);
  }

  let canvasH = sz.h;
  if (presetId === 'long_infographic') {
    canvasH = computeLongInfographicHeight(doc, sz.w);
    if (canvasH > LONG_INFOGRAPHIC_HEIGHT_CAP) {
      throw new RenderCapExceededError(presetId, canvasH, LONG_INFOGRAPHIC_HEIGHT_CAP);
    }
  }

  const canvas = document.createElement('canvas');
  canvas.width = sz.w;
  canvas.height = canvasH;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas 2D context unavailable');
  }

  const bgFn = BGS[doc.page.background] || BGS.solid_dark;
  bgFn.r(ctx, sz.w, canvasH, pal);
  renderDoc(ctx, doc, sz.w, canvasH, pal);

  return new Promise<Blob>((resolve, reject) => {
    requestAnimationFrame(() => {
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error(`toBlob returned null for preset ${presetId}`));
          return;
        }
        resolve(blob);
      }, 'image/png');
    });
  });
}

/**
 * Compute intrinsic height for the `long_infographic` preset by summing
 * `measureLayout` consumed heights with `size.h = Infinity` and adding the
 * top + bottom page padding from `engine.ts` (`pad = 64 * s`, applied at top
 * and bottom of the page).
 *
 * Pure: no DOM, no clock reads, no I/O. Same `(doc, width)` always returns
 * the same height.
 */
export function computeLongInfographicHeight(
  doc: CanonicalDocument,
  width: number,
): number {
  const measurements = measureLayout(doc, { w: width, h: Infinity, n: 'long_infographic' });
  const sectionsHeight = measurements.reduce((acc, m) => acc + m.consumedHeight, 0);
  const s = width / 1080;
  const padding = 2 * 64 * s;
  return sectionsHeight + padding;
}

/**
 * Thrown by `renderDocumentToBlob` when the measured intrinsic height of
 * `long_infographic` exceeds `LONG_INFOGRAPHIC_HEIGHT_CAP`. The orchestrator
 * (PR#3 ZIP export) catches this and marks the preset `qa_status: "skipped"`
 * in the manifest while continuing to render the other enabled presets.
 */
export class RenderCapExceededError extends Error {
  constructor(
    public presetId: string,
    public measuredHeight: number,
    public cap: number,
  ) {
    super(`Preset ${presetId} exceeds height cap: ${measuredHeight}px > ${cap}px`);
    this.name = 'RenderCapExceededError';
  }
}
