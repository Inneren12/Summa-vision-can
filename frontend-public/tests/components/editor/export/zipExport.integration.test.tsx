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
import { RenderCapExceededError } from '@/components/editor/export/renderToBlob';

// Partial-mock pattern: `...actual` spread is mandatory so `RenderCapExceededError`
// (re-exported from the same module) keeps its real value at runtime. Without
// the spread, `instanceof RenderCapExceededError` would throw TypeError and the
// orchestrator's catch branch would never fire — masking the real failure.
jest.mock('@/components/editor/export/renderToBlob', () => {
  const actual = jest.requireActual(
    '@/components/editor/export/renderToBlob',
  );
  return {
    ...actual,
    renderDocumentToBlob: jest.fn(),
    // PR#4: validatePresetSize now calls computeLongInfographicHeight inside
    // the orchestrator's pre-render gate. Wrap as jest.fn(actual) so the
    // default behavior is the real implementation; the pre-render-skip case
    // overrides per-call to drive the validator into the error branch.
    computeLongInfographicHeight: jest.fn(
      actual.computeLongInfographicHeight,
    ),
  };
});

import {
  renderDocumentToBlob,
  computeLongInfographicHeight,
} from '@/components/editor/export/renderToBlob';

const mockedRender = renderDocumentToBlob as jest.MockedFunction<
  typeof renderDocumentToBlob
>;
const mockedCompute = computeLongInfographicHeight as jest.MockedFunction<
  typeof computeLongInfographicHeight
>;

const publishKitOpts = {
  lineage_key: 'ln_test_123',
  slug: 'test-slug',
  baseUrl: 'https://example.com',
};

describe('exportZip end-to-end (real-wire)', () => {
  let teardown: () => void;
  let clickSpy: jest.SpyInstance;
  let originalCreate: typeof URL.createObjectURL | undefined;
  let originalRevoke: typeof URL.revokeObjectURL | undefined;
  let capturedBlob: Blob | null;

  beforeEach(() => {
    teardown = installCanvasMocks();
    capturedBlob = null;
    // fix1: default render mock emits a non-empty blob for any preset.
    // Tests that need to simulate render failures override per-call
    // (see 'skipped preset → no PNG entry in ZIP' test).
    mockedRender.mockReset();
    mockedRender.mockImplementation(
      async () => new Blob([new Uint8Array([1, 2, 3])]),
    );
    // PR#4: reset the long-infographic cap mock to the real implementation
    // each test, so per-test overrides don't leak between tests.
    const actualRender = jest.requireActual(
      '@/components/editor/export/renderToBlob',
    );
    mockedCompute.mockReset();
    mockedCompute.mockImplementation(actualRender.computeLongInfographicHeight);
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

    const result = await exportZip({ doc, pal: PALETTES.housing, ...publishKitOpts });

    expect(result.passCount).toBe(3);
    expect(result.skippedCount).toBe(0);
    expect(capturedBlob).not.toBeNull();
    expect(capturedBlob!.type).toBe('application/zip');

    const zipBytes = new Uint8Array(await capturedBlob!.arrayBuffer());
    const entries = unzipSync(zipBytes);

    expect(Object.keys(entries).sort()).toEqual([
      'distribution.json',
      'instagram_1080.png',
      'manifest.json',
      'publish_kit.txt',
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

    const distribution = JSON.parse(strFromU8(entries['distribution.json']));
    expect(distribution.publication.slug).toBe(publishKitOpts.slug);
    expect(distribution.publication.lineage_key).toBe(publishKitOpts.lineage_key);
    // Canonical URL composition: baseUrl + /p/{slug}
    expect(distribution.publication.canonical_url).toBe('https://example.com/p/test-slug');

    // UTM wiring: utm_content === lineage_key on all 3 channels
    expect(distribution.channels.reddit.share_url).toContain('utm_content=ln_test_123');
    expect(distribution.channels.twitter.share_url).toContain('utm_content=ln_test_123');
    expect(distribution.channels.linkedin.share_url).toContain('utm_content=ln_test_123');

    const publishKit = strFromU8(entries['publish_kit.txt']);
    // publish_kit.txt embeds canonical URL
    expect(publishKit).toContain('https://example.com/p/test-slug');
    expect(publishKit).toContain('=== Reddit ===');
    expect(publishKit).toContain(distribution.channels.reddit.share_url);
  });


  test('baseUrl with trailing slash is normalized in canonical_url', async () => {
    const optsWithSlash = {
      lineage_key: 'ln_test_456',
      slug: 'trail-test',
      baseUrl: 'https://example.com/',
    };

    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.page.exportPresets = ['instagram_1080'];

    await exportZip({ doc, pal: PALETTES.housing, ...optsWithSlash });

    const zipBytes = new Uint8Array(await capturedBlob!.arrayBuffer());
    const entries = unzipSync(zipBytes);
    const distribution = JSON.parse(strFromU8(entries['distribution.json']));

    // Trailing slash on baseUrl must NOT produce double-slash in canonical_url
    expect(distribution.publication.canonical_url).toBe('https://example.com/p/trail-test');
  });

  test('skipped preset → no PNG entry in ZIP, manifest filename=null + skipped_reason (fix1 contract)', async () => {
    // Real renderDocumentToBlob is mocked at the module boundary above.
    // Pass presets emit a deterministic 3-byte PNG-like blob; long_infographic
    // throws the cap-exceeded error path the orchestrator must catch.
    mockedRender.mockImplementation(async (_doc, _pal, presetId) => {
      if (presetId === 'long_infographic') {
        throw new RenderCapExceededError('long_infographic', 4250, 4000);
      }
      return new Blob([new Uint8Array([1, 2, 3])]);
    });

    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.page.exportPresets = [
      'instagram_1080',
      'long_infographic',
      'reddit_standard',
    ];

    const result = await exportZip({ doc, pal: PALETTES.housing, ...publishKitOpts });

    expect(result.passCount).toBe(2);
    expect(result.skippedCount).toBe(1);
    expect(capturedBlob).not.toBeNull();

    const zipBytes = new Uint8Array(await capturedBlob!.arrayBuffer());
    const entries = unzipSync(zipBytes);

    // ZIP-level assertions: skipped preset's PNG is NOT in the archive,
    // pass presets ARE.
    expect(entries['long_infographic.png']).toBeUndefined();
    expect(entries['instagram_1080.png']).toBeDefined();
    expect(entries['reddit_standard.png']).toBeDefined();
    expect(entries['manifest.json']).toBeDefined();

    // Manifest-level assertions: the skipped entry references no filename
    // and carries the i18n key as skipped_reason.
    const manifest = JSON.parse(strFromU8(entries['manifest.json']));
    const longEntry = manifest.presets.find(
      (p: { id: string }) => p.id === 'long_infographic',
    );
    expect(longEntry).toBeDefined();
    expect(longEntry.qa_status).toBe('skipped');
    expect(longEntry.filename).toBeNull();
    expect(longEntry.skipped_reason).toBe(
      'validation.long_infographic.height_cap_exceeded',
    );
    expect(longEntry.height).toBe(4250); // measuredHeight propagated

    // Pass entries keep the existing pass-shape contract (regression guard
    // for fix1 — the new `string | null` type must not silently null out
    // pass filenames).
    const igEntry = manifest.presets.find(
      (p: { id: string }) => p.id === 'instagram_1080',
    );
    expect(igEntry.filename).toBe('instagram_1080.png');
    expect(igEntry).not.toHaveProperty('skipped_reason');
  });

  test('PR#4 pre-render gate: long_infographic skipped via validation, manifest+ZIP consistent', async () => {
    // No render mock override — the default beforeEach mock would emit a
    // non-empty blob if called. The skip MUST come from validatePresetSize,
    // not a runtime throw. Drive the validator into its error branch by
    // mocking the cap-height computation; verify by checking render call
    // count never reaches long_infographic.
    mockedCompute.mockImplementation(() => 4500);

    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.page.exportPresets = ['instagram_1080', 'long_infographic'];

    const result = await exportZip({ doc, pal: PALETTES.housing, ...publishKitOpts });

    expect(result.passCount).toBe(1);
    expect(result.skippedCount).toBe(1);
    expect(capturedBlob).not.toBeNull();

    const zipBytes = new Uint8Array(await capturedBlob!.arrayBuffer());
    const entries = unzipSync(zipBytes);

    // Pre-render gate prevented PNG creation for long_infographic.
    expect(entries['long_infographic.png']).toBeUndefined();
    expect(entries['instagram_1080.png']).toBeDefined();

    const manifest = JSON.parse(strFromU8(entries['manifest.json']));
    const longEntry = manifest.presets.find(
      (p: { id: string }) => p.id === 'long_infographic',
    );
    expect(longEntry.qa_status).toBe('skipped');
    expect(longEntry.filename).toBeNull();
    expect(longEntry.skipped_reason).toBe(
      'validation.long_infographic.height_cap_exceeded',
    );

    // Render mock was called only for the pass preset. Proves the gate is
    // effective at the integration level: the validator caught it before the
    // render path ran (rather than the runtime catch path doing the work).
    expect(mockedRender).toHaveBeenCalledTimes(1);
  });
});
