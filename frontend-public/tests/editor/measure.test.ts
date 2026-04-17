import { measureLayout } from '../../src/components/editor/renderer/measure';
import { mkDoc, TPLS } from '../../src/components/editor/registry/templates';
import { SIZES } from '../../src/components/editor/config/sizes';

describe('measureLayout', () => {
  test('baseline template on matching size produces no overflow', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const size = SIZES.instagram_1080;
    const result = measureLayout(doc, size);
    const overflowed = result.filter(r => r.overflow);
    expect(overflowed).toHaveLength(0);
  });

  test('visual table on twitter size warns about chart section overflow', () => {
    const doc = mkDoc('visual_table', TPLS.visual_table);
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
});
