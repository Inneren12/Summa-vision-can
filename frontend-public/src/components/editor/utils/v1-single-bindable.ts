/**
 * Phase 3.1d Slice 5 (PR-08 R2): the v1 set of block types that the
 * walker promotes to `boundBlocks` in the publish payload. Centralized
 * here so both `walker.ts` and `shouldShowRepublishCtaForDoc` stay in
 * lockstep — closes polish item P3-042 (allowlist duplication).
 *
 * Mirrored exactly: any addition here MUST also satisfy walker's
 * filtering criteria (HALT-3: only `kind === 'single'`).
 */
import type { CanonicalDocument } from '../types';

export const V1_SINGLE_BINDABLE_TYPES: ReadonlySet<string> = new Set<string>([
  'hero_stat',
  'delta_badge',
]);

/**
 * Pure predicate: does the document contain at least one block whose type
 * is in the v1 single-bindable allowlist AND whose binding is structurally
 * a single-kind binding?
 *
 * "Structurally complete" here is intentionally lighter than the walker's
 * full validation — we surface the CTA whenever the operator has *any*
 * publishable single binding; the walker decides what actually ships at
 * publish time.
 *
 * MUST NOT call the walker (no console.warn side-effects, no skipped /
 * deferred tracking — this runs on every editor render).
 */
export function hasV1SinglePublishableBindings(
  doc: CanonicalDocument,
): boolean {
  for (const blockId in doc.blocks) {
    const block = doc.blocks[blockId];
    if (!V1_SINGLE_BINDABLE_TYPES.has(block.type)) continue;
    if (block.binding?.kind === 'single') return true;
  }
  return false;
}

/**
 * Returns the list of block IDs eligible for publish (single-kind binding
 * on a v1 allowlisted block type). Used by `shouldShowRepublishCtaForDoc`
 * to correlate per-block snapshot status against operator intent.
 */
export function collectV1SingleBindableBlockIds(
  doc: CanonicalDocument,
): string[] {
  const ids: string[] = [];
  for (const blockId in doc.blocks) {
    const block = doc.blocks[blockId];
    if (!V1_SINGLE_BINDABLE_TYPES.has(block.type)) continue;
    if (block.binding?.kind === 'single') ids.push(blockId);
  }
  return ids;
}
