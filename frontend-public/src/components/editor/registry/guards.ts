import type { CanonicalDocument, WorkflowState } from '../types';
import { BREG } from './blocks';
import { validateBlockData, normalizeBlockData } from '../validation/block-data';

export const SUPPORTED_SCHEMA_VERSIONS = [1] as const;
export const CURRENT_SCHEMA = 1;

const VALID_WORKFLOW_STATES: ReadonlySet<WorkflowState> = new Set<WorkflowState>([
  "draft", "in_review", "approved", "exported", "published",
]);

function normalizeWorkflow(raw: unknown): WorkflowState {
  if (typeof raw === "string" && VALID_WORKFLOW_STATES.has(raw as WorkflowState)) {
    return raw as WorkflowState;
  }
  return "draft";
}

export function validateImport(doc: unknown): string | null {
  // Phase 1: shape — required top-level fields exist with correct types.
  const shapeErr = validateDocumentShape(doc);
  if (shapeErr) return shapeErr;

  // Phase 2: references — all blockIds resolve, no duplicates, no orphans.
  const refErr = validateSectionReferences(doc as CanonicalDocument);
  if (refErr) return refErr;

  // Phase 3: registry — known block types, guards, slot rules, required blocks.
  const regErr = validateRegistryConstraints(doc as CanonicalDocument);
  if (regErr) return regErr;

  return null;
}

function validateDocumentShape(doc: any): string | null {
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

  if (typeof doc.workflow !== "string" || !VALID_WORKFLOW_STATES.has(doc.workflow as WorkflowState)) {
    return "Invalid workflow state";
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

  // Reject unsupported schema versions BEFORE any hydration work
  const rawVersion = typeof raw.schemaVersion === "number" ? raw.schemaVersion : CURRENT_SCHEMA;
  if (!SUPPORTED_SCHEMA_VERSIONS.includes(rawVersion)) {
    throw new Error(
      `Unsupported schemaVersion: ${rawVersion}. Supported: ${SUPPORTED_SCHEMA_VERSIONS.join(", ")}. ` +
      `If this is a newer version, please update the editor.`,
    );
  }

  const warnings: string[] = [];
  const now = new Date().toISOString();

  if (typeof raw.schemaVersion !== "number") {
    warnings.push(`Missing schemaVersion — assumed ${CURRENT_SCHEMA}`);
  }
  if (typeof raw.templateId !== "string") {
    warnings.push(`Missing templateId — defaulted to "single_stat_hero"`);
  }
  if (!raw.page || typeof raw.page !== "object") {
    warnings.push("Missing page config — filled with defaults");
  } else {
    if (typeof raw.page.size !== "string") warnings.push(`Missing page.size — defaulted to "instagram_1080"`);
    if (typeof raw.page.background !== "string") warnings.push(`Missing page.background — defaulted to "gradient_warm"`);
    if (typeof raw.page.palette !== "string") warnings.push(`Missing page.palette — defaulted to "housing"`);
  }
  if (!Array.isArray(raw.sections)) {
    warnings.push("Missing sections array — defaulted to []");
  }
  if (raw.workflow !== undefined && typeof raw.workflow === "string"
      && !VALID_WORKFLOW_STATES.has(raw.workflow as WorkflowState)) {
    warnings.push(`Invalid workflow "${raw.workflow}" — reset to "draft"`);
  }
  if (typeof raw.meta?.createdAt === "number") {
    warnings.push("meta.createdAt was numeric (epoch) — converted to ISO string");
  }
  if (typeof raw.meta?.updatedAt === "number") {
    warnings.push("meta.updatedAt was numeric (epoch) — converted to ISO string");
  }

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
      createdAt: typeof raw.meta?.createdAt === "string"
        ? raw.meta.createdAt
        : typeof raw.meta?.createdAt === "number"
          ? new Date(raw.meta.createdAt).toISOString()
          : now,
      updatedAt: typeof raw.meta?.updatedAt === "string"
        ? raw.meta.updatedAt
        : typeof raw.meta?.updatedAt === "number"
          ? new Date(raw.meta.updatedAt).toISOString()
          : now,
      version: typeof raw.meta?.version === "number" ? raw.meta.version : 1,
      history: Array.isArray(raw.meta?.history) ? [...raw.meta.history] : [],
    },
  };

  // Normalize each block: force id = key (invariant), sanitize props by registry schema
  let droppedBlocks = 0;
  let unknownTypeBlocks = 0;
  let idRealigned = 0;
  if (raw.blocks && typeof raw.blocks === "object") {
    for (const [key, block] of Object.entries(raw.blocks)) {
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
