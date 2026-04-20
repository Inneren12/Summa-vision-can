/**
 * @jest-environment jsdom
 */

import {
  CANVAS_FONT_FACES,
  preloadCanvasFonts,
} from '@/components/editor/renderer/font-preload';
import { TK } from '@/components/editor/config/tokens';

describe('CANVAS_FONT_FACES registry', () => {
  test('includes all three TK font families', () => {
    const families = new Set(CANVAS_FONT_FACES.map((f) => f.family));
    expect(families.has(TK.font.display)).toBe(true);
    expect(families.has(TK.font.body)).toBe(true);
    expect(families.has(TK.font.data)).toBe(true);
  });

  test('every entry has a plausible weight (100-900)', () => {
    for (const face of CANVAS_FONT_FACES) {
      expect(face.weight).toBeGreaterThanOrEqual(100);
      expect(face.weight).toBeLessThanOrEqual(900);
    }
  });

  test('display weights match recon audit (400/600/700/800)', () => {
    const displayWeights = CANVAS_FONT_FACES
      .filter((f) => f.family === TK.font.display)
      .map((f) => f.weight)
      .sort((a, b) => a - b);
    expect(displayWeights).toEqual([400, 600, 700, 800]);
  });

  test('body weights match recon audit (400/500/600)', () => {
    const bodyWeights = CANVAS_FONT_FACES
      .filter((f) => f.family === TK.font.body)
      .map((f) => f.weight)
      .sort((a, b) => a - b);
    expect(bodyWeights).toEqual([400, 500, 600]);
  });

  test('data weights match recon audit (400/500/600/700)', () => {
    const dataWeights = CANVAS_FONT_FACES
      .filter((f) => f.family === TK.font.data)
      .map((f) => f.weight)
      .sort((a, b) => a - b);
    expect(dataWeights).toEqual([400, 500, 600, 700]);
  });
});

describe('preloadCanvasFonts', () => {
  test('returns early when document.fonts.load is unavailable', async () => {
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: undefined,
    });
    try {
      await expect(preloadCanvasFonts()).resolves.toBeUndefined();
    } finally {
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });

  test('calls document.fonts.load once per CANVAS_FONT_FACES entry', async () => {
    const loadMock = jest.fn(() => Promise.resolve([]));
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: { load: loadMock, ready: Promise.resolve() },
    });
    try {
      await preloadCanvasFonts();
      expect(loadMock).toHaveBeenCalledTimes(CANVAS_FONT_FACES.length);
    } finally {
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });

  test('swallows individual face load failures and resolves', async () => {
    const loadMock = jest.fn((shorthand: string) => {
      if (shorthand.includes('500')) {
        return Promise.reject(new Error('simulated load failure'));
      }
      return Promise.resolve([]);
    });
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: { load: loadMock, ready: Promise.resolve() },
    });
    try {
      await expect(preloadCanvasFonts()).resolves.toBeUndefined();
      expect(warnSpy).toHaveBeenCalled();
    } finally {
      warnSpy.mockRestore();
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });

  test('shorthand format for first arg is "weight 1em family"', async () => {
    const loadMock = jest.fn(() => Promise.resolve([]));
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: { load: loadMock, ready: Promise.resolve() },
    });
    try {
      await preloadCanvasFonts();
      const [firstArgs] = loadMock.mock.calls as unknown[][];
      const firstCall = String(firstArgs?.[0] ?? '');
      expect(firstCall).toMatch(/^\d{3}\s+1em\s+/);
    } finally {
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });

  test('passes a multi-subset sample text to every fonts.load call', async () => {
    const loadMock = jest.fn(() => Promise.resolve([]));
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: { load: loadMock, ready: Promise.resolve() },
    });
    try {
      await preloadCanvasFonts();

      // Regression guard for the Task 6 follow-up. document.fonts.load
      // defaults its text arg to a single space (U+0020); without an
      // explicit arg, only the basic-Latin subset shard is resolved,
      // leaving late-subset shards (latin-ext, Greek, Cyrillic, etc.)
      // to fetch late and re-open the gap this module is meant to close.
      expect(loadMock.mock.calls.length).toBeGreaterThan(0);
      for (const call of loadMock.mock.calls) {
        expect(call.length).toBe(2);
        const text = call[1] as string;
        expect(typeof text).toBe('string');
        // Must include at least one non-ASCII character — a space-only
        // or basic-Latin-only string would silently regress the fix.
        const hasNonAscii = [...text].some(
          (ch) => ch.charCodeAt(0) > 0x007f,
        );
        expect(hasNonAscii).toBe(true);
      }
    } finally {
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });
});
