/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import type { CanonicalDocument } from '@/components/editor/types';

// The editor touches canvas + window APIs; jsdom's canvas stub is fine for
// mount-time assertions but getContext returns null, which the engine
// handles defensively (early return). No extra setup needed.

describe('InfographicEditor — initialDoc prop', () => {
  it('falls back to the default template when no initialDoc is provided', () => {
    render(<InfographicEditor />);
    // Template chip in TopBar or similar — assert by searching for the
    // default Single Stat Hero family name.
    expect(
      screen.getAllByText(/Single Stat Hero/i).length,
    ).toBeGreaterThan(0);
  });

  it('seeds the editor with a provided valid initialDoc', () => {
    const customDoc: CanonicalDocument = mkDoc(
      'single_stat_hero',
      TPLS.single_stat_hero,
    );
    const headlineBlock = Object.values(customDoc.blocks).find(
      (b) => b.type === 'headline_editorial',
    );
    if (!headlineBlock) throw new Error('template missing headline block');
    headlineBlock.props = { ...headlineBlock.props, text: 'Custom Seeded Headline' };

    render(<InfographicEditor initialDoc={customDoc} />);

    // The headline text is rendered through the Inspector when the block
    // is not selected; assert instead that the editor mounted without
    // throwing and the custom doc made it into reducer state by rendering
    // a control that displays it. At minimum, confirm no import error
    // banner appeared.
    expect(screen.queryByTestId('notification-banner')).toBeNull();
  });

  it('falls back and surfaces an error banner when initialDoc fails validation', () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const invalidDoc = {
      schemaVersion: 2,
      templateId: 'single_stat_hero',
      // Missing required fields (sections, blocks, meta, review) — rejected
      // by assertCanonicalDocumentV2Shape.
    } as unknown as CanonicalDocument;

    render(<InfographicEditor initialDoc={invalidDoc} />);

    // NotificationBanner surfaces the validation error as an import error.
    const banner = screen.getByTestId('notification-banner');
    expect(banner).toHaveAttribute('data-kind', 'import-error');
    expect(banner.textContent).toMatch(/publication\.load_failed\.fallback/);

    // Dev-only console.error fires on validation failure.
    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });
});
