import type { EditorState, EditorAction, CanonicalDocument } from '../types';
import { BREG } from '../registry/blocks';
import { TPLS, mkDoc } from '../registry/templates';
import { validateImport, migrateDoc } from '../registry/guards';

export const MAX_UNDO = 50;

export function reducer(state: EditorState, action: EditorAction): EditorState {
  const push = (newDoc: CanonicalDocument, summary = ""): EditorState => {
    const nv = (state.doc.meta.version || 0) + 1;
    const now = new Date().toISOString();
    const hist = [...(state.doc.meta.history || []).slice(-9), { version: state.doc.meta.version, savedAt: now, summary: summary || action.type }];
    return { ...state, doc: { ...newDoc, meta: { ...newDoc.meta, updatedAt: now, version: nv, history: hist } }, undoStack: [...state.undoStack, state.doc].slice(-MAX_UNDO), redoStack: [], dirty: true };
  };
  switch (action.type) {
    case "UPDATE_PROP": {
      const { blockId, key, value } = action;
      const b = state.doc.blocks[blockId];
      if (!b) return state;
      return push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, props: { ...b.props, [key]: value } } } }, `Updated ${BREG[b.type]?.name || b.type}.${key}`);
    }
    case "UPDATE_DATA": {
      const { blockId, data } = action;
      const b = state.doc.blocks[blockId];
      if (!b) return state;
      return push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, props: { ...b.props, ...data } } } }, `Updated ${BREG[b.type]?.name} data`);
    }
    case "TOGGLE_VIS": {
      const { blockId } = action;
      const b = state.doc.blocks[blockId];
      if (!b) return state;
      const r = BREG[b.type];
      if (r.status === "required_locked" || r.status === "required_editable") return state;
      return push({ ...state.doc, blocks: { ...state.doc.blocks, [blockId]: { ...b, visible: !b.visible } } }, `${b.visible ? "Hid" : "Showed"} ${r?.name}`);
    }
    case "CHANGE_PAGE": {
      const { key, value } = action;
      return push({ ...state.doc, page: { ...state.doc.page, [key]: value } }, `Changed ${key} to ${value}`);
    }
    case "SWITCH_TPL": {
      const { tid } = action;
      const t = TPLS[tid];
      if (!t) return state;
      return { ...state, doc: mkDoc(tid, t, t.overrides), undoStack: [...state.undoStack, state.doc].slice(-MAX_UNDO), redoStack: [], selectedBlockId: null, dirty: true };
    }
    case "IMPORT": {
      const err = validateImport(action.doc);
      if (err) { console.error("Import validation:", err); return state; }
      return { ...state, doc: migrateDoc(action.doc), undoStack: [], redoStack: [], selectedBlockId: null, dirty: false };
    }
    case "UNDO": {
      if (!state.undoStack.length) return state;
      return { ...state, doc: state.undoStack[state.undoStack.length - 1], undoStack: state.undoStack.slice(0, -1), redoStack: [...state.redoStack, state.doc], dirty: true };
    }
    case "REDO": {
      if (!state.redoStack.length) return state;
      return { ...state, doc: state.redoStack[state.redoStack.length - 1], undoStack: [...state.undoStack, state.doc], redoStack: state.redoStack.slice(0, -1), dirty: true };
    }
    case "SELECT":
      return { ...state, selectedBlockId: action.blockId };
    case "SAVED":
      return { ...state, dirty: false };
    default:
      return state;
  }
}

export function initState(): EditorState {
  return { doc: mkDoc("single_stat_hero", TPLS.single_stat_hero), undoStack: [], redoStack: [], selectedBlockId: null, dirty: false };
}
