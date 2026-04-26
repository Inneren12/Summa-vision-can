/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import type { AdminPublicationResponse } from '@/lib/types/publication';
import enMessages from '@/../messages/en.json';
import ruMessages from '@/../messages/ru.json';

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
      const explode = (value: string) => value['split']('.');
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

jest.mock('@/lib/api/admin', () => {
  const mockUpdateAdminPublication = jest.fn<
    Promise<AdminPublicationResponse>,
    [string, unknown]
  >();

  class AdminPublicationNotFoundError extends Error {
    constructor(public readonly id: string) {
      super(`Publication ${id} not found`);
      this.name = 'AdminPublicationNotFoundError';
    }
  }

  class BackendApiError extends Error {
    public readonly status: number;
    public readonly code: string | null;
    public readonly details: Record<string, unknown> | null;

    constructor(args: {
      status: number;
      code: string | null;
      message: string;
      details: Record<string, unknown> | null;
    }) {
      super(args.message);
      this.name = 'BackendApiError';
      this.status = args.status;
      this.code = args.code;
      this.details = args.details;
    }
  }

  return {
    __esModule: true,
    updateAdminPublication: mockUpdateAdminPublication,
    __mockUpdateAdminPublication: mockUpdateAdminPublication,
    AdminPublicationNotFoundError,
    BackendApiError,
  };
});

import InfographicEditor from '@/components/editor';
import { NextIntlClientProvider } from 'next-intl';
import {
  __mockUpdateAdminPublication as mockUpdateAdminPublication,
  AdminPublicationNotFoundError,
  BackendApiError,
} from '@/lib/api/admin';

function renderEditor(locale: 'en' | 'ru'): void {
  const messages = (locale === 'ru' ? ruMessages : enMessages) as Messages;
  render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <InfographicEditor publicationId="pub1" />
    </NextIntlClientProvider>,
  );
}

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

beforeEach(() => {
  jest.useFakeTimers();
  mockUpdateAdminPublication.mockReset();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('Autosave backend error-code wiring', () => {
  it('404 nested PUBLICATION_NOT_FOUND in EN locale shows localized not-found banner', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new AdminPublicationNotFoundError('pub1'),
    );
    renderEditor('en');

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent(
      'Publication not found — reload the page',
    );
  });

  it('422 nested PUBLICATION_UPDATE_PAYLOAD_INVALID in RU locale shows overridden RU message', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new BackendApiError({
        status: 422,
        code: 'PUBLICATION_UPDATE_PAYLOAD_INVALID',
        message: 'The submitted changes are invalid.',
        details: { validation_errors: [] },
      }),
    );
    renderEditor('ru');

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent(
      'Не удалось сохранить изменения. Проверьте поля и повторите попытку.',
    );
  });

  it('401 flat AUTH_API_KEY_INVALID in RU locale shows localized auth banner', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new BackendApiError({
        status: 401,
        code: 'AUTH_API_KEY_INVALID',
        message: 'Invalid API key',
        details: null,
      }),
    );
    renderEditor('ru');

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent(
      'Ошибка аутентификации администратора. Проверьте настройки доступа API.',
    );
  });

  it('429 flat AUTH_ADMIN_RATE_LIMITED in EN locale shows localized rate-limit banner', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new BackendApiError({
        status: 429,
        code: 'AUTH_ADMIN_RATE_LIMITED',
        message: 'Rate limited',
        details: null,
      }),
    );
    renderEditor('en');

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent(
      'Too many admin requests. Wait a moment and try again.',
    );
  });

  it('500 with plain Error(boom) preserves legacy message fallback', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('boom'));
    renderEditor('en');

    await triggerAutosaveAndWaitForBanner();

    expect(screen.getByTestId('notification-banner')).toHaveTextContent('boom');
  });
});
