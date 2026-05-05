/**
 * Phase 3.1d Slice 1b — Compare state machine reducer.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §C.1, §C.2, §C.3
 *
 * 4 states (idle/loading/success/error). `partial` is a severity bucket
 * inside `success.badge`, NOT a separate state.
 */

import type {
  CompareResponse,
  CompareBadgeSeverity,
} from '@/lib/types/compare';
import { aggregateCompareSeverity } from '@/lib/utils/compareSeverity';
import { BackendApiError } from '@/lib/api/admin';

export type CompareState =
  | { kind: 'idle' }
  | { kind: 'loading'; startedAt: number }
  | {
      kind: 'success';
      result: CompareResponse;
      comparedAt: string;
      badge: CompareBadgeSeverity;
    }
  | { kind: 'error'; error: BackendApiError | Error };

export type CompareAction =
  | { type: 'compare:start'; startedAt: number }
  | { type: 'compare:success'; result: CompareResponse }
  | { type: 'compare:error'; error: BackendApiError | Error }
  | { type: 'compare:reset' };

export const initialCompareState: CompareState = { kind: 'idle' };

export function compareReducer(
  state: CompareState,
  action: CompareAction,
): CompareState {
  switch (action.type) {
    case 'compare:start':
      return { kind: 'loading', startedAt: action.startedAt };

    case 'compare:success': {
      const badge = aggregateCompareSeverity(action.result);
      return {
        kind: 'success',
        result: action.result,
        comparedAt: action.result.compared_at,
        badge,
      };
    }

    case 'compare:error':
      return { kind: 'error', error: action.error };

    case 'compare:reset':
      return { kind: 'idle' };

    default: {
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}
