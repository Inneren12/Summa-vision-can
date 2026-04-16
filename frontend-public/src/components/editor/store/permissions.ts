import type { PermissionSet, BlockRegistryEntry } from '../types';

export const PERMS: Record<string, PermissionSet> = {
  template: {
    switchTemplate: false,
    changePalette: false,
    changeBackground: false,
    changeSize: true,
    editBlock: (reg: BlockRegistryEntry, key: string): boolean => {
      // Template mode: text/value content always editable, style/structure never
      const contentKeys = ["text", "value", "methodology", "label", "direction", "items", "series", "xLabels", "columns", "rows"];
      if (reg.status === "required_locked") return ["text", "value", "methodology"].includes(key);
      return contentKeys.includes(key);
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
