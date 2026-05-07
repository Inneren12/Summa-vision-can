/**
 * Phase 3.1d Slice 1b — Compare severity aggregation utilities.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §C.4
 *
 * Backend `stale_status` enum is `'fresh' | 'stale' | 'unknown'` only.
 * Frontend `CompareBadgeSeverity` extends with UI-only buckets `'missing'`
 * and `'partial'`. Aggregate precedence (recon Part 2 §E.4):
 *   1. Any block has stale_reasons including 'compare_failed' → 'partial'
 *   2. Else any block has stale_reasons including 'snapshot_missing' → 'missing'
 *   3. Else use overall_status ('fresh' | 'stale' | 'unknown')
 */

import type {
  BlockComparatorResult,
  CompareResponse,
  CompareBadgeSeverity,
  StaleReason,
} from '@/lib/types/compare';

export function aggregateCompareSeverity(
  result: CompareResponse,
): CompareBadgeSeverity {
  // Aggregate precedence (recon Part 2 §E.4 + Slice 1b recon §C.4):
  //   1. Any block has stale_reasons including 'compare_failed' → 'partial'
  //   2. Else any block has stale_reasons including 'snapshot_missing' → 'missing'
  //   3. Else fall through to backend overall_status ('fresh' | 'stale' | 'unknown')
  //
  // Empty block_results is a valid "editorial-only publication" state where
  // the backend returns its own overall_status (typically 'fresh') with no
  // bound blocks. The aggregate must defer to overall_status — it is NOT
  // hard-coded to 'unknown'.
  const blocks = result.block_results;

  if (blocks.some((b) => b.stale_reasons.includes('compare_failed'))) {
    return 'partial';
  }

  if (blocks.some((b) => b.stale_reasons.includes('snapshot_missing'))) {
    return 'missing';
  }

  return result.overall_status;
}

export function countReason(
  result: CompareResponse,
  reason: StaleReason,
): number {
  return result.block_results.filter((b) => b.stale_reasons.includes(reason))
    .length;
}

export interface CompareSummary {
  total: number;
  stale: number;
  missing: number;
  failed: number;
}

const STALE_REASONS: ReadonlyArray<StaleReason> = [
  'mapping_version_changed',
  'source_hash_changed',
  'value_changed',
  'missing_state_changed',
  'cache_row_stale',
];

/**
 * Phase 3.1d Slice 5 (PR-08): aggregate the union of stale reasons across
 * all block results into a deduplicated, stably-ordered list.
 *
 * Order: stable per StaleReason enum-declaration order (matches backend
 * recon §3 — same order as `lib/types/compare.ts` declares the union).
 * Empty array if no block has reasons (fresh publication).
 */
const REASON_ORDER: ReadonlyArray<StaleReason> = [
  'mapping_version_changed',
  'source_hash_changed',
  'value_changed',
  'missing_state_changed',
  'cache_row_stale',
  'compare_failed',
  'snapshot_missing',
];

export function aggregateReasons(
  blockResults: ReadonlyArray<BlockComparatorResult>,
): StaleReason[] {
  const seen = new Set<StaleReason>();
  for (const block of blockResults) {
    for (const reason of block.stale_reasons) {
      seen.add(reason);
    }
  }
  return REASON_ORDER.filter((r) => seen.has(r));
}

/**
 * Phase 3.1d Slice 5 (PR-08): detect whether the Pre-3.1d "Republish to
 * refresh" CTA should render. Founder lock 2026-05-07: any block result
 * carrying the `snapshot_missing` reason triggers the CTA. This single
 * condition covers true-pre-3.1d publications AND any future
 * DEBT-069 snapshot-cleanup case (recon §3.4 collapses all sub-causes
 * to the same SNAPSHOT_MISSING synthetic entry).
 */
export function shouldShowRepublishCta(
  blockResults: ReadonlyArray<BlockComparatorResult>,
): boolean {
  return blockResults.some((b) => b.stale_reasons.includes('snapshot_missing'));
}

export function summarizeCompare(result: CompareResponse): CompareSummary {
  // Block-level uniqueness: a single block with multiple stale reasons counts once.
  const staleBlocks = result.block_results.filter((b) =>
    b.stale_reasons.some((r) => STALE_REASONS.includes(r)),
  );

  return {
    total: result.block_results.length,
    stale: staleBlocks.length,
    missing: countReason(result, 'snapshot_missing'),
    failed: countReason(result, 'compare_failed'),
  };
}
