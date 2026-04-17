import type { WorkflowState, TimestampProvider } from '../types';

// Re-export so workflow consumers (reducer, tests, future UI) can pull
// every workflow-related type from one module instead of split imports.
export type { WorkflowAction, WorkflowState, TimestampProvider } from '../types';

// ────────────────────────────────────────────────────────────────────
// Workflow state machine
//
// Single source of truth for legal review-lifecycle transitions.
// Consumed by the reducer's `checkWorkflowPermission` gate (PR 2a) and
// by the Review panel UI (PR 3) for "Available next state" rendering.
//
// Legal transitions:
//   draft     → in_review
//   in_review → approved | draft   (approve OR changes requested)
//   approved  → exported | draft   (export OR revoke approval)
//   exported  → published
//   published → ∅                  (terminal)
//
// `DUPLICATE_AS_DRAFT` is NOT a transition — it's a lifecycle action
// that produces a fresh document. `transitionTarget` returns null for
// it; the reducer handles it as a special case.
// ────────────────────────────────────────────────────────────────────

export const TRANSITIONS: Record<WorkflowState, readonly WorkflowState[]> = {
  draft:     ["in_review"],
  in_review: ["approved", "draft"],
  approved:  ["exported", "draft"],
  exported:  ["published"],
  published: [],
} as const;

export function canTransition(from: WorkflowState, to: WorkflowState): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false;
}

export function availableTransitions(from: WorkflowState): readonly WorkflowState[] {
  return TRANSITIONS[from] ?? [];
}

/**
 * Workflow action discriminator strings. Exported as a constant so the
 * reducer's switch can be exhaustively type-checked and so tests can
 * iterate over every action shape.
 */
export const WORKFLOW_ACTION_TYPES = [
  "SUBMIT_FOR_REVIEW",
  "APPROVE",
  "REQUEST_CHANGES",
  "RETURN_TO_DRAFT",
  "MARK_EXPORTED",
  "MARK_PUBLISHED",
  "DUPLICATE_AS_DRAFT",
] as const;

export type WorkflowActionType = typeof WORKFLOW_ACTION_TYPES[number];

/**
 * Maps a workflow action to its target workflow state. Pure — does not
 * touch any document state. `null` for `DUPLICATE_AS_DRAFT` because that
 * action produces a brand-new document instead of transitioning the
 * existing one.
 */
export function transitionTarget(actionType: WorkflowActionType): WorkflowState | null {
  switch (actionType) {
    case "SUBMIT_FOR_REVIEW":  return "in_review";
    case "APPROVE":            return "approved";
    case "REQUEST_CHANGES":    return "draft";
    case "RETURN_TO_DRAFT":    return "draft";
    case "MARK_EXPORTED":      return "exported";
    case "MARK_PUBLISHED":     return "published";
    case "DUPLICATE_AS_DRAFT": return null;
  }
}

// ────────────────────────────────────────────────────────────────────
// Deterministic timestamp injection
//
// Reducers must be pure for snapshot testing and audit replay. Stage 3
// PR 1 already learned this lesson the hard way in the migration path
// (`deriveMigrationTimestamp` in registry/guards.ts). We carry the same
// discipline through to workflow transitions.
// ────────────────────────────────────────────────────────────────────

export const systemTimestampProvider: TimestampProvider = {
  now: () => new Date().toISOString(),
};

/**
 * Read-only states cannot be edited. Workflow transitions into one of
 * these clear undo/redo stacks because a subsequent undo would silently
 * flip approval/export status.
 */
export const READ_ONLY_WORKFLOW_STATES: ReadonlySet<WorkflowState> = new Set<WorkflowState>([
  "approved",
  "exported",
  "published",
]);

export function isReadOnlyWorkflow(state: WorkflowState): boolean {
  return READ_ONLY_WORKFLOW_STATES.has(state);
}
