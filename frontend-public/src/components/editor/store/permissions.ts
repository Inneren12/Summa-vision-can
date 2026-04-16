import type { PermissionSet, BlockRegistryEntry, EditorMode } from '../types';

// ────────────────────────────────────────────────────────────────────
// Permission Model — key categories
//
// Keys are partitioned by editorial intent, not by data type:
//
//  TEXT_CONTENT_KEYS  : copy editing only (headlines, labels, source
//                       attribution, benchmark label/value, axis units).
//                       Always editable — changing these does not alter
//                       the template's visual structure.
//
//  DATA_CONTENT_KEYS  : editing values within an existing structure
//                       (e.g. KPI direction). Changes state but not
//                       shape.
//
//  STRUCTURAL_KEYS    : changes that alter the shape/count of the
//                       visualization (items/series/rows/columns/xLabels).
//                       Template mode blocks these — add/remove items
//                       is reserved for Design mode because it changes
//                       what the template looks like.
//
//  STYLE_KEYS         : visual design controls (align, position, toggles,
//                       unit suffix). Template-controlled, so Template
//                       mode cannot edit. Design mode can.
//
// required_locked blocks (source, brand): only identity fields
// (text, value, methodology) are editable even in Template mode.
// ────────────────────────────────────────────────────────────────────

const TEXT_CONTENT_KEYS = [
  "text", "value", "methodology", "label",
  "benchmarkValue", "benchmarkLabel", "yUnit",
] as const;

const DATA_CONTENT_KEYS = [
  "direction", // KPI direction indicator
] as const;

// Structural keys — template mode blocks add/remove, design mode allows
// (exported for reference; gating is driven via canEditStructure helper)
export const STRUCTURAL_KEYS = [
  "items", "series", "xLabels", "rows", "columns",
] as const;

// Style keys — visual design, template-controlled
// (exported for reference; template mode blocks via editBlock)
export const STYLE_KEYS = [
  "align", "position", "showBenchmark", "showArea", "unit",
] as const;

export const PERMS: Record<EditorMode, PermissionSet> = {
  template: {
    switchTemplate: false,
    changePalette: false,
    changeBackground: false,
    changeSize: true,
    editBlock: (reg: BlockRegistryEntry, key: string): boolean => {
      // required_locked: only identity fields editable
      if (reg.status === "required_locked") {
        return ["text", "value", "methodology"].includes(key);
      }
      // Template mode allows text + data content, blocks structural + style
      const textOrData: readonly string[] = [...TEXT_CONTENT_KEYS, ...DATA_CONTENT_KEYS];
      return textOrData.includes(key);
    },
    toggleVisibility: (reg: BlockRegistryEntry): boolean =>
      reg.status === "optional_default" || reg.status === "optional_available",
  },
  design: {
    switchTemplate: true,
    changePalette: true,
    changeBackground: true,
    changeSize: true,
    editBlock: (): boolean => true,
    toggleVisibility: (): boolean => true,
  },
};

/**
 * Can the user structurally alter this block (add/remove items,
 * change series count, etc.)?
 * Template mode: no — structural changes belong to Design mode.
 * Design mode: yes.
 */
export function canEditStructure(_reg: BlockRegistryEntry, mode: EditorMode): boolean {
  return mode === "design";
}
