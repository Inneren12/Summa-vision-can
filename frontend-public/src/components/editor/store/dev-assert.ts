import type { EditorState } from '../types';
import { BREG } from '../registry/blocks';

/**
 * Development-only invariant checker for editor state.
 *
 * Defense-in-depth: even with the reducer permission gate (isActionAllowed)
 * and the import validator (validateImport), reducer cases can have subtle
 * bugs that corrupt state — wrong block.id assignment, missed reference,
 * stale undo entry, etc. This runs after every reducer step in dev so that
 * invariant violations surface immediately at the action that caused them,
 * not pages later when the UI tries to render the corrupted shape.
 *
 * No-op in production (early return).
 */
export function assertStateIntegrity(state: EditorState, actionType: string): void {
  if (process.env.NODE_ENV !== "development") return;

  const violations: string[] = [];
  const doc = state.doc;

  // Mode must be valid
  if (state.mode !== "template" && state.mode !== "design") {
    violations.push(`Invalid mode: ${state.mode}`);
  }

  // All section blockIds must resolve to blocks; no duplicate references
  const refIds = new Set<string>();
  for (const sec of doc.sections) {
    for (const bid of sec.blockIds) {
      if (!doc.blocks[bid]) {
        violations.push(`Section "${sec.id}" references missing block "${bid}"`);
      }
      if (refIds.has(bid)) {
        violations.push(`Block "${bid}" referenced multiple times`);
      }
      refIds.add(bid);
    }
  }

  // No orphan blocks; key/id sync; type known
  for (const bid of Object.keys(doc.blocks)) {
    if (!refIds.has(bid)) {
      violations.push(`Orphan block "${bid}"`);
    }
    const block = doc.blocks[bid];
    if (block.id !== bid) {
      violations.push(`Block key/id mismatch: key="${bid}", id="${block.id}"`);
    }
    if (!BREG[block.type]) {
      violations.push(`Unknown block type: ${block.type}`);
    }
  }

  // Undo stack bounded
  if (state.undoStack.length > 50) {
    violations.push(`Undo stack exceeded MAX_UNDO: ${state.undoStack.length}`);
  }

  if (violations.length > 0) {
    console.error(`[editor] State integrity violations after ${actionType}:`, violations);
  }
}
