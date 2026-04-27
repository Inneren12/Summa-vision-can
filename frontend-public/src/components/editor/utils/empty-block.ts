import type { Block } from '../types';
import { BREG } from '../registry/blocks';

/**
 * Deep-equality helper used by `isBlockEmpty`. Re-implemented locally to
 * avoid pulling in `lodash.isEqual` for a single comparison helper. Handles
 * plain objects, arrays, primitives, and NaN-equivalence the same way the
 * editor's serialized block props are shaped (no Dates, no Maps, no class
 * instances — everything is JSON-serialisable per `buildUpdatePayload`).
 */
function deepEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return false;
  if (typeof a !== 'object') return false;

  if (Array.isArray(a)) {
    if (!Array.isArray(b) || a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false;
    }
    return true;
  }
  if (Array.isArray(b)) return false;

  const ao = a as Record<string, unknown>;
  const bo = b as Record<string, unknown>;
  const aKeys = Object.keys(ao);
  const bKeys = Object.keys(bo);
  if (aKeys.length !== bKeys.length) return false;
  for (const k of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(bo, k)) return false;
    if (!deepEqual(ao[k], bo[k])) return false;
  }
  return true;
}

/**
 * A block is "empty" iff every prop equals the registry default. Used by
 * the context-menu Delete flow (Phase 1.6 Q5): empty default-state blocks
 * delete without confirm; non-empty blocks open the confirmation modal so
 * the operator can't lose meaningful work to an accidental click.
 *
 * Unknown block types fall back to "non-empty" — safer to confirm than to
 * silently nuke a registry-foreign block during transitional schema
 * states.
 */
export function isBlockEmpty(block: Block): boolean {
  const reg = BREG[block.type];
  if (!reg) return false;
  const defaults = reg.dp ?? {};
  const propKeys = Object.keys(block.props ?? {});

  // Any prop key present on the block but missing from defaults is
  // considered meaningful — empty check fails. Guards against blocks
  // that carry custom annotations / overrides which would otherwise
  // vanish without a confirm dialog.
  for (const key of propKeys) {
    if (!Object.prototype.hasOwnProperty.call(defaults, key)) return false;
  }

  for (const key of Object.keys(defaults)) {
    if (!deepEqual(block.props[key], defaults[key])) return false;
  }
  return true;
}
