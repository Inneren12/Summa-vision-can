import type { PermissionSet, BlockRegistryEntry, EditorMode, WorkflowState } from '../types';

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

// Exported so the workflow gate (`checkWorkflowPermission`) and any
// future per-key categorization helpers can reach the same source of
// truth as the mode gate.
export const TEXT_CONTENT_KEYS: readonly string[] = [
  "text", "value", "methodology", "label",
  "benchmarkValue", "benchmarkLabel", "yUnit",
] as const;

export const DATA_CONTENT_KEYS: readonly string[] = [
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
      return TEXT_CONTENT_KEYS.includes(key) || DATA_CONTENT_KEYS.includes(key);
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

// ────────────────────────────────────────────────────────────────────
// Workflow permission axis (Stage 3 PR 2a)
//
// This dimension is ORTHOGONAL to the mode gate above. The reducer's
// `isActionAllowed` runs both checks; an action must pass both to mutate
// the document.
//
// Workflow gate captures editorial lifecycle: in `draft` everything is
// allowed; in `in_review` only copy edits land; `approved`/`exported`/
// `published` are read-only beyond navigation. The mode gate (template
// vs design) is unchanged.
// ────────────────────────────────────────────────────────────────────

export type PropCategory = "text" | "data" | "structural" | "style" | "unknown";

/**
 * Classify a block-prop key by editorial category. Used by the workflow
 * gate to decide whether an `UPDATE_PROP` is a copy edit (allowed in
 * `in_review`) or a structural/style/data change (not allowed). Unknown
 * keys are returned as `"unknown"` and treated conservatively by the
 * gate (allowed in `draft` only).
 */
export function classifyKey(key: string): PropCategory {
  if (TEXT_CONTENT_KEYS.includes(key)) return "text";
  if (DATA_CONTENT_KEYS.includes(key)) return "data";
  if ((STRUCTURAL_KEYS as readonly string[]).includes(key)) return "structural";
  if ((STYLE_KEYS as readonly string[]).includes(key)) return "style";
  return "unknown";
}

export interface WorkflowPermission {
  textContent: boolean;
  dataContent: boolean;
  structural: boolean;
  style: boolean;
  importUndoRedo: boolean;
  // SELECT, SET_MODE, SAVED are always allowed and not represented here.
}

/**
 * Workflow permission matrix. Each row is the set of action categories
 * permitted while the document is in that workflow state.
 *
 *   draft     — fully editable
 *   in_review — copy edits only (text); import/undo/redo for safety
 *   approved  — read-only export-ready snapshot
 *   exported  — read-only PNG-emitted snapshot
 *   published — read-only terminal state
 */
export const WORKFLOW_PERMISSIONS: Record<WorkflowState, WorkflowPermission> = {
  draft: {
    textContent: true, dataContent: true, structural: true, style: true,
    importUndoRedo: true,
  },
  in_review: {
    textContent: true, dataContent: false, structural: false, style: false,
    importUndoRedo: true,
  },
  approved: {
    textContent: false, dataContent: false, structural: false, style: false,
    importUndoRedo: false,
  },
  exported: {
    textContent: false, dataContent: false, structural: false, style: false,
    importUndoRedo: false,
  },
  published: {
    textContent: false, dataContent: false, structural: false, style: false,
    importUndoRedo: false,
  },
};

const READ_ONLY_REASON = "Document is read-only in current workflow state";
const COPY_EDIT_ONLY_REASON =
  "Only copy edits allowed during review — return to draft first";

/**
 * Workflow-axis permission check. Mirrors `checkModePermission`'s
 * shape but ignores `state.mode` entirely — the two axes are orthogonal.
 *
 * Workflow transitions themselves (SUBMIT_FOR_REVIEW, APPROVE, ...) are
 * not gated here; the reducer enforces transition legality via
 * `canTransition` from `store/workflow.ts`. This function only gates
 * document-mutating actions.
 */
export function checkWorkflowPermission(
  workflow: WorkflowState,
  action: { type: string; key?: string; data?: Record<string, unknown> },
): { allowed: boolean; reason?: string } {
  const wp = WORKFLOW_PERMISSIONS[workflow];
  if (!wp) return { allowed: false, reason: `Unknown workflow state: ${workflow}` };

  switch (action.type) {
    // Copy-edit-aware actions: classify by prop key.
    case "UPDATE_PROP": {
      const cat = classifyKey(action.key ?? "");
      // In draft everything (including unknown keys) passes — keeps the
      // gate from blocking custom registry props the team adds later.
      if (workflow === "draft") return { allowed: true };
      if (cat === "text"       && wp.textContent)  return { allowed: true };
      if (cat === "data"       && wp.dataContent)  return { allowed: true };
      if (cat === "structural" && wp.structural)   return { allowed: true };
      if (cat === "style"      && wp.style)        return { allowed: true };
      // Unknown key in a non-draft workflow: deny (no silent bypass).
      if (workflow === "in_review") {
        return { allowed: false, reason: COPY_EDIT_ONLY_REASON };
      }
      return { allowed: false, reason: READ_ONLY_REASON };
    }
    case "UPDATE_DATA": {
      // UPDATE_DATA may carry several keys — every key must pass the
      // workflow gate for the action to be allowed.
      if (workflow === "draft") return { allowed: true };
      const keys = Object.keys(action.data ?? {});
      for (const k of keys) {
        const cat = classifyKey(k);
        const ok =
          (cat === "text"       && wp.textContent)  ||
          (cat === "data"       && wp.dataContent)  ||
          (cat === "structural" && wp.structural)   ||
          (cat === "style"      && wp.style);
        if (!ok) {
          if (workflow === "in_review") {
            return { allowed: false, reason: COPY_EDIT_ONLY_REASON };
          }
          return { allowed: false, reason: READ_ONLY_REASON };
        }
      }
      return { allowed: true };
    }

    case "TOGGLE_VIS":
      // Toggling block visibility is a structural change.
      return wp.structural
        ? { allowed: true }
        : { allowed: false, reason:
            workflow === "in_review" ? COPY_EDIT_ONLY_REASON : READ_ONLY_REASON };

    case "CHANGE_PAGE":
      return wp.style
        ? { allowed: true }
        : { allowed: false, reason:
            workflow === "in_review" ? COPY_EDIT_ONLY_REASON : READ_ONLY_REASON };

    case "SWITCH_TPL":
      return wp.style
        ? { allowed: true }
        : { allowed: false, reason:
            workflow === "in_review" ? COPY_EDIT_ONLY_REASON : READ_ONLY_REASON };

    case "IMPORT":
    case "UNDO":
    case "REDO":
      return wp.importUndoRedo
        ? { allowed: true }
        : { allowed: false, reason: READ_ONLY_REASON };

    // Always-allowed channels: navigation, mode-toggle, save-flag.
    case "SELECT":
    case "SET_MODE":
    case "SAVED":
      return { allowed: true };

    // Workflow transitions are validated by `canTransition` in the reducer,
    // not by this matrix.
    case "SUBMIT_FOR_REVIEW":
    case "APPROVE":
    case "REQUEST_CHANGES":
    case "RETURN_TO_DRAFT":
    case "MARK_EXPORTED":
    case "MARK_PUBLISHED":
    case "DUPLICATE_AS_DRAFT":
      return { allowed: true };

    default:
      return { allowed: false, reason: `Unknown action type: ${action.type}` };
  }
}
