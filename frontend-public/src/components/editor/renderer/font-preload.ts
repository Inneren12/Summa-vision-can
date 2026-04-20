/**
 * Canvas font preload registry (Stage 4 Task 6).
 *
 * Task 3's `document.fonts.ready` gate resolves when currently-requested
 * faces finish loading. With unicode-range subsets (next/font splits
 * Google families into multiple subset shards), a face is only
 * "requested" after a glyph from its range actually renders. Late-typed
 * non-ASCII characters trigger late subset fetches AFTER `fontsReady`
 * flipped true - exported PNGs silently use fallback fonts for those
 * glyphs.
 *
 * This module closes that gap by explicitly requesting every (family,
 * weight) the canvas renderer will draw, which forces the browser to
 * fetch all subset shards for those pairs up front. The preload runs
 * inside the existing mount-time timeout window in `index.tsx`.
 *
 * Lockstep with renderer: this list mirrors `ctx.font` usage in
 * `renderer/blocks.ts` and `renderer/debug-overlay.ts`. If the renderer
 * starts using a new (family, weight) combination, CANVAS_FONT_FACES
 * must be updated. A divergence means canvas may render glyphs in a
 * face that wasn't preloaded, re-opening the late-subset gap.
 */

import { TK } from '../config/tokens';

export interface CanvasFontFace {
  /** Font-family string exactly as passed to ctx.font. */
  family: string;
  weight: number;
}

/**
 * Every (family, weight) pair the canvas renderer uses. Audit of
 * renderer/blocks.ts and renderer/debug-overlay.ts as of Task 6:
 *
 *   display (Bricolage Grotesque): 400, 600, 700, 800
 *   body (DM Sans):                400, 500, 600
 *   data (JetBrains Mono):         400, 500, 600, 700
 *
 * If renderer changes, update here. Unit test pins this list.
 */
export const CANVAS_FONT_FACES: readonly CanvasFontFace[] = [
  { family: TK.font.display, weight: 400 },
  { family: TK.font.display, weight: 600 },
  { family: TK.font.display, weight: 700 },
  { family: TK.font.display, weight: 800 },
  { family: TK.font.body, weight: 400 },
  { family: TK.font.body, weight: 500 },
  { family: TK.font.body, weight: 600 },
  { family: TK.font.data, weight: 400 },
  { family: TK.font.data, weight: 500 },
  { family: TK.font.data, weight: 600 },
  { family: TK.font.data, weight: 700 },
] as const;

/**
 * Force the browser to fetch every CANVAS_FONT_FACES entry.
 *
 * Uses `document.fonts.load(fontShorthand)` which returns a promise
 * that resolves when all faces matching the shorthand have loaded
 * (including all unicode-range subset shards for the matched family).
 *
 * Never rejects. Individual face load failures are logged in dev but
 * do not fail the whole preload - the caller (mount effect) will still
 * flip fontsReady and let the browser fall back for missing faces.
 *
 * Returns a promise that resolves when all faces have completed
 * (successfully or otherwise). `document.fonts.ready` called after
 * this will immediately resolve because all requested faces are now
 * in loaded state.
 */
export async function preloadCanvasFonts(): Promise<void> {
  if (typeof document === 'undefined' || !document.fonts?.load) {
    return;
  }

  const loads = CANVAS_FONT_FACES.map((face) => {
    // "weight 1em family" - the 1em size is arbitrary; document.fonts.load
    // uses it only to identify the face, not to actually lay out anything.
    const shorthand = `${face.weight} 1em ${face.family}`;
    return document.fonts.load(shorthand).catch((err) => {
      if (process.env.NODE_ENV !== 'production') {
        console.warn(
          `[InfographicEditor] Failed to preload font (${shorthand}):`,
          err,
        );
      }
      return [];
    });
  });

  await Promise.all(loads);
}
