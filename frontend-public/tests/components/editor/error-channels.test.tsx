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

describe('NotificationBanner — Stage 4 Task 2 retry UX', () => {
  test('renders "Retrying in Xs…" when retryCountdownMs is set', () => {
    const state = base({ saveError: 'Network down' });
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
        retryCountdownMs={4000}
      />,
    );
    const countdown = screen.getByTestId('retry-countdown');
    expect(countdown.textContent).toMatch(/Retrying in 4s/);
  });

  test('countdown rounds up (3500ms → "4s")', () => {
    const state = base({ saveError: 'oops' });
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
        retryCountdownMs={3500}
      />,
    );
    expect(screen.getByTestId('retry-countdown').textContent).toMatch(/4s/);
  });

  test('hides countdown when retryCountdownMs is null (budget exhausted)', () => {
    const state = base({ saveError: 'exhausted' });
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
        retryCountdownMs={null}
        onManualRetry={() => {}}
      />,
    );
    expect(screen.queryByTestId('retry-countdown')).toBeNull();
  });

  test('"Retry now" button renders when onManualRetry is provided and click invokes it', () => {
    const state = base({ saveError: 'oops' });
    const onRetry = jest.fn();
    render(
      <NotificationBanner
        state={state}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
        dispatch={() => {}}
        retryCountdownMs={null}
        onManualRetry={onRetry}
      />,
    );
    const button = screen.getByTestId('retry-now-button');
    fireEvent.click(button);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  test('"Retry now" is absent when onManualRetry is omitted', () => {
    const state = base({ saveError: 'oops' });
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
    expect(screen.queryByTestId('retry-now-button')).toBeNull();
  });
});
