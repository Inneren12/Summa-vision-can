/**
 * Phase 3.1d — Compare/Publish/Binding shared types.
 *
 * Source of truth: docs/recon/phase-3-1d-frontend-recon-proper-part2.md §D.2
 * Backend schema: backend/src/schemas/staleness.py
 *
 * Backend reality:
 *   stale_status enum: 'fresh' | 'stale' | 'unknown' (no 'missing' literal)
 *   severity enum: 'info' | 'warning' | 'blocking'
 *   No top-level COMPARE_FAILED error code; partial encoded via per-block stale_reasons.
 *
 * Frontend CompareBadgeSeverity is a UI-only bucket mapped from backend payload.
 */

// ─── Backend-mirrored types ─────────────────────────────────────────────────

export type StaleStatus = 'fresh' | 'stale' | 'unknown';

export type StaleReason =
  | 'mapping_version_changed'
  | 'source_hash_changed'
  | 'value_changed'
  | 'missing_state_changed'
  | 'cache_row_stale'
  | 'compare_failed'
  | 'snapshot_missing';

export type Severity = 'info' | 'warning' | 'blocking';

export type CompareKind = 'drift_check' | 'snapshot_missing' | 'compare_failed';

export interface SnapshotFingerprint {
  mapping_version: number | null;
  source_hash: string;
  value: string | null;
  missing: boolean;
  is_stale: boolean;
  captured_at: string;
}

export interface ResolveFingerprint {
  mapping_version: number | null;
  source_hash: string;
  value: string | null;
  missing: boolean;
  is_stale: boolean;
  resolved_at: string;
}

export interface DriftCheckBasis {
  compare_kind: 'drift_check';
  matched_fields: string[];
  drift_fields: string[];
}

export interface SnapshotMissingBasis {
  compare_kind: 'snapshot_missing';
  cause: 'no_snapshot_row';
}

export interface CompareFailedBasis {
  compare_kind: 'compare_failed';
  resolve_error:
    | 'MAPPING_NOT_FOUND'
    | 'RESOLVE_CACHE_MISS'
    | 'RESOLVE_INVALID_FILTERS'
    | 'UNEXPECTED';
  details: {
    exception_type: string;
    message: string;
  };
}

export type CompareBasis = DriftCheckBasis | SnapshotMissingBasis | CompareFailedBasis;

export interface BlockComparatorResult {
  block_id: string;
  cube_id: string;
  semantic_key: string;
  stale_status: StaleStatus;
  stale_reasons: StaleReason[];
  severity: Severity;
  compared_at: string;
  snapshot: SnapshotFingerprint | null;
  current: ResolveFingerprint | null;
  compare_basis: CompareBasis;
}

export interface CompareResponse {
  publication_id: number;
  overall_status: StaleStatus;
  overall_severity: Severity;
  compared_at: string;
  block_results: BlockComparatorResult[];
}

// ─── Publish payload types ──────────────────────────────────────────────────

export interface BoundBlockReference {
  block_id: string;
  cube_id: string;
  semantic_key: string;
  dims: number[];
  members: number[];
  period?: string | null;
}

export interface PublishPayload {
  bound_blocks?: BoundBlockReference[];
}

// ─── Binding types (shape lock; consumers in later slices) ──────────────────

export interface SingleValueBinding {
  kind: 'single';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  /** Explicit backend-supported period, e.g. '2024-Q3'. Symbolic 'latest' out of scope per recon §J.4. */
  period: string;
  format?: string;
}

export interface TimeSeriesBinding {
  kind: 'time_series';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  period_range: { from: string; to: string } | { last_n: number };
  series_dim?: string;
  format?: string;
}

export interface CategoricalSeriesBinding {
  kind: 'categorical_series';
  cube_id: string;
  semantic_key: string;
  category_dim: string;
  filters: Record<string, string>;
  period: string;
  sort?: 'value_desc' | 'value_asc' | 'source_order';
  limit?: number;
}

export interface MultiMetricBinding {
  kind: 'multi_metric';
  cube_id: string;
  metrics: Array<{ semantic_key: string; label?: string }>;
  filters: Record<string, string>;
  period: string;
  format?: string;
}

export interface TabularBinding {
  kind: 'tabular';
  cube_id: string;
  columns: Array<{ semantic_key: string; label?: string }>;
  row_dim: string;
  filters: Record<string, string>;
  period: string;
  format?: string;
}

export type Binding =
  | SingleValueBinding
  | TimeSeriesBinding
  | CategoricalSeriesBinding
  | MultiMetricBinding
  | TabularBinding;

// ─── UI-only bucket type ────────────────────────────────────────────────────

/**
 * Frontend-only severity bucket for compare badge UI.
 * Mapped from backend payload via aggregate rule (recon Part 2 §E.4):
 *   1. Any block with stale_reasons containing 'compare_failed' → 'partial'
 *   2. Else any block with stale_reasons containing 'snapshot_missing' → 'missing'
 *   3. Else use overall_status ('fresh' | 'stale' | 'unknown')
 * Aggregate function lives in Slice 1b (useCompareState hook).
 */
export type CompareBadgeSeverity =
  | 'fresh'
  | 'stale'
  | 'missing'
  | 'unknown'
  | 'partial';
