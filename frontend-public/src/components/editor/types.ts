import type { ContrastIssue } from './validation/contrast';
import type { ValidationMessage } from './validation/types';

export type EditorMode = 'template' | 'design';
export type QAMode = 'draft' | 'publish';
export type LeftTab = 'templates' | 'blocks' | 'theme';
export type Direction = 'positive' | 'negative' | 'neutral';
export type BrandPosition = 'bottom-left' | 'bottom-right';
export type TextAlign = 'left' | 'center' | 'right';
export type PlatformId = 'reddit' | 'twitter' | 'linkedin';
export type WorkflowState = 'draft' | 'in_review' | 'approved' | 'exported' | 'published';
export type BlockStatus = 'required_locked' | 'required_editable' | 'optional_default' | 'optional_available';
export type BlockCategory = 'text' | 'data' | 'chart' | 'struct';
export type PageKey = 'size' | 'background' | 'palette';

// Autosave UI status (Stage 4 Task 2). Ephemeral — lives in component state,
// not reducer. `idle` means no scheduled or in-flight save; combined with
// `dirty=false` it means fully saved. `pending` means a debounce timer is
// armed. `saving` means a PATCH is in flight. `error` means the last attempt
// failed and the retry orchestration is active (or has exhausted its budget).
// `conflict` (Phase 1.3 polish) means the user dismissed a 412 modal without
// resolving — autosave is frozen until the next user edit re-arms `pending`,
// which then re-fires the PATCH and re-triggers the modal if the conflict is
// still real. Prevents the auto-loop where each tick re-412'd and re-opened.
export type SaveStatus = 'idle' | 'pending' | 'saving' | 'error' | 'conflict';

export interface BlockProps {
  [key: string]: any;
}

export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  // Phase 1.6: user-toggleable instance lock. When true, UPDATE_PROP /
  // UPDATE_DATA / TOGGLE_VIS are blocked; REMOVE_BLOCK and DUPLICATE_BLOCK
  // remain allowed (lock blocks editing/movement, not deletion).
  // Independent from registry-level `status: "required_locked"` which is
  // template-immutable and additionally blocks deletion.
  // Optional + undefined-coalesce-to-false for additive backward compat
  // (no schemaVersion bump in v1).
  locked?: boolean;
}

export interface Section {
  id: string;
  type: string;
  blockIds: string[];
}

export interface PageConfig {
  size: string;
  background: string;
  palette: string;
}

/**
 * Edit-history entry — one per save/snapshot. Populated by the reducer's
 * `push` helper as users edit blocks or page config.
 *
 * NOTE: semantically distinct from `WorkflowHistoryEntry`. Edit history
 * tracks undo/redo-style save snapshots; workflow history tracks review
 * lifecycle events (submit / approve / comment added). Do not merge them.
 */
export interface EditHistoryEntry {
  version: number;
  savedAt: string;
  summary: string;
}

/**
 * Workflow-history entry — one per workflow transition or review event.
 * Populated by the reducer (PR 2) and surfaced by the Review panel (PR 3).
 * In Stage 3 PR 1 only two actions are ever written: `"migrated"` (from the
 * v1 → v2 migration) and `"created"` (from `mkDoc`).
 */
export interface WorkflowHistoryEntry {
  ts: string;
  action: string;
  summary: string;
  author: string;
  fromWorkflow: WorkflowState | null;
  toWorkflow: WorkflowState | null;
}

export interface Comment {
  id: string;
  blockId: string;
  parentId: string | null;
  author: string;
  text: string;
  createdAt: string;
  updatedAt: string | null;
  resolved: boolean;
  resolvedAt: string | null;
  resolvedBy: string | null;
}

export interface Review {
  workflow: WorkflowState;
  history: WorkflowHistoryEntry[];
  comments: Comment[];
}

export interface DocMeta {
  createdAt: string;
  updatedAt: string;
  version: number;
  history: EditHistoryEntry[];
}

export interface CanonicalDocument {
  schemaVersion: number;
  templateId: string;
  page: PageConfig;
  sections: Section[];
  blocks: Record<string, Block>;
  meta: DocMeta;
  review: Review;
}

/**
 * Shape of documents written before Stage 3 PR 1. Exported strictly for the
 * migration signature in `registry/guards.ts`; application code should never
 * reference this type.
 */
export interface LegacyDocumentV1 {
  schemaVersion: 1;
  templateId: string;
  page: PageConfig;
  sections: Section[];
  blocks: Record<string, Block>;
  workflow: WorkflowState;
  meta: {
    createdAt: string;
    updatedAt: string;
    version: number;
    history: EditHistoryEntry[];
  };
}

export interface ControlDef {
  k: string;
  t: string;
  l: string;
  i18nKey?: string;
  labelKind?: 'label' | 'short_label';
  ml?: number;
  opts?: string[];
}

export interface BlockRegistryEntry {
  cat: BlockCategory;
  name: string;
  status: BlockStatus;
  allowedSections: string[];
  maxPerSection: number;
  dp: BlockProps;
  cst?: { maxChars?: number; maxLines?: number };
  ctrl: ControlDef[];
  guard?: (props: BlockProps) => boolean;
}

export interface ValidationResult {
  errors: ValidationMessage[];
  warnings: ValidationMessage[];
  info: ValidationMessage[];
  passed: ValidationMessage[];
  /**
   * Structured per-block contrast issues. String summaries are also
   * pushed to `errors` / `warnings` for QAPanel; this field preserves
   * blockId / ratio / threshold for Inspector per-block surfacing.
   */
  contrastIssues: ContrastIssue[];
}

export interface Palette {
  n: string;
  p: string;
  s: string;
  a: string;
  pos: string;
  neg: string;
}

export interface SizePreset {
  w: number;
  h: number;
  n: string;
}

export interface BackgroundEntry {
  n: string;
  r: (c: CanvasRenderingContext2D, w: number, h: number, p?: Palette) => void;
}

export interface TemplateSection {
  id: string;
  type: string;
  blockTypes: string[];
}

export interface TemplateEntry {
  fam: string;
  vr: string;
  variantKey: string;
  desc: string;
  descKey: string;
  defaultPal?: string;
  defaultBg?: string;
  defaultSize?: string;
  sections: TemplateSection[];
  overrides?: Record<string, BlockProps>;
}

export interface EditorState {
  doc: CanonicalDocument;
  undoStack: CanonicalDocument[];
  redoStack: CanonicalDocument[];
  selectedBlockId: string | null;
  dirty: boolean;
  // Save-error channel (B4). Populated by SAVE_FAILED; cleared by
  // DISMISS_SAVE_ERROR or by the next successful save snapshot match.
  // Distinct from the import-error channel surfaced from index.tsx —
  // see docs/modules/editor.md "Error channels" and the NotificationBanner
  // priority order (saveError > importError > _lastRejection > warnings).
  saveError: string | null;
  // Retry-orchestration state (DEBT-027 closure). `retryAttempt` is
  // 0-indexed into RETRY_DELAYS_MS at the call site; at length ==
  // RETRY_DELAYS_MS.length the budget is exhausted. `canAutoRetry` is
  // false for terminal failures (e.g. 404) — the retry effect skips
  // scheduling and only manual retry can re-arm. Both transition through
  // the reducer so doc-mutation actions can reset them atomically with
  // the document change (see cross-cutting reset at end of `reducer`).
  retryAttempt: number;
  canAutoRetry: boolean;
  // Tracks recent editing bursts so reducer can batch keystroke history.
  _lastAction?: { type: string; blockId?: string; key?: string; at: number };
  // Last rejection emitted by the permission gate. Set whenever an action
  // is blocked by mode or workflow checks; cleared on every successful
  // mutation. Distinct from `_lastAction` so the burst-batching fingerprint
  // is not perturbed by rejected dispatches. Read by tests and (PR 3) the
  // future Review panel toast surface.
  _lastRejection?: { type: string; reason: string; at: number };
  // Mode lives in reducer state so the permission gate has a single source of
  // truth for every dispatched action (see store/reducer.ts isActionAllowed).
  mode: EditorMode;
  // Optional injected ISO-timestamp provider. Defaults to the system clock
  // in `initState`; tests inject a mock to keep workflow transitions
  // deterministic across runs. Never serialized.
  _timestampProvider?: TimestampProvider;
}

export type EditorAction =
  | { type: 'UPDATE_PROP'; blockId: string; key: string; value: any }
  | { type: 'UPDATE_DATA'; blockId: string; data: Record<string, any> }
  | { type: 'TOGGLE_VIS'; blockId: string }
  | { type: 'TOGGLE_LOCK'; blockId: string }
  | { type: 'DUPLICATE_BLOCK'; blockId: string; newId?: string }
  | { type: 'REMOVE_BLOCK'; blockId: string }
  | { type: 'CHANGE_PAGE'; key: PageKey; value: string }
  | { type: 'SWITCH_TPL'; tid: string }
  | { type: 'IMPORT'; doc: CanonicalDocument }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SELECT'; blockId: string | null }
  // Snapshot-based save completion (B2). Payload carries the doc
  // reference captured at save start; the reducer clears `dirty` only if
  // state.doc is referentially equal to `snapshotDoc` (no intervening
  // edits). This replaces the older unconditional `SAVED` action.
  | { type: 'SAVED_IF_MATCHES'; snapshotDoc: CanonicalDocument }
  // Save failed — routed to `state.saveError` for the NotificationBanner.
  // `canAutoRetry` distinguishes transient failures (true → retry effect
  // schedules a backoff cycle) from terminal failures like 404 (false →
  // banner stays with manual "Retry now" only).
  | { type: 'SAVE_FAILED'; error: string; canAutoRetry: boolean }
  // User dismissed the save-error banner. Leaves `dirty` untouched.
  | { type: 'DISMISS_SAVE_ERROR' }
  // Manual "Retry now" pressed: reset retry budget so a fresh backoff
  // cycle starts on the next failure, and re-arm `canAutoRetry` (so the
  // user can recover from a prior terminal classification).
  | { type: 'RETRY_RESET' }
  // Retry timer fired — advance the delay index so the NEXT auto-retry
  // (if this one also fails) waits the next slot in RETRY_DELAYS_MS.
  // Dispatched by the retry-orchestration effect's timer callback right
  // before it calls performSave(). Mirrors the historical `attempt + 1`
  // write performed inside the timer pre-DEBT-027.
  | { type: 'RETRY_ATTEMPT_ADVANCE' }
  | { type: 'SET_MODE'; mode: EditorMode }
  | WorkflowAction
  | CommentAction;

// Workflow lifecycle actions — see store/workflow.ts for state-machine.
export type WorkflowAction =
  | { type: 'SUBMIT_FOR_REVIEW'; actor?: string; ts?: string }
  | { type: 'APPROVE'; actor?: string; ts?: string }
  | { type: 'REQUEST_CHANGES'; note?: string; actor?: string; ts?: string }
  | { type: 'RETURN_TO_DRAFT'; note?: string; actor?: string; ts?: string }
  | { type: 'MARK_EXPORTED'; filename: string; actor?: string; ts?: string }
  | { type: 'MARK_PUBLISHED'; channel: string; actor?: string; ts?: string }
  | { type: 'DUPLICATE_AS_DRAFT'; actor?: string; ts?: string };

// Comment lifecycle actions — see store/comments.ts for reducer helpers.
// Comment mutations do NOT participate in undo/redo (see docs/modules/editor.md
// "Comments subsystem"). `id` on ADD/REPLY is injectable for test determinism;
// the reducer falls back to `makeId()` when absent.
export type CommentAction =
  | { type: 'ADD_COMMENT'; blockId: string; text: string; actor?: string; ts?: string; id?: string }
  | { type: 'REPLY_TO_COMMENT'; parentId: string; text: string; actor?: string; ts?: string; id?: string }
  | { type: 'EDIT_COMMENT'; commentId: string; text: string; actor?: string; ts?: string }
  | { type: 'RESOLVE_COMMENT'; commentId: string; actor?: string; ts?: string }
  | { type: 'REOPEN_COMMENT'; commentId: string; actor?: string; ts?: string }
  | { type: 'DELETE_COMMENT'; commentId: string; actor?: string; ts?: string };

export interface TimestampProvider {
  now(): string;
}

export interface PermissionSet {
  switchTemplate: boolean;
  changePalette: boolean;
  changeBackground: boolean;
  changeSize: boolean;
  editBlock: (reg: BlockRegistryEntry, key: string) => boolean;
  toggleVisibility: (reg: BlockRegistryEntry) => boolean;
}

export interface KPIItem {
  label: string;
  value: string;
  delta: string;
  direction: Direction;
  _id: string;
}

export const SERIES_ROLES = ['primary', 'benchmark', 'secondary'] as const;
export type SeriesRole = typeof SERIES_ROLES[number];

export function isSeriesRole(v: unknown): v is SeriesRole {
  return typeof v === 'string' && (SERIES_ROLES as readonly string[]).includes(v);
}

export interface SeriesItem {
  label: string;
  role: SeriesRole;
  data: number[];
  _id: string;
}

export interface BarItem {
  label: string;
  value: number;
  flag: string;
  highlight: boolean;
  _id: string;
}
