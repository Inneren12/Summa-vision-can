/**
 * Editor-domain binding types for Phase 3.1d.
 *
 * Moved from `lib/types/compare.ts` per polish task P3-033 (Slice 2 of Phase
 * 3.1d). `Binding` is editor-domain (consumed by Inspector, ResolvePreview,
 * walker); `BoundBlockReference` remains in `lib/types/compare.ts` because it
 * is the wire/API shape sent to the backend at publish time.
 *
 * Slice 2 schema accepts ALL 5 kinds on ANY block (universal validation).
 * Per-block-type fit is registry-level metadata for the Slice 3a binding
 * picker UI, not a schema concern.
 */

export interface SingleValueBinding {
  kind: 'single';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  /** Explicit backend-supported period, e.g. '2024-Q3'. Symbolic 'latest' out of scope. */
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

/**
 * Phase 3.1d Slice 3a: per-block-type binding-fit hints (Slice 2 recon
 * §H.future.1 Option A — registry entry has `acceptsBinding?: BindingKind[]`).
 */
export type BindingKind = Binding['kind'];

/**
 * Validate an unknown value as a `Binding`.
 *
 * Behavior:
 * - Returns `null` for any malformed input (missing/wrong-type fields, empty
 *   strings, non-positive integers, mutex violations, empty arrays, empty
 *   filter keys, unknown discriminator, etc.).
 * - On valid input, returns a **canonically reconstructed** object containing
 *   only the schema's known fields. Unknown extra keys on the input are
 *   stripped. This is intentional — the function does NOT cast input directly.
 * - Forward-compatibility: unknown `kind` discriminators (future Phase 3.1f
 *   kinds) coerce to `null` ⇒ frontend treats the block as having no binding
 *   (graceful degradation; locked decision #4 universal validation).
 *
 * Used by:
 * - `hydrateImportedDoc` in `registry/guards.ts` (import/load path)
 * - Future Slice 3a binding editor (UI construction-time validation)
 * - Future Slice 4a publish walker (single-value adapter)
 */
export function validateBinding(value: unknown): Binding | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;

  const isStr = (x: unknown): x is string => typeof x === 'string';
  const isNonEmptyStr = (x: unknown): x is string =>
    typeof x === 'string' && x.trim().length > 0;
  const isOptStr = (x: unknown): boolean => x === undefined || isStr(x);
  const isOptNonEmptyStr = (x: unknown): boolean =>
    x === undefined || isNonEmptyStr(x);
  const isFilters = (x: unknown): x is Record<string, string> =>
    !!x &&
    typeof x === 'object' &&
    !Array.isArray(x) &&
    Object.entries(x as Record<string, unknown>).every(
      ([k, val]) => isNonEmptyStr(k) && isNonEmptyStr(val),
    );
  const isPositiveInt = (x: unknown): x is number =>
    typeof x === 'number' && Number.isInteger(x) && x > 0;
  /**
   * Canonical filters reconstruction:
   * - breaks aliasing with input (callers may mutate input freely)
   * - sorts keys for deterministic ordering (stable JSON.stringify; aligns
   *   with future Slice 4 deterministic dims/members emission)
   */
  const canonicalFilters = (x: Record<string, string>): Record<string, string> =>
    Object.fromEntries(
      Object.entries(x).sort(([a], [b]) => a.localeCompare(b)),
    );

  switch (v.kind) {
    case 'single': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isFilters(v.filters)) return null;
      if (!isNonEmptyStr(v.period)) return null;
      if (!isOptStr(v.format)) return null;
      return {
        kind: 'single',
        cube_id: v.cube_id as string,
        semantic_key: v.semantic_key as string,
        filters: canonicalFilters(v.filters as Record<string, string>),
        period: v.period as string,
        ...(v.format !== undefined ? { format: v.format as string } : {}),
      };
    }
    case 'time_series': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isFilters(v.filters)) return null;
      const pr = v.period_range as Record<string, unknown> | undefined;
      if (!pr || typeof pr !== 'object' || Array.isArray(pr)) return null;
      const hasFromTo =
        isNonEmptyStr(pr.from) && isNonEmptyStr(pr.to) && pr.last_n === undefined;
      const hasLastN =
        isPositiveInt(pr.last_n) && pr.from === undefined && pr.to === undefined;
      if (!(hasFromTo || hasLastN)) return null;
      if (!isOptNonEmptyStr(v.series_dim) || !isOptStr(v.format)) return null;
      return {
        kind: 'time_series',
        cube_id: v.cube_id as string,
        semantic_key: v.semantic_key as string,
        filters: canonicalFilters(v.filters as Record<string, string>),
        period_range:
          pr.last_n !== undefined
            ? { last_n: pr.last_n as number }
            : { from: pr.from as string, to: pr.to as string },
        ...(v.series_dim !== undefined ? { series_dim: v.series_dim as string } : {}),
        ...(v.format !== undefined ? { format: v.format as string } : {}),
      };
    }
    case 'categorical_series': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isNonEmptyStr(v.category_dim) || !isNonEmptyStr(v.period)) return null;
      if (!isFilters(v.filters)) return null;
      if (
        v.sort !== undefined &&
        !['value_desc', 'value_asc', 'source_order'].includes(v.sort as string)
      )
        return null;
      if (v.limit !== undefined && !isPositiveInt(v.limit)) return null;
      return {
        kind: 'categorical_series',
        cube_id: v.cube_id as string,
        semantic_key: v.semantic_key as string,
        category_dim: v.category_dim as string,
        filters: canonicalFilters(v.filters as Record<string, string>),
        period: v.period as string,
        ...(v.sort !== undefined
          ? { sort: v.sort as 'value_desc' | 'value_asc' | 'source_order' }
          : {}),
        ...(v.limit !== undefined ? { limit: v.limit as number } : {}),
      };
    }
    case 'multi_metric': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.period)) return null;
      if (!isFilters(v.filters)) return null;
      if (
        !Array.isArray(v.metrics) ||
        v.metrics.length === 0 ||
        !v.metrics.every(
          (m: unknown) =>
            !!m &&
            typeof m === 'object' &&
            isNonEmptyStr((m as Record<string, unknown>).semantic_key) &&
            isOptStr((m as Record<string, unknown>).label),
        )
      )
        return null;
      if (!isOptStr(v.format)) return null;
      return {
        kind: 'multi_metric',
        cube_id: v.cube_id as string,
        metrics: (v.metrics as Array<Record<string, unknown>>).map((m) => ({
          semantic_key: m.semantic_key as string,
          ...(m.label !== undefined ? { label: m.label as string } : {}),
        })),
        filters: canonicalFilters(v.filters as Record<string, string>),
        period: v.period as string,
        ...(v.format !== undefined ? { format: v.format as string } : {}),
      };
    }
    case 'tabular': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.row_dim) || !isNonEmptyStr(v.period))
        return null;
      if (!isFilters(v.filters)) return null;
      if (
        !Array.isArray(v.columns) ||
        v.columns.length === 0 ||
        !v.columns.every(
          (c: unknown) =>
            !!c &&
            typeof c === 'object' &&
            isNonEmptyStr((c as Record<string, unknown>).semantic_key) &&
            isOptStr((c as Record<string, unknown>).label),
        )
      )
        return null;
      if (!isOptStr(v.format)) return null;
      return {
        kind: 'tabular',
        cube_id: v.cube_id as string,
        columns: (v.columns as Array<Record<string, unknown>>).map((c) => ({
          semantic_key: c.semantic_key as string,
          ...(c.label !== undefined ? { label: c.label as string } : {}),
        })),
        row_dim: v.row_dim as string,
        filters: canonicalFilters(v.filters as Record<string, string>),
        period: v.period as string,
        ...(v.format !== undefined ? { format: v.format as string } : {}),
      };
    }
    default:
      return null;
  }
}
