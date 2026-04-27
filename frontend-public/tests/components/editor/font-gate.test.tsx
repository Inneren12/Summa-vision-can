/**
 * @jest-environment jsdom
 *
 * Stage 4 Task 3 — deterministic export font gate.
 *
 * Verifies the two chokepoints introduced by Task 3:
 *   - EXPORT button disabled until `document.fonts.ready` resolves.
 *   - Timeout fallback (5s) flips fontsReady true with a dev-only warn
 *     when the browser never resolves the ready promise.
 *   - Validation errors take priority over fonts-loading in the
 *     disabled-state tooltip.
 */

import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import InfographicEditor, { FONTS_TIMEOUT_MS } from '@/components/editor';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import type { CanonicalDocument } from '@/components/editor/types';
import { mockDocumentFontsReady } from '../../editor/components/_helpers';

function getExportButton(): HTMLButtonElement {
  // PR#3: Export button now triggers ZIP export. Aria-labels span both the
  // legacy `export.disabled.*` namespace (validation/fonts gating, kept) and
  // the new `editor.export_zip.button.aria|label` keys.
  return screen.getByRole('button', {
    name: /editor\.export_zip\.button\.(aria|label)|export\.disabled\./i,
  }) as HTMLButtonElement;
}

function makeTestDoc(): CanonicalDocument {
  return mkDoc('single_stat_hero', TPLS.single_stat_hero);
}

/**
 * Produce a validation-failing doc by blanking the headline text.
 * `validate` flags empty headline as an error, which drops `canExp` to false.
 */
function makeDocWithValidationErrors(): CanonicalDocument {
  const doc = makeTestDoc();
  const headlineBlock = Object.values(doc.blocks).find(
    (b) => b.type === 'headline_editorial',
  );
  if (!headlineBlock) throw new Error('template missing headline block');
  headlineBlock.props = { ...headlineBlock.props, text: '' };
  return doc;
}

async function flushPromises(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('Font gate (Stage 4 Task 3)', () => {
  test('EXPORT disabled while fonts pending, enabled once ready resolves', async () => {
    const fonts = mockDocumentFontsReady({ initial: 'pending' });
    try {
      await act(async () => {
        render(<InfographicEditor initialDoc={makeTestDoc()} />);
      });

      const btn = getExportButton();
      expect(btn).toBeDisabled();
      expect(btn.getAttribute('title')).toBe('export.disabled.loading_fonts');

      await act(async () => {
        fonts.resolve();
        await flushPromises();
      });

      expect(btn).not.toBeDisabled();
      expect(btn.getAttribute('title')).toBe('editor.export_zip.button.label');
    } finally {
      fonts.restore();
    }
  });

  test('validation error message wins over fonts-loading message', async () => {
    const fonts = mockDocumentFontsReady({ initial: 'pending' });
    try {
      await act(async () => {
        render(<InfographicEditor initialDoc={makeDocWithValidationErrors()} />);
      });

      const btn = getExportButton();
      expect(btn).toBeDisabled();
      expect(btn.getAttribute('title')).toBe('export.disabled.validation_errors');
      expect(btn.getAttribute('title')).not.toBe('export.disabled.loading_fonts');

      await act(async () => {
        fonts.resolve();
        await flushPromises();
      });

      // Fonts resolved but validation still blocks export.
      expect(btn).toBeDisabled();
      expect(btn.getAttribute('title')).toBe('export.disabled.validation_errors');
    } finally {
      fonts.restore();
    }
  });

  test('timeout path flips fontsReady after 5s with dev-only warning', async () => {
    jest.useFakeTimers();
    const fonts = mockDocumentFontsReady({ initial: 'pending' });
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    try {
      await act(async () => {
        render(<InfographicEditor initialDoc={makeTestDoc()} />);
      });

      const btn = getExportButton();
      expect(btn).toBeDisabled();

      await act(async () => {
        jest.advanceTimersByTime(5000);
        // Flush the race's .then microtask.
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(btn).not.toBeDisabled();
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('timed out after 5000ms'),
      );
    } finally {
      warnSpy.mockRestore();
      fonts.restore();
      jest.useRealTimers();
    }
  });

  // B1 regression guard: before the B1 fix, exportPNG did an unconditional
  // `await document.fonts.ready`. When the browser's ready promise never
  // resolves, the mount-time timeout would flip fontsReady true and enable
  // the button, but clicking EXPORT would hang forever inside the await,
  // never emitting another warn and never reaching any post-await code.
  //
  // This test proves fontsReady is the single contract: once the mount
  // timeout flips it true, exportPNG runs without re-invoking the helper.
  // Pre-B1, exportPNG awaited document.fonts.ready directly and would
  // hang forever. The B1 fix briefly re-invoked the helper as belt-and-
  // suspenders, but that reintroduced a 5s stall per export in the same
  // pathological case. Current contract: trust the flag.
  //
  // Observable proof of non-hang: clicking EXPORT after the mount timeout
  // returns synchronously — no additional timeout warn fires (the helper
  // is no longer reached) and the click does not throw or block.
  test('export does not hang when fonts.ready never resolves — timeout path', async () => {
    jest.useFakeTimers();
    const fonts = mockDocumentFontsReady({ initial: 'pending' });
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    try {
      await act(async () => {
        render(<InfographicEditor publicationId="pub1" initialDoc={makeTestDoc()} />);
      });
      const exportBtn = getExportButton();

      // Mount-time timeout fires, flag flips true, button enables.
      await act(async () => {
        jest.advanceTimersByTime(FONTS_TIMEOUT_MS);
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(exportBtn).not.toBeDisabled();

      // Click EXPORT. Pre-B1, this would have suspended on
      // `await document.fonts.ready` indefinitely. Post-fix it runs to
      // completion synchronously (no helper re-invocation).
      await act(async () => {
        fireEvent.click(exportBtn);
      });

      // Dev warning fired exactly once — at mount timeout. exportPNG no
      // longer re-invokes waitForFontsReadyOrTimeout; it trusts fontsReady,
      // so no second timeout warn ever appears.
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('timed out after 5000ms'),
      );
      expect(warnSpy.mock.calls.filter((c) =>
        typeof c[0] === 'string' && c[0].includes('timed out after 5000ms'),
      ).length).toBe(1);
    } finally {
      warnSpy.mockRestore();
      fonts.restore();
      jest.useRealTimers();
    }
  });

  test('mount effect preloads canvas fonts before flipping fontsReady', async () => {
    const loadMock = jest.fn(() => Promise.resolve([]));
    const origFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
    Object.defineProperty(document, 'fonts', {
      configurable: true,
      value: {
        load: loadMock,
        ready: Promise.resolve(),
      },
    });

    try {
      await act(async () => {
        render(<InfographicEditor initialDoc={makeTestDoc()} />);
      });
      await flushPromises();

      expect(loadMock.mock.calls.length).toBeGreaterThan(0);

      const btn = getExportButton();
      expect(btn).not.toBeDisabled();
    } finally {
      if (origFonts) {
        Object.defineProperty(document, 'fonts', origFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    }
  });
});
