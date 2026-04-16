import type { CanonicalDocument, WorkflowState } from '../types';
import { BREG } from './blocks';
import { CURRENT_SCHEMA } from './templates';

export function validateImport(doc: unknown): string | null {
  // Phase 1: Shape
  if (!doc || typeof doc !== "object") return "Not an object";
  const d = doc as any;
  if (typeof d.schemaVersion !== "number") return "Missing schemaVersion";
  if (typeof d.templateId !== "string") return "Missing templateId";
  if (!d.page || typeof d.page !== "object") return "Missing page";
  if (!d.page.size || !d.page.background || !d.page.palette) return "Incomplete page config";
  if (!Array.isArray(d.sections)) return "Missing sections array";
  if (!d.blocks || typeof d.blocks !== "object") return "Missing blocks object";

  // Phase 2: Referential integrity
  const allRefIds = new Set<string>();
  const sectionIds = new Set<string>();
  for (const sec of d.sections) {
    if (!sec.id || !sec.type || !Array.isArray(sec.blockIds)) return `Invalid section structure: ${JSON.stringify(sec?.id)}`;
    if (sectionIds.has(sec.id)) return `Duplicate section id: "${sec.id}"`;
    sectionIds.add(sec.id);
    for (const bid of sec.blockIds) {
      if (!d.blocks[bid]) return `Section "${sec.id}" references missing block "${bid}"`;
      if (allRefIds.has(bid)) return `Block "${bid}" referenced in multiple sections`;
      allRefIds.add(bid);
    }
  }
  for (const bid of Object.keys(d.blocks)) {
    if (!allRefIds.has(bid)) return `Orphan block "${bid}" not referenced by any section`;
  }

  // Phase 3: Registry constraints + explicit block.id uniqueness
  const seenIds = new Set<string>();
  for (const [id, block] of Object.entries(d.blocks)) {
    const b = block as any;
    if (seenIds.has(b.id)) return `Duplicate block.id value: "${b.id}"`;
    seenIds.add(b.id);
    if (b.id !== id) return `Block id mismatch: key="${id}" but block.id="${b.id}"`;
    const reg = BREG[b.type];
    if (!reg) return `Unknown block type: "${b.type}" (${id})`;
    if (reg.guard && !reg.guard(b.props)) return `Invalid props for ${b.type} (${id})`;
    // Check block is in allowed section
    const parentSec = d.sections.find((s: any) => s.blockIds.includes(id));
    if (parentSec && !reg.allowedSections.includes(parentSec.type)) {
      return `Block "${b.type}" not allowed in section type "${parentSec.type}"`;
    }
  }

  return null;
}

/**
 * Hydrates a raw imported document into a structurally complete CanonicalDocument.
 * Fills defaults for any missing fields, normalizes block structure.
 * NOTE: This is not a versioned migration pipeline yet. It is structural hydration.
 * True schema migrations (v1 -> v2 -> v3) will be added here in the future via a MIGRATIONS map.
 */
export function hydrateImportedDoc(raw: any): CanonicalDocument {
  if (!raw || typeof raw !== "object") {
    throw new Error("Cannot hydrate non-object document");
  }

  const now = new Date().toISOString();

  const doc: CanonicalDocument = {
    schemaVersion: typeof raw.schemaVersion === "number" ? raw.schemaVersion : CURRENT_SCHEMA,
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
    workflow: typeof raw.workflow === "string" ? (raw.workflow as WorkflowState) : "draft",
    meta: {
      createdAt: raw.meta?.createdAt ?? now,
      updatedAt: raw.meta?.updatedAt ?? now,
      version: typeof raw.meta?.version === "number" ? raw.meta.version : 1,
      history: Array.isArray(raw.meta?.history) ? [...raw.meta.history] : [],
    },
  };

  // Normalize each block: ensure id/type/props/visible exist, fill defaults from registry
  if (raw.blocks && typeof raw.blocks === "object") {
    for (const [id, block] of Object.entries(raw.blocks)) {
      const b = block as any;
      if (!b || typeof b !== "object") continue;
      const reg = BREG[b.type];
      const defaults = reg?.dp || {};
      doc.blocks[id] = {
        id: String(b.id ?? id),
        type: String(b.type ?? ""),
        props: { ...defaults, ...(b.props || {}) },
        visible: typeof b.visible === "boolean" ? b.visible : true,
      };
    }
  }

  return doc;
}

// Keep old name as alias during transition
export const migrateDoc = hydrateImportedDoc;
