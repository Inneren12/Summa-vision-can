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
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import { PALETTES } from '@/components/editor/config/palettes';
import type { CanonicalDocument, Block, Section } from '@/components/editor/types';
import { installCanvasMocks } from '../../../__utils__/canvasMock';

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
    page: { size: 'long_infographic', background: 'solid_dark', palette: 'housing' },
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

  test('returns Blob for twitter preset', async () => {
    const doc = baselineDoc();
    const blob = await renderDocumentToBlob(doc, PAL, 'twitter');
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/png');
  });

  test('throws on unknown preset id', async () => {
    const doc = baselineDoc();
    await expect(renderDocumentToBlob(doc, PAL, 'nonexistent_preset')).rejects.toThrow(
      /Unknown preset id: nonexistent_preset/,
    );
  });

  test('re-entrancy: 7 sequential calls in single tick produce 7 distinct Blobs (Risk 1)', async () => {
    const doc = baselineDoc();
    const presets = [
      'instagram_1080',
      'instagram_port',
      'twitter',
      'reddit',
      'linkedin',
      'story',
      'long_infographic',
    ];
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
    await expect(renderDocumentToBlob(doc, PAL, 'reddit')).rejects.toThrow(
      /toBlob returned null for preset reddit/,
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
});
