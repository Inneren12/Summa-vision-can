import type { CanonicalDocument } from '../types';
import { BREG } from './blocks';

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

  // Phase 3: Registry constraints
  for (const [id, block] of Object.entries(d.blocks)) {
    const b = block as any;
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

export function migrateDoc(raw: any): CanonicalDocument {
  const now = new Date().toISOString();
  const doc = {
    ...raw,
    workflow: raw.workflow ?? "draft",
    meta: {
      createdAt: raw.meta?.createdAt ?? now,
      updatedAt: raw.meta?.updatedAt ?? now,
      version: raw.meta?.version ?? 1,
      history: Array.isArray(raw.meta?.history) ? [...raw.meta.history] : [],
    },
    page: {
      size: raw.page?.size ?? "instagram_1080",
      background: raw.page?.background ?? "gradient_warm",
      palette: raw.page?.palette ?? "housing",
    },
    blocks: { ...raw.blocks },
  };

  // Per-block: fill missing props from registry defaults
  for (const [id, block] of Object.entries(doc.blocks)) {
    const b = block as any;
    const reg = BREG[b.type];
    if (!reg) continue;
    const filledProps = { ...reg.dp, ...b.props };
    doc.blocks[id] = { ...b, props: filledProps, visible: b.visible ?? true };
  }

  return doc as CanonicalDocument;
}
