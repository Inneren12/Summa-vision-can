/**
 * @jest-environment jsdom
 */

/**
 * Real-wire integration test (DEBT-030 PR2 Fix Round 3, reviewer Issue #5).
 *
 * Unlike autosave-backend-codes.test.tsx (which mocks updateAdminPublication
 * and pre-rejects with BackendApiError), this test mocks `global.fetch`
 * and lets the REAL admin.ts -> extractor -> BackendApiError -> autosave
 * pipeline execute end-to-end. This catches breakage anywhere in the
 * chain, not just the consumer-side mapping.
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
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

function clickPalette(name: RegExp): void {
  const themeTab = document.getElementById('left-tab-theme');
  expect(themeTab).toBeDefined();
  fireEvent.click(themeTab!);
  const paletteButton = screen
    .getAllByRole('button')
    .find((button) => Boolean(name.exec(`palette: ${button.textContent ?? ''}`)));
  expect(paletteButton).toBeDefined();
  fireEvent.click(paletteButton!);
}

async function triggerAutosaveAndWaitForBanner(): Promise<void> {
  clickPalette(/palette: government/i);
  act(() => {
    jest.advanceTimersByTime(2000);
  });
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('Autosave real-wire integration (no admin mock)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.useFakeTimers();
    global.fetch = jest.fn(async (url, init) => {
      if (typeof url === 'string' && url.includes('/api/admin/publications/') && init?.method === 'PATCH') {
        return {
          ok: false,
          status: 422,
          json: async () => ({
            detail: {
              error_code: 'PUBLICATION_UPDATE_PAYLOAD_INVALID',
              message: 'The submitted changes are invalid.',
              details: { validation_errors: [] },
            },
          }),
        } as Response;
      }

      if (typeof url === 'string' && url.includes('/api/admin/publications/') && !init?.method) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 'pub1',
            headline: 'Initial',
            eyebrow: null,
            description: null,
            source_text: null,
            footnote: null,
            chart_type: 'single_stat_hero',
            visual_config: null,
            review: null,
            document_state: null,
          }),
        } as Response;
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response;
    }) as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.useRealTimers();
  });

  it('renders localized message when backend returns nested PUBLICATION_UPDATE_PAYLOAD_INVALID', async () => {
    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
        <InfographicEditor publicationId="pub1" />
      </NextIntlClientProvider>,
    );

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent(
      'Changes were rejected. Review the publication fields and try again.',
    );
  });
});
