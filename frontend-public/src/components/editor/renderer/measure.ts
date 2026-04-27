import { SECTION_LAYOUT } from './engine';
import type { CanonicalDocument, SizePreset } from '../types';

export interface BlockMeasurement {
  blockId: string;
  type: string;
  estimatedHeight: number;
}

export interface SectionMeasurement {
  sectionId: string;
  sectionType: string;
  availableHeight: number;
  consumedHeight: number;
  overflow: boolean;
  blocks: BlockMeasurement[];
}

/**
 * Approximate block height without canvas context.
 * These estimates mirror the main measurements in renderer/blocks.ts.
 * If a block renderer changes its layout math, update the corresponding
 * estimate here.
 */
function estimateBlockHeight(blockType: string, props: any, width: number, scale: number): number {
  const s = scale;
  const text = typeof props?.text === 'string' ? props.text : '';

  const estimates: Record<string, () => number> = {
    eyebrow_tag: () => 20 * s,

    headline_editorial: () => {
      const manualLines = text.split('\n').length;
      const avgCharsPerLine = Math.max(1, Math.floor((width * 0.95) / (42 * s * 0.55)));
      const totalLines = text.split('\n').reduce((sum: number, line: string) => {
        return sum + Math.max(1, Math.ceil(line.length / avgCharsPerLine));
      }, 0);
      return (Math.max(totalLines, manualLines) * 50 + 10) * s;
    },

    subtitle_descriptor: () => {
      if (!text) return 0;
      const avgCharsPerLine = Math.max(1, Math.floor((width * 0.9) / (16 * s * 0.55)));
      const lines = Math.ceil(text.length / avgCharsPerLine);
      return (lines * 22 + 10) * s;
    },

    hero_stat: () => (props?.value ? 150 * s : 0),

    delta_badge: () => (props?.value ? 24 * s : 0),

    body_annotation: () => {
      if (!text) return 0;
      const avgCharsPerLine = Math.max(1, Math.floor((width * 0.8) / (13 * s * 0.55)));
      const lines = Math.ceil(text.length / avgCharsPerLine);
      return (lines * 20 + 10) * s;
    },

    // source_footer renderer always returns 30*s (two-line layout for text + methodology).
    // Keep this in sync with renderer/blocks.ts if the footer layout changes.
    source_footer: () => 30 * s,

    brand_stamp: () => 20 * s,

    bar_horizontal: () => {
      const items = Array.isArray(props?.items) ? props.items : [];
      if (items.length === 0) return 0;
      return Math.max(items.length * 35 * s, 100 * s);
    },

    line_editorial: () => {
      const series = Array.isArray(props?.series) ? props.series : [];
      return series.length > 0 ? 250 * s : 0;
    },

    comparison_kpi: () => {
      const items = Array.isArray(props?.items) ? props.items : [];
      return items.length > 0 ? 130 * s : 0;
    },

    table_enriched: () => {
      const rows = Array.isArray(props?.rows) ? props.rows : [];
      // Match renderer: rowH is capped at 36*s (actual rendering clamps to fit)
      return (rows.length * 36 + 20) * s;
    },

    small_multiple: () => {
      const items = Array.isArray(props?.items) ? props.items : [];
      const rows = Math.ceil(items.length / 3);
      return rows * 160 * s;
    },
  };

  const fn = estimates[blockType];
  return fn ? fn() : 40 * s;
}

/**
 * Compute estimated layout for a document at a given canvas size.
 * Returns per-section consumed/available/overflow so QA can warn BEFORE
 * the user sees a broken render.
 *
 * Pass `size.h === Infinity` to measure intrinsic content height for
 * variable-height presets (long_infographic). In that mode the per-section
 * `availableHeight` is the unbounded sentinel and `overflow` is always
 * `false` — section overflow is meaningless when the canvas can grow to
 * fit. Callers (renderDocumentToBlob) sum `consumedHeight` to get the
 * intrinsic page height before deciding whether to render or reject for
 * exceeding the preset cap.
 */
export function measureLayout(doc: CanonicalDocument, size: SizePreset): SectionMeasurement[] {
  const s = size.w / 1080;
  const pad = 64 * s;
  const unbounded = size.h === Infinity;
  const results: SectionMeasurement[] = [];

  doc.sections.forEach(sec => {
    const layoutFn = SECTION_LAYOUT[sec.type];
    if (!layoutFn) return;
    const layout = layoutFn(size.w, size.h, s, pad);

    const blockMeasures: BlockMeasurement[] = [];
    let consumed = 0;

    sec.blockIds.forEach(bid => {
      const block = doc.blocks[bid];
      if (!block || !block.visible) return;
      const estimated = estimateBlockHeight(block.type, block.props, layout.w, s);
      blockMeasures.push({ blockId: bid, type: block.type, estimatedHeight: estimated });
      consumed += estimated;
    });

    results.push({
      sectionId: sec.id,
      sectionType: sec.type,
      availableHeight: layout.h,
      consumedHeight: consumed,
      overflow: unbounded ? false : consumed > layout.h * 1.1,
      blocks: blockMeasures,
    });
  });

  return results;
}
