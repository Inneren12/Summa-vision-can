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
  const themeTab = document.getElementById('left-tab-theme');
  expect(themeTab).toBeDefined();
  fireEvent.click(themeTab!);
  const paletteButton = screen
    .getAllByRole('button', { name: /theme\.option\.palette\.aria/i })
    .find((button) => name.test(`palette: ${button.textContent ?? ''}`));
  expect(paletteButton).toBeDefined();
  fireEvent.click(paletteButton!);
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

    // User edits again. Attempt counter resets; retry effect re-enters at
    // delay[0] = 2000ms (the debounce effect is the sole save orchestrator
    // during saveError, and delay[0] is functionally identical to the
    // debounce window — see Stage 4 Task 2 fix, B2).
    clickPalette(/palette: energy/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(4);

    // Call 4 advanced the attempt counter, so the next retry is at
    // delay[1] = 4000ms. This matches the exponential-backoff schedule
    // starting fresh from the edit. Pre-B2 fix the 5th call happened at
    // +2000 because the old code had a debounce timer racing the retry
    // effect — the second timer no-op'd against savingRef but injected a
    // short-latency follow-up that looked indistinguishable from a retry.
    act(() => { jest.advanceTimersByTime(4000); });
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
    expect(banner.textContent).toMatch(/publication\.not_found\.reload/i);
  });
});

describe('Autosave — terminal errors (404, Stage 4 Task 2 fix B1)', () => {
  test('AdminPublicationNotFoundError does not trigger auto-retry', async () => {
    mockUpdateAdminPublication.mockRejectedValue(
      new MockAdminPublicationNotFoundError('pub1'),
    );

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);

    // Debounce → PATCH1, which 404s.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Advance past all four retry windows (2+4+8+16 = 30s) plus slack.
    act(() => { jest.advanceTimersByTime(60_000); });
    await flushMicrotasks();

    // Still exactly one call — terminal error blocked auto-retry.
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);
  });

  test('manual "Retry now" after 404 overrides the terminal flag', async () => {
    mockUpdateAdminPublication.mockRejectedValueOnce(
      new MockAdminPublicationNotFoundError('pub1'),
    );

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Simulate publication being (re)created in another tab — next PATCH succeeds.
    mockUpdateAdminPublication.mockResolvedValueOnce({} as AdminPublicationResponse);

    const retryBtn = screen.getByTestId('retry-now-button');
    await act(async () => {
      fireEvent.click(retryBtn);
      await Promise.resolve();
    });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);
  });

  test('dismissing a 404 banner does not re-enable autosave (Stage 4 Task 2 B5)', async () => {
    // Every PATCH returns 404. If the dismiss-bypass guard is missing,
    // a second PATCH would fire 2s after the user clicks Dismiss.
    mockUpdateAdminPublication.mockRejectedValue(
      new MockAdminPublicationNotFoundError('pub1'),
    );

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);

    // First PATCH fires and 404s.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // User clicks Dismiss (✕) on the save-error banner.
    const dismissBtn = screen.getByLabelText(/dismiss save error/i);
    await act(async () => {
      fireEvent.click(dismissBtn);
      await Promise.resolve();
    });
    await flushMicrotasks();

    // Reducer cleared saveError but left dirty = true. Without the B5
    // guard the debounce effect would schedule a new PATCH here.
    // With the guard canAutoRetryRef.current is still false → no schedule.
    act(() => { jest.advanceTimersByTime(60_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);
  });

  test('user edit after 404 re-enables auto-retry for the next failure', async () => {
    mockUpdateAdminPublication.mockRejectedValueOnce(
      new MockAdminPublicationNotFoundError('pub1'),
    );

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Next attempt: transient failure. canAutoRetryRef flips back to true
    // on the incoming edit (edit-reset effect) and the retry effect will
    // schedule a backoff cycle from delay[0].
    mockUpdateAdminPublication.mockRejectedValue(new Error('network timeout'));

    clickPalette(/palette: energy/i);
    // Retry effect schedules at delay[0]=2000ms (attempt counter just reset).
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);

    // Transient failure → auto-retry at delay[1]=4000ms (attempt counter
    // advanced when call 2 fired). Advancing here proves the backoff
    // cycle is active, which is only possible because canAutoRetryRef
    // flipped back to true on the user edit.
    act(() => { jest.advanceTimersByTime(4000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(3);
  });
});

describe('Autosave — single-scheduler guarantee (Stage 4 Task 2 fix B2)', () => {
  test('edit during active saveError schedules exactly one next save', async () => {
    // First attempt fails (transient). Second PATCH — triggered by the
    // retry effect after the user edit — resolves.
    mockUpdateAdminPublication.mockRejectedValueOnce(new Error('network'));
    mockUpdateAdminPublication.mockResolvedValueOnce({} as AdminPublicationResponse);

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // saveError now set; retry scheduled at delay[0]=2000. User edits
    // during this window. The debounce effect must NOT also schedule.
    clickPalette(/palette: energy/i);

    // Advance to the retry delay boundary. Exactly one PATCH fires —
    // from the retry effect, not a racing debounce timer.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);

    // Advance further to prove no queued-up extra save fires.
    act(() => { jest.advanceTimersByTime(10_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);
  });
});

describe('Autosave — slow-PATCH re-arm (Stage 4 Task 2 fix B4)', () => {
  test('debounce fires during in-flight PATCH → reschedules and saves latest doc', async () => {
    // First PATCH hangs (controlled promise). Second PATCH resolves.
    let resolveFirstSave: (v: AdminPublicationResponse) => void = () => {};
    const firstSavePromise = new Promise<AdminPublicationResponse>((resolve) => {
      resolveFirstSave = resolve;
    });
    mockUpdateAdminPublication.mockReturnValueOnce(firstSavePromise);
    mockUpdateAdminPublication.mockResolvedValueOnce({} as AdminPublicationResponse);

    render(<InfographicEditor publicationId="pub1" />);

    // Edit 1 → first PATCH fires and hangs; savingRef becomes true.
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Edit 2 arrives while first PATCH is still in flight.
    clickPalette(/palette: energy/i);

    // Debounce timer fires at +2000ms from edit 2. savingRef is still
    // true → callback re-arms one more debounce cycle instead of
    // dropping. Pre-B4 fix this would be a silent no-op and the
    // second edit would never reach the backend until another
    // mutating action or Ctrl+S.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Resolve the first PATCH. savingRef clears.
    await act(async () => {
      resolveFirstSave({} as AdminPublicationResponse);
      await Promise.resolve();
    });

    // Re-armed timer is still scheduled. Advance the next 2000ms cycle.
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();

    // Second PATCH now fires with the post-edit-2 doc.
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(2);
  });

  test('no infinite re-arm loop when performSave proceeds normally', async () => {
    mockUpdateAdminPublication.mockResolvedValue({} as AdminPublicationResponse);

    render(<InfographicEditor publicationId="pub1" />);
    clickPalette(/palette: government/i);
    act(() => { jest.advanceTimersByTime(2000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);

    // Advance far. Re-arm only fires when savingRef is true at the
    // moment the debounce callback runs; otherwise performSave fires
    // and the timer is not re-scheduled.
    act(() => { jest.advanceTimersByTime(60_000); });
    await flushMicrotasks();
    expect(mockUpdateAdminPublication).toHaveBeenCalledTimes(1);
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
