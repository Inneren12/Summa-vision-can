/**
 * Phase 3.1d Slice 4a — single-value walker.
 *
 * Pure function. Iterates `CanonicalDocument.blocks` and produces:
 * - `boundBlocks`: BoundBlockReference[] for the publish payload
 *   (single-kind bindings only, well-formed numeric filters).
 * - `deferred`: bindings whose kind is unsupported in v1 (multi-value
 *   types — Phase 3.1e). Block keeps its document binding intact;
 *   only the snapshot capture is skipped at publish.
 * - `skipped`: single-kind bindings whose filters fail Number(...) parsing.
 *   Operator-facing as warning per HALT-3; backend would return 422 if
 *   forwarded, so we drop client-side instead. Logs `console.warn` for dev
 *   visibility.
 *
 * Filter encoding (locked per Recon Delta 02 D-02):
 * - `binding.filters` shape is `Record<string, string>` with semantic
 *   content: stringified position_id keys + stringified member_id values.
 * - Walker emits numeric arrays paired positionally:
 *     keys.sort(localeCompare) → dims[i] = Number(key), members[i] = Number(value).
 * - Alphabetical key order matches Slice 2 canonicalFilters and Slice 3b
 *   fetchResolvedValue contract — end-to-end consistent.
 *
 * Block ordering: Object.entries(doc.blocks) yields insertion order in
 * V8/SpiderMonkey for string keys. Backend snapshot upsert is keyed by
 * (publication_id, block_id) so order is functionally irrelevant for
 * storage. Tests should not assert ordering.
 */
import type { CanonicalDocument } from '../types';
import type { BoundBlockReference } from '@/lib/types/compare';

export type DeferredReason =
  | 'time_series'
  | 'categorical_series'
  | 'multi_metric'
  | 'tabular';

export type SkippedReason = 'non_numeric_filters';

export interface DeferredBinding {
  block_id: string;
  kind: DeferredReason;
}

export interface SkippedBinding {
  block_id: string;
  reason: SkippedReason;
}

export interface WalkerResult {
  boundBlocks: BoundBlockReference[];
  deferred: DeferredBinding[];
  skipped: SkippedBinding[];
}

const UNSUPPORTED_KINDS: ReadonlySet<DeferredReason> = new Set<DeferredReason>([
  'time_series',
  'categorical_series',
  'multi_metric',
  'tabular',
]);

export function walkBoundBlocks(doc: CanonicalDocument): WalkerResult {
  const boundBlocks: BoundBlockReference[] = [];
  const deferred: DeferredBinding[] = [];
  const skipped: SkippedBinding[] = [];

  for (const [blockId, block] of Object.entries(doc.blocks)) {
    const binding = block.binding;
    if (!binding) continue;

    if (UNSUPPORTED_KINDS.has(binding.kind as DeferredReason)) {
      deferred.push({
        block_id: blockId,
        kind: binding.kind as DeferredReason,
      });
      continue;
    }

    if (binding.kind !== 'single') continue;

    const sortedKeys = Object.keys(binding.filters).sort((a, b) =>
      a.localeCompare(b),
    );
    const dims: number[] = [];
    const members: number[] = [];
    let malformed = false;

    for (const key of sortedKeys) {
      const dim = Number(key);
      const member = Number(binding.filters[key]);
      if (!Number.isFinite(dim) || !Number.isFinite(member)) {
        malformed = true;
        break;
      }
      dims.push(dim);
      members.push(member);
    }

    if (malformed) {
      skipped.push({ block_id: blockId, reason: 'non_numeric_filters' });
      console.warn(
        `[walkBoundBlocks] dropping block ${blockId} from publish payload: ` +
          `non-numeric filters (got ${JSON.stringify(binding.filters)})`,
      );
      continue;
    }

    boundBlocks.push({
      block_id: blockId,
      cube_id: binding.cube_id,
      semantic_key: binding.semantic_key,
      dims,
      members,
      period: binding.period ?? null,
    });
  }

  return { boundBlocks, deferred, skipped };
}
