import type { CanonicalDocument, WorkflowState } from '../types';
import { BREG } from './blocks';

export const SUPPORTED_SCHEMA_VERSIONS = [1] as const;
export const CURRENT_SCHEMA = 1;

const VALID_WORKFLOW_STATES: WorkflowState[] = [
  "draft", "in_review", "approved", "exported", "published",
];

function normalizeWorkflow(raw: unknown): WorkflowState {
  if (typeof raw === "string" && VALID_WORKFLOW_STATES.includes(raw as WorkflowState)) {
    return raw as WorkflowState;
  }
  return "draft";
}

export function validateImport(doc: unknown): string | null {
  // Phase 1: Shape
  if (!doc || typeof doc !== "object") return "Not an object";
  const d = doc as any;
  if (typeof d.schemaVersion !== "number") return "Missing schemaVersion";
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(d.schemaVersion)) {
    return `Unsupported schemaVersion: ${d.schemaVersion}. Supported: ${SUPPORTED_SCHEMA_VERSIONS.join(", ")}`;
  }
  if (typeof d.templateId !== "string") return "Missing templateId";
  if (!d.page || typeof d.page !== "object") return "Missing page";
  if (!d.page.size || !d.page.background || !d.page.palette) return "Incomplete page config";
  if (!Array.isArray(d.sections)) return "Missing sections array";
  if (!d.blocks || typeof d.blocks !== "object") return "Missing blocks object";

  // Phase 2: Referential integrity (must be complete BEFORE Phase 3)
  const allRefIds = new Set<string>();
  const sectionIds = new Set<string>();
  const blockToSectionType = new Map<string, string>();

  for (const sec of d.sections) {
    if (!sec.id || !sec.type || !Array.isArray(sec.blockIds)) {
      return `Invalid section structure: ${JSON.stringify(sec?.id)}`;
    }
    if (sectionIds.has(sec.id)) return `Duplicate section id: "${sec.id}"`;
    sectionIds.add(sec.id);

    for (const bid of sec.blockIds) {
      if (typeof bid !== "string") return `Non-string blockId in section "${sec.id}"`;
      // Every blockId referenced by section must exist in blocks
      if (!d.blocks[bid]) {
        return `Section "${sec.id}" references missing block "${bid}"`;
      }
      // No duplicate references across sections
      if (allRefIds.has(bid)) {
        return `Block "${bid}" is referenced in multiple sections`;
      }
      allRefIds.add(bid);
      blockToSectionType.set(bid, sec.type);
    }
  }

  // Orphan check: every block in doc.blocks must be referenced by some section
  for (const bid of Object.keys(d.blocks)) {
    if (!allRefIds.has(bid)) {
      return `Orphan block "${bid}" not referenced by any section`;
    }
  }

  // Phase 3: Registry constraints + explicit block.id uniqueness
  const seenInternalIds = new Set<string>();
  for (const [id, block] of Object.entries(d.blocks)) {
    const b = block as any;
    if (!b || typeof b !== "object") return `Block "${id}" is not an object`;

    // Key-id consistency invariant (hydrator enforces this, but we re-check)
    if (b.id !== id) return `Block id mismatch: key="${id}" but block.id="${b.id}"`;
    if (seenInternalIds.has(b.id)) return `Duplicate block.id value: "${b.id}"`;
    seenInternalIds.add(b.id);

    if (typeof b.type !== "string") return `Block "${id}" has no type`;
    if (!b.props || typeof b.props !== "object") return `Block "${id}" has no props`;

    const reg = BREG[b.type];
    if (!reg) return `Unknown block type: "${b.type}" (${id})`;
    if (reg.guard && !reg.guard(b.props)) return `Invalid props for ${b.type} (${id})`;

    // O(1) section-type lookup (built in Phase 2)
    const parentSecType = blockToSectionType.get(id);
    if (parentSecType && !reg.allowedSections.includes(parentSecType)) {
      return `Block "${b.type}" not allowed in section type "${parentSecType}"`;
    }
  }

  // Phase 4: Section cardinality + required blocks
  const blockTypesByType: Record<string, number> = {};
  const blockTypesBySection: Record<string, Record<string, number>> = {};

  for (const sec of d.sections) {
    blockTypesBySection[sec.id] = {};
    for (const bid of sec.blockIds) {
      const b = d.blocks[bid];
      if (!b) continue;
      blockTypesByType[b.type] = (blockTypesByType[b.type] || 0) + 1;
      blockTypesBySection[sec.id][b.type] = (blockTypesBySection[sec.id][b.type] || 0) + 1;
    }
  }

  // Check maxPerSection per section
  for (const sec of d.sections) {
    const counts = blockTypesBySection[sec.id];
    for (const [type, count] of Object.entries(counts)) {
      const reg = BREG[type];
      if (reg?.maxPerSection && count > reg.maxPerSection) {
        return `Section "${sec.id}" has ${count}x "${type}", max allowed is ${reg.maxPerSection}`;
      }
    }
  }

  // Check required blocks present at document level
  const requiredTypes = Object.entries(BREG)
    .filter(([, reg]) => reg.status === "required_locked" || reg.status === "required_editable")
    .map(([type]) => type);

  for (const reqType of requiredTypes) {
    if (!blockTypesByType[reqType]) {
      return `Required block "${reqType}" is missing from document`;
    }
  }

  return null;
}

/**
 * Sanitize a raw props object against a block's default-prop shape.
 * Unknown keys are dropped; type-mismatched values are replaced with defaults.
 * Ensures hydrated blocks never carry string-when-boolean or NaN-when-number values.
 */
function sanitizeBlockProps(type: string, rawProps: any): Record<string, any> {
  const reg = BREG[type];
  if (!reg) return rawProps || {};
  const defaults = reg.dp || {};
  const result: Record<string, any> = { ...defaults };

  if (!rawProps || typeof rawProps !== "object") return result;

  // For each default key, coerce raw value to match default's type
  for (const [key, defaultVal] of Object.entries(defaults)) {
    if (!(key in rawProps)) continue;
    const rawVal = rawProps[key];

    if (Array.isArray(defaultVal)) {
      // Keep array as-is if it's an array, else use default
      result[key] = Array.isArray(rawVal) ? rawVal : defaultVal;
      continue;
    }

    const defaultType = typeof defaultVal;
    if (defaultType === "boolean") {
      result[key] = typeof rawVal === "boolean" ? rawVal : defaultVal;
    } else if (defaultType === "number") {
      result[key] = typeof rawVal === "number" && Number.isFinite(rawVal) ? rawVal : defaultVal;
    } else if (defaultType === "string") {
      result[key] = typeof rawVal === "string" ? rawVal : defaultVal;
    } else if (defaultType === "object") {
      // Object defaults — pass through if raw is object, else default
      result[key] = rawVal && typeof rawVal === "object" ? rawVal : defaultVal;
    } else {
      result[key] = rawVal;
    }
  }

  // Unknown keys (not in defaults) are dropped — strict mode
  return result;
}

/**
 * Hydrates a raw imported document into a structurally complete CanonicalDocument.
 * Fills defaults for any missing fields, normalizes block structure.
 * Rejects documents with unsupported schemaVersion (throws).
 * NOTE: This is not a versioned migration pipeline yet. It is structural hydration.
 * True schema migrations (v1 -> v2 -> v3) will be added here in the future via a MIGRATIONS map.
 */
export function hydrateImportedDoc(raw: any): CanonicalDocument {
  if (!raw || typeof raw !== "object") {
    throw new Error("Cannot hydrate non-object document");
  }

  // Reject unsupported schema versions BEFORE any hydration work
  const rawVersion = typeof raw.schemaVersion === "number" ? raw.schemaVersion : CURRENT_SCHEMA;
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(rawVersion)) {
    throw new Error(
      `Unsupported schemaVersion: ${rawVersion}. Supported: ${SUPPORTED_SCHEMA_VERSIONS.join(", ")}. ` +
      `If this is a newer version, please update the editor.`,
    );
  }

  const now = new Date().toISOString();

  const doc: CanonicalDocument = {
    schemaVersion: rawVersion, // guaranteed supported
    templateId: typeof raw.templateId === "string" ? raw.templateId : "single_stat_hero",
    page: {
      size: typeof raw.page?.size === "string" ? raw.page.size : "instagram_1080",
      background: typeof raw.page?.background === "string" ? raw.page.background : "gradient_warm",
      palette: typeof raw.page?.palette === "string" ? raw.page.palette : "housing",
    },
    sections: Array.isArray(raw.sections) ? raw.sections.map((sec: any) => ({
      id: String(sec.id || ""),
      type: String(sec.type || ""),
      blockIds: Array.isArray(sec.blockIds) ? sec.blockIds.map(String) : [],
    })) : [],
    blocks: {},
    workflow: normalizeWorkflow(raw.workflow),
    meta: {
      createdAt: raw.meta?.createdAt ?? now,
      updatedAt: raw.meta?.updatedAt ?? now,
      version: typeof raw.meta?.version === "number" ? raw.meta.version : 1,
      history: Array.isArray(raw.meta?.history) ? [...raw.meta.history] : [],
    },
  };

  // Normalize each block: force id = key (invariant), sanitize props by registry schema
  if (raw.blocks && typeof raw.blocks === "object") {
    for (const [key, block] of Object.entries(raw.blocks)) {
      const b = block as any;
      if (!b || typeof b !== "object") continue;
      doc.blocks[key] = {
        id: key, // FORCE id to match object key — cannot drift out of sync
        type: String(b.type ?? ""),
        props: sanitizeBlockProps(String(b.type ?? ""), b.props),
        visible: typeof b.visible === "boolean" ? b.visible : true,
      };
    }
  }

  return doc;
}

// Keep old name as alias during transition
export const migrateDoc = hydrateImportedDoc;
