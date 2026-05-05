import {
  compareReducer,
  initialCompareState,
  type CompareState,
} from '../compareReducer';
import type { CompareResponse } from '@/lib/types/compare';

const okResult: CompareResponse = {
  publication_id: 1,
  overall_status: 'fresh',
  overall_severity: 'info',
  compared_at: '2026-05-04T00:00:00Z',
  block_results: [],
};

describe('compareReducer', () => {
  it('idle → loading on compare:start', () => {
    const next = compareReducer(initialCompareState, {
      type: 'compare:start',
      startedAt: 12345,
    });
    expect(next).toEqual({ kind: 'loading', startedAt: 12345 });
  });

  it('loading → success on compare:success with computed badge', () => {
    const loading: CompareState = { kind: 'loading', startedAt: 0 };
    const next = compareReducer(loading, {
      type: 'compare:success',
      result: okResult,
    });
    expect(next.kind).toBe('success');
    if (next.kind === 'success') {
      // Empty block_results falls through to overall_status: 'fresh'
      expect(next.badge).toBe('fresh');
      expect(next.result).toBe(okResult);
      expect(next.comparedAt).toBe(okResult.compared_at);
    }
  });

  it('loading → error on compare:error', () => {
    const loading: CompareState = { kind: 'loading', startedAt: 0 };
    const err = new Error('boom');
    const next = compareReducer(loading, { type: 'compare:error', error: err });
    expect(next.kind).toBe('error');
    if (next.kind === 'error') {
      expect(next.error).toBe(err);
    }
  });

  it('success → loading on compare:start (re-compare)', () => {
    const success: CompareState = {
      kind: 'success',
      result: okResult,
      comparedAt: okResult.compared_at,
      badge: 'fresh',
    };
    const next = compareReducer(success, {
      type: 'compare:start',
      startedAt: 12345,
    });
    expect(next.kind).toBe('loading');
  });

  it('error → loading on compare:start (retry after error)', () => {
    const error: CompareState = { kind: 'error', error: new Error('x') };
    const next = compareReducer(error, {
      type: 'compare:start',
      startedAt: 12345,
    });
    expect(next.kind).toBe('loading');
  });

  it('any state → idle on compare:reset', () => {
    const success: CompareState = {
      kind: 'success',
      result: okResult,
      comparedAt: okResult.compared_at,
      badge: 'fresh',
    };
    const next = compareReducer(success, { type: 'compare:reset' });
    expect(next.kind).toBe('idle');
  });

  it('compare:start is deterministic given same startedAt input', () => {
    // Guards against future regressions reintroducing Date.now() into the
    // reducer. With the timestamp supplied via the action, the reducer
    // becomes a pure function and the same input must produce the same output.
    const a = compareReducer(initialCompareState, {
      type: 'compare:start',
      startedAt: 999,
    });
    const b = compareReducer(initialCompareState, {
      type: 'compare:start',
      startedAt: 999,
    });
    expect(a).toEqual(b);
  });
});
