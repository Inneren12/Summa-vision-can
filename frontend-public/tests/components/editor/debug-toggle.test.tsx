/**
 * @jest-environment jsdom
 *
 * Stage 4 Task 4 integration tests for the debug-overlay toggle.
 * Covers availability gating (dev always / prod with `?debug=1`),
 * button state flips, and keyboard shortcut behaviour.
 */

import { render, fireEvent } from '@testing-library/react';
import InfographicEditor from '@/components/editor';

const ORIG_ENV = process.env.NODE_ENV;

function setNodeEnv(v: 'development' | 'production' | 'test'): void {
  // NODE_ENV is typed as readonly under @types/node; the runtime value is
  // plain and assignable. Casting locally is cleaner than disabling the
  // whole rule at the file level.
  (process.env as Record<string, string | undefined>).NODE_ENV = v;
}

afterEach(() => {
  setNodeEnv(ORIG_ENV as 'development' | 'production' | 'test');
});

describe('Debug overlay toggle', () => {
  test('DBG button visible in development; clicking toggles state (aria-label flips)', () => {
    setNodeEnv('development');
    const { getByText, queryByLabelText } = render(<InfographicEditor />);
    const btn = getByText('DBG').closest('button')!;
    expect(btn.getAttribute('aria-label')).toMatch(/enable debug overlay/i);
    fireEvent.click(btn);
    expect(queryByLabelText(/disable debug overlay/i)).not.toBeNull();
  });

  test('DBG button hidden in production without ?debug=1', () => {
    setNodeEnv('production');
    // jsdom default location has no search; no need to tweak.
    const { queryByText } = render(<InfographicEditor />);
    expect(queryByText('DBG')).toBeNull();
  });

  test('DBG button appears in production when ?debug=1', async () => {
    setNodeEnv('production');
    // jsdom refuses Object.defineProperty on window.location.search, but
    // history.pushState mutates it legitimately.
    window.history.pushState({}, '', '?debug=1');
    try {
      const { findByText } = render(<InfographicEditor />);
      const btn = await findByText('DBG');
      expect(btn).toBeInTheDocument();
    } finally {
      window.history.pushState({}, '', '/');
    }
  });

  test('Ctrl+Shift+D toggles debug in development', () => {
    setNodeEnv('development');
    const { getByText, queryByLabelText } = render(<InfographicEditor />);
    expect(getByText('DBG')).toBeInTheDocument();
    expect(queryByLabelText(/enable debug overlay/i)).not.toBeNull();
    fireEvent.keyDown(window, { key: 'd', ctrlKey: true, shiftKey: true });
    expect(queryByLabelText(/disable debug overlay/i)).not.toBeNull();
    fireEvent.keyDown(window, { key: 'd', ctrlKey: true, shiftKey: true });
    expect(queryByLabelText(/enable debug overlay/i)).not.toBeNull();
  });

  test('Ctrl+Shift+D is ignored in production without ?debug=1', () => {
    setNodeEnv('production');
    const { queryByText } = render(<InfographicEditor />);
    expect(queryByText('DBG')).toBeNull();
    fireEvent.keyDown(window, { key: 'd', ctrlKey: true, shiftKey: true });
    // Button still absent — the shortcut branch bails when !debugAvailable.
    expect(queryByText('DBG')).toBeNull();
  });
});
