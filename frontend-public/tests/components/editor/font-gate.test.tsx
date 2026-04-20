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
import { render, screen, act } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
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
});
