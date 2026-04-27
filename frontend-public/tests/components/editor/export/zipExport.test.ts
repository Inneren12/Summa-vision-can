/**
 * @jest-environment jsdom
 *
 * Phase 2.1 PR#3 — unit tests for the multi-preset ZIP export orchestrator
 * and its two pure helper modules (`zipFilename.ts`, `manifest.ts`).
 *
 * Pairs with the real-wire `zipExport.integration.test.tsx` end-to-end
 * test, which decodes the produced ZIP via `fflate.unzipSync` and asserts
 * on entry filenames + manifest content (Q-2.1-11 hybrid testing).
 */
import { exportZip } from '@/components/editor/export/zipExport';
import { buildManifest } from '@/components/editor/export/manifest';
import { buildZipFilename } from '@/components/editor/export/zipFilename';
import {
  RenderCapExceededError,
} from '@/components/editor/export/renderToBlob';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import { PALETTES } from '@/components/editor/config/palettes';
import type { CanonicalDocument } from '@/components/editor/types';
import type { PresetId } from '@/components/editor/config/sizes';
import { installCanvasMocks } from '../../../__utils__/canvasMock';

jest.mock('@/components/editor/export/renderToBlob', () => {
  const actual = jest.requireActual(
    '@/components/editor/export/renderToBlob',
  );
  return {
    ...actual,
    renderDocumentToBlob: jest.fn(),
  };
});

import { renderDocumentToBlob } from '@/components/editor/export/renderToBlob';

const mockedRender = renderDocumentToBlob as jest.MockedFunction<
  typeof renderDocumentToBlob
>;

function makeDoc(presets: readonly PresetId[]): CanonicalDocument {
  const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
  doc.page.exportPresets = [...presets];
  return doc;
}

describe('buildZipFilename', () => {
  test('format YYYYMMDD-HHmmss with template id', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const now = new Date(2026, 3, 27, 14, 30, 22);
    expect(buildZipFilename(doc, now)).toBe(
      'summa-single_stat_hero-export-20260427-143022.zip',
    );
  });

  test('zero-pads single-digit components', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.templateId = 't';
    const now = new Date(2026, 0, 1, 9, 5, 7);
    expect(buildZipFilename(doc, now)).toBe('summa-t-export-20260101-090507.zip');
  });

  test('pure: same input yields same output', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.templateId = 'x';
    const now = new Date(2026, 5, 15, 12, 0, 0);
    expect(buildZipFilename(doc, now)).toBe(buildZipFilename(doc, now));
  });
});

describe('buildManifest', () => {
  test('schemaVersion=1 + templateId + ISO timestamp', () => {
    const doc = makeDoc(['instagram_1080']);
    doc.templateId = 'ranked_bar';
    const generatedAt = new Date('2026-04-27T14:30:22.000Z');
    const m = buildManifest(doc, [], generatedAt);
    expect(m.schemaVersion).toBe(1);
    expect(m.publication_id).toBeNull();
    expect(m.templateId).toBe('ranked_bar');
    expect(m.generated_at).toBe('2026-04-27T14:30:22.000Z');
    expect(m.presets).toEqual([]);
  });

  test('preset entries match SIZES width/height + filename = `${id}.png`', () => {
    const doc = makeDoc(['instagram_1080']);
    const m = buildManifest(
      doc,
      [{ presetId: 'instagram_1080', status: 'pass', blob: new Blob() }],
      new Date(),
    );
    expect(m.presets[0]).toEqual({
      id: 'instagram_1080',
      filename: 'instagram_1080.png',
      width: 1080,
      height: 1080,
      qa_status: 'pass',
    });
  });

  test('skipped preset → filename=null, skipped_reason set, measuredHeight in height field (fix1 manifest contract)', () => {
    const doc = makeDoc(['long_infographic']);
    const m = buildManifest(
      doc,
      [
        {
          presetId: 'long_infographic',
          status: 'skipped',
          skipReason: 'validation.long_infographic.height_cap_exceeded',
          measuredHeight: 4250,
        },
      ],
      new Date(),
    );
    expect(m.presets[0].qa_status).toBe('skipped');
    expect(m.presets[0].height).toBe(4250);
    // PR#3 fix1: skipped entries must NOT reference a PNG filename that is
    // not present in the ZIP. `null` is the explicit "no file" sentinel.
    expect(m.presets[0].filename).toBeNull();
    expect(m.presets[0].skipped_reason).toBe(
      'validation.long_infographic.height_cap_exceeded',
    );
  });

  test('pass preset → filename=`<id>.png`, no skipped_reason field (fix1 manifest contract)', () => {
    // Mirror assertion: the pass path must keep filename populated and
    // must NOT emit a `skipped_reason` field. This locks the contract
    // at both ends.
    const doc = makeDoc(['instagram_1080']);
    const m = buildManifest(
      doc,
      [{ presetId: 'instagram_1080', status: 'pass', blob: new Blob() }],
      new Date(),
    );
    expect(m.presets[0].filename).toBe('instagram_1080.png');
    expect(m.presets[0]).not.toHaveProperty('skipped_reason');
  });

  test('preserves order of input results array (PR#2 fix2 manifest determinism)', () => {
    const doc = makeDoc([
      'twitter_landscape',
      'instagram_1080',
      'reddit_standard',
    ]);
    const m = buildManifest(
      doc,
      [
        { presetId: 'twitter_landscape', status: 'pass', blob: new Blob() },
        { presetId: 'instagram_1080', status: 'pass', blob: new Blob() },
        { presetId: 'reddit_standard', status: 'pass', blob: new Blob() },
      ],
      new Date(),
    );
    expect(m.presets.map((p) => p.id)).toEqual([
      'twitter_landscape',
      'instagram_1080',
      'reddit_standard',
    ]);
  });
});

describe('exportZip orchestrator (unit)', () => {
  let teardown: () => void;
  let clickSpy: jest.SpyInstance;
  let originalCreate: typeof URL.createObjectURL | undefined;
  let originalRevoke: typeof URL.revokeObjectURL | undefined;

  beforeEach(() => {
    teardown = installCanvasMocks();
    mockedRender.mockReset();
    // jsdom does not implement URL.createObjectURL/revokeObjectURL, so
    // direct assignment (rather than jest.spyOn) is required. Capture the
    // originals (likely undefined) for restoration in afterEach.
    originalCreate = (URL as unknown as { createObjectURL?: typeof URL.createObjectURL }).createObjectURL;
    originalRevoke = (URL as unknown as { revokeObjectURL?: typeof URL.revokeObjectURL }).revokeObjectURL;
    URL.createObjectURL = jest.fn(() => 'blob:fake-url');
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

  test('snapshots doc via structuredClone — mutating original after call does not affect ZIP content', async () => {
    mockedRender.mockImplementation(async () => new Blob([new Uint8Array([1, 2, 3])]));

    const doc = makeDoc(['instagram_1080']);
    const originalTemplateId = doc.templateId;

    const promise = exportZip({ doc, pal: PALETTES.housing });
    // Mutate the original doc immediately. The snapshot is taken
    // synchronously at entry, so this mutation must not affect the result.
    doc.templateId = 'mutated_after_call';

    const result = await promise;
    // Filename is derived from snapshot.templateId (not the mutated value)
    expect(result.filename.startsWith(`summa-${originalTemplateId}-export-`)).toBe(true);
  });

  test('catches RenderCapExceededError → skipped status, continues with other presets', async () => {
    mockedRender.mockImplementation(async (_doc, _pal, presetId) => {
      if (presetId === 'long_infographic') {
        throw new RenderCapExceededError('long_infographic', 4250, 4000);
      }
      return new Blob([new Uint8Array([1, 2, 3])]);
    });

    const doc = makeDoc(['instagram_1080', 'long_infographic', 'reddit_standard']);
    const result = await exportZip({ doc, pal: PALETTES.housing });

    expect(result.totalPresets).toBe(3);
    expect(result.passCount).toBe(2);
    expect(result.skippedCount).toBe(1);
    expect(result.skipped[0].presetId).toBe('long_infographic');
    expect(result.skipped[0].skipReason).toBe(
      'validation.long_infographic.height_cap_exceeded',
    );
    expect(result.skipped[0].measuredHeight).toBe(4250);
  });

  test('non-RenderCapExceededError errors propagate (no swallow)', async () => {
    mockedRender.mockImplementation(async () => {
      throw new Error('canvas allocation failed');
    });

    const onProgress = jest.fn();
    const doc = makeDoc(['instagram_1080']);
    await expect(
      exportZip({ doc, pal: PALETTES.housing, onProgress }),
    ).rejects.toThrow('canvas allocation failed');

    const phases = onProgress.mock.calls.map((c) => c[0].phase);
    expect(phases).toContain('error');
    expect(phases).not.toContain('done');
  });

  test('onProgress called with correct phases in order', async () => {
    mockedRender.mockImplementation(async () => new Blob([new Uint8Array([1, 2, 3])]));

    const onProgress = jest.fn();
    const doc = makeDoc(['instagram_1080', 'twitter_landscape', 'reddit_standard']);
    await exportZip({ doc, pal: PALETTES.housing, onProgress });

    const phases = onProgress.mock.calls.map((c) => c[0]);
    expect(phases[0]).toEqual({ phase: 'rendering', current: 1, total: 3 });
    expect(phases[1]).toEqual({ phase: 'rendering', current: 2, total: 3 });
    expect(phases[2]).toEqual({ phase: 'rendering', current: 3, total: 3 });
    expect(phases[3]).toEqual({ phase: 'packing' });
    expect(phases[4].phase).toBe('done');
  });

  test('throws when exportPresets is empty', async () => {
    const doc = makeDoc([]);
    await expect(exportZip({ doc, pal: PALETTES.housing })).rejects.toThrow(
      /No presets enabled/,
    );
  });
});
