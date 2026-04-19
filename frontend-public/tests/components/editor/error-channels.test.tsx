/**
 * @jest-environment jsdom
 *
 * Tests for the NotificationBanner priority order (B4 fix):
 *   saveError > importError > _lastRejection > importWarnings.
 *
 * The banner is rendered in isolation with controlled state so each
 * tier is exercised deterministically.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationBanner } from '@/components/editor/components/NotificationBanner';
import type { EditorState, EditorAction } from '@/components/editor/types';
import { initState } from '@/components/editor/store/reducer';

function base(overrides: Partial<EditorState> = {}): EditorState {
  return { ...initState(), ...overrides };
}

describe('NotificationBanner — error channel priority (B4)', () => {
  test('saveError wins over importError', () => {
    const state = base({ saveError: 'Network down' });
    render(
      <NotificationBanner
        state={state}
        importError="Bad import JSON"
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
      />,
    );
    const banner = screen.getByTestId('notification-banner');
    expect(banner).toHaveAttribute('data-kind', 'save-error');
    expect(banner.textContent).toMatch(/Network down/);
  });

  test('importError surfaces when saveError is null', () => {
    render(
      <NotificationBanner
        state={base()}
        importError="Bad import JSON"
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
      />,
    );
    const banner = screen.getByTestId('notification-banner');
    expect(banner).toHaveAttribute('data-kind', 'import-error');
  });

  test('saveError beats _lastRejection', () => {
    const state = base({
      saveError: 'Network down',
      _lastRejection: {
        type: 'UPDATE_PROP',
        reason: 'Blocked by workflow',
        at: Date.now(),
      },
    });
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
      />,
    );
    const banner = screen.getByTestId('notification-banner');
    expect(banner).toHaveAttribute('data-kind', 'save-error');
  });

  test('Dismiss button dispatches DISMISS_SAVE_ERROR without touching dirty', () => {
    const state = base({ saveError: 'oops', dirty: true });
    const dispatched: EditorAction[] = [];
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={(action) => dispatched.push(action)}
      />,
    );
    const dismiss = screen.getByRole('button', { name: /dismiss save error/i });
    fireEvent.click(dismiss);
    expect(dispatched).toEqual([{ type: 'DISMISS_SAVE_ERROR' }]);
  });
});
