import type { EditorState, EditorAction, CanonicalDocument } from '../types';
import { BREG } from '../registry/blocks';
import { TPLS, mkDoc } from '../registry/templates';
import { validateImport } from '../registry/guards';
import { PERMS } from './permissions';
import { assertStateIntegrity } from './dev-assert';
import { assertDocumentIntegrity } from '../validation/invariants';

export const MAX_UNDO = 50;

/**
 * Defense-in-depth permission gate. Runs BEFORE every reducer mutation.
 *
 * UI components already disable buttons and hide editors based on the same
 * PERMS table, but UI gating alone is insufficient — keyboard shortcuts,
 * a future command palette, devtools, tests, or bulk-import flows can
 * dispatch actions directly. The reducer is the only place all dispatches
 * funnel through, so policy enforcement here guarantees the invariant.
 *
 * Returns { allowed: false, reason } for blocked actions; the caller
 * (reducer) treats this as a no-op and logs the reason in dev.
 */
function isActionAllowed(state: EditorState, action: EditorAction): { allowed: boolean; reason?: string } {
  const perms = PERMS[state.mode];
  if (!perms) return { allowed: false, reason: `Unknown mode: ${state.mode}` };

  switch (action.type) {
    case "UPDATE_PROP": {
      const block = state.doc.blocks[action.blockId];
      if (!block) return { allowed: false, reason: `Block ${action.blockId} not found` };
      const reg = BREG[block.type];
      if (!reg) return { allowed: false, reason: `Unknown block type: ${block.type}` };
      if (!perms.editBlock(reg, action.key)) {
        return { allowed: false, reason: `Cannot edit "${action.key}" on ${reg.name} in ${state.mode} mode` };
      }
      return { allowed: true };
    }

    case "UPDATE_DATA": {
      const block = state.doc.blocks[action.blockId];
      if (!block) return { allowed: false, reason: `Block ${action.blockId} not found` };
      const reg = BREG[block.type];
      if (!reg) return { allowed: false, reason: `Unknown block type: ${block.type}` };
      // UPDATE_DATA can carry multiple structural keys — every key must pass
      for (const key of Object.keys(action.data)) {
        if (!perms.editBlock(reg, key)) {
          return { allowed: false, reason: `Cannot edit data key "${key}" on ${reg.name} in ${state.mode} mode` };
        }
      }
      return { allowed: true };
    }

    case "TOGGLE_VIS": {
      const block = state.doc.blocks[action.blockId];
      if (!block) return { allowed: false, reason: `Block ${action.blockId} not found` };
      const reg = BREG[block.type];
      if (!reg) return { allowed: false, reason: `Unknown block type: ${block.type}` };
      if (!perms.toggleVisibility(reg)) {
        return { allowed: false, reason: `Cannot toggle visibility of ${reg.name} in ${state.mode} mode` };
      }
      return { allowed: true };
    }

    case "CHANGE_PAGE": {
      if (action.key === "palette" && !perms.changePalette) {
        return { allowed: false, reason: `Cannot change palette in ${state.mode} mode` };
      }
      if (action.key === "background" && !perms.changeBackground) {
        return { allowed: false, reason: `Cannot change background in ${state.mode} mode` };
      }
      if (action.key === "size" && !perms.changeSize) {
        return { allowed: false, reason: `Cannot change size in ${state.mode} mode` };
      }
      return { allowed: true };
    }

    case "SWITCH_TPL": {
      if (!perms.switchTemplate) {
        return { allowed: false, reason: `Cannot switch template in ${state.mode} mode` };
      }
      return { allowed: true };
    }

    case "IMPORT":
    case "UNDO":
    case "REDO":
    case "SELECT":
    case "SAVED":
    case "SET_MODE":
      // Always allowed:
      //   SELECT, SET_MODE — non-mutating UI state
      //   IMPORT — validated separately inside the reducer body (defense in depth)
      //   UNDO/REDO — operate on existing trusted history snapshots
      //   SAVED — flag flip
      return { allowed: true };

    default:
      return { allowed: false, reason: "Unknown action type" };
  }
}

export function reducer(state: EditorState, action: EditorAction): EditorState {
  // Permission gate — runs before any mutation
  const check = isActionAllowed(state, action);
  if (!check.allowed) {
    if (process.env.NODE_ENV === "development") {
      console.warn(`[editor] Action blocked: ${action.type} \u2014 ${check.reason}`);
    }
    return state; // no-op
  }

  const push = (newDoc: CanonicalDocument, summary = ""): EditorState => {
    const nv = (state.doc.meta.version || 0) + 1;
    const now = new Date().toISOString();
    const hist = [...(state.doc.meta.history || []).slice(-9), { version: state.doc.meta.version, savedAt: now, summary: summary || action.type }];

    const isBatchable = action.type === "UPDATE_PROP"
      && state._lastAction?.type === "UPDATE_PROP"
      && state._lastAction?.blockId === action.blockId
      && state._lastAction?.key === action.key
      && (Date.now() - state._lastAction.at) < 800;

    const undoStack = isBatchable
      ? state.undoStack
      : [...state.undoStack, state.doc].slice(-MAX_UNDO);

    return {
      ...state,
      doc: { ...newDoc, meta: { ...newDoc.meta, updatedAt: now, version: nv, history: hist } },
      undoStack,
      redoStack: [],
      dirty: true,
      // Keep action fingerprint for keystroke burst batching.
      _lastAction: {
        type: action.type,
        blockId: action.type === "UPDATE_PROP" ? action.blockId : undefined,
        key: action.type === "UPDATE_PROP" ? action.key : undefined,
        at: Date.now(),
      },
    };
  };

  let nextState: EditorState = state;

  switch (action.type) {
    case "UPDATE_PROP": {
      const { blockId, key, value } = action;
      const b = state.doc.blocks[blockId];
      if (!b) { nextState = state; break; }
      nextState = push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, props: { ...b.props, [key]: value } } } }, `Updated ${BREG[b.type]?.name || b.type}.${key}`);
      break;
    }
    case "UPDATE_DATA": {
      const { blockId, data } = action;
      const b = state.doc.blocks[blockId];
      if (!b) { nextState = state; break; }
      nextState = push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, props: { ...b.props, ...data } } } }, `Updated ${BREG[b.type]?.name} data`);
      break;
    }
    case "TOGGLE_VIS": {
      const { blockId } = action;
      const b = state.doc.blocks[blockId];
      if (!b) { nextState = state; break; }
      const r = BREG[b.type];
      // The permission gate (toggleVisibility) already filters required_*; this
      // is a structural belt-and-suspenders against a registry without a status.
      if (r.status === "required_locked" || r.status === "required_editable") { nextState = state; break; }
      nextState = push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, visible: !b.visible } } }, `${b.visible ? "Hid" : "Showed"} ${r?.name}`);
      break;
    }
    case "CHANGE_PAGE": {
      const { key, value } = action;
      nextState = push({ ...state.doc, page: { ...state.doc.page, [key]: value } }, `Changed ${key} to ${value}`);
      break;
    }
    case "SWITCH_TPL": {
      const { tid } = action;
      const t = TPLS[tid];
      if (!t) { nextState = state; break; }
      nextState = {
        ...state,
        doc: mkDoc(tid, t, t.overrides),
        undoStack: [...state.undoStack, state.doc].slice(-MAX_UNDO),
        // Structural template change invalidates redo chain.
        redoStack: [],
        selectedBlockId: null,
        dirty: true,
        _lastAction: undefined,
      };
      break;
    }
    case "IMPORT": {
      // Defense in depth: the index.tsx import handler already runs
      // hydrateImportedDoc + validateImport, but the reducer cannot trust
      // every dispatcher (tests, devtools, future automation).
      const err = validateImport(action.doc);
      if (err) {
        if (process.env.NODE_ENV === "development") {
          console.error(`[editor] IMPORT rejected by reducer: ${err}`);
        }
        nextState = state;
        break;
      }
      nextState = { ...state, doc: action.doc, undoStack: [], redoStack: [], selectedBlockId: null, dirty: false, _lastAction: undefined };
      break;
    }
    case "UNDO": {
      if (!state.undoStack.length) { nextState = state; break; }
      const prev = state.undoStack[state.undoStack.length - 1];
      // Skip invalid snapshots so undo cannot restore broken block references.
      const valid = prev.sections.every(sec => sec.blockIds.every(bid => prev.blocks[bid] !== undefined));
      if (!valid) {
        nextState = { ...state, undoStack: state.undoStack.slice(0, -1), _lastAction: undefined };
        break;
      }
      nextState = {
        ...state,
        doc: prev,
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, state.doc].slice(-MAX_UNDO),
        dirty: true,
        _lastAction: undefined,
      };
      break;
    }
    case "REDO": {
      if (!state.redoStack.length) { nextState = state; break; }
      nextState = {
        ...state,
        doc: state.redoStack[state.redoStack.length - 1],
        undoStack: [...state.undoStack, state.doc].slice(-MAX_UNDO),
        redoStack: state.redoStack.slice(0, -1),
        dirty: true,
        _lastAction: undefined,
      };
      break;
    }
    case "SELECT":
      nextState = { ...state, selectedBlockId: action.blockId };
      break;
    case "SAVED":
      nextState = { ...state, dirty: false };
      break;
    case "SET_MODE":
      nextState = { ...state, mode: action.mode };
      break;
    default:
      nextState = state;
  }

  if (process.env.NODE_ENV === "development" && nextState !== state) {
    const violations = assertDocumentIntegrity(nextState.doc);
    const errors = violations.filter(v => v.severity === "error");
    if (errors.length > 0) {
      console.error(
        `[editor] Document integrity violations after ${action.type}:`,
        errors.map(v => `${v.code}: ${v.message}`),
      );
    }
  }

  // Dev-only: verify state integrity after mutation
  assertStateIntegrity(nextState, action.type);

  return nextState;
}

export function initState(): EditorState {
  return {
    doc: mkDoc("single_stat_hero", TPLS.single_stat_hero),
    undoStack: [],
    redoStack: [],
    selectedBlockId: null,
    dirty: false,
    _lastAction: undefined,
    mode: "design",
  };
}
