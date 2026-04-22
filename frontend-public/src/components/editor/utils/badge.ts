import type { BlockStatus } from '../types';

type InspectorTranslator = (key: string) => string;

export function badgeLabel(tInspector: InspectorTranslator, st: BlockStatus): string {
  switch (st) {
    case 'required_locked':
      return tInspector('badge.required_locked');
    case 'required_editable':
      return tInspector('badge.required_editable');
    case 'optional_default':
      return tInspector('badge.optional_default');
    case 'optional_available':
      return tInspector('badge.optional_available');
    default:
      return 'UNKNOWN';
  }
}

export function badgeColor(st: BlockStatus, tokens: { err: string; acc: string; pos: string; txtM: string }): string {
  const colors: Record<BlockStatus, string> = {
    required_locked: tokens.err,
    required_editable: tokens.acc,
    optional_default: tokens.pos,
    optional_available: tokens.txtM,
  };
  return colors[st];
}
