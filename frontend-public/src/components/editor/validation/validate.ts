import type { CanonicalDocument, ValidationResult } from '../types';
import { BREG } from '../registry/blocks';
import { SIZES } from '../config/sizes';
import type { PresetId } from '../config/sizes';
import { PALETTES } from '../config/palettes';
import { BGS } from '../config/backgrounds';
import { validateBlockData } from './block-data';
import { validateContrast } from './contrast';
import { measureLayout } from '../renderer/measure';
import {
  computeLongInfographicHeight,
  LONG_INFOGRAPHIC_HEIGHT_CAP,
} from '../export/renderToBlob';

// Block type names from BREG (e.g. "Ranked Bars", "KPI Compare") flow through
// validation messages as `{blockName}` params unchanged. They remain EN in both
// locales for this slice. Full localization of BREG block type names happens in
// Phase 1 Slice 3 (block editors + registry migration).

/**
 * Phase 2.1 PR#4 — split: size-independent rules. Operates on `doc` only,
 * does NOT read `SIZES[doc.page.size]` dimensions. Membership-only checks
 * (e.g. `SIZES[doc.page.size]` enum guard) stay here because they verify
 * the page config string, not layout. Everything that consults `sz.w` / `sz.h`
 * for a real layout decision moves to `validatePresetSize`.
 */
export function validateDocument(doc: CanonicalDocument): ValidationResult {
  const R: ValidationResult = { errors: [], warnings: [], info: [], passed: [], contrastIssues: [] };
  const blocks = Object.values(doc.blocks).filter(b => b.visible);
  const types = blocks.map(b => b.type);

  if (!PALETTES[doc.page.palette]) R.errors.push({ key: 'validation.page.unknown_palette', params: { palette: doc.page.palette } });
  if (!BGS[doc.page.background]) R.errors.push({ key: 'validation.page.unknown_background', params: { background: doc.page.background } });
  if (!SIZES[doc.page.size]) R.errors.push({ key: 'validation.page.unknown_size', params: { size: doc.page.size } });

  (["source_footer", "brand_stamp", "headline_editorial"] as string[]).forEach(req => {
    if (types.includes(req)) R.passed.push({ key: 'validation.required_block.present', params: { blockName: BREG[req].name } });
    else R.errors.push({ key: 'validation.required_block.missing', params: { blockName: BREG[req].name } });
  });

  const hl = blocks.find(b => b.type === "headline_editorial");
  if (hl && !(hl.props.text || "").trim()) R.errors.push({ key: 'validation.headline.empty' });
  const hs = blocks.find(b => b.type === "hero_stat");
  if (hs && !(hs.props.value || "").trim()) R.errors.push({ key: 'validation.hero_number.empty' });

  blocks.forEach(b => {
    const reg = BREG[b.type];
    if (!reg?.cst?.maxChars) return;
    const txt = (b.props.text || b.props.value || "").replace(/\n/g, "");
    const mx = reg.cst.maxChars;
    if (txt.length > mx) R.errors.push({ key: 'validation.max_chars.overflow', params: { blockName: reg.name, count: txt.length, max: mx } });
    else if (txt.length > mx * .9) R.warnings.push({ key: 'validation.max_chars.near_limit', params: { blockName: reg.name, count: txt.length, max: mx } });
  });

  blocks.forEach(b => {
    const reg = BREG[b.type];
    if (!reg?.cst?.maxLines) return;
    const lines = (b.props.text || "").split("\n").length;
    if (lines > reg.cst.maxLines) R.warnings.push({ key: 'validation.max_lines.near_limit', params: { blockName: reg.name, count: lines, max: reg.cst.maxLines } });
  });

  const seenSectionIds = new Set<string>();
  doc.sections.forEach(sec => {
    if (seenSectionIds.has(sec.id)) {
      R.errors.push({ key: 'validation.section.duplicate_id', params: { id: sec.id } });
    } else {
      seenSectionIds.add(sec.id);
    }
    const seenBlockIdsInSection = new Set<string>();
    sec.blockIds.forEach(bid => {
      if (seenBlockIdsInSection.has(bid)) {
        R.errors.push({ key: 'validation.section.duplicate_block_id', params: { sectionId: sec.id, blockId: bid } });
      } else {
        seenBlockIdsInSection.add(bid);
      }
    });
  });

  doc.sections.forEach(sec => {
    sec.blockIds.forEach(bid => {
      const b = doc.blocks[bid];
      if (!b) return;
      const reg = BREG[b.type];
      if (reg && !reg.allowedSections.includes(sec.type)) {
        R.errors.push({ key: 'validation.section.block_not_allowed', params: { blockName: reg.name, sectionType: sec.type } });
      }
    });
    const counts: Record<string, number> = {};
    sec.blockIds.forEach(bid => {
      const b = doc.blocks[bid];
      if (!b || !b.visible) return;
      counts[b.type] = (counts[b.type] || 0) + 1;
    });
    Object.entries(counts).forEach(([t, c]) => {
      const reg = BREG[t];
      if (reg?.maxPerSection && c > reg.maxPerSection) {
        R.warnings.push({ key: 'validation.section.max_per_section', params: { blockName: reg.name, count: c, sectionType: sec.type, max: reg.maxPerSection } });
      }
    });
  });

  blocks.forEach(b => {
    const dv = validateBlockData(b.type, b.props);
    if (!dv.valid) {
      const name = BREG[b.type]?.name || b.type;
      dv.errors.forEach(err => R.errors.push({
        ...err,
        prefix: name,
      }));
    }
  });

  blocks.forEach(b => {
    if (b.type === "bar_horizontal") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 25 && n <= 30) R.warnings.push({ key: 'validation.density.ranked_bars_dense', params: { count: n } });
    }
    if (b.type === "line_editorial") {
      const xl = Array.isArray(b.props.xLabels) ? b.props.xLabels.length : 0;
      if (xl > 12) R.warnings.push({ key: 'validation.density.line_chart_overlap', params: { count: xl } });
    }
    if (b.type === "comparison_kpi") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 4) R.warnings.push({ key: 'validation.density.kpi_compare_cramped' });
    }
    if (b.type === "small_multiple") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 9) R.warnings.push({ key: 'validation.density.small_multiples_dense' });
    }
  });

  if (hl) {
    const len = (hl.props.text || "").replace(/\n/g, "").length;
    if (len > 60 && len <= 80) R.info.push({ key: 'validation.layout.headline_shorter', params: { count: len } });
    const lines = (hl.props.text || "").split("\n");
    const longest = Math.max(...lines.map((l: string) => l.length));
    if (longest > 28) R.warnings.push({ key: 'validation.layout.headline_line_overflow', params: { count: longest } });
  }

  const sf = blocks.find(b => b.type === "source_footer");
  if (sf && sf.props.text === BREG.source_footer.dp.text) R.warnings.push({ key: 'validation.source_footer.default_text' });

  blocks.forEach(b => {
    if (b.type === "body_annotation" && !(b.props.text || "").trim()) R.warnings.push({ key: 'validation.layout.annotation_empty' });
  });

  const contrastIssues = validateContrast(doc);
  R.contrastIssues = contrastIssues;
  for (const issue of contrastIssues) {
    if (issue.severity === 'error') {
      R.errors.push(issue.message);
    } else {
      R.warnings.push(issue.message);
    }
  }

  return R;
}

/**
 * Phase 2.1 PR#4 — split: size-dependent rules ONLY. Caller passes the preset
 * to evaluate; the function reads `SIZES[presetId]` rather than `doc.page.size`,
 * so the Inspector can preview "what would happen if I exported `X`?" without
 * mutating the editing canvas.
 *
 * Includes the long-infographic pre-render cap check: this mirrors the
 * runtime `RenderCapExceededError` thrown by `renderDocumentToBlob` for the
 * same condition (uses the same i18n key + cap constant). The runtime throw
 * STAYS — defense-in-depth, the renderer guarantees no OOM even if validator
 * and renderer ever drift.
 */
export function validatePresetSize(
  doc: CanonicalDocument,
  presetId: PresetId,
): ValidationResult {
  const R: ValidationResult = { errors: [], warnings: [], info: [], passed: [], contrastIssues: [] };
  const sz = SIZES[presetId];
  if (!sz) {
    return R;
  }

  const blocks = Object.values(doc.blocks).filter(b => b.visible);
  const types = blocks.map(b => b.type);

  blocks.forEach(b => {
    if (b.type === "bar_horizontal") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 10 && sz.h < 800) R.warnings.push({ key: 'validation.density.ranked_bars_height' });
    }
    if (b.type === "table_enriched") {
      const n = Array.isArray(b.props.rows) ? b.props.rows.length : 0;
      if (n > 12) R.warnings.push({ key: 'validation.density.visual_table_overflow', params: { count: n, size: sz.n } });
    }
  });

  if (sz.h < 700 && types.includes("body_annotation")) R.info.push({ key: 'validation.layout.annotation_landscape' });
  if (sz.w < 1100 && types.includes("table_enriched")) R.warnings.push({ key: 'validation.layout.table_narrow' });

  if (presetId === 'long_infographic') {
    const measuredHeight = computeLongInfographicHeight(doc, sz.w);
    if (measuredHeight > LONG_INFOGRAPHIC_HEIGHT_CAP) {
      R.errors.push({
        key: 'validation.long_infographic.height_cap_exceeded',
        params: { measured: Math.round(measuredHeight), cap: LONG_INFOGRAPHIC_HEIGHT_CAP },
      });
    }
  } else {
    const layout = measureLayout(doc, sz);
    layout.forEach(sec => {
      if (sec.overflow) {
        R.warnings.push({
          key: 'validation.layout.section_overflow',
          params: { sectionType: sec.sectionType, usedPx: Math.round(sec.consumedHeight), availablePx: Math.round(sec.availableHeight) },
        });
      }
    });
  }

  return R;
}

function mergeValidationResults(a: ValidationResult, b: ValidationResult): ValidationResult {
  return {
    errors: [...a.errors, ...b.errors],
    warnings: [...a.warnings, ...b.warnings],
    info: [...a.info, ...b.info],
    passed: [...a.passed, ...b.passed],
    contrastIssues: [...a.contrastIssues, ...b.contrastIssues],
  };
}

/**
 * Phase 2.1 PR#4 — back-compat wrapper. Production callsite is the QA panel
 * at `index.tsx:330`. Returns the same merged shape callers have always
 * received: size-independent rules first, then size-dependent rules for the
 * doc's current `page.size`.
 */
export function validate(doc: CanonicalDocument): ValidationResult {
  const docResult = validateDocument(doc);
  const sizeResult = validatePresetSize(doc, doc.page.size as PresetId);
  return mergeValidationResults(docResult, sizeResult);
}
