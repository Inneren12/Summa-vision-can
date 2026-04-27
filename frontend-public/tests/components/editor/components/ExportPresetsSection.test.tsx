/**
 * @jest-environment jsdom
 *
 * Phase 2.1 PR#2 — Inspector / Export presets section.
 *
 * Covers (per recon §8 PR#2 row): renders all SIZES presets, force-enables
 * the current canvas size, dispatches UPDATE_PAGE_EXPORT_PRESETS on toggle,
 * reflects the doc's `exportPresets` value in checkbox state, and surfaces
 * `long_infographic` (operator opt-in surface; post-PR#3 the legacy size
 * picker also exposes it).
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import enMessages from '@/../messages/en.json';

type Messages = Record<string, unknown>;

jest.mock('next-intl', () => {
  const React = jest.requireActual('react');
  type Messages = Record<string, unknown>;
  const Ctx = React.createContext<{ messages: Messages }>({ messages: {} });

  function get(messages: Messages, path: string[]): unknown {
    return path.reduce<unknown>((acc, key) => (
      acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[key] : undefined
    ), messages);
  }

  function useTranslations(namespace?: string) {
    const { messages } = React.useContext(Ctx);
    return (key: string) => {
      const explode = (value: string) => value.split('.');
      const path = namespace ? [...explode(namespace), ...explode(key)] : explode(key);
      const val = get(messages, path);
      return typeof val === 'string' ? val : (namespace ? `${namespace}.${key}` : key);
    };
  }

  function NextIntlClientProvider({
    children,
    messages,
  }: {
    children: React.ReactNode;
    locale: string;
    messages: Record<string, unknown>;
  }) {
    return React.createElement(Ctx.Provider, { value: { messages } }, children);
  }

  return {
    useTranslations,
    useLocale: () => 'en',
    useFormatter: () => null,
    NextIntlClientProvider,
  };
});

import { NextIntlClientProvider } from 'next-intl';
import { ExportPresetsSection } from '@/components/editor/components/ExportPresetsSection';
import { SIZES, DEFAULT_EXPORT_PRESETS } from '@/components/editor/config/sizes';
import type { EditorAction } from '@/components/editor/types';

function renderSection(
  props: Partial<React.ComponentProps<typeof ExportPresetsSection>> = {},
) {
  const dispatch = jest.fn<void, [EditorAction]>();
  const utils = render(
    <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
      <ExportPresetsSection
        currentSize="instagram_1080"
        exportPresets={[...DEFAULT_EXPORT_PRESETS]}
        dispatch={dispatch}
        canEdit
        {...props}
      />
    </NextIntlClientProvider>,
  );
  return { dispatch, ...utils };
}

describe('ExportPresetsSection', () => {
  test('renders one checkbox per preset in SIZES (7 total)', () => {
    renderSection();
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(Object.keys(SIZES).length);
    expect(Object.keys(SIZES).length).toBe(7);
  });

  test('checkbox matching page.size is disabled and checked', () => {
    renderSection({ currentSize: 'instagram_1080', exportPresets: [] });
    const current = screen.getByTestId('export-preset-instagram_1080') as HTMLInputElement;
    expect(current.checked).toBe(true);
    expect(current.disabled).toBe(true);
  });

  test('clicking the disabled current-size checkbox does not dispatch', () => {
    const { dispatch } = renderSection({
      currentSize: 'instagram_1080',
      exportPresets: [],
    });
    const current = screen.getByTestId('export-preset-instagram_1080');
    fireEvent.click(current);
    expect(dispatch).not.toHaveBeenCalled();
  });

  test('toggling a non-current preset dispatches UPDATE_PAGE_EXPORT_PRESETS with the next list', () => {
    const { dispatch } = renderSection({
      currentSize: 'instagram_1080',
      exportPresets: [],
    });
    const target = screen.getByTestId('export-preset-twitter_landscape');
    fireEvent.click(target);
    expect(dispatch).toHaveBeenCalledWith({
      type: 'UPDATE_PAGE_EXPORT_PRESETS',
      exportPresets: ['twitter_landscape'],
    });
  });

  test('un-checking an already-enabled preset removes it from the list', () => {
    const { dispatch } = renderSection({
      currentSize: 'instagram_1080',
      exportPresets: ['twitter_landscape', 'reddit_standard'],
    });
    const target = screen.getByTestId('export-preset-twitter_landscape');
    fireEvent.click(target);
    expect(dispatch).toHaveBeenCalledWith({
      type: 'UPDATE_PAGE_EXPORT_PRESETS',
      exportPresets: ['reddit_standard'],
    });
  });

  test('checked state reflects exportPresets list', () => {
    renderSection({
      currentSize: 'instagram_1080',
      exportPresets: ['twitter_landscape', 'linkedin_landscape'],
    });
    const twitter = screen.getByTestId('export-preset-twitter_landscape') as HTMLInputElement;
    const linkedin = screen.getByTestId('export-preset-linkedin_landscape') as HTMLInputElement;
    const reddit = screen.getByTestId('export-preset-reddit_standard') as HTMLInputElement;
    expect(twitter.checked).toBe(true);
    expect(linkedin.checked).toBe(true);
    expect(reddit.checked).toBe(false);
  });

  test('long_infographic checkbox is rendered (operator opt-in surface)', () => {
    // Both EXPORTABLE_PRESET_IDS (post-PR#3) and the export-presets section
    // include `long_infographic`. The two lists remain semantically distinct
    // (size picker vs. ZIP inclusion) but their members happen to overlap
    // entirely now that the ZIP flow handles RenderCapExceededError.
    renderSection();
    const longInfo = screen.getByTestId('export-preset-long_infographic') as HTMLInputElement;
    expect(longInfo).toBeDefined();
    expect(longInfo.disabled).toBe(false);
  });

  test('long_infographic can be enabled via toggle', () => {
    const { dispatch } = renderSection({
      currentSize: 'instagram_1080',
      exportPresets: [],
    });
    const longInfo = screen.getByTestId('export-preset-long_infographic');
    fireEvent.click(longInfo);
    expect(dispatch).toHaveBeenCalledWith({
      type: 'UPDATE_PAGE_EXPORT_PRESETS',
      exportPresets: ['long_infographic'],
    });
  });

  test('all checkboxes disabled when canEdit is false', () => {
    renderSection({ canEdit: false });
    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
    for (const cb of checkboxes) {
      expect(cb.disabled).toBe(true);
    }
  });

  test('DEFAULT_EXPORT_PRESETS matches recon-approved common-4', () => {
    expect(DEFAULT_EXPORT_PRESETS).toEqual([
      'instagram_1080',
      'twitter_landscape',
      'reddit_standard',
      'linkedin_landscape',
    ]);
  });
});
