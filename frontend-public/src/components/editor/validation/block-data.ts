import type { Direction } from '../types';
import { SERIES_ROLES } from '../types';
import type { ValidationMessage } from './types';

/**
 * Per-block-type semantic data validators.
 *
 * Single source of truth for data-shape invariants. Consumed by:
 *  - Registry `guard` functions (reject malformed props at import time)
 *  - Top-level validate() (surface human-readable errors in the QA panel)
 *
 * Keeping the rules here, rather than duplicated between registry/blocks.ts
 * and validation/validate.ts, means a tightened invariant can't drift between
 * the two layers.
 *
 * Validation strictness policy:
 * - Structural identifiers (label, role, type, country): non-empty string required
 * - Display-only text (delta, benchmarkLabel, flag, methodology): empty string allowed
 * - Numeric values (value, data[], rank): finite number required
 * - Arrays (items, series, xLabels, rows): non-empty, correct length
 */

export interface BlockDataValidation {
  valid: boolean;
  errors: ValidationMessage[];
}

export interface BlockDataNormalization {
  props: any;
  warnings: string[];
}

const VALID_DIRECTIONS: readonly Direction[] = ["positive", "negative", "neutral"];
const VALID_SERIES_ROLES: readonly string[] = SERIES_ROLES;

const OK: BlockDataValidation = { valid: true, errors: [] };

function result(errors: ValidationMessage[]): BlockDataValidation {
  return { valid: errors.length === 0, errors };
}

function deterministicNestedId(blockId: string, key: string, idx: number): string {
  return `${blockId}_${key}_${idx}`;
}

export function validateBarHorizontalData(props: any): BlockDataValidation {
  const errors: ValidationMessage[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: [{ key: 'validation.items.array_required' }] };
  }
  if (props.items.length === 0) {
    errors.push({ key: 'validation.items.min_one' });
  }
  if (props.items.length > 30) {
    errors.push({ key: 'validation.items.too_many', params: { count: props.items.length, max: 30 } });
  }
  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push({ key: 'validation.item.label_required', params: { index: i } });
    }
    if (typeof it?.value !== "number" || !Number.isFinite(it.value)) {
      errors.push({ key: 'validation.item.value_finite', params: { index: i } });
    }
  });

  if (props.showBenchmark === true) {
    if (typeof props.benchmarkValue !== "number" || !Number.isFinite(props.benchmarkValue)) {
      errors.push({ key: 'validation.benchmark.value_finite_when_enabled' });
    }
  }

  return result(errors);
}

export function validateLineEditorialData(props: any): BlockDataValidation {
  const errors: ValidationMessage[] = [];

  if (!Array.isArray(props?.series)) {
    return { valid: false, errors: [{ key: 'validation.series.array_required' }] };
  }
  if (!Array.isArray(props.xLabels)) {
    return { valid: false, errors: [{ key: 'validation.xlabels.array_required' }] };
  }
  if (props.series.length === 0) errors.push({ key: 'validation.series.min_one' });
  if (props.xLabels.length === 0) errors.push({ key: 'validation.xlabels.non_empty' });
  if (!props.xLabels.every((l: any) => typeof l === "string" && l.trim() !== "")) {
    errors.push({ key: 'validation.xlabels.all_non_empty' });
  }

  props.series.forEach((s: any, i: number) => {
    if (typeof s?.label !== "string" || !s.label.trim()) {
      errors.push({ key: 'validation.series.label_required', params: { index: i } });
    }
    if (!VALID_SERIES_ROLES.includes(s?.role)) {
      errors.push({ key: 'validation.series.role_invalid', params: { index: i, allowed: VALID_SERIES_ROLES.join(', ') } });
    }
    if (!Array.isArray(s?.data)) {
      errors.push({ key: 'validation.series.data_array_required', params: { index: i } });
      return;
    }
    if (s.data.length !== props.xLabels.length) {
      errors.push({
        key: 'validation.series.points_mismatch',
        params: { index: i, label: s.label, points: s.data.length, xLabels: props.xLabels.length },
      });
    }
    if (!s.data.every((v: any) => typeof v === "number" && Number.isFinite(v))) {
      errors.push({ key: 'validation.series.non_finite_values', params: { index: i, label: s.label } });
    }
  });

  return result(errors);
}

export function validateComparisonKpiData(props: any): BlockDataValidation {
  const errors: ValidationMessage[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: [{ key: 'validation.items.array_required' }] };
  }
  if (props.items.length < 2) errors.push({ key: 'validation.kpi.min_two' });
  if (props.items.length > 4) errors.push({ key: 'validation.kpi.max_items', params: { count: props.items.length, max: 4 } });

  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push({ key: 'validation.kpi.label_required', params: { index: i } });
    }
    if (typeof it?.value !== "string" || !it.value.trim()) {
      errors.push({ key: 'validation.kpi.value_required', params: { index: i } });
    }
    if (typeof it?.delta !== "string") {
      errors.push({ key: 'validation.kpi.delta_string', params: { index: i } });
    }
    if (!VALID_DIRECTIONS.includes(it?.direction)) {
      errors.push({ key: 'validation.kpi.direction_invalid', params: { index: i, allowed: VALID_DIRECTIONS.join(', ') } });
    }
  });

  return result(errors);
}

export function validateTableEnrichedData(props: any): BlockDataValidation {
  const errors: ValidationMessage[] = [];

  if (!Array.isArray(props?.columns)) {
    return { valid: false, errors: [{ key: 'validation.table.columns_array_required' }] };
  }
  if (!Array.isArray(props.rows)) {
    return { valid: false, errors: [{ key: 'validation.table.rows_array_required' }] };
  }
  if (props.columns.length < 2) errors.push({ key: 'validation.table.columns_min_two' });
  if (props.rows.length === 0) errors.push({ key: 'validation.table.rows_min_one' });

  props.rows.forEach((r: any, i: number) => {
    if (typeof r?.country !== "string" || !r.country.trim()) {
      errors.push({ key: 'validation.row.country_required', params: { index: i } });
    }
    if (typeof r?.rank !== "number" || !Number.isFinite(r.rank)) {
      errors.push({ key: 'validation.row.rank_finite', params: { index: i } });
    }
    if (!Array.isArray(r?.vals)) {
      errors.push({ key: 'validation.row.vals_array_required', params: { index: i } });
      return;
    }
    if (r.vals.length !== props.columns.length - 1) {
      errors.push({
        key: 'validation.row.vals_count_mismatch',
        params: { index: i, vals: r.vals.length, dataColumns: props.columns.length - 1 },
      });
    }
  });

  return result(errors);
}

export function validateSmallMultipleData(props: any): BlockDataValidation {
  const errors: ValidationMessage[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: [{ key: 'validation.items.array_required' }] };
  }
  if (props.items.length === 0) errors.push({ key: 'validation.items.min_one' });

  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push({ key: 'validation.item.label_required', params: { index: i } });
    }
    if (!Array.isArray(it?.data)) {
      errors.push({ key: 'validation.small_multiple.data_array_required', params: { index: i } });
      return;
    }
    if (it.data.length === 0) {
      errors.push({ key: 'validation.small_multiple.data_empty', params: { index: i, label: it.label } });
    }
    if (!it.data.every((v: any) => typeof v === "number" && Number.isFinite(v))) {
      errors.push({ key: 'validation.small_multiple.non_finite_values', params: { index: i, label: it.label } });
    }
  });

  return result(errors);
}

export function validateBlockData(type: string, props: any): BlockDataValidation {
  switch (type) {
    case "bar_horizontal": return validateBarHorizontalData(props);
    case "line_editorial": return validateLineEditorialData(props);
    case "comparison_kpi": return validateComparisonKpiData(props);
    case "table_enriched": return validateTableEnrichedData(props);
    case "small_multiple": return validateSmallMultipleData(props);
    default: return OK;
  }
}

export function normalizeBlockData(
  type: string,
  props: any,
  blockId: string,
): BlockDataNormalization {
  if (!props || typeof props !== "object") {
    return { props, warnings: [] };
  }

  if (type === "bar_horizontal" && Array.isArray(props.items)) {
    const warnings: string[] = [];
    const items = props.items.map((it: any, idx: number) => {
      if (it && typeof it === "object" && typeof it._id === "string" && it._id.trim()) {
        return it;
      }
      warnings.push(`bar_horizontal.items[${idx}] missing _id — assigned deterministic id`);
      return { ...it, _id: deterministicNestedId(blockId, "items", idx) };
    });
    return { props: { ...props, items }, warnings };
  }

  if (type === "line_editorial" && Array.isArray(props.series)) {
    const warnings: string[] = [];
    const series = props.series.map((it: any, idx: number) => {
      if (it && typeof it === "object" && typeof it._id === "string" && it._id.trim()) {
        return it;
      }
      warnings.push(`line_editorial.series[${idx}] missing _id — assigned deterministic id`);
      return { ...it, _id: deterministicNestedId(blockId, "series", idx) };
    });
    return { props: { ...props, series }, warnings };
  }

  if (type === "comparison_kpi" && Array.isArray(props.items)) {
    const warnings: string[] = [];
    const items = props.items.map((it: any, idx: number) => {
      if (it && typeof it === "object" && typeof it._id === "string" && it._id.trim()) {
        return it;
      }
      warnings.push(`comparison_kpi.items[${idx}] missing _id — assigned deterministic id`);
      return { ...it, _id: deterministicNestedId(blockId, "items", idx) };
    });
    return { props: { ...props, items }, warnings };
  }

  return { props, warnings: [] };
}
