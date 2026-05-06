/**
 * Phase 3.1d Slice 3a — registry-level lock test for `acceptsBinding`.
 *
 * V1 ships binding-picker support for `hero_stat` + `delta_badge` only
 * (Recon Delta 01 D-03). Other multi-value kinds (time_series, categorical
 * series, multi_metric, tabular, small_multiple) are schema-accepted by
 * Slice 2 validateBinding but NOT bindable in v1 picker UI. This test
 * locks that scope so future PRs can't silently expand it without
 * acknowledging the precondition (Slice 4a multi-value walker, Phase 3.1e
 * backend snapshot extension, etc.).
 */
import { BREG } from '../blocks';

describe('registry: acceptsBinding (Phase 3.1d Slice 3a v1 scope lock)', () => {
  it('hero_stat declares acceptsBinding: ["single"]', () => {
    expect(BREG.hero_stat?.acceptsBinding).toEqual(['single']);
  });

  it('delta_badge declares acceptsBinding: ["single"]', () => {
    expect(BREG.delta_badge?.acceptsBinding).toEqual(['single']);
  });

  it('exactly two block types declare acceptsBinding (locks v1 scope)', () => {
    const bindable = Object.entries(BREG)
      .filter(([, reg]) => reg.acceptsBinding !== undefined)
      .map(([key]) => key)
      .sort();
    expect(bindable).toEqual(['delta_badge', 'hero_stat']);
  });
});
