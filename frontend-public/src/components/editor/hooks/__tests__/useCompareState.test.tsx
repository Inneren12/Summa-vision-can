import { renderHook, act, waitFor } from '@testing-library/react';
import { useCompareState } from '../useCompareState';
import type { CompareResponse } from '@/lib/types/compare';

jest.mock('@/lib/api/admin', () => {
  const actual = jest.requireActual('@/lib/api/admin');
  return {
    ...actual,
    comparePublication: jest.fn(),
  };
});

import { comparePublication } from '@/lib/api/admin';

const mockedCompare = comparePublication as jest.MockedFunction<
  typeof comparePublication
>;

const okResult: CompareResponse = {
  publication_id: 1,
  overall_status: 'fresh',
  overall_severity: 'info',
  compared_at: '2026-05-04T00:00:00Z',
  block_results: [],
};

describe('useCompareState', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initial state is idle', () => {
    const { result } = renderHook(() => useCompareState('42'));
    expect(result.current.state.kind).toBe('idle');
  });

  it('compare() success transitions idle → loading → success', async () => {
    mockedCompare.mockResolvedValue(okResult);
    const { result } = renderHook(() => useCompareState('42'));

    act(() => {
      result.current.compare();
    });
    expect(result.current.state.kind).toBe('loading');

    await waitFor(() => expect(result.current.state.kind).toBe('success'));
    if (result.current.state.kind === 'success') {
      // Empty block_results falls through to overall_status: 'fresh' (okResult.overall_status)
      expect(result.current.state.badge).toBe('fresh');
    }
  });

  it('compare() error transitions idle → loading → error', async () => {
    const err = new Error('Network');
    mockedCompare.mockRejectedValue(err);
    const { result } = renderHook(() => useCompareState('42'));

    act(() => {
      result.current.compare();
    });

    await waitFor(() => expect(result.current.state.kind).toBe('error'));
    if (result.current.state.kind === 'error') {
      expect(result.current.state.error).toBe(err);
    }
  });

  it('aborts in-flight request on unmount', () => {
    let capturedSignal: AbortSignal | undefined;
    mockedCompare.mockImplementation((_id, opts) => {
      capturedSignal = opts?.signal;
      return new Promise(() => {});
    });
    const { result, unmount } = renderHook(() => useCompareState('42'));
    act(() => {
      result.current.compare();
    });
    unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it('re-compare cancels prior in-flight request', () => {
    const signals: AbortSignal[] = [];
    mockedCompare.mockImplementation((_id, opts) => {
      if (opts?.signal) signals.push(opts.signal);
      return new Promise(() => {});
    });
    const { result } = renderHook(() => useCompareState('42'));

    act(() => {
      result.current.compare();
    });
    act(() => {
      result.current.compare();
    });

    expect(signals.length).toBe(2);
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });

  it('reset() returns state to idle and aborts in-flight', () => {
    let capturedSignal: AbortSignal | undefined;
    mockedCompare.mockImplementation((_id, opts) => {
      capturedSignal = opts?.signal;
      return new Promise(() => {});
    });
    const { result } = renderHook(() => useCompareState('42'));
    act(() => {
      result.current.compare();
    });
    act(() => {
      result.current.reset();
    });
    expect(result.current.state.kind).toBe('idle');
    expect(capturedSignal?.aborted).toBe(true);
  });

  it('does not call API when publicationId is empty string', () => {
    const { result } = renderHook(() => useCompareState(''));
    act(() => {
      result.current.compare();
    });
    expect(mockedCompare).not.toHaveBeenCalled();
    expect(result.current.state.kind).toBe('idle');
  });
});
