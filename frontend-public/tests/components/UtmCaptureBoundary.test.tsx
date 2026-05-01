/**
 * Phase 2.3 — UtmCaptureBoundary mount-time capture test.
 *
 * The boundary lives at root layout so that UTM params are captured
 * before any client-side navigation can strip them from window.location.
 */
import { render } from '@testing-library/react';
import { UtmCaptureBoundary } from '@/components/UtmCaptureBoundary';
import { UTM_STORAGE_KEY } from '@/lib/attribution/utm';

describe('UtmCaptureBoundary', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
    window.sessionStorage.clear();
  });

  it('persists URL UTM to sessionStorage on mount', () => {
    window.history.pushState(
      {},
      '',
      '/g/42?utm_source=reddit&utm_medium=social&utm_campaign=publish_kit&utm_content=ln_xyz',
    );

    render(
      <UtmCaptureBoundary>
        <div data-testid="child">child</div>
      </UtmCaptureBoundary>,
    );

    const stored = JSON.parse(
      window.sessionStorage.getItem(UTM_STORAGE_KEY) ?? '{}',
    );
    expect(stored).toEqual({
      utm_source: 'reddit',
      utm_medium: 'social',
      utm_campaign: 'publish_kit',
      utm_content: 'ln_xyz',
    });
  });

  it('does not write to sessionStorage on a clean URL', () => {
    render(
      <UtmCaptureBoundary>
        <div />
      </UtmCaptureBoundary>,
    );

    expect(window.sessionStorage.getItem(UTM_STORAGE_KEY)).toBeNull();
  });

  it('renders children unchanged', () => {
    const { getByTestId } = render(
      <UtmCaptureBoundary>
        <div data-testid="child">hello</div>
      </UtmCaptureBoundary>,
    );

    expect(getByTestId('child').textContent).toBe('hello');
  });
});
