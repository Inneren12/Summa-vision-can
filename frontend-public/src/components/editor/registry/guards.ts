import type { CanonicalDocument, LegacyDocumentV1, WorkflowState } from '../types';
import { BREG } from './blocks';
import { validateBlockData, normalizeBlockData } from '../validation/block-data';

export const SUPPORTED_SCHEMA_VERSIONS = [1, 2] as const;
export const CURRENT_SCHEMA_VERSION = 2;
// Kept as an alias for existing call sites (templates.ts, legacy tests).
export const CURRENT_SCHEMA = CURRENT_SCHEMA_VERSION;

const VALID_WORKFLOW_STATES: ReadonlySet<WorkflowState> = new Set<WorkflowState>([
  "draft", "in_review", "approved", "exported", "published",
]);

/**
 * Derive the timestamp for the synthetic `"migrated"` audit entry from
 * existing document fields so the migration is pure relative to its input.
 *
 * Using `Date.now()` / `new Date().toISOString()` here would make the same
 * v1 document produce different v2 outputs across invocations — which
 * breaks snapshot tests, export diffing, autosave reconciliation, and any
 * downstream audit-replay workflow that assumes identical inputs yield
 * identical outputs.
 *
 * Precedence: `meta.updatedAt` → `meta.createdAt` → epoch sentinel. The
 * `"1970-01-01T00:00:00.000Z"` fallback is intentional: it makes the
 * absence of timestamp information self-evident in any audit log rather
 * than silently inventing a plausible-looking time.
 */
function deriveMigrationTimestamp(doc: LegacyDocumentV1): string {
  const EPOCH = "1970-01-01T00:00:00.000Z";
  const isIsoString = (v: unknown): v is string =>
    typeof v === "string" && !Number.isNaN(Date.parse(v));
  if (isIsoString(doc.meta?.updatedAt)) return doc.meta.updatedAt;
  if (isIsoString(doc.meta?.createdAt)) return doc.meta.createdAt;
  return EPOCH;
}

/**
 * Migration functions that upgrade a document from version N to N+1.
 * Each migration is PURE: it takes a doc at version N and returns a fresh
 * doc at version N+1. No input mutation; no I/O.
 *
 * Storage currently contains only v1 documents, so the only real-world
 * migration is `1 → 2`. The chain infrastructure is retained so future
 * schema bumps can add `MIGRATIONS[2]` etc. without reshaping this module.
 */
const MIGRATIONS: Record<number, (doc: any) => any> = {
  1: (doc: LegacyDocumentV1): CanonicalDocument => {
    const { workflow, ...restRoot } = doc;
    const resolvedWorkflow: WorkflowState =
      typeof workflow === "string" && VALID_WORKFLOW_STATES.has(workflow as WorkflowState)
        ? (workflow as WorkflowState)
        : "draft";
    const migratedAt = deriveMigrationTimestamp(doc);
    return {
      ...restRoot,
      schemaVersion: 2,
      meta: { ...doc.meta },
      review: {
        workflow: resolvedWorkflow,
        history: [
          {
            ts: migratedAt,
            action: "migrated",
            summary: "Document migrated to schema v2",
            author: "system",
            fromWorkflow: null,
            toWorkflow: resolvedWorkflow,
          },
        ],
        comments: [],
      },
    };
  },
};

/**
 * Apply migrations sequentially from the document's current version to CURRENT_SCHEMA.
 * Called from hydrateImportedDoc BEFORE structural hydration.
 */
function applyMigrations(raw: any): { doc: any; warnings: string[] } {
  const warnings: string[] = [];
  if (!raw || typeof raw !== "object") return { doc: raw, warnings };

  let current = { ...raw };
  const startVersion = typeof current.schemaVersion === "number" ? current.schemaVersion : CURRENT_SCHEMA;

  if (startVersion > CURRENT_SCHEMA) {
    // Future version — we can't migrate forward, reject earlier in the pipeline
    return { doc: current, warnings };
  }

  for (let v = startVersion; v < CURRENT_SCHEMA; v++) {
    const migrateFn = MIGRATIONS[v];
    if (!migrateFn) {
      // HARD ABORT: cannot safely skip — later migrations would run against older schema shape
      const msg = `Missing migration from schemaVersion ${v} to ${v + 1} — pipeline aborted`;
      warnings.push(msg);
      throw new Error(
        `Cannot migrate document from schemaVersion ${startVersion} to ${CURRENT_SCHEMA}: ${msg}. ` +
        `Please add MIGRATIONS[${v}] to registry/guards.ts or use a document at a supported version.`,
      );
    }
    try {
      current = migrateFn(current);
      warnings.push(`Migrated schemaVersion ${v} → ${v + 1}`);
    } catch (err: any) {
      const msg = `Migration ${v} → ${v + 1} failed: ${err?.message ?? "unknown"}`;
      warnings.push(msg);
      throw new Error(`Migration pipeline failed at v${v}: ${msg}`);
    }
  }

  return { doc: current, warnings };
}

function normalizeWorkflow(raw: unknown): WorkflowState {
  if (typeof raw === "string" && VALID_WORKFLOW_STATES.has(raw as WorkflowState)) {
    return raw as WorkflowState;
  }
  return "draft";
}

/**
 * Document-shape validator. Returns null on success, error message on
 * failure. Module-internal — `validateImportStrict` is the single public
 * entry point for import validation. De-exported in the PR 2a follow-up
 * to prevent call sites from reaching around the migration step.
 *
 * Accepts only v2-shaped documents (every v2 invariant is asserted:
 * `meta.workflow` forbidden, `review.workflow` required, `review.history`
 * element shape, etc.) — hence the assertive name.
 */
function assertCanonicalDocumentV2Shape(doc: any): string | null {
  if (!doc || typeof doc !== "object") return "Not an object";
  if (typeof doc.schemaVersion !== "number") return "Missing schemaVersion";
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(doc.schemaVersion)) {
    return `Unsupported schemaVersion: ${doc.schemaVersion}. Supported: ${SUPPORTED_SCHEMA_VERSIONS.join(", ")}`;
  }

  if (!doc.templateId || typeof doc.templateId !== "string") return "Missing templateId";
  if (!doc.page || typeof doc.page !== "object") return "Missing page config";
  if (!doc.sections || !Array.isArray(doc.sections)) return "Missing sections array";
  if (!doc.blocks || typeof doc.blocks !== "object" || Array.isArray(doc.blocks)) return "Missing blocks object";
  if (!doc.meta || typeof doc.meta !== "object") return "Missing meta";

  if (!doc.page.size || !doc.page.background || !doc.page.palette) return "Incomplete page config";
  if (typeof doc.meta.createdAt !== "string" || typeof doc.meta.updatedAt !== "string") return "Invalid meta timestamps";
  if (typeof doc.meta.version !== "number" || !Array.isArray(doc.meta.history)) return "Invalid meta version/history";
  if ("workflow" in doc.meta) return "meta.workflow is not allowed in v2 (lives in review.workflow)";
  if ("schemaVersion" in doc.meta) return "meta.schemaVersion is not allowed (root is the single source)";

  if ("workflow" in doc) return "root-level workflow is not allowed in v2 (lives in review.workflow)";
  if ("comments" in doc) return "root-level comments is not allowed in v2 (lives in review.comments)";

  if (!doc.review || typeof doc.review !== "object") return "Missing review section";
  if (typeof doc.review.workflow !== "string" || !VALID_WORKFLOW_STATES.has(doc.review.workflow as WorkflowState)) {
    return "Invalid review.workflow state";
  }
  if (!Array.isArray(doc.review.history)) return "Invalid review.history (must be array)";
  if (!Array.isArray(doc.review.comments)) return "Invalid review.comments (must be array)";

  // Per-element shape checks for review.history and review.comments.
  // `validateWorkflowHistoryEntry` covers audit entries; `validateCommentEntry`
  // (added in Stage 3 PR 2b, closing DEBT-023) covers comment shape.
  for (let i = 0; i < doc.review.history.length; i++) {
    const entryErr = validateWorkflowHistoryEntry(doc.review.history[i], i);
    if (entryErr) return entryErr;
  }
  for (let i = 0; i < doc.review.comments.length; i++) {
    const entryErr = validateCommentEntry(doc.review.comments[i], i);
    if (entryErr) return entryErr;
  }

  // Duplicate id check (must come BEFORE referential integrity, because a
  // Set built via `new Set(comments.map(c => c.id))` would silently dedup
  // duplicates and let malformed docs slip through — `buildThreads` keys a
  // Map by id, and `applyEdit/Resolve/DeleteComment` use `.find(c => c.id
  // === target)`, both of which would then leave the duplicate as an
  // unreachable ghost that corrupts the audit trail).
  const seenIds = new Set<string>();
  for (let i = 0; i < doc.review.comments.length; i++) {
    const id = doc.review.comments[i].id;
    if (seenIds.has(id)) {
      return `review.comments[${i}].id "${id}" duplicates an earlier comment`;
    }
    seenIds.add(id);
  }

  // Referential integrity: every non-null parentId must point to a real
  // comment id in the same document. This closes the last gap of DEBT-023 —
  // without it, a serialized doc could reference a dead parent and break
  // `buildThreads` orphan handling in the UI. Safe to use `seenIds` now
  // that duplicates have been ruled out above.
  for (let i = 0; i < doc.review.comments.length; i++) {
    const c = doc.review.comments[i];
    if (c.parentId !== null && !seenIds.has(c.parentId)) {
      return `review.comments[${i}].parentId "${c.parentId}" does not match any comment id`;
    }
  }

  // Threading depth: replies may only target root comments. Helpers in
  // store/comments.ts (buildThreads, threadUnresolvedCount, isThreadResolved)
  // are flat by design; a reply-to-reply would silently misrepresent thread
  // shape in the UI. Enforced both here (on import) and in the reducer (on
  // dispatch) so neither path can introduce nested threads.
  const commentById = new Map<string, any>(
    doc.review.comments.map((c: any) => [c.id, c]),
  );
  for (let i = 0; i < doc.review.comments.length; i++) {
    const c = doc.review.comments[i];
    if (c.parentId !== null) {
      const parent = commentById.get(c.parentId);
      if (parent && parent.parentId !== null) {
        return `review.comments[${i}] is a reply to a reply (threading depth must be one level)`;
      }
    }
  }

  // Referential integrity: every comment must anchor to a real block.
  const blockIds = new Set<string>(Object.keys(doc.blocks));
  for (let i = 0; i < doc.review.comments.length; i++) {
    const c = doc.review.comments[i];
    if (!blockIds.has(c.blockId)) {
      return `review.comments[${i}].blockId "${c.blockId}" does not match any block in doc.blocks`;
    }
  }

  return null;
}

function validateCommentEntry(c: any, idx: number): string | null {
  const path = `review.comments[${idx}]`;
  if (!c || typeof c !== "object") return `${path} is not an object`;

  if (typeof c.id !== "string" || c.id.length === 0) {
    return `${path}.id must be a non-empty string`;
  }
  if (typeof c.blockId !== "string" || c.blockId.length === 0) {
    return `${path}.blockId must be a non-empty string`;
  }

  if (c.parentId !== null && typeof c.parentId !== "string") {
    return `${path}.parentId must be string or null`;
  }
  if (typeof c.parentId === "string" && c.parentId.length === 0) {
    return `${path}.parentId must be a non-empty string or null`;
  }
  if (c.parentId === c.id) {
    return `${path}.parentId must not equal the comment's own id (self-reference)`;
  }

  if (typeof c.author !== "string" || c.author.length === 0) {
    return `${path}.author must be a non-empty string`;
  }
  if (typeof c.text !== "string") return `${path}.text must be a string`;

  if (typeof c.createdAt !== "string" || Number.isNaN(Date.parse(c.createdAt))) {
    return `${path}.createdAt must be a valid ISO 8601 string`;
  }

  if (c.updatedAt !== null) {
    if (typeof c.updatedAt !== "string" || Number.isNaN(Date.parse(c.updatedAt))) {
      return `${path}.updatedAt must be null or a valid ISO 8601 string`;
    }
  }

  if (typeof c.resolved !== "boolean") return `${path}.resolved must be a boolean`;

  if (c.resolved) {
    if (typeof c.resolvedAt !== "string" || Number.isNaN(Date.parse(c.resolvedAt))) {
      return `${path}.resolvedAt must be a valid ISO 8601 string when resolved is true`;
    }
    if (typeof c.resolvedBy !== "string" || c.resolvedBy.length === 0) {
      return `${path}.resolvedBy must be a non-empty string when resolved is true`;
    }
  } else {
    if (c.resolvedAt !== null) return `${path}.resolvedAt must be null when resolved is false`;
    if (c.resolvedBy !== null) return `${path}.resolvedBy must be null when resolved is false`;
  }

  return null;
}

function validateWorkflowHistoryEntry(entry: any, idx: number): string | null {
  const path = `review.history[${idx}]`;
  if (!entry || typeof entry !== "object") return `${path} is not an object`;
  if (typeof entry.ts !== "string" || entry.ts.length === 0 || Number.isNaN(Date.parse(entry.ts))) {
    return `${path}.ts is invalid`;
  }
  if (typeof entry.action !== "string" || entry.action.length === 0) {
    return `${path}.action is invalid`;
  }
  if (typeof entry.summary !== "string" || entry.summary.length === 0) {
    return `${path}.summary is invalid`;
  }
  if (typeof entry.author !== "string" || entry.author.length === 0) {
    return `${path}.author is invalid`;
  }
  if (entry.fromWorkflow !== null
      && (typeof entry.fromWorkflow !== "string"
          || !VALID_WORKFLOW_STATES.has(entry.fromWorkflow as WorkflowState))) {
    return `${path}.fromWorkflow is invalid`;
  }
  if (entry.toWorkflow !== null
      && (typeof entry.toWorkflow !== "string"
          || !VALID_WORKFLOW_STATES.has(entry.toWorkflow as WorkflowState))) {
    return `${path}.toWorkflow is invalid`;
  }
  return null;
}

function validateSectionReferences(doc: CanonicalDocument): string | null {
  const allRefIds = new Set<string>();
  const sectionIds = new Set<string>();

  for (const sec of doc.sections) {
    if (!sec.id || !sec.type || !Array.isArray(sec.blockIds)) {
      return `Invalid section: ${sec?.id ?? "unknown"}`;
    }
    if (sectionIds.has(sec.id)) return `Duplicate section id: "${sec.id}"`;
    sectionIds.add(sec.id);

    for (const bid of sec.blockIds) {
      if (typeof bid !== "string") return `Invalid blockId in section "${sec.id}"`;
      if (!doc.blocks[bid]) return `Section "${sec.id}" references missing block "${bid}"`;
      if (allRefIds.has(bid)) return `Block "${bid}" referenced in multiple sections`;
      allRefIds.add(bid);
    }
  }

  for (const bid of Object.keys(doc.blocks)) {
    if (!allRefIds.has(bid)) return `Orphan block "${bid}" not in any section`;
  }

  return null;
}

function validateRegistryConstraints(doc: CanonicalDocument): string | null {
  const requiredBlockTypes = new Set(["source_footer", "brand_stamp", "headline_editorial"]);
  const presentRequiredTypes = new Set<string>();

  for (const [id, block] of Object.entries(doc.blocks)) {
    if (!block || typeof block !== "object") return `Block "${id}" is not an object`;
    if (block.id !== id) return `Block id mismatch: key="${id}" but block.id="${block.id}"`;
    if (typeof block.type !== "string") return `Block "${id}" has no type`;
    if (!block.props || typeof block.props !== "object") return `Block "${id}" has no props`;

    const reg = BREG[block.type];
    if (!reg) return `Unknown block type: ${block.type} (${id})`;
    if (reg.guard && !reg.guard(block.props)) return `Invalid props for ${block.type} (${id})`;

    const blockDataValidation = validateBlockData(block.type, block.props);
    if (!blockDataValidation.valid) {
      return `Invalid props for ${block.type} (${id}): ${blockDataValidation.errors.join("; ")}`;
    }

    if (requiredBlockTypes.has(block.type)) {
      presentRequiredTypes.add(block.type);
    }
  }

  for (const sec of doc.sections) {
    const counts: Record<string, number> = {};
    for (const bid of sec.blockIds) {
      const b = doc.blocks[bid];
      const reg = BREG[b.type];

      if (!reg.allowedSections.includes(sec.type)) {
        return `Block "${b.type}" not allowed in section "${sec.type}"`;
      }

      counts[b.type] = (counts[b.type] || 0) + 1;
      if (reg.maxPerSection && counts[b.type] > reg.maxPerSection) {
        return `Too many ${b.type} in section "${sec.type}" (max ${reg.maxPerSection})`;
      }
    }
  }

  for (const requiredType of requiredBlockTypes) {
    if (!presentRequiredTypes.has(requiredType)) {
      return `Required block "${requiredType}" is missing from document`;
    }
  }

  return null;
}

/**
 * Sanitize a raw props object against a block's default-prop shape.
 * Unknown keys are dropped; type-mismatched values are replaced with defaults.
 * Ensures hydrated blocks never carry string-when-boolean or NaN-when-number values.
 */
function sanitizeBlockProps(
  type: string,
  blockId: string,
  rawProps: any,
  warnings: string[],
): Record<string, any> {
  const reg = BREG[type];
  if (!reg) return rawProps || {};
  const defaults = reg.dp || {};
  const result: Record<string, any> = { ...defaults };

  if (!rawProps || typeof rawProps !== "object") {
    warnings.push(`Block "${blockId}" (${type}) props were malformed — replaced with defaults`);
    const normalized = normalizeBlockData(type, result, blockId);
    warnings.push(...normalized.warnings.map(w => `Block "${blockId}" (${type}): ${w}`));
    return normalized.props;
  }

  // For each default key, coerce raw value to match default's type
  for (const [key, defaultVal] of Object.entries(defaults)) {
    if (!(key in rawProps)) continue;
    const rawVal = rawProps[key];

    if (Array.isArray(defaultVal)) {
      // Keep array as-is if it's an array, else use default
      if (!Array.isArray(rawVal)) {
        warnings.push(`Block "${blockId}" (${type}).${key} expected array — defaulted`);
      }
      result[key] = Array.isArray(rawVal) ? rawVal : defaultVal;
      continue;
    }

    const defaultType = typeof defaultVal;
    if (defaultType === "boolean") {
      if (typeof rawVal !== "boolean") {
        warnings.push(`Block "${blockId}" (${type}).${key} expected boolean — defaulted`);
      }
      result[key] = typeof rawVal === "boolean" ? rawVal : defaultVal;
    } else if (defaultType === "number") {
      if (!(typeof rawVal === "number" && Number.isFinite(rawVal))) {
        warnings.push(`Block "${blockId}" (${type}).${key} expected finite number — defaulted`);
      }
      result[key] = typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : defaultVal;
    } else if (defaultType === "string") {
      if (typeof rawVal !== "string") {
        warnings.push(`Block "${blockId}" (${type}).${key} expected string — defaulted`);
      }
      result[key] = typeof rawVal === "string" ? rawVal : defaultVal;
    } else if (defaultType === "object") {
      // Object defaults — pass through if raw is object, else default
      if (!(rawVal && typeof rawVal === "object")) {
        warnings.push(`Block "${blockId}" (${type}).${key} expected object — defaulted`);
      }
      result[key] = rawVal && typeof rawVal === "object" ? rawVal : defaultVal;
    } else {
      result[key] = rawVal;
    }
  }

  // Unknown keys (not in defaults) are dropped — strict mode
  const normalized = normalizeBlockData(type, result, blockId);
  warnings.push(...normalized.warnings.map(w => `Block "${blockId}" (${type}): ${w}`));
  return normalized.props;
}

/**
 * Result of hydrating a raw imported document. `warnings` captures every
 * normalization decision the hydrator made, so the UI can surface what was
 * changed instead of silently mutating the user's document.
 */
export interface HydrationResult {
  doc: CanonicalDocument;
  warnings: string[];
}

/**
 * Hydrates a raw imported document into a structurally complete CanonicalDocument.
 * Fills defaults for any missing fields, normalizes block structure.
 * Rejects documents with unsupported schemaVersion (throws).
 * NOTE: This is not a versioned migration pipeline yet. It is structural hydration.
 * True schema migrations (v1 -> v2 -> v3) will be added here in the future via a MIGRATIONS map.
 *
 * Returns both the hydrated doc AND a list of human-readable warnings describing
 * every field that was defaulted, coerced, or dropped. Empty warnings array means
 * the import was clean.
 */
export function hydrateImportedDoc(raw: any): HydrationResult {
  if (!raw || typeof raw !== "object") {
    throw new Error("Cannot hydrate non-object document");
  }

  // Reject unsupported schemaVersion before migration
  const rawVersion = typeof raw.schemaVersion === "number" ? raw.schemaVersion : CURRENT_SCHEMA;
  if (rawVersion > CURRENT_SCHEMA) {
    throw new Error(
      `Unsupported schemaVersion: ${rawVersion}. Supported: ${SUPPORTED_SCHEMA_VERSIONS.join(", ")}. ` +
      `If this is from a newer version, please update the editor.`,
    );
  }

  const warnings: string[] = [];

  // Phase 0: Apply sequential migrations v1 → v2 → ... → CURRENT_SCHEMA
  let source: any;
  try {
    const migrated = applyMigrations(raw);
    warnings.push(...migrated.warnings);
    source = migrated.doc;
  } catch (err: any) {
    throw new Error(`Document migration failed: ${err?.message ?? "unknown error"}`);
  }

  const now = new Date().toISOString();

  if (typeof source.schemaVersion !== "number") {
    warnings.push(`Missing schemaVersion — assumed ${CURRENT_SCHEMA}`);
  }
  if (typeof source.templateId !== "string") {
    warnings.push(`Missing templateId — defaulted to "single_stat_hero"`);
  }
  if (!source.page || typeof source.page !== "object") {
    warnings.push("Missing page config — filled with defaults");
  } else {
    if (typeof source.page.size !== "string") warnings.push(`Missing page.size — defaulted to "instagram_1080"`);
    if (typeof source.page.background !== "string") warnings.push(`Missing page.background — defaulted to "gradient_warm"`);
    if (typeof source.page.palette !== "string") warnings.push(`Missing page.palette — defaulted to "housing"`);
  }
  if (!Array.isArray(source.sections)) {
    warnings.push("Missing sections array — defaulted to []");
  }
  const rawWorkflow = source.review?.workflow;
  if (rawWorkflow !== undefined && typeof rawWorkflow === "string"
      && !VALID_WORKFLOW_STATES.has(rawWorkflow as WorkflowState)) {
    warnings.push(`Invalid workflow "${rawWorkflow}" — reset to "draft"`);
  }
  if (typeof source.meta?.createdAt === "number") {
    warnings.push("meta.createdAt was numeric (epoch) — converted to ISO string");
  }
  if (typeof source.meta?.updatedAt === "number") {
    warnings.push("meta.updatedAt was numeric (epoch) — converted to ISO string");
  }

  const doc: CanonicalDocument = {
    schemaVersion: typeof source.schemaVersion === "number" ? source.schemaVersion : CURRENT_SCHEMA,
    templateId: typeof source.templateId === "string" ? source.templateId : "single_stat_hero",
    page: {
      size: typeof source.page?.size === "string" ? source.page.size : "instagram_1080",
      background: typeof source.page?.background === "string" ? source.page.background : "gradient_warm",
      palette: typeof source.page?.palette === "string" ? source.page.palette : "housing",
    },
    sections: Array.isArray(source.sections) ? source.sections.map((sec: any) => ({
      id: String(sec.id || ""),
      type: String(sec.type || ""),
      blockIds: Array.isArray(sec.blockIds) ? sec.blockIds.map(String) : [],
    })) : [],
    blocks: {},
    meta: {
      createdAt: typeof source.meta?.createdAt === "string"
        ? source.meta.createdAt
        : typeof source.meta?.createdAt === "number"
          ? new Date(source.meta.createdAt).toISOString()
          : now,
      updatedAt: typeof source.meta?.updatedAt === "string"
        ? source.meta.updatedAt
        : typeof source.meta?.updatedAt === "number"
          ? new Date(source.meta.updatedAt).toISOString()
          : now,
      version: typeof source.meta?.version === "number" ? source.meta.version : 1,
      history: Array.isArray(source.meta?.history) ? [...source.meta.history] : [],
    },
    review: {
      workflow: normalizeWorkflow(rawWorkflow),
      history: Array.isArray(source.review?.history) ? [...source.review.history] : [],
      comments: Array.isArray(source.review?.comments) ? [...source.review.comments] : [],
    },
  };

  // Normalize each block: force id = key (invariant), sanitize props by registry schema
  let droppedBlocks = 0;
  let unknownTypeBlocks = 0;
  let idRealigned = 0;
  if (source.blocks && typeof source.blocks === "object") {
    for (const [key, block] of Object.entries(source.blocks)) {
      const b = block as any;
      if (!b || typeof b !== "object") { droppedBlocks++; continue; }
      const type = String(b.type ?? "");
      if (!BREG[type]) unknownTypeBlocks++;
      if (typeof b.id === "string" && b.id !== key) idRealigned++;
      doc.blocks[key] = {
        id: key, // FORCE id to match object key — cannot drift out of sync
        type,
        props: sanitizeBlockProps(type, key, b.props, warnings),
        visible: typeof b.visible === "boolean" ? b.visible : true,
      };
    }
  }
  if (droppedBlocks > 0) warnings.push(`Dropped ${droppedBlocks} malformed block entr${droppedBlocks === 1 ? "y" : "ies"}`);
  if (unknownTypeBlocks > 0) warnings.push(`${unknownTypeBlocks} block${unknownTypeBlocks === 1 ? "" : "s"} with unknown type (will fail validation)`);
  if (idRealigned > 0) warnings.push(`Realigned ${idRealigned} block id${idRealigned === 1 ? "" : "s"} to match object key`);

  return { doc, warnings };
}


export { MIGRATIONS, applyMigrations };

export interface MigrationResult {
  doc: CanonicalDocument;
  appliedMigrations: number[];
}

/**
 * Pure, throwing migration — walks `MIGRATIONS[n]` from the doc's starting
 * version up to `CURRENT_SCHEMA_VERSION` and returns the v-current shape.
 *
 * Rejects non-objects, future-version docs, and any migration step that
 * fails to bump `schemaVersion` by exactly one. Idempotent on an
 * already-current document (returns it unchanged with `appliedMigrations: []`).
 */
export function migrateDoc(raw: unknown): MigrationResult {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("Cannot migrate: invalid document");
  }

  let current: any = { ...(raw as Record<string, unknown>) };
  const startVersion = typeof current.schemaVersion === "number" ? current.schemaVersion : 1;

  if (startVersion > CURRENT_SCHEMA_VERSION) {
    throw new Error(
      `Document schema version ${startVersion} is newer than this client supports (max: ${CURRENT_SCHEMA_VERSION})`,
    );
  }

  const appliedMigrations: number[] = [];
  for (let v = startVersion; v < CURRENT_SCHEMA_VERSION; v++) {
    const fn = MIGRATIONS[v];
    if (!fn) {
      throw new Error(`Missing migration from schemaVersion ${v} to ${v + 1}`);
    }
    current = fn(current);
    if (current?.schemaVersion !== v + 1) {
      throw new Error(
        `Migration ${v} → ${v + 1} did not bump schemaVersion (got ${current?.schemaVersion})`,
      );
    }
    appliedMigrations.push(v + 1);
  }

  return { doc: current as CanonicalDocument, appliedMigrations };
}

/**
 * Validates a raw document, runs migrations, and returns a typed
 * `CanonicalDocument`. Throws on any violation.
 *
 * As of Stage 3 PR 2a this is the SOLE import-validation entry point.
 * The legacy string-returning `validateImport(doc): string | null` was
 * removed — DEBT-022 closed.
 *
 * Pipeline:
 *   1. `migrateDoc` — bumps to current schema (idempotent on v2 input)
 *   2. `assertCanonicalDocumentV2Shape` — top-level shape + `review.history` element shape
 *   3. `validateSectionReferences` — block id integrity, no orphans
 *   4. `validateRegistryConstraints` — types, slot rules, required blocks
 */
export function validateImportStrict(raw: unknown): CanonicalDocument {
  const { doc } = migrateDoc(raw);

  const shapeErr = assertCanonicalDocumentV2Shape(doc);
  if (shapeErr) throw new Error(shapeErr);
  const refErr = validateSectionReferences(doc);
  if (refErr) throw new Error(refErr);
  const regErr = validateRegistryConstraints(doc);
  if (regErr) throw new Error(regErr);

  if (doc.schemaVersion !== CURRENT_SCHEMA_VERSION) {
    throw new Error(
      `Post-migration schemaVersion must be ${CURRENT_SCHEMA_VERSION}, got ${doc.schemaVersion}`,
    );
  }

  return doc;
}
