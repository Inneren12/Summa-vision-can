export type EditorMode = 'template' | 'design';
export type QAMode = 'draft' | 'publish';
export type LeftTab = 'templates' | 'blocks' | 'theme';
export type Direction = 'positive' | 'negative' | 'neutral';
export type BrandPosition = 'bottom-left' | 'bottom-right';
export type TextAlign = 'left' | 'center' | 'right';
export type WorkflowState = 'draft' | 'in_review' | 'approved' | 'exported' | 'published';
export type BlockStatus = 'required_locked' | 'required_editable' | 'optional_default' | 'optional_available';
export type BlockCategory = 'text' | 'data' | 'chart' | 'struct';
export type PageKey = 'size' | 'background' | 'palette';

export interface BlockProps {
  [key: string]: any;
}

export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
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
  errors: string[];
  warnings: string[];
  info: string[];
  passed: string[];
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
  desc: string;
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
  // Tracks recent editing bursts so reducer can batch keystroke history.
  _lastAction?: { type: string; blockId?: string; key?: string; at: number };
  // Mode lives in reducer state so the permission gate has a single source of
  // truth for every dispatched action (see store/reducer.ts isActionAllowed).
  mode: EditorMode;
}

export type EditorAction =
  | { type: 'UPDATE_PROP'; blockId: string; key: string; value: any }
  | { type: 'UPDATE_DATA'; blockId: string; data: Record<string, any> }
  | { type: 'TOGGLE_VIS'; blockId: string }
  | { type: 'CHANGE_PAGE'; key: PageKey; value: string }
  | { type: 'SWITCH_TPL'; tid: string }
  | { type: 'IMPORT'; doc: CanonicalDocument }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SELECT'; blockId: string | null }
  | { type: 'SAVED' }
  | { type: 'SET_MODE'; mode: EditorMode };

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
