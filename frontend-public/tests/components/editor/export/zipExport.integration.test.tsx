/**
 * @jest-environment jsdom
 *
 * Phase 2.1 PR#3 — real-wire integration test for the multi-preset ZIP
 * export pipeline (Risk 5 mitigation per recon §5).
 *
 * "Real-wire" here means: real `mkDoc` template factory, real palette and
 * background registries, real `renderDoc` engine driving a (mocked) 2D
 * context, real `requestAnimationFrame`, real `toBlob` mock that produces
 * non-empty PNG byte sequences, real `fflate.zipSync` packing, and a final
 * decode of the resulting bytes via `fflate.unzipSync` to assert on entry
 * filenames + manifest content. The only fakes are the canvas surface
 * (jsdom returns null from getContext) and the URL/click anchor download
 * trigger (jsdom doesn't navigate).
 *
 * Pairs with the unit tests in `zipExport.test.ts`; together they satisfy
 * the Q-2.1-11 hybrid testing pattern (helper-level units + one full
 * end-to-end pipeline check).
 */
import { unzipSync, strFromU8 } from 'fflate';
import { exportZip } from '@/components/editor/export/zipExport';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import { PALETTES } from '@/components/editor/config/palettes';
import { installCanvasMocks } from '../../../__utils__/canvasMock';

describe('exportZip end-to-end (real-wire)', () => {
  let teardown: () => void;
  let clickSpy: jest.SpyInstance;
  let originalCreate: typeof URL.createObjectURL | undefined;
  let originalRevoke: typeof URL.revokeObjectURL | undefined;
  let capturedBlob: Blob | null;

  beforeEach(() => {
    teardown = installCanvasMocks();
    capturedBlob = null;
    // jsdom does not implement URL.createObjectURL/revokeObjectURL — assign
    // directly rather than via jest.spyOn (which requires the property to
    // already exist).
    originalCreate = (URL as unknown as { createObjectURL?: typeof URL.createObjectURL }).createObjectURL;
    originalRevoke = (URL as unknown as { revokeObjectURL?: typeof URL.revokeObjectURL }).revokeObjectURL;
    URL.createObjectURL = jest.fn((blob: Blob) => {
      capturedBlob = blob;
      return 'blob:fake-url';
    });
    URL.revokeObjectURL = jest.fn(() => undefined);
    clickSpy = jest
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
  });

  afterEach(() => {
    teardown();
    if (originalCreate) {
      URL.createObjectURL = originalCreate;
    } else {
      delete (URL as unknown as { createObjectURL?: unknown }).createObjectURL;
    }
    if (originalRevoke) {
      URL.revokeObjectURL = originalRevoke;
    } else {
      delete (URL as unknown as { revokeObjectURL?: unknown }).revokeObjectURL;
    }
    clickSpy.mockRestore();
  });

  test('produces a valid ZIP with manifest.json + per-preset PNG entries', async () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.page.exportPresets = [
      'instagram_1080',
      'twitter_landscape',
      'reddit_standard',
    ];

    const result = await exportZip({ doc, pal: PALETTES.housing });

    expect(result.passCount).toBe(3);
    expect(result.skippedCount).toBe(0);
    expect(capturedBlob).not.toBeNull();
    expect(capturedBlob!.type).toBe('application/zip');

    const zipBytes = new Uint8Array(await capturedBlob!.arrayBuffer());
    const entries = unzipSync(zipBytes);

    expect(Object.keys(entries).sort()).toEqual([
      'instagram_1080.png',
      'manifest.json',
      'reddit_standard.png',
      'twitter_landscape.png',
    ]);

    expect(entries['instagram_1080.png'].length).toBeGreaterThan(0);
    expect(entries['twitter_landscape.png'].length).toBeGreaterThan(0);
    expect(entries['reddit_standard.png'].length).toBeGreaterThan(0);

    const manifest = JSON.parse(strFromU8(entries['manifest.json']));
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.publication_id).toBeNull();
    expect(manifest.templateId).toBe('single_stat_hero');
    expect(manifest.presets).toHaveLength(3);
    expect(manifest.presets.every((p: { qa_status: string }) => p.qa_status === 'pass'),
    ).toBe(true);
    // Order matches doc.page.exportPresets exactly (PR#2 fix2 deterministic
    // export invariant).
    expect(manifest.presets.map((p: { id: string }) => p.id)).toEqual([
      'instagram_1080',
      'twitter_landscape',
      'reddit_standard',
    ]);
  });
});
