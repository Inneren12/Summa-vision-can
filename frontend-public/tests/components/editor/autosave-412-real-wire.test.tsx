/**
 * @jest-environment jsdom
 */

/**
 * Phase 1.3 — autosave 412 real-wire integration test.
 *
 * Mocks ``global.fetch`` (NOT the admin module) so the full pipeline
 * exercises:
 *   admin.ts → BackendApiError → editor.performSave.catch → modal state
 *
 * Per TEST_INFRASTRUCTURE.md §4.1.
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
    return (key: string, params?: Record<string, unknown>) => {
      const explode = (value: string) => value.split('.');
      const path = namespace ? [...explode(namespace), ...explode(key)] : explode(key);
      const val = get(messages, path);
      if (typeof val !== 'string') {
        return namespace ? `${namespace}.${key}` : key;
      }
      if (!params) return val;
      return Object.entries(params).reduce(
        (acc, [k, v]) => acc.replace(`{${k}}`, String(v)),
        val,
      );
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

async function triggerAutosave(): Promise<void> {
  clickPalette(/palette: government/i);
  act(() => {
    jest.advanceTimersByTime(2000);
  });
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('Autosave 412 PRECONDITION_FAILED real-wire', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.useRealTimers();
  });

  function setUpMockFetch(opts: { failingStatus: number; envelope: unknown }) {
    global.fetch = jest.fn(async (url, init) => {
      if (typeof url === 'string' && url.includes('/api/admin/publications/') && init?.method === 'PATCH') {
        return {
          ok: false,
          status: opts.failingStatus,
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => opts.envelope,
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers(),
        json: async () => ({}),
      } as Response;
    }) as typeof fetch;
  }

  it('412 PRECONDITION_FAILED surfaces the modal and bypasses NotificationBanner auto-retry', async () => {
    setUpMockFetch({
      failingStatus: 412,
      envelope: {
        detail: {
          error_code: 'PRECONDITION_FAILED',
          message: 'The publication has been modified since you loaded it.',
          details: {
            server_etag: 'W/"server1234567890"',
            client_etag: 'W/"client1234567890"',
          },
        },
      },
    });

    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
        <InfographicEditor publicationId="pub1" />
      </NextIntlClientProvider>,
    );

    await triggerAutosave();

    // Modal is open; title key resolves through the messages fixture.
    expect(
      screen.getByText('Publication has changed'),
    ).toBeInTheDocument();
    // Both buttons present.
    expect(
      screen.getByRole('button', { name: /Reload \(lose my changes\)/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Save as new draft/i }),
    ).toBeInTheDocument();

    // Server etag passed through from BackendApiError.details into the modal.
    const dialog = screen.getByRole('dialog', { hidden: false });
    expect(dialog.getAttribute('data-server-etag')).toBe('W/"server1234567890"');
  });

  it('stale-field regression — second 412 with different details does not show first 412 server etag', async () => {
    // First 412.
    setUpMockFetch({
      failingStatus: 412,
      envelope: {
        detail: {
          error_code: 'PRECONDITION_FAILED',
          message: 'The publication has been modified since you loaded it.',
          details: {
            server_etag: 'W/"first0000000000"',
            client_etag: 'W/"client0000000000"',
          },
        },
      },
    });

    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
        <InfographicEditor publicationId="pub1" />
      </NextIntlClientProvider>,
    );

    await triggerAutosave();

    let dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('data-server-etag')).toBe('W/"first0000000000"');

    // Dismiss (Esc); modal closes — non-resolving.
    fireEvent.keyDown(document, { key: 'Escape' });

    // Swap fetch to return a different server etag, then trigger again.
    setUpMockFetch({
      failingStatus: 412,
      envelope: {
        detail: {
          error_code: 'PRECONDITION_FAILED',
          message: 'The publication has been modified since you loaded it.',
          details: {
            server_etag: 'W/"second000000000"',
            client_etag: 'W/"client0000000000"',
          },
        },
      },
    });

    await triggerAutosave();

    dialog = screen.getByRole('dialog');
    // The new modal must reflect the SECOND 412's server_etag, not the first.
    expect(dialog.getAttribute('data-server-etag')).toBe('W/"second000000000"');
  });
});
