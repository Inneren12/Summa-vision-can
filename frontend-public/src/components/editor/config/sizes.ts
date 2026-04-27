import type { SizePreset } from '../types';

export const SIZES: Record<string, SizePreset> = {
  instagram_1080:      { w: 1080, h: 1080, n: "IG 1:1" },
  instagram_portrait:  { w: 1080, h: 1350, n: "IG 4:5" },
  twitter_landscape:   { w: 1200, h: 675,  n: "Twitter/X" },
  reddit_standard:     { w: 1200, h: 900,  n: "Reddit" },
  linkedin_landscape:  { w: 1200, h: 627,  n: "LinkedIn" },
  instagram_story:     { w: 1080, h: 1920, n: "Story" },
  long_infographic:    { w: 1200, h: 4000, n: "Long Infographic" },
};

/**
 * Preset IDs currently exposed to the UI export dropdown.
 *
 * `long_infographic` is intentionally OMITTED here even though it exists in
 * SIZES. The legacy single-PNG export flow does not enforce the 4000px cap;
 * exposing the preset in UI before PR#3 (ZIP orchestrator) ships would let
 * users export an oversize document silently.
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
 */
export const DEFAULT_EXPORT_PRESETS: readonly string[] = [
  "instagram_1080",
  "twitter_landscape",
  "reddit_standard",
  "linkedin_landscape",
] as const;
