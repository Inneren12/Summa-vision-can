import type { CanonicalDocument } from '../types';
import { BREG } from '../registry/blocks';

export interface InvariantViolation {
  code: string;
  message: string;
  severity: 'error' | 'warning';
}

/**
 * Verify that a document is internally consistent.
 * Called in dev mode AFTER every reducer action to catch corruption early.
 *
 * Returns an array of violations instead of throwing — reducer should log
 * these but not crash, because a corrupt document might still be recoverable
 * by user action (e.g., undo, switch template).
 */
export function assertDocumentIntegrity(doc: CanonicalDocument): InvariantViolation[] {
  const violations: InvariantViolation[] = [];
  const referencedIds = new Set<string>();

  // INV-1: every section blockId resolves to an existing block
  doc.sections.forEach(sec => {
    sec.blockIds.forEach(bid => {
      if (!doc.blocks[bid]) {
        violations.push({
          code: 'DANGLING_REF',
          message: `Section "${sec.id}" references missing block "${bid}"`,
          severity: 'error',
        });
      }
      if (referencedIds.has(bid)) {
        violations.push({
          code: 'DUPLICATE_REF',
          message: `Block "${bid}" referenced by multiple sections`,
          severity: 'error',
        });
      }
      referencedIds.add(bid);
    });
  });

  // INV-2: every block in doc.blocks is referenced by exactly one section
  Object.keys(doc.blocks).forEach(bid => {
    if (!referencedIds.has(bid)) {
      violations.push({
        code: 'ORPHAN_BLOCK',
        message: `Block "${bid}" not referenced by any section`,
        severity: 'warning',
      });
    }
  });

  // INV-3: universally-required blocks must exist
  const universalRequired = ['source_footer', 'brand_stamp', 'headline_editorial'];
  universalRequired.forEach(reqType => {
    const found = Object.values(doc.blocks).some(b => b.type === reqType);
    if (!found) {
      violations.push({
        code: 'MISSING_REQUIRED',
        message: `Required block type "${reqType}" not found`,
        severity: 'error',
      });
    }
  });

  // INV-4: every block must be placed in an allowed section type
  doc.sections.forEach(sec => {
    sec.blockIds.forEach(bid => {
      const block = doc.blocks[bid];
      if (!block) return;
      const reg = BREG[block.type];
      if (!reg) {
        violations.push({
          code: 'UNKNOWN_TYPE',
          message: `Unknown block type: "${block.type}"`,
          severity: 'error',
        });
        return;
      }
      if (!reg.allowedSections.includes(sec.type)) {
        violations.push({
          code: 'WRONG_SECTION',
          message: `Block "${reg.name}" in "${sec.type}" section (allowed: ${reg.allowedSections.join(', ')})`,
          severity: 'error',
        });
      }
    });
  });

  // INV-5: block.id === object key in doc.blocks
  Object.entries(doc.blocks).forEach(([key, block]) => {
    if (block.id !== key) {
      violations.push({
        code: 'ID_MISMATCH',
        message: `Block key "${key}" does not match block.id "${block.id}"`,
        severity: 'error',
      });
    }
  });

  return violations;
}
