import type { CanonicalDocument, ValidationResult } from '../types';
import { BREG } from '../registry/blocks';
import { SIZES } from '../config/sizes';
import { PALETTES } from '../config/palettes';

export function validate(doc: CanonicalDocument): ValidationResult {
  const R: ValidationResult = { errors: [], warnings: [], info: [], passed: [] };
  const blocks = Object.values(doc.blocks).filter(b => b.visible);
  const types = blocks.map(b => b.type);
  const sz = SIZES[doc.page.size] || SIZES.instagram_1080;

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
  // Slot compatibility
  doc.sections.forEach(sec => {
    sec.blockIds.forEach(bid => { const b = doc.blocks[bid]; if (!b) return; const reg = BREG[b.type]; if (reg && !reg.allowedSections.includes(sec.type)) R.errors.push(`${reg.name} not allowed in ${sec.type}`); });
    const counts: Record<string, number> = {};
    sec.blockIds.forEach(bid => { const b = doc.blocks[bid]; if (!b || !b.visible) return; counts[b.type] = (counts[b.type] || 0) + 1; });
    Object.entries(counts).forEach(([t, c]) => { const reg = BREG[t]; if (reg?.maxPerSection && c > reg.maxPerSection) R.warnings.push(`${reg.name}: ${c}x in ${sec.type} (max ${reg.maxPerSection})`); });
  });

  // CHART-AWARE VALIDATION (Stage 2 Polish)
  blocks.forEach(b => {
    if (b.type === "bar_horizontal") {
      const items = b.props.items || [];
      if (!items.length) R.errors.push("Ranked Bars: no data items");
      if (items.some((i: any) => typeof i.value !== "number" || isNaN(i.value))) R.errors.push("Ranked Bars: NaN value detected");
      if (items.some((i: any) => !i.label?.trim())) R.warnings.push("Ranked Bars: item missing label");
      if (items.length > 25) R.warnings.push(`Ranked Bars: ${items.length} items \u2014 may be dense`);
      if (items.length > 30) R.errors.push(`Ranked Bars: ${items.length} items exceeds max 30`);
      // Layout density for small sizes
      if (items.length > 10 && (sz.h < 800)) R.warnings.push("Ranked Bars: too many items for this canvas height");
    }
    if (b.type === "line_editorial") {
      const sr = b.props.series || [], xl = b.props.xLabels || [];
      if (!sr.length) R.errors.push("Line Chart: no series data");
      sr.forEach((s: any) => { if (!s.data?.length) R.errors.push(`Line Chart: series "${s.label}" has no data`); if (s.data?.some((v: any) => typeof v !== "number" || isNaN(v))) R.errors.push(`Line Chart: NaN in "${s.label}"`); if (s.data?.length !== xl.length) R.warnings.push(`Line Chart: "${s.label}" has ${s.data?.length} points but ${xl.length} labels`); });
      if (xl.length > 12) R.warnings.push(`Line Chart: ${xl.length} x-labels \u2014 may overlap`);
    }
    if (b.type === "comparison_kpi") {
      const items = b.props.items || [];
      if (items.length < 2) R.errors.push("KPI Compare: need at least 2 items");
      if (items.length > 4) R.warnings.push("KPI Compare: more than 4 items may be cramped");
      items.forEach((it: any, i: number) => { if (!it.value?.trim()) R.warnings.push(`KPI #${i + 1}: empty value`); if (!it.label?.trim()) R.warnings.push(`KPI #${i + 1}: empty label`); });
    }
    if (b.type === "table_enriched") {
      const cols = b.props.columns || [], rows = b.props.rows || [];
      if (!rows.length) R.errors.push("Visual Table: no rows");
      rows.forEach((r: any, i: number) => { if (r.vals?.length !== cols.length - 1) R.warnings.push(`Table row ${i + 1}: ${r.vals?.length} values, expected ${cols.length - 1}`); });
      if (rows.length > 12) R.warnings.push(`Visual Table: ${rows.length} rows \u2014 may overflow on ${sz.n}`);
    }
    if (b.type === "small_multiple") {
      const items = b.props.items || [];
      if (!items.length) R.errors.push("Small Multiples: no items");
      items.forEach((it: any, i: number) => { if (!it.data?.length) R.errors.push(`Small Mult #${i + 1}: no data`); if (!it.label?.trim()) R.warnings.push(`Small Mult #${i + 1}: no label`); });
      if (items.length > 9) R.warnings.push("Small Multiples: more than 9 cells may be too dense");
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

  return R;
}
