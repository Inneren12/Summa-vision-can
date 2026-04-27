import type { CanonicalDocument, Palette } from '../types';
import { SIZES } from '../config/sizes';
import type { PresetId } from '../config/sizes';
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
 * - main-thread-only: must NOT be called from Web Worker context.
 * - rAF-bound: render pass + toBlob run inside `requestAnimationFrame` so that
 *   sequential per-preset rendering (PR#3 ZIP loop) yields between frames,
 *   keeping the editor UI responsive during multi-preset export.
 * - Caller must ensure `document.fonts.ready` has resolved before invoking.
 *   Helper does NOT re-check fonts. For sequential per-preset rendering,
 *   check fonts ONCE at loop entry to avoid the 5-second stall the B1 fix
 *   removed (`index.tsx:1218-1223`).
 * - Re-entrant: safe to invoke N times back-to-back in a single tick with
 *   different `presetId` values. Each invocation creates a fresh detached
 *   canvas; `renderDoc` reads no module-scope mutable state.
 *
 * For `long_infographic` preset:
 * - Variable height via `measureLayout` summation (Infinity sentinel).
 * - Hard cap (`LONG_INFOGRAPHIC_HEIGHT_CAP`) enforced before canvas allocation;
 *   throws `RenderCapExceededError` carrying the raw measured height.
 * - `Math.ceil` applied to the fractional measured height before assigning
 *   `canvas.height` (browsers coerce via ToUint32 which would truncate sub-px
 *   overflow and clip rendered content).
 *
 * @throws RenderCapExceededError if long_infographic measured height > cap.
 * @throws Error from canvas.toBlob if encoding fails.
 */
/**
 * Phase 2.1 PR#2 (Q-2.1-12 / approval gate A5): preset IDs are now stable
 * post-rename, so tighten the parameter to a literal union over `SIZES`.
 * The `if (!sz)` runtime guard below stays — `PresetId` is compile-time-only,
 * and a legacy doc that escaped migration could still arrive carrying an
 * unknown preset id at runtime.
 *
 * PR#2 fix2 (P1.2): the canonical `PresetId` type lives next to `SIZES` in
 * `config/sizes.ts` (was briefly in a dedicated `presetIds.ts` per fix1 —
 * that introduced a circular type import). `types.ts` (for `PageConfig`)
 * imports it via `import type` so no runtime dependency on `sizes.ts`
 * leaks. The original `ExportPresetId` name is kept as a re-export for
 * the existing call sites; under the hood it IS `PresetId`.
 */
export type ExportPresetId = PresetId;

export async function renderDocumentToBlob(
  doc: CanonicalDocument,
  pal: Palette,
  presetId: ExportPresetId,
): Promise<Blob> {
  const sz = SIZES[presetId];
  if (!sz) {
    throw new Error(`Unknown preset id: ${presetId}`);
  }

  // After the BLOCKER-1 fix tightened SIZES to a literal-key shape, `sz.h`
  // is a numeric literal union — without the explicit `number` annotation,
  // assigning `Math.ceil(measuredHeight)` below would fail to widen.
  let canvasH: number = sz.h;
  if (presetId === 'long_infographic') {
    const measuredHeight = computeLongInfographicHeight(doc, sz.w);
    if (measuredHeight > LONG_INFOGRAPHIC_HEIGHT_CAP) {
      // Report the raw measured height in the error so consumers can show
      // the actual overflow magnitude in UI ("exceeds by N px").
      throw new RenderCapExceededError(
        presetId,
        measuredHeight,
        LONG_INFOGRAPHIC_HEIGHT_CAP,
      );
    }
    // canvas.height must be integer — browsers coerce via ToUint32, which
    // truncates fractional values and would clip rendered content. Ceil to
    // include any sub-pixel overflow safely.
    canvasH = Math.ceil(measuredHeight);
  }

  const canvas = document.createElement('canvas');
  canvas.width = sz.w;
  canvas.height = canvasH;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas 2D context unavailable');
  }

  return new Promise<Blob>((resolve, reject) => {
    requestAnimationFrame(() => {
      try {
        const bgFn = BGS[doc.page.background] || BGS.solid_dark;
        bgFn.r(ctx, sz.w, canvasH, pal);
        renderDoc(ctx, doc, sz.w, canvasH, pal);

        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error(`toBlob returned null for preset ${presetId}`));
            return;
          }
          resolve(blob);
        }, 'image/png');
      } catch (err) {
        reject(err);
      }
    });
  });
}

// CONTRACT: This function's padding formula must stay in sync with
// renderer/engine.ts page padding (currently `pad = 64 * s` top + bottom)
// and the section stacking model (currently no inter-section gaps).
// If engine.ts changes either, update this function AND the regression test
// in renderToBlob.test.ts "padding contract" describe block.
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
 *
 * TODO PR#3: consumers should map error type + .presetId/.measuredHeight/.cap
 * fields to the i18n key `validation.long_infographic.height_cap_exceeded`,
 * NOT show error.message in UI (message is en-only debug text).
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
