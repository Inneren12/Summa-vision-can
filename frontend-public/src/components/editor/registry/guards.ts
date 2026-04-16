import type { CanonicalDocument } from '../types';
import { BREG } from './blocks';

export function validateImport(doc: CanonicalDocument): string | null {
  if (!doc?.schemaVersion || !doc?.blocks || !doc?.sections) return "Missing required fields";
  for (const [id, b] of Object.entries(doc.blocks)) {
    const reg = BREG[b.type];
    if (!reg) return `Unknown block type: ${b.type}`;
    if (reg.guard && !reg.guard(b.props)) return `Invalid props for ${b.type} (${id})`;
  }
  return null; // valid
}

export function migrateDoc(doc: CanonicalDocument): CanonicalDocument {
  if (!doc.workflow) doc.workflow = "draft";
  if (!doc.meta) doc.meta = { createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), version: 1, history: [] };
  if (!doc.meta.history) doc.meta.history = [];
  if (!doc.page) doc.page = { size: "instagram_1080", background: "gradient_warm", palette: "housing" };
  return doc;
}
