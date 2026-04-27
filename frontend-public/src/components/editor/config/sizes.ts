import type { SizePreset } from '../types';
import type { PresetId } from './presetIds';

/**
 * Phase 2.1 PR#2 fix1 (BLOCKER-1): use `as const satisfies` instead of an
 * explicit `Record<string, SizePreset>` annotation so the literal keys are
 * preserved. With the prior `Record<string, SizePreset>` type, every key
 * collapsed to `string` and `keyof typeof SIZES` resolved to `string` —
 * defeating the type-tightening goal of `ExportPresetId`.
 *
 * The `satisfies` clause still enforces that every value matches the
 * `SizePreset` shape; it just avoids widening the keys.
 */
export const SIZES = {
  instagram_1080:      { w: 1080, h: 1080, n: "IG 1:1" },
  instagram_portrait:  { w: 1080, h: 1350, n: "IG 4:5" },
  twitter_landscape:   { w: 1200, h: 675,  n: "Twitter/X" },
  reddit_standard:     { w: 1200, h: 900,  n: "Reddit" },
  linkedin_landscape:  { w: 1200, h: 627,  n: "LinkedIn" },
  instagram_story:     { w: 1080, h: 1920, n: "Story" },
  long_infographic:    { w: 1200, h: 4000, n: "Long Infographic" },
} as const satisfies Record<string, SizePreset>;

/**
 * Preset IDs currently exposed in the LEGACY editor size picker (single-PNG
 * export flow). NOT the same as the Inspector "Export presets" list — that
 * one shows ALL preset IDs from SIZES (including `long_infographic`), per
 * recon Q-2.1-9. Two distinct lists with different purposes.
 *
 * `long_infographic` is OMITTED here because the legacy single-PNG export
 * does not enforce the 4000px cap. Exposing it before PR#3 (ZIP orchestrator)
 * ships would let users export an oversize document silently.
 *
 * PR#3 expands this list to include `long_infographic` once the ZIP flow
 * catches `RenderCapExceededError` and surfaces a skipped-on-cap toast.
 */
export const EXPORTABLE_PRESET_IDS = [
  "instagram_1080",
  "instagram_portrait",
  "twitter_landscape",
  "reddit_standard",
  "linkedin_landscape",
  "instagram_story",
] as const;

export type ExportablePresetId = typeof EXPORTABLE_PRESET_IDS[number];

/**
 * Default `page.exportPresets` for new documents and for migration of
 * pre-v3 documents (Phase 2.1 PR#2). The "common-4" set covers the
 * highest-signal social channels per the operator distribution roadmap.
 *
 * Operators opt-in to `instagram_portrait`, `instagram_story`, and
 * `long_infographic` through the Inspector "Export presets" UI per recon
 * Q-2.1-8 / approval gate A2.
 *
 * PR#2 fix1 (P2.1): `as const satisfies readonly PresetId[]` preserves the
 * literal element types AND validates that every entry is a valid `PresetId`
 * at compile time. A typo here would now be a build-time error rather than
 * silently shipping garbage to the migration default.
 */
export const DEFAULT_EXPORT_PRESETS = [
  "instagram_1080",
  "twitter_landscape",
  "reddit_standard",
  "linkedin_landscape",
] as const satisfies readonly PresetId[];

/**
 * Normalizes the `page.exportPresets` list to enforce two invariants:
 *
 *   1. Every element is a known preset ID (filters out garbage from JSON
 *      imports, legacy beta data, or future-version documents).
 *   2. The current canvas size is always included — the operator cannot
 *      accidentally produce a ZIP that excludes the working canvas
 *      (BLOCKER-2 from PR#2 review: was UI-only, now reducer-enforced).
 *
 * Used in:
 *   - `UPDATE_PAGE_EXPORT_PRESETS` reducer action (Inspector toggle path)
 *   - `CHANGE_PAGE` reducer action when `key === "size"` (size-change path
 *     auto-includes the new size in exportPresets)
 *   - v2 → v3 migration step (after `page.size` rename + per-element
 *     legacy ID rename)
 *
 * The current size is only added when it's a known preset ID — a doc whose
 * `page.size` is corrupt (e.g. arrived via a partial migration) does not
 * get a phantom entry; it just yields an exportPresets list missing that
 * size, which downstream code already handles.
 */
export function normalizeExportPresets(
  presets: readonly string[] | undefined,
  currentSize: string,
): PresetId[] {
  const out = new Set<PresetId>();

  const source = presets ?? DEFAULT_EXPORT_PRESETS;
  for (const id of source) {
    if (typeof id === 'string' && id in SIZES) {
      out.add(id as PresetId);
    }
  }

  if (currentSize in SIZES) {
    out.add(currentSize as PresetId);
  }

  return [...out];
}
