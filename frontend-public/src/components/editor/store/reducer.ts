import type { EditorState, EditorAction, CanonicalDocument, WorkflowAction, WorkflowHistoryEntry, TimestampProvider } from '../types';
import { BREG } from '../registry/blocks';
import { TPLS, mkDoc } from '../registry/templates';
import { validateImportStrict } from '../registry/guards';
import { PERMS, checkWorkflowPermission } from './permissions';
import { assertStateIntegrity } from './dev-assert';
import { assertDocumentIntegrity } from '../validation/invariants';
import {
  WORKFLOW_ACTION_TYPES,
  canTransition,
  isReadOnlyWorkflow,
  systemTimestampProvider,
  transitionTarget,
  type WorkflowActionType,
} from './workflow';
import {
  applyAddComment,
  applyDeleteComment,
  applyEditComment,
  applyReopenComment,
  applyReplyToComment,
  applyResolveComment,
} from './comments';

export const MAX_UNDO = 50;

function isWorkflowAction(action: EditorAction): action is WorkflowAction {
  return (WORKFLOW_ACTION_TYPES as readonly string[]).includes(action.type);
}

/**
 * Mode-axis permission gate. Renamed from the original `isActionAllowed`
 * body in PR 2a; the new top-level `isActionAllowed` runs both this and
 * `checkWorkflowPermission` (orthogonal axes — both must pass).
 *
 * UI components already disable buttons and hide editors based on the same
 * PERMS table, but UI gating alone is insufficient — keyboard shortcuts,
 * a future command palette, devtools, tests, or bulk-import flows can
 * dispatch actions directly. The reducer is the only place all dispatches
 * funnel through, so policy enforcement here guarantees the invariant.
 */
function checkModePermission(state: EditorState, action: EditorAction): { allowed: boolean; reason?: string } {
  // Workflow actions don't have a mode-axis gate. They are gated by
  // workflow legality (`canTransition`) inside the reducer body.
  if (isWorkflowAction(action)) return { allowed: true };

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
    case "SAVED_IF_MATCHES":
    case "SAVE_FAILED":
    case "DISMISS_SAVE_ERROR":
    case "RETRY_RESET":
    case "RETRY_ATTEMPT_ADVANCE":
    case "SET_MODE":
      // Always allowed:
      //   SELECT, SET_MODE — non-mutating UI state
      //   IMPORT — validated separately inside the reducer body (defense in depth)
      //   UNDO/REDO — operate on existing trusted history snapshots
      //   SAVED_IF_MATCHES / SAVE_FAILED / DISMISS_SAVE_ERROR /
      //     RETRY_RESET / RETRY_ATTEMPT_ADVANCE — save-channel bookkeeping
      return { allowed: true };

    case "ADD_COMMENT":
    case "REPLY_TO_COMMENT":
    case "EDIT_COMMENT":
    case "RESOLVE_COMMENT":
    case "REOPEN_COMMENT":
    case "DELETE_COMMENT":
      // Commenting is not gated by editor mode — a template-mode reviewer
      // needs the same annotation surface as a design-mode editor.
      return { allowed: true };

    default:
      return { allowed: false, reason: "Unknown action type" };
  }
}

/**
 * Orthogonal two-axis permission gate. Mode and workflow are checked
 * independently; an action must pass both to mutate the document.
 *
 * Mode axis (template vs design) was the only gate before PR 2a.
 * Workflow axis (draft / in_review / approved / exported / published)
 * was added in PR 2a — see `checkWorkflowPermission`.
 */
function isActionAllowed(state: EditorState, action: EditorAction): { allowed: boolean; reason?: string } {
  const modeCheck = checkModePermission(state, action);
  if (!modeCheck.allowed) return modeCheck;

  const wfCheck = checkWorkflowPermission(state.doc.review.workflow, action);
  if (!wfCheck.allowed) return wfCheck;

  return { allowed: true };
}

export function getProvider(state: EditorState): TimestampProvider {
  return state._timestampProvider ?? systemTimestampProvider;
}

function resolveTimestamp(state: EditorState, action: WorkflowAction): string {
  return action.ts ?? getProvider(state).now();
}

/**
 * Default actor fallback for audit-log entries. Shared by the workflow and
 * comment reducer paths so every history entry produced by dispatched actions
 * carries a consistent author string when the caller omits `actor`.
 */
export function resolveActor(action: { actor?: string }): string {
  return action.actor ?? "you";
}

function workflowSummary(action: WorkflowAction, fromWorkflow: string): string {
  switch (action.type) {
    case "SUBMIT_FOR_REVIEW":  return "Submitted for review";
    case "APPROVE":            return "Approved for export";
    case "REQUEST_CHANGES":
      return action.note
        ? `Changes requested: ${action.note}`
        : "Changes requested; returned to draft";
    case "RETURN_TO_DRAFT":
      return action.note
        ? `Returned to draft: ${action.note}`
        : "Approval revoked; returned to draft";
    case "MARK_EXPORTED":      return `Exported as ${action.filename}`;
    case "MARK_PUBLISHED":     return `Published to ${action.channel}`;
    case "DUPLICATE_AS_DRAFT": return `Duplicated from ${fromWorkflow} document`;
  }
}

function workflowHistoryAction(actionType: WorkflowActionType): string {
  switch (actionType) {
    case "SUBMIT_FOR_REVIEW":  return "submitted";
    case "APPROVE":            return "approved";
    case "REQUEST_CHANGES":    return "changes_requested";
    case "RETURN_TO_DRAFT":    return "returned_to_draft";
    case "MARK_EXPORTED":      return "exported";
    case "MARK_PUBLISHED":     return "published";
    case "DUPLICATE_AS_DRAFT": return "duplicated";
  }
}

export function withRejection(state: EditorState, actionType: string, reason: string): EditorState {
  if (process.env.NODE_ENV === "development") {
    console.warn(`[editor] Action blocked: ${actionType} \u2014 ${reason}`);
  }
  return { ...state, _lastRejection: { type: actionType, reason, at: Date.now() } };
}

export function reducer(state: EditorState, action: EditorAction): EditorState {
  // Permission gate — runs before any mutation. Failures land in
  // `_lastRejection`; `_lastAction` (burst-batching fingerprint) is
  // intentionally untouched on rejection.
  const check = isActionAllowed(state, action);
  if (!check.allowed) {
    return withRejection(state, action.type, check.reason ?? "Unknown reason");
  }

  const push = (newDoc: CanonicalDocument, summary = ""): EditorState => {
    const nv = (state.doc.meta.version || 0) + 1;
    // Edit-snapshot timestamp flows through the injected provider so tests
    // can assert deterministic `meta.updatedAt` / `history[].savedAt` values.
    // The push helper is the only place an edit snapshot is written.
    const now = getProvider(state).now();
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
      _lastRejection: undefined,
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
        _lastRejection: undefined,
      };
      break;
    }
    case "IMPORT": {
      // DEBT-022 closure: reducer now uses the throwing strict validator.
      // Defense in depth: index.tsx already runs hydrateImportedDoc +
      // validateImportStrict, but the reducer cannot trust every dispatcher
      // (tests, devtools, future automation), so it re-validates here.
      try {
        const validated = validateImportStrict(action.doc);
        nextState = {
          ...state,
          doc: validated,
          undoStack: [],
          redoStack: [],
          selectedBlockId: null,
          dirty: false,
          _lastAction: undefined,
          _lastRejection: undefined,
        };
      } catch (err) {
        const reason = err instanceof Error ? err.message : "Import validation failed";
        if (process.env.NODE_ENV === "development") {
          console.error(`[editor] IMPORT rejected: ${reason}`);
        }
        // Route through withRejection so UI can read a uniform signal.
        nextState = withRejection(state, action.type, reason);
      }
      break;
    }
    case "UNDO": {
      if (!state.undoStack.length) { nextState = state; break; }
      const prev = state.undoStack[state.undoStack.length - 1];
      // Skip invalid snapshots so undo cannot restore broken block references.
      const valid = prev.sections.every(sec => sec.blockIds.every(bid => prev.blocks[bid] !== undefined));
      if (!valid) {
        nextState = { ...state, undoStack: state.undoStack.slice(0, -1), _lastAction: undefined, _lastRejection: undefined };
        break;
      }
      // Overlay the live `review` section onto the restored snapshot.
      // Content edits are rewound; comments, workflow, and audit history
      // live on an independent timeline (see docs/modules/editor.md
      // "Undo/redo overlay policy") and must survive UNDO.
      const undoTs = getProvider(state).now();
      const restored: CanonicalDocument = {
        ...prev,
        review: {
          workflow: state.doc.review.workflow,
          history: state.doc.review.history,
          comments: state.doc.review.comments,
        },
        meta: {
          ...prev.meta,
          // UNDO is itself a mutation event; advance updatedAt to now rather
          // than reusing the snapshot's original timestamp.
          updatedAt: undoTs,
        },
      };
      nextState = {
        ...state,
        doc: restored,
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, state.doc].slice(-MAX_UNDO),
        dirty: true,
        _lastAction: undefined,
        _lastRejection: undefined,
      };
      break;
    }
    case "REDO": {
      if (!state.redoStack.length) { nextState = state; break; }
      const next = state.redoStack[state.redoStack.length - 1];
      // Same overlay policy as UNDO — comments and audit trail must
      // survive a redo of an edit that was itself rewound earlier.
      const redoTs = getProvider(state).now();
      const restored: CanonicalDocument = {
        ...next,
        review: {
          workflow: state.doc.review.workflow,
          history: state.doc.review.history,
          comments: state.doc.review.comments,
        },
        meta: {
          ...next.meta,
          updatedAt: redoTs,
        },
      };
      nextState = {
        ...state,
        doc: restored,
        undoStack: [...state.undoStack, state.doc].slice(-MAX_UNDO),
        redoStack: state.redoStack.slice(0, -1),
        dirty: true,
        _lastAction: undefined,
        _lastRejection: undefined,
      };
      break;
    }
    case "SELECT":
      nextState = { ...state, selectedBlockId: action.blockId, _lastRejection: undefined };
      break;
    case "SAVED_IF_MATCHES": {
      // B2 fix: clear `dirty` only when the current doc is the exact
      // reference we snapshotted at save start. Reference equality is
      // sufficient because the reducer treats `doc` as immutable — every
      // edit produces a new doc object. If the user typed during the
      // in-flight PATCH, the snapshot's unsaved edits never reached the
      // backend, so keeping `dirty: true` is correct.
      //
      // DEBT-027: a successful save also resets the retry budget so the
      // next failure starts from delay[0]. This previously lived in the
      // retry-orchestration effect, which observed `saveError` flipping
      // to null.
      const cleared = { saveError: null, retryAttempt: 0, _lastRejection: undefined };
      if (state.doc === action.snapshotDoc) {
        nextState = { ...state, dirty: false, ...cleared };
      } else {
        // Save itself succeeded, so clear any prior save error; but
        // `dirty` stays set because the server is now behind the UI.
        nextState = { ...state, ...cleared };
      }
      break;
    }
    case "SAVE_FAILED":
      // DEBT-027: capture `canAutoRetry` here so the retry orchestration
      // effect can read it from state instead of from a ref.
      // `canAutoRetry: false` is the terminal (404) classification;
      // transient failures pass `true`. `retryAttempt` is intentionally
      // NOT incremented here — it advances when the retry timer fires
      // (RETRY_ATTEMPT_ADVANCE), matching the historical `attempt + 1`
      // write performed inside the timer callback pre-DEBT-027.
      // Incrementing on SAVE_FAILED would shift the backoff schedule
      // so the first auto-retry waited RETRY_DELAYS_MS[1] instead of [0].
      nextState = {
        ...state,
        saveError: action.error,
        canAutoRetry: action.canAutoRetry,
        _lastRejection: undefined,
      };
      break;
    case "DISMISS_SAVE_ERROR":
      // DEBT-027: dismiss also resets the retry budget. The original
      // retry effect treated saveError → null as the reset trigger
      // regardless of whether the clear came from SAVED_IF_MATCHES or
      // DISMISS_SAVE_ERROR; preserve that. `canAutoRetry` is intentionally
      // left as-is — the dismiss-bypass guard (B5) relies on a 404's
      // `canAutoRetry: false` surviving until a new edit or manual retry.
      nextState = { ...state, saveError: null, retryAttempt: 0, _lastRejection: undefined };
      break;
    case "RETRY_RESET":
      // DEBT-027: manual "Retry now" path. Resets the budget AND re-arms
      // canAutoRetry so a previously-terminal error can be retried.
      nextState = { ...state, retryAttempt: 0, canAutoRetry: true, _lastRejection: undefined };
      break;
    case "RETRY_ATTEMPT_ADVANCE":
      // DEBT-027: replaces the historical `attempt + 1` write performed
      // inside the retry-orchestration timer callback pre-DEBT-027.
      nextState = { ...state, retryAttempt: state.retryAttempt + 1, _lastRejection: undefined };
      break;
    case "SET_MODE":
      nextState = { ...state, mode: action.mode, _lastRejection: undefined };
      break;
    case "SUBMIT_FOR_REVIEW":
    case "APPROVE":
    case "REQUEST_CHANGES":
    case "RETURN_TO_DRAFT":
    case "MARK_EXPORTED":
    case "MARK_PUBLISHED":
      nextState = applyWorkflowTransition(state, action);
      break;
    case "DUPLICATE_AS_DRAFT":
      nextState = applyDuplicateAsDraft(state, action);
      break;
    // Comment-lifecycle actions are OUTSIDE the undo/redo timeline.
    // Each applyXxx returns a new state with `doc.review.comments` (and
    // optionally `doc.review.history`) updated, `dirty: true`, and
    // `_lastRejection: undefined` — but never touches `undoStack`,
    // `redoStack`, or `_lastAction`.
    case "ADD_COMMENT":
      nextState = applyAddComment(state, action);
      break;
    case "REPLY_TO_COMMENT":
      nextState = applyReplyToComment(state, action);
      break;
    case "EDIT_COMMENT":
      nextState = applyEditComment(state, action);
      break;
    case "RESOLVE_COMMENT":
      nextState = applyResolveComment(state, action);
      break;
    case "REOPEN_COMMENT":
      nextState = applyReopenComment(state, action);
      break;
    case "DELETE_COMMENT":
      nextState = applyDeleteComment(state, action);
      break;
    default:
      nextState = state;
  }

  // DEBT-027 cross-cutting reset: a doc-mutating action while a save error
  // is active means the user edited during error state. Reset the retry
  // budget so the next attempt re-enters the backoff cycle at delay[0],
  // and re-arm `canAutoRetry` so a previously-terminal error can be
  // retried against the now-different document. The check uses the BEFORE
  // state's `saveError` because no doc-mutating reducer case touches it
  // (saveError is only set by SAVE_FAILED and cleared by SAVED_IF_MATCHES
  // / DISMISS_SAVE_ERROR / RETRY_RESET, none of which mutate `doc`).
  // Replaces the deleted `useEffect(..., [doc])` in index.tsx that used
  // an exhaustive-deps disable to skip `state.saveError` in its deps.
  if (state.saveError != null && nextState.doc !== state.doc) {
    nextState = { ...nextState, retryAttempt: 0, canAutoRetry: true };
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

function applyWorkflowTransition(state: EditorState, action: WorkflowAction): EditorState {
  const from = state.doc.review.workflow;
  const to = transitionTarget(action.type);
  if (to === null) {
    // Should not happen for the 6 transition actions — DUPLICATE_AS_DRAFT
    // is handled separately. Defensive guard for refactors.
    return withRejection(state, action.type, `Action ${action.type} has no transition target`);
  }
  if (!canTransition(from, to)) {
    return withRejection(state, action.type, `Illegal transition: ${from} \u2192 ${to}`);
  }

  const ts = resolveTimestamp(state, action);
  const author = resolveActor(action);
  const entry: WorkflowHistoryEntry = {
    ts,
    action: workflowHistoryAction(action.type as WorkflowActionType),
    summary: workflowSummary(action, from),
    author,
    fromWorkflow: from,
    toWorkflow: to,
  };

  const nextDoc: CanonicalDocument = {
    ...state.doc,
    meta: { ...state.doc.meta, updatedAt: ts },
    review: {
      ...state.doc.review,
      workflow: to,
      history: [...state.doc.review.history, entry],
    },
  };

  // Crossing into a read-only workflow clears undo/redo. Otherwise an
  // undo after APPROVE would silently revert approval state. Stacks are
  // deliberately PRESERVED across SUBMIT_FOR_REVIEW so REQUEST_CHANGES can
  // restore undo once the document is back in draft. UNDO/REDO are blocked
  // while the workflow itself is `in_review` via WORKFLOW_PERMISSIONS.
  const intoReadOnly = isReadOnlyWorkflow(to);

  return {
    ...state,
    doc: nextDoc,
    undoStack: intoReadOnly ? [] : state.undoStack,
    redoStack: intoReadOnly ? [] : state.redoStack,
    // Transitions mutate the document (review.workflow, review.history,
    // meta.updatedAt) — treat as unsaved content changes. Only SAVED or a
    // successful persistence round-trip should clear the dirty flag.
    dirty: true,
    _lastAction: undefined,
    _lastRejection: undefined,
  };
}

function applyDuplicateAsDraft(state: EditorState, action: WorkflowAction): EditorState {
  const from = state.doc.review.workflow;
  if (from !== "exported" && from !== "published") {
    return withRejection(
      state,
      action.type,
      `Duplicate is only allowed from exported or published (current: ${from})`,
    );
  }

  const ts = resolveTimestamp(state, action);
  const author = resolveActor(action);

  // Deep-clone the document so the duplicate cannot alias the original's
  // sections/blocks. JSON round-trip is safe here because CanonicalDocument
  // is data-only (no functions, dates, or non-JSON values).
  const cloned = JSON.parse(JSON.stringify({
    templateId: state.doc.templateId,
    page: state.doc.page,
    sections: state.doc.sections,
    blocks: state.doc.blocks,
  })) as Pick<CanonicalDocument, "templateId" | "page" | "sections" | "blocks">;

  const newDoc: CanonicalDocument = {
    schemaVersion: state.doc.schemaVersion,
    ...cloned,
    meta: {
      createdAt: ts,
      updatedAt: ts,
      version: 0,
      history: [],
    },
    review: {
      workflow: "draft",
      history: [
        {
          ts,
          action: "duplicated",
          summary: `Duplicated from ${from} document`,
          author,
          fromWorkflow: null,
          toWorkflow: "draft",
        },
      ],
      comments: [],
    },
  };

  return {
    ...state,
    doc: newDoc,
    undoStack: [],
    redoStack: [],
    selectedBlockId: null,
    // A duplicated document is unsaved by definition — the new identity
    // has not been persisted anywhere yet.
    dirty: true,
    _lastAction: undefined,
    _lastRejection: undefined,
  };
}

export function initState(initialDoc?: CanonicalDocument): EditorState {
  const seededDoc = initialDoc ?? mkDoc("single_stat_hero", TPLS.single_stat_hero);
  return {
    doc: seededDoc,
    undoStack: [],
    redoStack: [],
    selectedBlockId: null,
    dirty: false,
    saveError: null,
    retryAttempt: 0,
    canAutoRetry: true,
    _lastAction: undefined,
    _lastRejection: undefined,
    mode: "design",
    _timestampProvider: systemTimestampProvider,
  };
}
