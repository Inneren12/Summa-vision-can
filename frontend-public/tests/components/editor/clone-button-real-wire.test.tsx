/** @jest-environment jsdom */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import enMessages from '@/../messages/en.json';

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

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
import { useRouter } from 'next/navigation';

describe('Clone button — real-wire pipeline', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: '42', status: 'DRAFT' }),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('clicking Clone fires fetch and routes to new editor on 201', async () => {
    const push = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({ push });
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    doc.review.workflow = 'published';

    render(
      <NextIntlClientProvider locale="en" messages={enMessages as Record<string, unknown>}>
        <InfographicEditor publicationId="1" initialDoc={doc} />
      </NextIntlClientProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: /clone/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/admin/publications/1/clone'),
        expect.objectContaining({ method: 'POST' }),
      );
    });

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith('/admin/editor/42');
    });
  });
});
