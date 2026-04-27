import { measureLayout } from '../../src/components/editor/renderer/measure';
import { mkDoc, TPLS } from '../../src/components/editor/registry/templates';
import { SIZES } from '../../src/components/editor/config/sizes';

describe('measureLayout', () => {
  test('baseline template on matching size produces no overflow', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const size = SIZES.instagram_1080;
    const result = measureLayout(doc, size);
    const overflowed = result.filter(r => r.overflow && r.sectionType !== 'footer');
    expect(overflowed).toHaveLength(0);
  });

  test('visual table on twitter size warns about chart section overflow', () => {
    const doc = mkDoc('visual_table', TPLS.visual_table);
    const tableBlockId = Object.keys(doc.blocks).find(id => doc.blocks[id].type === 'table_enriched');
    if (!tableBlockId) throw new Error('missing table_enriched block');
    doc.blocks[tableBlockId].props.rows = Array.from({ length: 16 }, (_, i) => ({
      rank: i + 1,
      flag: '🇨🇦',
      country: `Country ${i + 1}`,
      vals: [50, 20, 30, 60],
    }));
    const size = SIZES.twitter;
    const result = measureLayout(doc, size);
    const chartSection = result.find(r => r.sectionType === 'chart');
    expect(chartSection?.overflow).toBe(true);
  });

  test('returns per-block measurements', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const size = SIZES.instagram_1080;
    const result = measureLayout(doc, size);
    expect(result.length).toBeGreaterThan(0);
    result.forEach(sec => {
      expect(sec.blocks.length).toBeGreaterThanOrEqual(0);
      sec.blocks.forEach(b => {
        expect(typeof b.estimatedHeight).toBe('number');
        expect(b.estimatedHeight).toBeGreaterThanOrEqual(0);
      });
    });
  });

  test('unbounded mode: overflow is forced false even when consumed would exceed any finite available', () => {
    // Guard against future drift in the Infinity sentinel path. The contract
    // is that overflow is unconditionally false when size.h === Infinity, so
    // long_infographic measurement never spuriously rejects content.
    // Build a doc tall enough to overflow any reasonable bounded canvas; in
    // unbounded mode every section must still report overflow: false.
    const doc = mkDoc('visual_table', TPLS.visual_table);
    const tableBlockId = Object.keys(doc.blocks).find(id => doc.blocks[id].type === 'table_enriched');
    if (!tableBlockId) throw new Error('missing table_enriched block');
    doc.blocks[tableBlockId].props.rows = Array.from({ length: 50 }, (_, i) => ({
      rank: i + 1,
      flag: '🇨🇦',
      country: `Country ${i + 1}`,
      vals: [50, 20, 30, 60],
    }));

    const result = measureLayout(doc, { w: 1200, h: Infinity, n: 'unbounded_test' });
    expect(result.length).toBeGreaterThan(0);
    result.forEach(sec => {
      expect(sec.overflow).toBe(false);
    });

    // Sanity: same doc on a finite canvas DOES overflow somewhere — this
    // confirms we'd have caught a regression where unbounded mode silently
    // started using a finite available height.
    const finite = measureLayout(doc, { w: 1200, h: 600, n: 'finite_test' });
    expect(finite.some(s => s.overflow)).toBe(true);
  });

});
