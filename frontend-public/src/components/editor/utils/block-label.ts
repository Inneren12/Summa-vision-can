import { blockDisplayLabel } from '../store/comments';

type TranslatorFn = (key: string, params?: Record<string, unknown>) => string;

/**
 * Safely resolves a user-facing label for a block type.
 *
 * Resolution order:
 *  1. undefined/null blockType → generic fallback via tReview('comment.block_generic')
 *  2. tBlockType(`${blockType}.name`) if that key exists in the catalog (happy path)
 *  3. blockDisplayLabel(blockType) — EN from BREG — if key is missing but type is in registry
 *  4. Raw blockType string — last-resort for types not in BREG or catalog
 *
 * Step 3 is the "legacy/experimental blockType in old documents" case. Step 4 prevents
 * UI-level crashes when encountering completely unknown types.
 */
export function resolveBlockLabel(
  blockType: string | undefined | null,
  tBlockType: TranslatorFn,
  tReview: TranslatorFn,
): string {
  if (!blockType) {
    return tReview('comment.block_generic');
  }

  const key = `${blockType}.name`;
  const translated = tBlockType(key);

  // next-intl returns the raw key when a translation is missing (default behavior).
  // If the returned value equals the key, no translation exists.
  if (translated === key) {
    const fallback = blockDisplayLabel(blockType);
    // blockDisplayLabel returns BREG[type]?.name ?? blockType.
    // If type is not in BREG either, it returns the raw type string — better than nothing.
    return fallback;
  }

  return translated;
}
