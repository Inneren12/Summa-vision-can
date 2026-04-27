import type { SIZES } from './sizes';

/**
 * Canonical preset ID type — union of all keys in SIZES.
 *
 * After PR#2 BLOCKER-1 fix (SIZES uses `as const satisfies`), this resolves
 * to a true union type:
 *   "instagram_1080" | "instagram_portrait" | "twitter_landscape"
 *   | "reddit_standard" | "linkedin_landscape" | "instagram_story"
 *   | "long_infographic"
 *
 * Use this for any internal API surface that should accept ONLY known preset
 * IDs at compile time. Runtime data (loaded documents, JSON imports) may still
 * contain unknown strings — runtime guards (e.g. `if (!SIZES[id])`) remain
 * required for those paths.
 */
export type PresetId = keyof typeof SIZES;
