import type { Direction } from '../types';
import { SERIES_ROLES } from '../types';

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
 */

export interface BlockDataValidation {
  valid: boolean;
  errors: string[];
}

const VALID_DIRECTIONS: readonly Direction[] = ["positive", "negative", "neutral"];
const VALID_SERIES_ROLES: readonly string[] = SERIES_ROLES;

const OK: BlockDataValidation = { valid: true, errors: [] };

function result(errors: string[]): BlockDataValidation {
  return { valid: errors.length === 0, errors };
}

export function validateBarHorizontalData(props: any): BlockDataValidation {
  const errors: string[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: ["items must be an array"] };
  }
  if (props.items.length === 0) {
    errors.push("at least one item required");
  }
  if (props.items.length > 30) {
    errors.push(`too many items: ${props.items.length} (max 30)`);
  }
  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push(`item[${i}]: label must be non-empty string`);
    }
    if (typeof it?.value !== "number" || !Number.isFinite(it.value)) {
      errors.push(`item[${i}]: value must be a finite number`);
    }
  });

  // Benchmark overlay must carry a finite number when enabled; otherwise the
  // renderer either skips it or draws at a NaN y-coordinate.
  if (props.showBenchmark === true) {
    if (typeof props.benchmarkValue !== "number" || !Number.isFinite(props.benchmarkValue)) {
      errors.push("showBenchmark is true but benchmarkValue is not a finite number");
    }
  }

  return result(errors);
}

export function validateLineEditorialData(props: any): BlockDataValidation {
  const errors: string[] = [];

  if (!Array.isArray(props?.series)) {
    return { valid: false, errors: ["series must be an array"] };
  }
  if (!Array.isArray(props.xLabels)) {
    return { valid: false, errors: ["xLabels must be an array"] };
  }
  if (props.series.length === 0) errors.push("at least one series required");
  if (props.xLabels.length === 0) errors.push("xLabels cannot be empty");
  if (!props.xLabels.every((l: any) => typeof l === "string")) {
    errors.push("all xLabels must be strings");
  }

  props.series.forEach((s: any, i: number) => {
    if (typeof s?.label !== "string" || !s.label.trim()) {
      errors.push(`series[${i}]: label must be non-empty string`);
    }
    if (!VALID_SERIES_ROLES.includes(s?.role)) {
      errors.push(`series[${i}]: role must be one of ${VALID_SERIES_ROLES.join(", ")}`);
    }
    if (!Array.isArray(s?.data)) {
      errors.push(`series[${i}]: data must be an array`);
      return;
    }
    if (s.data.length !== props.xLabels.length) {
      errors.push(`series[${i}] "${s.label}": ${s.data.length} points but ${props.xLabels.length} xLabels`);
    }
    if (!s.data.every((v: any) => typeof v === "number" && Number.isFinite(v))) {
      errors.push(`series[${i}] "${s.label}": contains non-finite values`);
    }
  });

  return result(errors);
}

export function validateComparisonKpiData(props: any): BlockDataValidation {
  const errors: string[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: ["items must be an array"] };
  }
  if (props.items.length < 2) errors.push("at least 2 KPI items required");
  if (props.items.length > 4) errors.push(`too many items: ${props.items.length} (max 4)`);

  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push(`kpi[${i}]: label must be non-empty string`);
    }
    if (typeof it?.value !== "string" || !it.value.trim()) {
      errors.push(`kpi[${i}]: value must be non-empty string`);
    }
    if (typeof it?.delta !== "string") {
      errors.push(`kpi[${i}]: delta must be string`);
    }
    if (!VALID_DIRECTIONS.includes(it?.direction)) {
      errors.push(`kpi[${i}]: direction must be one of ${VALID_DIRECTIONS.join(", ")}`);
    }
  });

  return result(errors);
}

export function validateTableEnrichedData(props: any): BlockDataValidation {
  const errors: string[] = [];

  if (!Array.isArray(props?.columns)) {
    return { valid: false, errors: ["columns must be an array"] };
  }
  if (!Array.isArray(props.rows)) {
    return { valid: false, errors: ["rows must be an array"] };
  }
  if (props.columns.length < 2) errors.push("at least 2 columns required");
  if (props.rows.length === 0) errors.push("at least one row required");

  props.rows.forEach((r: any, i: number) => {
    if (typeof r?.country !== "string" || !r.country.trim()) {
      errors.push(`row[${i}]: country must be non-empty string`);
    }
    if (typeof r?.rank !== "number" || !Number.isFinite(r.rank)) {
      errors.push(`row[${i}]: rank must be a finite number`);
    }
    if (!Array.isArray(r?.vals)) {
      errors.push(`row[${i}]: vals must be an array`);
      return;
    }
    if (r.vals.length !== props.columns.length - 1) {
      errors.push(`row[${i}]: ${r.vals.length} vals but ${props.columns.length - 1} data columns`);
    }
  });

  return result(errors);
}

export function validateSmallMultipleData(props: any): BlockDataValidation {
  const errors: string[] = [];

  if (!Array.isArray(props?.items)) {
    return { valid: false, errors: ["items must be an array"] };
  }
  if (props.items.length === 0) errors.push("at least one item required");

  props.items.forEach((it: any, i: number) => {
    if (typeof it?.label !== "string" || !it.label.trim()) {
      errors.push(`item[${i}]: label must be non-empty string`);
    }
    if (!Array.isArray(it?.data)) {
      errors.push(`item[${i}]: data must be an array`);
      return;
    }
    if (it.data.length === 0) {
      errors.push(`item[${i}] "${it.label}": data is empty`);
    }
    if (!it.data.every((v: any) => typeof v === "number" && Number.isFinite(v))) {
      errors.push(`item[${i}] "${it.label}": contains non-finite values`);
    }
  });

  return result(errors);
}

/**
 * Dispatch a block type to its semantic validator. Unknown types are
 * treated as valid (no data constraints) — unknown-type rejection is the
 * registry's job, not the data validator's.
 */
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
