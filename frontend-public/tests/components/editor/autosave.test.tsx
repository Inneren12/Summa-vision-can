/**
 * @jest-environment jsdom
 *
 * Stage 4 Task 2 — autosave integration tests.
 *
 * Covers:
 *   - Debounce: 2000ms quiet window after the last mutating action.
 *   - Ctrl+S cancels the pending timer and fires an immediate save.
 *   - Save-status transitions (idle → pending → saving → idle / error).
 *   - Exponential-backoff retry (2s, 4s, 8s, 16s) driven by state.saveError.
 *   - Retry budget exhaustion → banner persists with Retry button, no timer.
 *   - Manual "Retry now" resets attempt count and fires immediately.
 *   - User edit during error state resets attempt count.
 *   - beforeunload guard attaches while dirty and detaches once clean.
 *
 * Uses the shared `_admin-api-mock` helper to route `updateAdminPublication`
 * through a jest.fn() each test case configures.
 */

import './_admin-api-mock';

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import InfographicEditor from '@/components/editor';
import type { AdminPublicationResponse } from '@/lib/types/publication';
import {
  mockUpdateAdminPublication,
  MockAdminPublicationNotFoundError,
  resetAdminApiMock,
} from './_admin-api-mock';

beforeEach(() => {
  jest.useFakeTimers();
  resetAdminApiMock();
});

afterEach(() => {
  jest.useRealTimers();
});

/**
 * Run pending microtasks so the PATCH promise's .then / .catch / .finally
 * settle inside an `act` block — React state updates from those callbacks
 * otherwise leak into the next test and trigger act warnings.
 */
async function flushMicrotasks(): Promise<void> {
  // Hand control back to the microtask queue. `act` wraps state updates
  // the resolved promise schedules.
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

/**
 * Click a palette button in the LeftPanel's theme tab. This dispatches
 * a CHANGE_PAGE action, which is mutating — each call produces a new
 * `state.doc` reference and sets `dirty: true`, which re-arms the
 * autosave debounce timer.
 */
function clickPalette(name: RegExp): void {
  // Tab switch happens synchronously inside the click handler.
  const themeTab = screen.getByRole('tab', { name: /theme tab/i });
  fireEvent.click(themeTab);
  const paletteButton = screen.getByRole('button', { name });
  fireEvent.click(paletteButton);
}

describe('Autosave — debounce', () => {
  test('no PATCH fires at mount', () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor publicationId="pub1" />);
    jest.advanceTimersByTime(10_000);
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();
  });

  test('PATCH fires exactly 2000ms after the last mutating action', async () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);

    act(() => {
      jest.advanceTimersByTime(1999);
    });
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);
    expect(mockUpdateAdminPublication).toHaveBeenCalledWith('pub1', expect.any(Object));

    await flushMicrotasks();
  });

  test('rapid successive edits coalesce into a single PATCH', async () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(1000); });

    clickPalette(/palette: energy/i);
    act(() => { jest.advanceTimersByTime(1000); });

    clickPalette(/palette: society/i);
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();

    act(() => { jest.advanceTimersByTime(1999); });
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();

    act(() => { jest.advanceTimersByTime(1); });
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    await flushMicrotasks();
  });

  test('no PATCH fires when publicationId is absent', () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor />);
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(10_000); });
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();
  });
});

describe('Autosave — Ctrl+S cancels pending debounce', () => {
  test('Ctrl+S fires immediately and the debounce timer does not re-fire', async () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    expect(mockUpdateAdminPublication).not.toHaveBeenCalled();

    // Fire Ctrl+S 500ms into the debounce window.
    act(() => { jest.advanceTimersByTime(500); });
    fireEvent.keyDown(window, { key: 's', ctrlKey: true });
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    await flushMicrotasks();

    // Advance past what would have been the timer fire (500+2000ms).
    // The effect's own cleanup + the explicit cancel inside the handler
    // together ensure no second call.
    act(() => { jest.advanceTimersByTime(3000); });
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);
  });
});

describe('Autosave — status transitions', () => {
  test('idle → pending → saving → idle on success', async () => {
    let resolvePatch: (v: AdminPublicationResponse) => void = () => {};
    mockUpdateAdminPublication.mockImplementation(
      () => new Promise<AdminPublicationResponse>((resolve) => { resolvePatch = resolve; }),
    );

    render(<InfographicEditor publicationId="pub1" />);
    // Initial: no indicator (not dirty, idle).
    expect(screen.queryByTestId('save-status-indicator')).toBeNull();

    clickPalette(/palette: government/i);
    // After dispatch: dirty + pending → amber dot, data-status=pending.
    const pendingIndicator = screen.getByTestId('save-status-indicator');
    expect(pendingIndicator.getAttribute('data-status')).toBe('pending');

    act(() => { jest.advanceTimersByTime(2000); });
    // PATCH in flight → saving (pulsing).
    const savingIndicator = screen.getByTestId('save-status-indicator');
    expect(savingIndicator.getAttribute('data-status')).toBe('saving');

    await act(async () => {
      resolvePatch({} as AdminPublicationResponse);
      await Promise.resolve();
    });

    // After resolve: dirty=false, idle → indicator hidden entirely.
    expect(screen.queryByTestId('save-status-indicator')).toBeNull();
  });

  test('error state surfaces red dot + banner', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('Network down'));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();

    const indicator = screen.getByTestId('save-status-indicator');
    expect(indicator.getAttribute('data-status')).toBe('error');

    const banner = screen.getByTestId('notification-banner');
    expect(banner.getAttribute('data-kind')).toBe('save-error');
    expect(banner.textContent).toMatch(/Network down/);
  });
});

describe('Autosave — exponential backoff retry', () => {
  test('first retry fires at +2000ms, second at +4000ms, third at +8000ms, fourth at +16000ms', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('boom'));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);

    // Initial PATCH (t=2000 from debounce).
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Retry #1 at +2000ms.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);

    // Retry #2 at +4000ms.
    act(() => { jest.advanceTimersByTime(4000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(3);

    // Retry #3 at +8000ms.
    act(() => { jest.advanceTimersByTime(8000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(4);

    // Retry #4 at +16000ms.
    act(() => { jest.advanceTimersByTime(16_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(5);

    // Budget exhausted: no further retry even after long delay.
    act(() => { jest.advanceTimersByTime(60_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(5);
  });

  test('banner renders Retry button after budget is exhausted', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('still down'));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    act(() => { jest.advanceTimersByTime(4000); });
    await flushMicrotasks();
    act(() => { jest.advanceTimersByTime(8000); });
    await flushMicrotasks();
    act(() => { jest.advanceTimersByTime(16_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(5);

    // Budget exhausted — no countdown, banner still visible, Retry present.
    expect(screen.queryByTestId('retry-countdown')).toBeNull();
    expect(screen.getByTestId('retry-now-button')).toBeInTheDocument();
  });
});

describe('Autosave — manual retry', () => {
  test('clicking "Retry now" fires a save immediately and resets attempt count', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('still down'));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Click Retry while countdown is scheduled.
    const retryButton = screen.getByTestId('retry-now-button');
    fireEvent.click(retryButton);
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);

    // Attempt counter reset — next auto-retry schedules at delay[0] = 2000ms.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(3);
  });
});

describe('Autosave — user edit during error resets retry budget', () => {
  test('a new mutating edit in error state re-enters the retry cycle at delay[0]', async () => {
    mockUpdateAdminPublication.mockRejectedValue(new Error('boom'));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    // Advance through two retries → attempt counter is at 2.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    act(() => { jest.advanceTimersByTime(4000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(3);

    // User edits again. Attempt counter resets; debounce re-arms.
    clickPalette(/palette: energy/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(4);

    // Next auto-retry is at delay[0] = 2000ms (not delay[3] = 16000ms).
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(5);
  });
});

describe('Autosave — 404 produces the dedicated error message', () => {
  test('AdminPublicationNotFoundError surfaces "reload the page" copy', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new MockAdminPublicationNotFoundError('pub1'),
    );
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();

    const banner = screen.getByTestId('notification-banner');
    expect(banner.textContent).toMatch(/reload the page/i);
  });
});

describe('Autosave — beforeunload guard', () => {
  test('beforeunload event is prevented while dirty', () => {
    mockUpdateAdminPublication.mockImplementation(() => new Promise(() => {}));
    render(<InfographicEditor publicationId="pub1" />);

    clickPalette(/palette: government/i);

    const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    const preventSpy = jest.spyOn(event, 'preventDefault');
    window.dispatchEvent(event);

    expect(preventSpy).toHaveBeenCalled();
  });

  test('beforeunload does not fire preventDefault when clean', async () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);
    render(<InfographicEditor publicationId="pub1" />);

    // No edits — dirty is false, no listener attached.
    const event = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent;
    const preventSpy = jest.spyOn(event, 'preventDefault');
    window.dispatchEvent(event);

    expect(preventSpy).not.toHaveBeenCalled();
  });
});
