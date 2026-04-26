/**
 * @jest-environment jsdom
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { TopBar } from '@/components/editor/components/TopBar';
import { TPLS, mkDoc } from '@/components/editor/registry/templates';
import type { EditorAction } from '@/components/editor/types';

function makeDoc() {
  return mkDoc('single_stat_hero', TPLS.single_stat_hero);
}

function renderTopBar(overrides: Partial<React.ComponentProps<typeof TopBar>> = {}) {
  const fileRef = React.createRef<HTMLInputElement>();
  const baseProps: React.ComponentProps<typeof TopBar> = {
    doc: makeDoc(),
    dispatch: (() => undefined) as React.Dispatch<EditorAction>,
    undoStack: [],
    redoStack: [],
    dirty: false,
    mode: 'design',
    setMode: () => undefined,
    errs: 0,
    warns: 0,
    si: '0err · 0warn',
    canExp: true,
    fileRef,
    importJSON: () => undefined,
    exportJSON: () => undefined,
    markSaved: () => undefined,
    exportPNG: () => undefined,
    saveStatus: 'idle',
    fontsReady: true,
  };
  return render(<TopBar {...baseProps} {...overrides} />);
}

describe('TopBar — Crop zone toggle', () => {
  test('renders Crop button when onToggleCropZone provided', () => {
    renderTopBar({ onToggleCropZone: () => undefined, cropZoneAvailable: true });
    expect(screen.getByRole('button', { name: 'editor.actions.cropZone' })).toBeInTheDocument();
  });

  test('Crop button is disabled when cropZoneAvailable=false', () => {
    renderTopBar({ onToggleCropZone: () => undefined, cropZoneAvailable: false });
    expect(screen.getByRole('button', { name: 'editor.actions.cropZone' })).toBeDisabled();
  });

  test('clicking Crop button fires onToggleCropZone', () => {
    const handler = jest.fn();
    renderTopBar({ onToggleCropZone: handler, cropZoneAvailable: true });
    fireEvent.click(screen.getByRole('button', { name: 'editor.actions.cropZone' }));
    expect(handler).toHaveBeenCalledTimes(1);
  });

  test('active visual state when cropZoneEnabled=true', () => {
    const { rerender } = renderTopBar({
      onToggleCropZone: () => undefined,
      cropZoneAvailable: true,
      cropZoneEnabled: false,
    });
    const inactiveStyle = screen.getByRole('button', { name: 'editor.actions.cropZone' }).getAttribute('style');

    rerender(
      <TopBar
        doc={makeDoc()}
        dispatch={(() => undefined) as React.Dispatch<EditorAction>}
        undoStack={[]}
        redoStack={[]}
        dirty={false}
        mode="design"
        setMode={() => undefined}
        errs={0}
        warns={0}
        si="0err · 0warn"
        canExp={true}
        fileRef={React.createRef<HTMLInputElement>()}
        importJSON={() => undefined}
        exportJSON={() => undefined}
        markSaved={() => undefined}
        exportPNG={() => undefined}
        saveStatus="idle"
        fontsReady={true}
        onToggleCropZone={() => undefined}
        cropZoneAvailable={true}
        cropZoneEnabled={true}
      />,
    );

    const activeStyle = screen.getByRole('button', { name: 'editor.actions.cropZone' }).getAttribute('style');
    expect(activeStyle).not.toEqual(inactiveStyle);
  });

  test('Crop button is not visually active when enabled but unavailable', () => {
    renderTopBar({
      onToggleCropZone: () => undefined,
      cropZoneAvailable: false,
      cropZoneEnabled: true,
    });
    const style = screen
      .getByRole('button', { name: 'editor.actions.cropZone' })
      .getAttribute('style') || '';
    expect(style).toContain('font-weight: 400');
  });
});
