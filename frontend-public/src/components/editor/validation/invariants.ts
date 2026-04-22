import type { CanonicalDocument } from '../types';
import { BREG } from '../registry/blocks';
import type { ValidationMessage } from './types';

export interface InvariantViolation {
  code: string;
  message: ValidationMessage;
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
          message: { key: 'validation.integrity.dangling_ref', params: { sectionId: sec.id, blockId: bid } },
          severity: 'error',
        });
      }
      if (referencedIds.has(bid)) {
        violations.push({
          code: 'DUPLICATE_REF',
          message: { key: 'validation.integrity.duplicate_ref', params: { blockId: bid } },
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
        message: { key: 'validation.integrity.orphan_block', params: { blockId: bid } },
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
        message: { key: 'validation.integrity.required_block_missing', params: { type: reqType } },
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
          message: { key: 'validation.integrity.unknown_block_type', params: { type: block.type } },
          severity: 'error',
        });
        return;
      }
      if (!reg.allowedSections.includes(sec.type)) {
        violations.push({
          code: 'WRONG_SECTION',
          message: {
            key: 'validation.integrity.wrong_section',
            params: { blockName: reg.name, sectionType: sec.type, allowed: reg.allowedSections.join(', ' ) },
          },
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
        message: { key: 'validation.integrity.id_mismatch', params: { key, blockId: block.id } },
        severity: 'error',
      });
    }
  });

  return violations;
}
