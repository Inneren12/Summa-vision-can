import type { CanonicalDocument, Palette } from '../types';
import { PALETTES } from '../config/palettes';
import { BG_META } from '../config/backgrounds';
import { TK } from '../config/tokens';

/**
 * Structured contrast issue. One per (block, text role) below threshold.
 * Consumed by:
 *   - validate.ts: stringified into ValidationResult.errors / .warnings
 *   - Inspector.tsx: filtered by selectedBlockId for per-block UI
 */
export interface ContrastIssue {
  blockId: string;
  blockType: string;
  /** Text role within the block (e.g. 'value', 'label', 'primary'). */
  slot: string;
  textColor: string;
  bgColor: string;
  bgPoint: 'base' | 'lightestStop';
  ratio: number;
  threshold: number;
  severity: 'error' | 'warning';
  message: string;
}

/** One text role rendered by a block, with the colour it actually uses. */
export interface BlockTextSlot {
  /** Semantic role within the block (e.g. 'value', 'label', 'delta_pos'). */
  slot: string;
  /** Hex colour the renderer paints for that slot (after theme resolution). */
  color: string;
  /** WCAG large-text threshold applies only when the rendered slot qualifies. */
  isLarge: boolean;
}

/** Block types that render text at all. Everything else is skipped. */
export const TEXT_BEARING_BLOCKS = new Set<string>([
  'eyebrow_tag',
  'headline_editorial',
  'subtitle_descriptor',
  'hero_stat',
  'delta_badge',
  'body_annotation',
  'source_footer',
  'brand_stamp',
  'bar_horizontal',
  'line_editorial',
  'comparison_kpi',
  'table_enriched',
  'small_multiple',
]);

/**
 * Map (blockType, slot) → text colour in the current palette.
 *
 * Duplicates the renderer's hardcoded token choices by design: if the
 * renderer changes, the validator must update in lockstep. A divergence
 * means the validator lies. Guarded by tests.
 */
export function getBlockTextSlots(
  blockType: string,
  pal: Palette,
): BlockTextSlot[] {
  switch (blockType) {
    case 'eyebrow_tag':
      return [{ slot: "primary", color: TK.c.txtM, isLarge: false }];
    case 'headline_editorial':
      return [{ slot: "primary", color: TK.c.txtP, isLarge: true }];
    case 'subtitle_descriptor':
      return [{ slot: "primary", color: TK.c.txtS, isLarge: false }];
    case 'hero_stat':
      return [
        { slot: 'value', color: pal.p, isLarge: true },
        { slot: 'label', color: TK.c.txtS, isLarge: false },
      ];
    case 'delta_badge':
      // Direction-dependent at render time; worst case for contrast
      // is pal.neg (red) on dark bg. Use it as the representative.
      return [{ slot: "primary", color: pal.neg, isLarge: false }];
    case 'body_annotation':
      return [{ slot: "primary", color: TK.c.txtS, isLarge: false }];
    case 'source_footer':
      return [{ slot: "primary", color: TK.c.txtM, isLarge: false }];
    case 'brand_stamp':
      return [{ slot: "primary", color: TK.c.acc, isLarge: false }];
    case 'bar_horizontal':
      return [
        { slot: 'label', color: TK.c.txtS, isLarge: false },
        { slot: 'value', color: TK.c.txtP, isLarge: false },
      ];
    case 'line_editorial':
      return [{ slot: "primary", color: pal.p, isLarge: false }];
    case 'comparison_kpi':
      return [
        { slot: 'value', color: TK.c.txtP, isLarge: true },
        { slot: 'delta_pos', color: pal.pos, isLarge: false },
        { slot: 'delta_neg', color: pal.neg, isLarge: false },
        { slot: 'label', color: TK.c.txtS, isLarge: false },
      ];
    case 'table_enriched':
      return [
        { slot: 'header', color: TK.c.txtS, isLarge: false },
        { slot: 'rank', color: pal.p, isLarge: false },
        { slot: 'cell', color: TK.c.txtP, isLarge: false },
        { slot: 'metric', color: TK.c.txtS, isLarge: false },
        { slot: 'score', color: TK.c.txtP, isLarge: false },
      ];
    case 'small_multiple':
      return [{ slot: "primary", color: TK.c.txtP, isLarge: false }];
    default:
      return [];
  }
}

// ---- WCAG 2.1 math ------------------------------------------------------

/** Parse #RRGGBB → {r, g, b} as 0-255 integers. Throws on malformed input. */
export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) throw new Error(`Invalid hex colour: ${hex}`);
  const n = parseInt(m[1], 16);
  return { r: (n >> 16) & 0xff, g: (n >> 8) & 0xff, b: n & 0xff };
}

function channelLinear(c255: number): number {
  const c = c255 / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** WCAG 2.1 relative luminance in [0, 1]. */
export function relativeLuminance(hex: string): number {
  const { r, g, b } = hexToRgb(hex);
  return (
    0.2126 * channelLinear(r) +
    0.7152 * channelLinear(g) +
    0.0722 * channelLinear(b)
  );
}

/** WCAG 2.1 contrast ratio. Always ≥ 1 (orders arguments internally). */
export function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  const [light, dark] = l1 >= l2 ? [l1, l2] : [l2, l1];
  return (light + 0.05) / (dark + 0.05);
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

// ---- Validator ----------------------------------------------------------

/**
 * Check every text-bearing block's text colour against the document's
 * background. Returns structured issues; string summaries are the
 * caller's responsibility (validate.ts assembles them).
 *
 * Gradient handling:
 *   - base fails            → error (unrecoverable; do not double-emit)
 *   - base passes, light fails → warning (gradient hazard)
 *   - both pass             → emit nothing
 */
export function validateContrast(doc: CanonicalDocument): ContrastIssue[] {
  const issues: ContrastIssue[] = [];

  const pal = PALETTES[doc.page.palette];
  const bgMeta = BG_META[doc.page.background];
  // Unknown palette/background ids are flagged by the outer validator;
  // skip contrast math so we don't throw on missing data.
  if (!pal || !bgMeta) return issues;

  for (const section of doc.sections) {
    for (const blockId of section.blockIds) {
      const block = doc.blocks[blockId];
      if (!block || !block.visible) continue;
      if (!TEXT_BEARING_BLOCKS.has(block.type)) continue;

      const textSlots = getBlockTextSlots(block.type, pal);

      for (const { slot, color, isLarge } of textSlots) {
        const threshold = isLarge ? 3.0 : 4.5;
        const baseRatio = contrastRatio(color, bgMeta.base);
        if (baseRatio < threshold) {
          const ratio = round2(baseRatio);
          issues.push({
            blockId,
            blockType: block.type,
            slot,
            textColor: color,
            bgColor: bgMeta.base,
            bgPoint: 'base',
            ratio,
            threshold,
            severity: 'error',
            message: `${block.type}.${slot}: contrast ${ratio.toFixed(2)}:1 below ${threshold}:1 on ${bgMeta.base}`,
          });
          continue;
        }

        if (bgMeta.isGradient && bgMeta.lightestStop) {
          const lightRatio = contrastRatio(color, bgMeta.lightestStop);
          if (lightRatio < threshold) {
            const ratio = round2(lightRatio);
            issues.push({
              blockId,
              blockType: block.type,
              slot,
              textColor: color,
              bgColor: bgMeta.lightestStop,
              bgPoint: 'lightestStop',
              ratio,
              threshold,
              severity: 'warning',
              message: `${block.type}.${slot}: contrast ${ratio.toFixed(2)}:1 below ${threshold}:1 on ${bgMeta.lightestStop}`,
            });
          }
        }
      }
    }
  }

  return issues;
}
