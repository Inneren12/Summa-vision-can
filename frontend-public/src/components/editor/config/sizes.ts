import type { SizePreset } from '../types';

export const SIZES: Record<string, SizePreset> = {
  instagram_1080: { w: 1080, h: 1080, n: "IG 1:1" },
  instagram_port: { w: 1080, h: 1350, n: "IG 4:5" },
  twitter:        { w: 1200, h: 675,  n: "Twitter/X" },
  reddit:         { w: 1200, h: 900,  n: "Reddit" },
  linkedin:       { w: 1200, h: 627,  n: "LinkedIn" },
  story:          { w: 1080, h: 1920, n: "Story" },
};
