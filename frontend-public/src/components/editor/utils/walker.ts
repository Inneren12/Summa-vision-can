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
 * - Walker emits numeric arrays paired positionally and sorted by numeric
 *   ascending dim (Slice 4a fix P1-3): dim/member tokens are parsed via
 *   parseIntegerFilterToken (strict integers only), then pairs are sorted
 *   by dim. dims[i] ↔ members[i] pairing is preserved.
 * - Block-type allowlist (Slice 4a fix P1-1): single bindings on block
 *   types other than hero_stat / delta_badge are skipped — v1 publish
 *   scope per milestone wrapper §HALT-3.
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

export type SkippedReason =
  | 'non_numeric_filters'
  | 'unsupported_block_type';

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

/**
 * Phase 3.1d Slice 4a fix (P1-1): block-type allowlist for v1 publish.
 * Milestone wrapper §HALT-3 locks supported types as `hero_stat` and
 * `delta_badge` only. Walker MUST skip any single-binding on other
 * block types (current or future) — backend snapshot capture is scoped
 * to these two in v1. Slice 4a/Slice 1a registry already declares
 * acceptsBinding=['single'] only on these two; the walker enforces the
 * same invariant at publish-payload boundary defensively.
 */
const SUPPORTED_SINGLE_BINDING_BLOCK_TYPES: ReadonlySet<string> = new Set<string>([
  'hero_stat',
  'delta_badge',
]);

/**
 * Phase 3.1d Slice 4a fix (P1-2): strict integer parser for filter
 * dim/member values.
 *
 * Backend `GET /api/v1/admin/resolve/...` and the publish payload
 * `dim: list[int]` / `member: list[int]` accept only integers.
 * `Number(...)` is too permissive: `Number('1.5')` → 1.5, `Number('')`
 * → 0, `Number(' ')` → 0, `Number('01')` → 1. We accept only:
 *   - "0"
 *   - any positive-integer string with no leading zero
 * No decimals, no whitespace, no signs, no scientific notation.
 * Returns null for invalid inputs so caller can route to skipped[].
 */
function parseIntegerFilterToken(value: string): number | null {
  if (!/^(0|[1-9]\d*)$/.test(value)) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

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

    // Phase 3.1d Slice 4a fix (P1-1): block-type allowlist enforcement.
    // V1 only ships hero_stat + delta_badge. Single bindings on other
    // block types are skipped from the publish payload (block keeps its
    // document binding intact; only snapshot capture is omitted).
    if (!SUPPORTED_SINGLE_BINDING_BLOCK_TYPES.has(block.type)) {
      skipped.push({ block_id: blockId, reason: 'unsupported_block_type' });
      continue;
    }

    // Phase 3.1d Slice 4a fix (P1-2): strict integer parsing.
    // parseIntegerFilterToken rejects floats, whitespace, empty strings,
    // leading-zero forms — backend `dim: list[int]` would otherwise get
    // wrong values silently or 422.
    //
    // Phase 3.1d Slice 4a fix (P1-3): numeric ascending order for the
    // canonical wire form. Pair-and-sort instead of key-then-pair so we
    // don't redo a string-based lexicographic ordering. Pairing remains
    // positional (backend dim[i] ↔ member[i]).
    type Pair = { dim: number; member: number };
    const pairs: Pair[] = [];
    let malformed = false;

    for (const [keyRaw, valueRaw] of Object.entries(binding.filters)) {
      const dim = parseIntegerFilterToken(keyRaw);
      const member = parseIntegerFilterToken(valueRaw);
      if (dim === null || member === null) {
        malformed = true;
        break;
      }
      pairs.push({ dim, member });
    }

    if (malformed) {
      skipped.push({ block_id: blockId, reason: 'non_numeric_filters' });
      console.warn(
        `[walkBoundBlocks] dropping block ${blockId} from publish payload: ` +
          `non-numeric filters (got ${JSON.stringify(binding.filters)})`,
      );
      continue;
    }

    pairs.sort((a, b) => a.dim - b.dim);
    const dims = pairs.map((p) => p.dim);
    const members = pairs.map((p) => p.member);

    boundBlocks.push({
      block_id: blockId,
      cube_id: binding.cube_id,
      semantic_key: binding.semantic_key,
      dims,
      members,
      // Phase 3.1d Slice 4a fix (Polish P2-1): Slice 2 validateBinding
      // guarantees `period: string` on a valid SingleValueBinding —
      // walker should not soften that invariant with `?? null`. If a
      // corrupted runtime state ever produces `period: undefined`,
      // backend Pydantic accepts `null` (BoundBlockReference.period:
      // str | None per recon §3.2), so the JSON-stringify of undefined
      // (which becomes nothing — field omitted entirely) is also
      // accepted. Either way, walker no longer adds defensive coercion.
      period: binding.period,
    });
  }

  return { boundBlocks, deferred, skipped };
}
