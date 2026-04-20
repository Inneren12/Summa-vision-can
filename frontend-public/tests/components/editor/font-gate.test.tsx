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
  return screen.getByRole('button', { name: /export as png|export disabled/i }) as HTMLButtonElement;
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
      expect(btn.getAttribute('title')).toMatch(/loading fonts/i);

      await act(async () => {
        fonts.resolve();
        await flushPromises();
      });

      expect(btn).not.toBeDisabled();
      expect(btn.getAttribute('title')).toBe('Export as PNG');
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
      expect(btn.getAttribute('title')).toMatch(/validation error/i);
      expect(btn.getAttribute('title')).not.toMatch(/loading fonts/i);

      await act(async () => {
        fonts.resolve();
        await flushPromises();
      });

      // Fonts resolved but validation still blocks export.
      expect(btn).toBeDisabled();
      expect(btn.getAttribute('title')).toMatch(/validation error/i);
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
  // This test proves the shared helper's timeout now protects the export
  // path too. Observable proof: the dev-only timeout warn fires a SECOND
  // time when exportPNG's await completes via the helper's 5s timeout. If
  // the export path hung on `document.fonts.ready`, the second warn would
  // never fire — the helper would not even be entered.
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

      // One warn so far — the mount-time timeout.
      const warnsAfterMount = warnSpy.mock.calls.filter((c) =>
        typeof c[0] === 'string' && c[0].includes('timed out after 5000ms'),
      ).length;
      expect(warnsAfterMount).toBe(1);

      // Click EXPORT. Under the broken pre-B1 code, exportPNG would hit
      // `await document.fonts.ready` and suspend forever — no further
      // timeouts fire, no further warns are emitted.
      await act(async () => {
        fireEvent.click(exportBtn);
      });

      // Advance past the export-path timeout. If the helper is being used,
      // the inner setTimeout in waitForFontsReadyOrTimeout fires and emits
      // its dev warn, and the async exportPNG continues past the await.
      await act(async () => {
        jest.advanceTimersByTime(FONTS_TIMEOUT_MS);
        await Promise.resolve();
        await Promise.resolve();
      });

      // Contract: export await completed via timeout → second warn fired.
      // Non-hang is observable as a count increase. If the export path
      // hangs (pre-B1), this stays at 1 and the assertion fails.
      const warnsAfterExport = warnSpy.mock.calls.filter((c) =>
        typeof c[0] === 'string' && c[0].includes('timed out after 5000ms'),
      ).length;
      expect(warnsAfterExport).toBe(2);
    } finally {
      warnSpy.mockRestore();
      fonts.restore();
      jest.useRealTimers();
    }
  });
});
