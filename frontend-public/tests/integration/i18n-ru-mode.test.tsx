import React from 'react';
import { render } from '@testing-library/react';
import { LeftPanel } from '../../src/components/editor/components/LeftPanel';
import { Inspector } from '../../src/components/editor/components/Inspector';
import { ReviewPanel } from '../../src/components/editor/components/ReviewPanel';
import { PERMS } from '../../src/components/editor/store/permissions';
import { initState } from '../../src/components/editor/store/reducer';
import { BREG } from '../../src/components/editor/registry/blocks';
import ruMessages from '../../messages/ru.json';

const nextIntlMock = jest.requireMock('next-intl') as {
  useTranslations: jest.Mock;
};

const EN_UI_DENYLIST = [
  'Inspector',
  'Review',
  'Select a block',
  'from Blocks tab',
  'Show resolved',
  'No threads to show',
  'History',
  'Add comment',
  'Reply',
  'Comment deleted',
  'Benchmark line',
  'Area fill',
  'Right rail',
  'Export as PNG',
];

function get(obj: unknown, path: string[]): unknown {
  return path.reduce<unknown>((acc, key) => (
    acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[key] : undefined
  ), obj);
}

function installRuTranslations(): void {
  nextIntlMock.useTranslations.mockImplementation((namespace: string) => {
    return (key: string, params?: Record<string, unknown>) => {
      const fullPath = [...namespace.split('.'), ...key.split('.')];
      const raw = get(ruMessages, fullPath);
      if (typeof raw !== 'string') return `${namespace}.${key}`;
      return raw.replace(/\{(\w+)\}/g, (_, token: string) => String(params?.[token] ?? `{${token}}`));
    };
  });
}

function findDeniedEnglishPhrases(text: string): string[] {
  return EN_UI_DENYLIST.filter((phrase) => text.includes(phrase));
}

describe('i18n — no EN leakage in RU mode', () => {
  beforeEach(() => {
    installRuTranslations();
  });

  it('LeftPanel renders without English UI chrome leak', () => {
    const state = initState();
    const { container } = render(
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

  it('Inspector renders without English UI chrome leak', () => {
    const state = initState();
    const selId = Object.keys(state.doc.blocks)[0] ?? null;
    const selB = selId ? state.doc.blocks[selId] : null;
    const selR = selB ? BREG[selB.type] : null;
    const { container } = render(
      <Inspector
        selB={selB}
        selR={selR}
        selId={selId}
        mode="design"
        canEdit={() => true}
        dispatch={jest.fn()}
        contrastIssues={[]}
      />,
    );
    expect(findDeniedEnglishPhrases(container.textContent ?? '')).toEqual([]);
  });

  it('ReviewPanel renders without English UI chrome leak', () => {
    const state = initState();
    const { container } = render(
      <ReviewPanel
        state={state}
        dispatch={jest.fn()}
        onRequestNote={jest.fn()}
      />,
    );
    expect(findDeniedEnglishPhrases(container.textContent ?? '')).toEqual([]);
  });
});
