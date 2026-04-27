/**
 * @jest-environment jsdom
 *
 * Real-wire integration test for the Phase 2.1 PR#1 render helper (Risk 5).
 *
 * "Real-wire" here means: real `mkDoc` template factory, real palette and
 * background registries, real `renderDoc` engine driving a real (mocked) 2D
 * context, real `requestAnimationFrame` from jsdom, real `toBlob` mock that
 * synthesises a non-empty PNG byte sequence. The only fake surface is the
 * canvas itself — jsdom returns null from `getContext` and lacks a `toBlob`
 * implementation, so the export path cannot reach the byte boundary in any
 * other way today.
 *
 * Pairs with the unit tests in renderToBlob.test.ts; together they satisfy
 * the Q-2.1-11 hybrid testing pattern (unit per helper + one end-to-end).
 */
import { renderDocumentToBlob } from '@/components/editor/export/renderToBlob';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import { PALETTES } from '@/components/editor/config/palettes';
import { installCanvasMocks } from '../../../__utils__/canvasMock';

describe('renderDocumentToBlob — real-wire integration', () => {
  let teardown: () => void;

  beforeEach(() => {
    teardown = installCanvasMocks();
  });

  afterEach(() => {
    teardown();
  });

  test('end-to-end: real doc + real renderDoc + mocked canvas yields a valid PNG Blob', async () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const blob = await renderDocumentToBlob(doc, PALETTES.housing, 'instagram_1080');

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);
    expect(blob.type).toBe('image/png');
  });
});
