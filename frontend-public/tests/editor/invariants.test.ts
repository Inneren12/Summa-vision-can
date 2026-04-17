import { assertDocumentIntegrity } from '../../src/components/editor/validation/invariants';
import { mkDoc, TPLS } from '../../src/components/editor/registry/templates';

describe('assertDocumentIntegrity', () => {
  test('baseline template has no violations', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const violations = assertDocumentIntegrity(doc);
    expect(violations).toHaveLength(0);
  });

  test('detects dangling block reference', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.sections[0].blockIds.push('nonexistent_block');
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'DANGLING_REF')).toBe(true);
  });

  test('detects duplicate block reference across sections', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const firstBlockId = doc.sections[0].blockIds[0];
    doc.sections[1].blockIds.push(firstBlockId);
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'DUPLICATE_REF')).toBe(true);
  });

  test('detects orphan block', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.blocks.orphan_1 = {
      id: 'orphan_1',
      type: 'body_annotation',
      props: { text: 'orphan' },
      visible: true,
    };
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'ORPHAN_BLOCK')).toBe(true);
  });

  test('detects missing required block', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const sourceId = Object.keys(doc.blocks).find(
      id => doc.blocks[id].type === 'source_footer',
    );
    if (!sourceId) throw new Error('fixture missing source_footer');
    delete doc.blocks[sourceId];
    doc.sections.forEach(sec => {
      sec.blockIds = sec.blockIds.filter(bid => bid !== sourceId);
    });
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'MISSING_REQUIRED')).toBe(true);
  });

  test('detects block.id mismatch with object key', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const firstKey = Object.keys(doc.blocks)[0];
    doc.blocks[firstKey].id = 'different_id';
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'ID_MISMATCH')).toBe(true);
  });

  test('detects block in wrong section type', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const footer = doc.sections.find(s => s.type === 'footer');
    const header = doc.sections.find(s => s.type === 'header');
    if (!footer || !header) throw new Error('fixture missing sections');
    const sourceId = footer.blockIds.find(bid => doc.blocks[bid].type === 'source_footer');
    if (!sourceId) throw new Error('fixture missing source_footer');
    footer.blockIds = footer.blockIds.filter(b => b !== sourceId);
    header.blockIds.push(sourceId);
    const violations = assertDocumentIntegrity(doc);
    expect(violations.some(v => v.code === 'WRONG_SECTION')).toBe(true);
  });
});
