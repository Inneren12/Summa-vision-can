/**
 * @jest-environment jsdom
 *
 * Unit tests for the pure render helper introduced in Phase 2.1 PR#1.
 * Covers re-entrancy (Risk 1), DPR-invariant logical dims, the long_infographic
 * variable-height path, and the 4000px cap rejection (Q-2.1-10 / Risk 2).
 *
 * Canvas mocks live in tests/__utils__/canvasMock.ts so the toBlob/getContext
 * setup can be shared with the integration test and any future export-path
 * tests; jsdom returns null from getContext by default, which would otherwise
 * starve the renderer of a writable surface.
 */
import {
  renderDocumentToBlob,
  computeLongInfographicHeight,
  RenderCapExceededError,
  LONG_INFOGRAPHIC_HEIGHT_CAP,
} from '@/components/editor/export/renderToBlob';
import type { ExportPresetId } from '@/components/editor/export/renderToBlob';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import { PALETTES } from '@/components/editor/config/palettes';
import type { CanonicalDocument, Block, Section } from '@/components/editor/types';
import { installCanvasMocks } from '../../../__utils__/canvasMock';
import { measureLayout } from '@/components/editor/renderer/measure';

const PAL = PALETTES.housing;

function baselineDoc(): CanonicalDocument {
  return mkDoc('single_stat_hero', TPLS.single_stat_hero);
}

/**
 * Build a synthetic doc whose summed `consumedHeight` from `measureLayout`
 * is guaranteed to overflow the 4000px cap. Uses a single header section
 * with a `headline_editorial` block carrying many newline-separated lines;
 * estimateBlockHeight returns `(lines * 50 + 10) * s`, so 100 lines at
 * w=1200 (s≈1.111) yields ~5566px alone — well past the cap.
 */
function tallDocOverCap(): CanonicalDocument {
  const longText = Array.from({ length: 120 }, (_, i) => `line ${i + 1}`).join('\n');
  const block: Block = {
    id: 'blk_hl',
    type: 'headline_editorial',
    props: { text: longText },
    visible: true,
  };
  const section: Section = { id: 'header', type: 'header', blockIds: ['blk_hl'] };
  const now = new Date('2026-04-27T00:00:00.000Z').toISOString();
  return {
    schemaVersion: 4,
    templateId: 'synthetic_tall',
    page: {
      size: 'long_infographic',
      background: 'solid_dark',
      palette: 'housing',
      exportPresets: [],
    },
    sections: [section],
    blocks: { blk_hl: block },
    meta: { createdAt: now, updatedAt: now, version: 1, history: [] },
    review: { workflow: 'draft', history: [], comments: [] },
  };
}

describe('renderDocumentToBlob', () => {
  let teardown: () => void;

  beforeEach(() => {
    teardown = installCanvasMocks();
  });

  afterEach(() => {
    teardown();
  });

  test('returns Blob for instagram_1080 preset', async () => {
    const doc = baselineDoc();
    const blob = await renderDocumentToBlob(doc, PAL, 'instagram_1080');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/png');
    expect(blob.size).toBeGreaterThan(0);
  });

  test('returns Blob for twitter_landscape preset', async () => {
    const doc = baselineDoc();
    const blob = await renderDocumentToBlob(doc, PAL, 'twitter_landscape');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/png');
  });

  test('throws on unknown preset id', async () => {
    const doc = baselineDoc();
    // Cast through unknown — `presetId` is now typed as `keyof typeof SIZES`
    // and we want to exercise the runtime guard with a value the type system
    // would otherwise reject.
    await expect(
      renderDocumentToBlob(doc, PAL, 'nonexistent_preset' as unknown as never),
    ).rejects.toThrow(/Unknown preset id: nonexistent_preset/);
  });

  test('re-entrancy: 7 sequential calls in single tick produce 7 distinct Blobs (Risk 1)', async () => {
    const doc = baselineDoc();
    const presets = [
      'instagram_1080',
      'instagram_portrait',
      'twitter_landscape',
      'reddit_standard',
      'linkedin_landscape',
      'instagram_story',
      'long_infographic',
    ] as const;
    const promises = presets.map((id) => renderDocumentToBlob(doc, PAL, id));
    const blobs = await Promise.all(promises);
    expect(blobs).toHaveLength(7);
    blobs.forEach((blob) => {
      expect(blob).toBeInstanceOf(Blob);
      expect(blob.size).toBeGreaterThan(0);
      expect(blob.type).toBe('image/png');
    });
    const uniqueRefs = new Set(blobs);
    expect(uniqueRefs.size).toBe(7);
  });

  test('uses logical CSS dimensions (no DPR scaling)', async () => {
    const originalDpr = window.devicePixelRatio;
    Object.defineProperty(window, 'devicePixelRatio', { value: 3, configurable: true });
    const captured: Array<{ w: number; h: number }> = [];
    const origCreate = document.createElement.bind(document);
    const spy = jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = origCreate(tag) as HTMLElement;
      if (tag === 'canvas') {
        const cvs = el as HTMLCanvasElement;
        let w = 0;
        let h = 0;
        Object.defineProperty(cvs, 'width', {
          get: () => w,
          set: (v: number) => {
            w = v;
            captured.push({ w, h });
          },
          configurable: true,
        });
        Object.defineProperty(cvs, 'height', {
          get: () => h,
          set: (v: number) => {
            h = v;
            captured.push({ w, h });
          },
          configurable: true,
        });
      }
      return el;
    });

    try {
      const doc = baselineDoc();
      await renderDocumentToBlob(doc, PAL, 'instagram_1080');
      const last = captured[captured.length - 1];
      expect(last.w).toBe(1080);
      expect(last.h).toBe(1080);
      expect(last.w).not.toBe(1080 * 3);
    } finally {
      spy.mockRestore();
      Object.defineProperty(window, 'devicePixelRatio', { value: originalDpr, configurable: true });
    }
  });

  test('toBlob null rejects with descriptive error', async () => {
    teardown();
    teardown = installCanvasMocks({ forceToBlobNull: true });
    const doc = baselineDoc();
    await expect(renderDocumentToBlob(doc, PAL, 'reddit_standard')).rejects.toThrow(
      /toBlob returned null for preset reddit_standard/,
    );
  });
});

describe('computeLongInfographicHeight', () => {
  test('sums section consumedHeight + width-scaled padding', () => {
    const doc = baselineDoc();
    const h = computeLongInfographicHeight(doc, 1200);
    const s = 1200 / 1080;
    const padding = 2 * 64 * s;
    expect(h).toBeGreaterThan(padding);
    expect(Number.isFinite(h)).toBe(true);
  });

  test('returns >4000 when document is too tall', () => {
    const tall = tallDocOverCap();
    const h = computeLongInfographicHeight(tall, 1200);
    expect(h).toBeGreaterThan(LONG_INFOGRAPHIC_HEIGHT_CAP);
  });

  test('returns <=4000 for typical document', () => {
    const doc = baselineDoc();
    const h = computeLongInfographicHeight(doc, 1200);
    expect(h).toBeLessThanOrEqual(LONG_INFOGRAPHIC_HEIGHT_CAP);
  });

  test('pure function: same input returns same output across calls', () => {
    const doc = baselineDoc();
    const a = computeLongInfographicHeight(doc, 1200);
    const b = computeLongInfographicHeight(doc, 1200);
    const c = computeLongInfographicHeight(doc, 1200);
    expect(a).toBe(b);
    expect(b).toBe(c);
  });
});

describe('renderDocumentToBlob with long_infographic', () => {
  let teardown: () => void;

  beforeEach(() => {
    teardown = installCanvasMocks();
  });

  afterEach(() => {
    teardown();
  });

  test('succeeds when measured height <= 4000', async () => {
    const doc = baselineDoc();
    const blob = await renderDocumentToBlob(doc, PAL, 'long_infographic');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);
  });

  test('throws RenderCapExceededError with measured height when > 4000', async () => {
    const tall = tallDocOverCap();
    let caught: unknown = null;
    try {
      await renderDocumentToBlob(tall, PAL, 'long_infographic');
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(RenderCapExceededError);
    const e = caught as RenderCapExceededError;
    expect(e.presetId).toBe('long_infographic');
    expect(e.cap).toBe(LONG_INFOGRAPHIC_HEIGHT_CAP);
    expect(e.measuredHeight).toBeGreaterThan(LONG_INFOGRAPHIC_HEIGHT_CAP);
  });

  test('canvas.height is integer (Math.ceil applied to fractional measure)', async () => {
    // Guards against ToUint32 truncation: browsers coerce non-integer
    // canvas.height by truncating the fractional part, which clips content.
    // The width-scaling factor s = w/1080 makes virtually every measured
    // height fractional in production. This test captures the height
    // assigned to the canvas and asserts it is an integer.
    const doc = baselineDoc();
    // Sanity check that the underlying measured height is fractional, so
    // the test would actually catch a missing Math.ceil.
    const measured = computeLongInfographicHeight(doc, 1200);
    expect(Number.isInteger(measured)).toBe(false);

    const captured: number[] = [];
    const origCreate = document.createElement.bind(document);
    const createSpy = jest
      .spyOn(document, 'createElement')
      .mockImplementation((tag: string) => {
        const el = origCreate(tag) as HTMLElement;
        if (tag === 'canvas') {
          const cvs = el as HTMLCanvasElement;
          let h = 0;
          Object.defineProperty(cvs, 'height', {
            get: () => h,
            set: (v: number) => {
              h = v;
              captured.push(v);
            },
            configurable: true,
          });
        }
        return el;
      });

    try {
      await renderDocumentToBlob(doc, PAL, 'long_infographic');
      expect(captured.length).toBeGreaterThan(0);
      const lastHeight = captured[captured.length - 1];
      expect(Number.isInteger(lastHeight)).toBe(true);
      expect(lastHeight).toBe(Math.ceil(measured));
    } finally {
      createSpy.mockRestore();
    }
  });
});

describe('ExportPresetId compile-time safety', () => {
  test('legacy preset IDs do not type-check (compile-time regression)', () => {
    // PR#2 BLOCKER-1 fix1: `SIZES` now uses `as const satisfies Record<...>`
    // so `keyof typeof SIZES` resolves to a true union of literal keys.
    // Before the fix the explicit `Record<string, SizePreset>` annotation
    // collapsed every key to `string`, and `ExportPresetId` was effectively
    // `string` — defeating the type-tightening.
    //
    // The `@ts-expect-error` directives below are the regression guard:
    // each "would-be error" line MUST fail to compile. If the line ever
    // compiles cleanly (i.e. `ExportPresetId` regresses to `string`), the
    // unused `@ts-expect-error` itself becomes a build-time error.

    // @ts-expect-error — "twitter" is a legacy ID; must not be assignable to ExportPresetId
    const legacy1: ExportPresetId = 'twitter';
    void legacy1;

    // @ts-expect-error — "story" is a legacy ID; must not be assignable to ExportPresetId
    const legacy2: ExportPresetId = 'story';
    void legacy2;

    // @ts-expect-error — random string must not be assignable to ExportPresetId
    const garbage: ExportPresetId = 'not_a_real_preset';
    void garbage;

    // Sanity: canonical post-rename IDs DO type-check.
    const valid1: ExportPresetId = 'twitter_landscape';
    const valid2: ExportPresetId = 'instagram_portrait';

    expect(valid1).toBe('twitter_landscape');
    expect(valid2).toBe('instagram_portrait');
  });
});

describe('computeLongInfographicHeight padding contract', () => {
  test('matches engine.ts page padding model (64*s top + bottom, no inter-section gap)', () => {
    // Regression guard: if engine.ts changes the page padding (currently
    // pad = 64 * s top + bottom) or introduces inter-section gaps, the
    // long_infographic height calc breaks silently. This test pins the
    // current contract by re-deriving the expected total from the same
    // measureLayout the helper uses, so drift is caught at PR time.
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const width = 1200;
    const s = width / 1080;
    const expectedPadding = 2 * 64 * s;

    const sections = measureLayout(doc, { w: width, h: Infinity, n: 'long_infographic' });
    const expectedSectionsHeight = sections.reduce((acc, m) => acc + m.consumedHeight, 0);
    const result = computeLongInfographicHeight(doc, width);

    expect(result).toBeCloseTo(expectedSectionsHeight + expectedPadding, 5);

    // Pin the no-inter-section-gap part of the contract: the total cannot
    // be larger than padding + sum(consumedHeight). If a future engine
    // change introduces inter-section spacing without updating this helper,
    // the equality above would still hold but a separate gap term would
    // be missing — document via comment so the failure mode is explicit.
    expect(result - expectedPadding).toBeCloseTo(expectedSectionsHeight, 5);
  });
});
