/**
 * @jest-environment jsdom
 */

/**
 * Phase 1.3 polish — conflict-guard regression test.
 *
 * The 'conflict' SaveStatus is the production guard that breaks the
 * "autosave → 412 → modal → Esc-dismiss → autosave → 412" loop. After a
 * non-resolving dismiss, the autosave debounce effect must short-circuit
 * (`saveStatus === 'conflict'`) and NOT issue another PATCH until the
 * user's next edit re-arms `'pending'`.
 *
 * Without this test, a future refactor could silently remove the guard
 * and the modal-reopen loop would return without surfacing in any
 * existing test.
 */
import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
import enMessages from '@/../messages/en.json';

type Messages = Record<string, unknown>;

jest.mock('next-intl', () => {
  const React = jest.requireActual('react');
  const Ctx = React.createContext({ messages: {} });
  function get(messages: Record<string, unknown>, path: string[]): unknown {
    return path.reduce<unknown>(
      (acc, k) => (acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[k] : undefined),
      messages,
    );
  }
  function useTranslations(namespace?: string) {
    const { messages } = React.useContext(Ctx) as { messages: Record<string, unknown> };
    return (key: string, params?: Record<string, unknown>) => {
      const path = (namespace ? namespace.split('.').concat(key.split('.')) : key.split('.'));
      const val = get(messages, path);
      if (typeof val !== 'string') return namespace ? `${namespace}.${key}` : key;
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
  return { useTranslations, useLocale: () => 'en', useFormatter: () => null, NextIntlClientProvider };
});

import { NextIntlClientProvider } from 'next-intl';

function clickPalette(name: RegExp): void {
  const themeTab = document.getElementById('left-tab-theme');
  fireEvent.click(themeTab!);
  const button = screen
    .getAllByRole('button')
    .find((b) => Boolean(name.exec(`palette: ${b.textContent ?? ''}`)));
  fireEvent.click(button!);
}

async function tickAutosave(): Promise<void> {
  act(() => {
    jest.advanceTimersByTime(2000);
  });
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('Phase 1.3 — conflict guard prevents autosave loop after 412 dismissal', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.useRealTimers();
  });

  it('after Esc-dismiss of 412 modal, no further PATCH fires until next user edit', async () => {
    const patchCalls: number[] = [];

    global.fetch = jest.fn(async (url, init) => {
      const u = String(url);
      if (u.includes('/api/admin/publications/pub1') && init?.method === 'PATCH') {
        patchCalls.push(Date.now());
        return {
          ok: false,
          status: 412,
          headers: new Headers({ 'Content-Type': 'application/json' }),
          json: async () => ({
            detail: {
              error_code: 'PRECONDITION_FAILED',
              message: 'Stale.',
              details: {
                server_etag: '"server"',
                client_etag: '"v1"',
              },
            },
          }),
        } as Response;
      }
      return { ok: true, status: 200, headers: new Headers(), json: async () => ({}) } as Response;
    }) as typeof fetch;

    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
        <InfographicEditor publicationId="pub1" initialEtag={'"v1"'} />
      </NextIntlClientProvider>,
    );

    // First edit → autosave fires → 412 → modal opens.
    clickPalette(/palette: government/i);
    await tickAutosave();
    expect(patchCalls.length).toBe(1);
    expect(screen.queryByRole('dialog')).not.toBeNull();

    // Esc-dismiss the modal — saveStatus flips to 'conflict'.
    fireEvent.keyDown(document, { key: 'Escape' });
    await act(async () => {
      await Promise.resolve();
    });

    // Advance time well past the debounce window. The conflict guard
    // MUST hold — no second PATCH fires despite time advancing.
    act(() => {
      jest.advanceTimersByTime(10000);
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(patchCalls.length).toBe(1); // STILL 1 — guard held

    // User makes a fresh edit — different palette, new doc reference.
    // The conflict-reset effect catches this, flips back to 'pending',
    // autosave debounce fires, and a SECOND PATCH attempts.
    clickPalette(/palette: society/i);
    await tickAutosave();

    expect(patchCalls.length).toBe(2); // Now 2 — release confirmed
  });
});
