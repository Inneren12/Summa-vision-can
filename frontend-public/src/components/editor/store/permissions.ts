import type { PermissionSet, BlockRegistryEntry, EditorMode } from '../types';

const CONTENT_KEYS = [
  "text", "value", "methodology", "label", "direction",
  "items", "series", "xLabels", "columns", "rows",
  "benchmarkValue", "benchmarkLabel", "yUnit",
] as const;

export const PERMS: Record<EditorMode, PermissionSet> = {
  template: {
    switchTemplate: false,
    changePalette: false,
    changeBackground: false,
    changeSize: true,
    editBlock: (reg: BlockRegistryEntry, key: string): boolean => {
      // Template mode: text/value content always editable, style/structure never
      if (reg.status === "required_locked") return ["text", "value", "methodology"].includes(key);
      return (CONTENT_KEYS as readonly string[]).includes(key);
    },
    toggleVisibility: (reg: BlockRegistryEntry): boolean => reg.status === "optional_default" || reg.status === "optional_available",
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
