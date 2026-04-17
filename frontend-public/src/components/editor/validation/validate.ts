import type { CanonicalDocument, ValidationResult } from '../types';
import { BREG } from '../registry/blocks';
import { SIZES } from '../config/sizes';
import { PALETTES } from '../config/palettes';
import { BGS } from '../config/backgrounds';
import { validateBlockData } from './block-data';
import { measureLayout } from '../renderer/measure';

export function validate(doc: CanonicalDocument): ValidationResult {
  const R: ValidationResult = { errors: [], warnings: [], info: [], passed: [] };
  const blocks = Object.values(doc.blocks).filter(b => b.visible);
  const types = blocks.map(b => b.type);
  const sz = SIZES[doc.page.size] || SIZES.instagram_1080;

  // Page config validity — reject unknown palette/background/size so the doc
  // can't silently render with fallback styling the author never asked for.
  if (!PALETTES[doc.page.palette]) R.errors.push(`Unknown palette: "${doc.page.palette}"`);
  if (!BGS[doc.page.background]) R.errors.push(`Unknown background: "${doc.page.background}"`);
  if (!SIZES[doc.page.size]) R.errors.push(`Unknown size: "${doc.page.size}"`);

  // Required blocks
  (["source_footer", "brand_stamp", "headline_editorial"] as string[]).forEach(req => {
    if (types.includes(req)) R.passed.push(`${BREG[req].name} present`);
    else R.errors.push(`${BREG[req].name} is required`);
  });
  // Empty content
  const hl = blocks.find(b => b.type === "headline_editorial");
  if (hl && !(hl.props.text || "").trim()) R.errors.push("Headline is empty");
  const hs = blocks.find(b => b.type === "hero_stat");
  if (hs && !(hs.props.value || "").trim()) R.errors.push("Hero number is empty");
  // Char/line limits
  blocks.forEach(b => { const reg = BREG[b.type]; if (!reg?.cst?.maxChars) return; const txt = (b.props.text || b.props.value || "").replace(/\n/g, ""), mx = reg.cst.maxChars; if (txt.length > mx) R.errors.push(`${reg.name}: ${txt.length}/${mx} OVERFLOW`); else if (txt.length > mx * .9) R.warnings.push(`${reg.name}: ${txt.length}/${mx} chars`); });
  blocks.forEach(b => { const reg = BREG[b.type]; if (!reg?.cst?.maxLines) return; const lines = (b.props.text || "").split("\n").length; if (lines > reg.cst.maxLines) R.warnings.push(`${reg.name}: ${lines}/${reg.cst.maxLines} lines`); });

  // Structural integrity: duplicate section.id (global) and duplicate
  // blockId within any section's blockIds array. validateImportStrict()
  // enforces these at import time, but validate() also runs on live state mutated
  // by the reducer — check again here to catch regressions from unfamiliar
  // code paths (tests, devtools, future bulk actions).
  const seenSectionIds = new Set<string>();
  doc.sections.forEach(sec => {
    if (seenSectionIds.has(sec.id)) {
      R.errors.push(`Duplicate section id: "${sec.id}"`);
    } else {
      seenSectionIds.add(sec.id);
    }
    const seenBlockIdsInSection = new Set<string>();
    sec.blockIds.forEach(bid => {
      if (seenBlockIdsInSection.has(bid)) {
        R.errors.push(`Section "${sec.id}" has duplicate blockId: "${bid}"`);
      } else {
        seenBlockIdsInSection.add(bid);
      }
    });
  });

  // Slot compatibility
  doc.sections.forEach(sec => {
    sec.blockIds.forEach(bid => { const b = doc.blocks[bid]; if (!b) return; const reg = BREG[b.type]; if (reg && !reg.allowedSections.includes(sec.type)) R.errors.push(`${reg.name} not allowed in ${sec.type}`); });
    const counts: Record<string, number> = {};
    sec.blockIds.forEach(bid => { const b = doc.blocks[bid]; if (!b || !b.visible) return; counts[b.type] = (counts[b.type] || 0) + 1; });
    Object.entries(counts).forEach(([t, c]) => { const reg = BREG[t]; if (reg?.maxPerSection && c > reg.maxPerSection) R.warnings.push(`${reg.name}: ${c}x in ${sec.type} (max ${reg.maxPerSection})`); });
  });

  // STRUCTURED DATA VALIDATION — delegate to the per-type validators in
  // validation/block-data.ts. Keeps the semantic rules in one place (also
  // consumed by registry guards).
  blocks.forEach(b => {
    const dv = validateBlockData(b.type, b.props);
    if (!dv.valid) {
      const name = BREG[b.type]?.name || b.type;
      dv.errors.forEach(err => R.errors.push(`${name}: ${err}`));
    }
  });

  // Density / layout warnings that are presentation-specific (not data-semantic)
  // remain outside the shared validator: they depend on canvas size + overall
  // doc context, not the block's own props.
  blocks.forEach(b => {
    if (b.type === "bar_horizontal") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 25 && n <= 30) R.warnings.push(`Ranked Bars: ${n} items \u2014 may be dense`);
      if (n > 10 && sz.h < 800) R.warnings.push("Ranked Bars: too many items for this canvas height");
    }
    if (b.type === "line_editorial") {
      const xl = Array.isArray(b.props.xLabels) ? b.props.xLabels.length : 0;
      if (xl > 12) R.warnings.push(`Line Chart: ${xl} x-labels \u2014 may overlap`);
    }
    if (b.type === "comparison_kpi") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 4) R.warnings.push("KPI Compare: more than 4 items may be cramped");
    }
    if (b.type === "table_enriched") {
      const n = Array.isArray(b.props.rows) ? b.props.rows.length : 0;
      if (n > 12) R.warnings.push(`Visual Table: ${n} rows \u2014 may overflow on ${sz.n}`);
    }
    if (b.type === "small_multiple") {
      const n = Array.isArray(b.props.items) ? b.props.items.length : 0;
      if (n > 9) R.warnings.push("Small Multiples: more than 9 cells may be too dense");
    }
  });

  // LAYOUT SAFETY (Stage 2 Polish)
  // Headline width
  if (hl) {
    const len = (hl.props.text || "").replace(/\n/g, "").length;
    if (len > 60 && len <= 80) R.info.push(`Headline ${len} chars \u2014 shorter may work better`);
    const lines = (hl.props.text || "").split("\n");
    const longest = Math.max(...lines.map((l: string) => l.length));
    if (longest > 28) R.warnings.push(`Headline line ${longest} chars \u2014 may overflow small sizes`);
  }
  // Source placeholder
  const sf = blocks.find(b => b.type === "source_footer");
  if (sf && sf.props.text === BREG.source_footer.dp.text) R.warnings.push("Source is still default");
  // Contrast
  const pal = PALETTES[doc.page.palette];
  if (pal) {
    const hex = pal.p.replace("#", "");
    const r = parseInt(hex.substr(0, 2), 16), g = parseInt(hex.substr(2, 2), 16), b2 = parseInt(hex.substr(4, 2), 16);
    const lum = (0.299 * r + 0.587 * g + 0.114 * b2) / 255;
    if (lum < 0.15) R.warnings.push("Primary color may be too dark on dark bg");
  }
  // Size-specific warnings
  if (sz.h < 700 && types.includes("body_annotation")) R.info.push("Annotation may not fit on landscape sizes");
  if (sz.w < 1100 && types.includes("table_enriched")) R.warnings.push("Visual Table may be cramped on narrow canvas");

  // Empty annotation
  blocks.forEach(b => { if (b.type === "body_annotation" && !(b.props.text || "").trim()) R.warnings.push("Annotation block is empty"); });


  const size = SIZES[doc.page.size];
  if (size) {
    const layout = measureLayout(doc, size);
    layout.forEach(sec => {
      if (sec.overflow) {
        R.warnings.push(
          `Section "${sec.sectionType}" may overflow: ~${Math.round(sec.consumedHeight)}px used / ${Math.round(sec.availableHeight)}px available`,
        );
      }
    });
  }

  return R;
}
