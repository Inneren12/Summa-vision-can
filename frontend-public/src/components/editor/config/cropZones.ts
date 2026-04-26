import type { PlatformId } from '../types';
import { SIZES } from './sizes';

export interface CropZone {
  // Coordinates in base 1080-width units; renderer scales by canvas.w / 1080.
  x: number;
  y: number;
  w: number;
  h: number;
  platform: PlatformId;
}

export type PresetId = keyof typeof SIZES;

// Sparse map: only (preset, platform) pairs that make sense have entries.
// v1 collapses to single-overlay-per-preset; platform sub-map is retained to
// ease a future multi-overlay expansion without changing data shape.
//
// NOTE: these are working defaults. Exact platform crop dimensions are tracked
// as follow-up debt for live verification against current platform layouts.
export const CROP_ZONES: Partial<
  Record<PresetId, Partial<Record<PlatformId, CropZone>>>
> = {
  // Native preset cases — full canvas (label-only render in helper).
  reddit: {
    reddit: { x: 0, y: 0, w: 1200, h: 900, platform: 'reddit' },
  },
  twitter: {
    twitter: { x: 0, y: 0, w: 1200, h: 675, platform: 'twitter' },
  },
  linkedin: {
    linkedin: { x: 0, y: 0, w: 1200, h: 627, platform: 'linkedin' },
  },

  // Cross-post collapse: instagram presets default to Reddit crop overlay.
  instagram_1080: {
    reddit: { x: 0, y: 135, w: 1080, h: 810, platform: 'reddit' },
  },
  // 1080x1350 center-crop for 810px-tall Reddit aspect window.
  instagram_port: {
    reddit: { x: 0, y: 270, w: 1080, h: 810, platform: 'reddit' },
  },

  // story preset omitted (no overlay).
};

/**
 * Returns the crop zone (if any) configured for a given preset.
 * v1: single-overlay collapse (first configured platform entry).
 */
export function getCropZoneForPreset(presetId: string): CropZone | null {
  const platformsForPreset = CROP_ZONES[presetId as PresetId];
  if (!platformsForPreset) return null;

  const entries = Object.values(platformsForPreset).filter(
    (zone): zone is CropZone => zone !== undefined,
  );
  return entries[0] ?? null;
}
