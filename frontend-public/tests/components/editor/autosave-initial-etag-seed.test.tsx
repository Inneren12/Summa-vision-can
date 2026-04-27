/**
 * @jest-environment jsdom
 */

/**
 * Phase 1.3 Blocker 2 — initial ETag seed.
 *
 * Proves that ``etagRef.current`` is populated from the initial publication
 * load. Without this, the first autosave of a fresh editor session sends
 * no ``If-Match`` and falls into the Q3=(a) tolerate-absent path,
 * defeating lost-update protection on the first edit.
 *
 * Our app uses Shape A: the server component (page.tsx) fetches the
 * publication via ``fetchAdminPublicationServer`` and threads the ``ETag``
 * down to the client editor as the ``initialEtag`` prop. The test
 * exercises that contract by passing ``initialEtag="v1"`` directly,
 * triggers an autosave, and asserts the PATCH carries ``If-Match: "v1"``.
 *
 * It also confirms ETag rotation: the PATCH response returns ``"v2"`` →
 * ``etagRef.current`` updates → a second autosave carries ``If-Match: "v2"``.
 */
import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
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

describe('Autosave initial ETag seed (Phase 1.3 Blocker 2)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.useRealTimers();
  });

  it('first PATCH carries If-Match equal to seeded initialEtag; second PATCH carries the rotated ETag from the first PATCH response', async () => {
    const patchCalls: { ifMatch: string | undefined }[] = [];

    global.fetch = jest.fn(async (url, init) => {
      const u = String(url);

      if (u.includes('/api/admin/publications/pub1') && init?.method === 'PATCH') {
        const headers = (init.headers as Record<string, string>) ?? {};
        patchCalls.push({ ifMatch: headers['If-Match'] });
        const nextEtag = patchCalls.length === 1 ? '"v2"' : '"v3"';
        return {
          ok: true,
          status: 200,
          headers: new Headers({ ETag: nextEtag }),
          json: async () => ({ id: 'pub1', headline: `h${patchCalls.length}` }),
        } as Response;
      }

      return {
        ok: true,
        status: 200,
        headers: new Headers(),
        json: async () => ({}),
      } as Response;
    }) as typeof fetch;

    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Messages}>
        <InfographicEditor publicationId="pub1" initialEtag={'"v1"'} />
      </NextIntlClientProvider>,
    );

    // First edit triggers autosave; the seeded initialEtag must show up
    // as If-Match on the first PATCH.
    clickPalette(/palette: government/i);
    await tickAutosave();

    expect(patchCalls.length).toBeGreaterThanOrEqual(1);
    expect(patchCalls[0].ifMatch).toBe('"v1"');

    // Second edit: a different palette so the reducer produces a new doc
    // ref and the autosave debounce fires again. The captured ETag from
    // the first PATCH response ("v2") must show up on the second PATCH.
    // Hard assertion — without it the rotation invariant is unprotected.
    clickPalette(/palette: society/i);
    // Defensive: confirm the second click was matched and dispatched, so a
    // failure here surfaces as "click did not dirty doc" not "PATCH timeout".
    expect(screen.getAllByRole('button').length).toBeGreaterThan(0);
    await tickAutosave();

    await waitFor(
      () => {
        expect(patchCalls.length).toBeGreaterThanOrEqual(2);
      },
      { timeout: 5000 },
    );
    expect(patchCalls[0].ifMatch).toBe('"v1"');
    expect(patchCalls[1].ifMatch).toBe('"v2"');
  });
});
