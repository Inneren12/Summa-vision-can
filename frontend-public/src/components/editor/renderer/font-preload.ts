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
 * Sample text passed as the second argument to `document.fonts.load()`.
 *
 * Context: `FontFaceSet.load(font, text)` matches `text` against each
 * @font-face's `unicode-range` and resolves only the subset shards
 * containing at least one character from `text`. Without this argument,
 * the spec defaults `text` to a single space (U+0020), which matches
 * ONLY the basic-Latin shard. Late fetches for latin-ext / Vietnamese /
 * Greek / Cyrillic shards then re-open the exact late-subset gap this
 * module is meant to close.
 *
 * One character per subset shard next/font emits for Latin-family
 * Google fonts (audited against the compiled next/font CSS in Task 6
 * recon §7):
 *
 *   A   U+0041   basic Latin
 *   é   U+00E9   Latin-1 Supplement / latin-ext (French, Spanish, etc.)
 *   ř   U+0159   latin-ext-A (Czech, Slovak, Croatian)
 *   ắ   U+1EAF   Vietnamese
 *   α   U+03B1   Greek
 *   я   U+044F   Cyrillic
 *
 * Explicit non-goals: CJK, Arabic, Hebrew, Devanagari, emoji. These
 * are not shipped by next/font for these Latin-family families, and
 * Task 6's scope note excluded them ("acceptable for the Canadian
 * macro-data product scope; a future refresh adding broader
 * multilingual coverage would extend the subset declaration in
 * layout.tsx").
 */
const PRELOAD_SAMPLE_TEXT = 'Aéřắαя';

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
    // PRELOAD_SAMPLE_TEXT is the second argument: one character per
    // unicode-range subset shard, so the browser resolves every shard
    // (latin, latin-ext, Vietnamese, Greek, Cyrillic) instead of
    // defaulting to a single space and resolving only basic Latin.
    const shorthand = `${face.weight} 1em ${face.family}`;
    return document.fonts.load(shorthand, PRELOAD_SAMPLE_TEXT).catch((err) => {
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
