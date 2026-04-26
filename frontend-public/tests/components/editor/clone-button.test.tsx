/** @jest-environment jsdom */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import enMessages from '@/../messages/en.json';

jest.mock('@/lib/api/admin', () => ({
  ...jest.requireActual('@/lib/api/admin'),
  cloneAdminPublication: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
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
import { cloneAdminPublication, BackendApiError } from '@/lib/api/admin';

const cloneMock = cloneAdminPublication as jest.Mock;

function renderEditor(workflow: 'draft' | 'published') {
  const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
  doc.review.workflow = workflow;
  render(
    <NextIntlClientProvider locale="en" messages={enMessages as Record<string, unknown>}>
      <InfographicEditor publicationId="1" initialDoc={doc} />
    </NextIntlClientProvider>,
  );
}

describe('Clone button component states', () => {
  beforeEach(() => {
    cloneMock.mockReset();
  });

  it('renders enabled when workflow is published', () => {
    renderEditor('published');
    expect(screen.getByRole('button', { name: /^clone$/i })).toBeEnabled();
  });

  it('renders disabled when workflow is draft', () => {
    renderEditor('draft');
    expect(screen.getByRole('button', { name: /^clone$/i })).toBeDisabled();
  });

  it('is disabled while clone is in flight', async () => {
    cloneMock.mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve({ id: '2' }), 10)));
    renderEditor('published');
    const btn = screen.getByRole('button', { name: /^clone$/i });
    fireEvent.click(btn);
    expect(screen.getByRole('button', { name: /cloning/i })).toBeDisabled();
    await waitFor(() => expect(cloneMock).toHaveBeenCalled());
  });

  it('shows localized message on 409 backend code', async () => {
    cloneMock.mockRejectedValue(
      new BackendApiError({
        status: 409,
        code: 'PUBLICATION_CLONE_NOT_ALLOWED',
        message: 'cannot clone draft',
        details: { current_status: 'DRAFT' },
      }),
    );

    renderEditor('published');
    fireEvent.click(screen.getByRole('button', { name: /^clone$/i }));

    await waitFor(() => {
      expect(screen.getByTestId('notification-banner')).toHaveTextContent(
        'This publication cannot be cloned because it is not yet published.',
      );
    });
  });
});
