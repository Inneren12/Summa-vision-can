import React from 'react';
import { render } from '@testing-library/react';
import { LeftPanel } from '../../src/components/editor/components/LeftPanel';
import { PERMS } from '../../src/components/editor/store/permissions';
import { initState } from '../../src/components/editor/store/reducer';
import ruMessages from '../../messages/ru.json';

const EN_UI_DENYLIST = [
  'Inspector',
  'Review',
  'Select a block',
  'from Blocks tab',
  'Right rail',
  'Export as PNG',
];

jest.mock('next-intl', () => {
  const React = jest.requireActual('react');
  type Messages = Record<string, unknown>;
  const Ctx = React.createContext<{ messages: Messages }>({ messages: {} });

  function get(messages: Messages, path: string[]): unknown {
    return path.reduce<unknown>((acc, key) => (
      acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[key] : undefined
    ), messages);
  }

  function useTranslations(namespace: string) {
    const { messages } = React.useContext(Ctx);
    return (key: string) => {
      const val = get(messages, [...namespace.split('.'), ...key.split('.')]);
      return typeof val === 'string' ? val : `${namespace}.${key}`;
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
    useLocale: () => 'ru',
    useFormatter: () => null,
    NextIntlClientProvider,
  };
});

import { NextIntlClientProvider, useTranslations } from 'next-intl';
type Messages = Record<string, unknown>;

function renderInRu(component: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="ru" messages={ruMessages as Messages}>
      {component}
    </NextIntlClientProvider>,
  );
}

function findDeniedEnglishPhrases(text: string): string[] {
  return EN_UI_DENYLIST.filter((phrase) => text.includes(phrase));
}

function TestHook() {
  const t = useTranslations('qa');
  return <span>{t('title')}</span>;
}

describe('i18n — no EN leakage in RU mode', () => {
  it('provider wiring smoke — real translations resolve', () => {
    const { getByText, queryByText } = renderInRu(<TestHook />);
    expect(getByText('QA')).toBeInTheDocument();
    expect(queryByText('qa.title')).not.toBeInTheDocument();
  });

  it('LeftPanel renders without English UI chrome leak', () => {
    const state = initState();
    const { container } = renderInRu(
      <LeftPanel
        doc={state.doc}
        dispatch={jest.fn()}
        selId={state.selectedBlockId}
        ltab="blocks"
        setLtab={jest.fn()}
        effectivePerms={PERMS.design}
      />,
    );

    expect(findDeniedEnglishPhrases(container.textContent ?? '')).toEqual([]);
  });
});
