/**
 * Phase 3.1d Slice 3b — ResolvePreview component tests.
 *
 * Mocks `fetchResolvedValue` from `@/lib/api/admin-resolve` and exercises
 * the debounce / loading / success / error states. Locale strings come
 * from the project-wide next-intl mock (`src/__mocks__/next-intl/index.ts`):
 * `useTranslations(ns)` returns `(key) => "${ns}.${key}"`, so error
 * branches render dotted-key identifiers (e.g. "publication.binding.
 * resolve.mapping_not_found").
 */
import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import type { SingleValueBinding } from '../types';

jest.mock('@/lib/api/admin-resolve', () => {
  class ResolveFetchError extends Error {
    constructor(
      public status: number,
      public code: string,
      message: string,
    ) {
      super(message);
      this.name = 'ResolveFetchError';
    }
  }
  return {
    fetchResolvedValue: jest.fn(),
    ResolveFetchError,
  };
});

import {
  fetchResolvedValue,
  ResolveFetchError,
} from '@/lib/api/admin-resolve';
import { ResolvePreview } from '../ResolvePreview';

const mockFetch = fetchResolvedValue as jest.MockedFunction<
  typeof fetchResolvedValue
>;

function makeBinding(
  overrides: Partial<SingleValueBinding> = {},
): SingleValueBinding {
  return {
    kind: 'single',
    cube_id: '18100004',
    semantic_key: 'metric_x',
    filters: { geo: 'CA' },
    period: '2024-Q3',
    ...overrides,
  };
}

function neverResolves<T>(): Promise<T> {
  return new Promise(() => {});
}

beforeEach(() => {
  jest.useFakeTimers();
  mockFetch.mockReset();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('ResolvePreview — null binding', () => {
  it('renders nothing when binding is null', () => {
    render(<ResolvePreview binding={null} />);
    expect(screen.queryByTestId('resolve-preview')).toBeNull();
    expect(mockFetch).not.toHaveBeenCalled();
  });
});

describe('ResolvePreview — loading state', () => {
  it('renders loading state immediately when binding is set, before debounce fires', () => {
    mockFetch.mockReturnValue(neverResolves());
    render(<ResolvePreview binding={makeBinding()} />);
    // Loading state is set synchronously when binding is non-null;
    // debounce delays only the actual fetch.
    expect(screen.getByTestId('resolve-preview-loading')).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('does not call fetchResolvedValue until debounce elapses', () => {
    mockFetch.mockReturnValue(neverResolves());
    render(<ResolvePreview binding={makeBinding()} />);
    act(() => {
      jest.advanceTimersByTime(290);
    });
    expect(mockFetch).not.toHaveBeenCalled();
    act(() => {
      jest.advanceTimersByTime(20);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

describe('ResolvePreview — success state', () => {
  it('renders value, units, period, and cache_status hit badge', async () => {
    mockFetch.mockResolvedValueOnce({
      cube_id: '18100004',
      semantic_key: 'metric_x',
      coord: '1.1.0.0.0.0.0.0.0.0',
      period: '2024-Q3',
      value: '6.73',
      missing: false,
      resolved_at: '2026-05-07T00:00:00Z',
      source_hash: 'h',
      is_stale: false,
      units: '%',
      cache_status: 'hit',
      mapping_version: 1,
    });
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(screen.getByTestId('resolve-preview-success')).toBeInTheDocument(),
    );
    const success = screen.getByTestId('resolve-preview-success');
    expect(success).toHaveTextContent('6.73');
    expect(success).toHaveTextContent('%');
    expect(success).toHaveTextContent('(2024-Q3)');
    expect(screen.getByTestId('resolve-preview-cache-status')).toHaveTextContent(
      'hit',
    );
  });

  it('renders cache_status primed badge', async () => {
    mockFetch.mockResolvedValueOnce({
      cube_id: '18100004',
      semantic_key: 'metric_x',
      coord: '1.1.0.0.0.0.0.0.0.0',
      period: '2024-Q3',
      value: '1',
      missing: false,
      resolved_at: '2026-05-07T00:00:00Z',
      source_hash: 'h',
      is_stale: false,
      units: null,
      cache_status: 'primed',
      mapping_version: null,
    });
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-cache-status'),
      ).toHaveTextContent('primed'),
    );
  });

  it('renders "missing" placeholder when missing is true', async () => {
    mockFetch.mockResolvedValueOnce({
      cube_id: '18100004',
      semantic_key: 'metric_x',
      coord: '1.1.0.0.0.0.0.0.0.0',
      period: '2024-Q3',
      value: null,
      missing: true,
      resolved_at: '2026-05-07T00:00:00Z',
      source_hash: 'h',
      is_stale: false,
      units: null,
      cache_status: 'hit',
      mapping_version: null,
    });
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(screen.getByTestId('resolve-preview-success')).toHaveTextContent(
        'missing',
      ),
    );
  });

  it('renders "null" placeholder when value is null and missing is false', async () => {
    mockFetch.mockResolvedValueOnce({
      cube_id: '18100004',
      semantic_key: 'metric_x',
      coord: '1.1.0.0.0.0.0.0.0.0',
      period: '2024-Q3',
      value: null,
      missing: false,
      resolved_at: '2026-05-07T00:00:00Z',
      source_hash: 'h',
      is_stale: false,
      units: null,
      cache_status: 'hit',
      mapping_version: null,
    });
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(screen.getByTestId('resolve-preview-success')).toHaveTextContent(
        'null',
      ),
    );
  });
});

describe('ResolvePreview — error states', () => {
  it('renders mapping_not_found locale when error code is MAPPING_NOT_FOUND', async () => {
    mockFetch.mockRejectedValueOnce(
      new ResolveFetchError(404, 'MAPPING_NOT_FOUND', 'no mapping'),
    );
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-error-mapping_not_found'),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId('resolve-preview-error-mapping_not_found'),
    ).toHaveTextContent('publication.binding.resolve.mapping_not_found');
  });

  it('renders cache_miss locale when error code is RESOLVE_CACHE_MISS', async () => {
    mockFetch.mockRejectedValueOnce(
      new ResolveFetchError(404, 'RESOLVE_CACHE_MISS', 'cache miss'),
    );
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-error-resolve_cache_miss'),
      ).toHaveTextContent('publication.binding.resolve.cache_miss'),
    );
  });

  it('renders invalid_filters locale when error code is RESOLVE_INVALID_FILTERS', async () => {
    mockFetch.mockRejectedValueOnce(
      new ResolveFetchError(400, 'RESOLVE_INVALID_FILTERS', 'bad filters'),
    );
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-error-resolve_invalid_filters'),
      ).toHaveTextContent('publication.binding.resolve.invalid_filters'),
    );
  });

  it('renders raw message when error code is UNKNOWN', async () => {
    mockFetch.mockRejectedValueOnce(
      new ResolveFetchError(500, 'UNKNOWN', 'something blew up'),
    );
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-error-unknown'),
      ).toHaveTextContent('something blew up'),
    );
  });

  it('falls back to UNKNOWN when error is not a ResolveFetchError', async () => {
    mockFetch.mockRejectedValueOnce(new Error('network down'));
    render(<ResolvePreview binding={makeBinding()} />);
    await act(async () => {
      jest.advanceTimersByTime(310);
    });
    await waitFor(() =>
      expect(
        screen.getByTestId('resolve-preview-error-unknown'),
      ).toHaveTextContent('network down'),
    );
  });
});

describe('ResolvePreview — debounce + abort behaviour', () => {
  it('aborts in-flight fetch when binding changes before completion', async () => {
    let firstSignal: AbortSignal | undefined;
    mockFetch.mockImplementationOnce((_b, opts) => {
      firstSignal = opts?.signal;
      return neverResolves();
    });
    mockFetch.mockResolvedValueOnce({
      cube_id: '18100004',
      semantic_key: 'metric_x',
      coord: '1.1.0.0.0.0.0.0.0.0',
      period: '2024-Q3',
      value: '1',
      missing: false,
      resolved_at: '2026-05-07T00:00:00Z',
      source_hash: 'h',
      is_stale: false,
      units: null,
      cache_status: 'hit',
      mapping_version: null,
    });

    const b1 = makeBinding({ filters: { geo: 'CA' } });
    const b2 = makeBinding({ filters: { geo: 'ON' } });

    const { rerender } = render(<ResolvePreview binding={b1} />);
    act(() => {
      jest.advanceTimersByTime(310);
    });
    expect(firstSignal?.aborted).toBe(false);

    rerender(<ResolvePreview binding={b2} />);
    // Re-render aborts the previous controller synchronously.
    expect(firstSignal?.aborted).toBe(true);
  });

  it('clears debounce timer when binding becomes null mid-debounce', () => {
    mockFetch.mockReturnValue(neverResolves());
    const { rerender } = render(<ResolvePreview binding={makeBinding()} />);
    act(() => {
      jest.advanceTimersByTime(150);
    });
    expect(mockFetch).not.toHaveBeenCalled();

    rerender(<ResolvePreview binding={null} />);
    act(() => {
      jest.advanceTimersByTime(500);
    });
    // Still no fetch — debounce was cleared and binding is null.
    expect(mockFetch).not.toHaveBeenCalled();
    expect(screen.queryByTestId('resolve-preview')).toBeNull();
  });

  it('does not refetch when binding fingerprint is unchanged across re-renders', () => {
    mockFetch.mockReturnValue(neverResolves());
    const b = makeBinding();
    const { rerender } = render(<ResolvePreview binding={b} />);
    act(() => {
      jest.advanceTimersByTime(310);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Re-render with a structurally-identical binding object — fingerprint
    // (JSON.stringify) is unchanged → effect should not re-run.
    rerender(<ResolvePreview binding={{ ...b }} />);
    act(() => {
      jest.advanceTimersByTime(310);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
