/**
 * Phase 3.1d Slice 1b — useCompareState hook.
 *
 * Source of truth: docs/recon/phase-3-1d-slice-1b-recon.md §C.5, §C.6
 *
 * Manual trigger only. AbortController cancels in-flight on unmount and on
 * re-compare.
 */

import { useReducer, useRef, useEffect, useCallback } from 'react';
import { comparePublication } from '@/lib/api/admin';
import {
  compareReducer,
  initialCompareState,
  type CompareState,
} from './compareReducer';

export interface UseCompareStateResult {
  state: CompareState;
  compare: () => void;
  reset: () => void;
}

export function useCompareState(publicationId: string): UseCompareStateResult {
  const [state, dispatch] = useReducer(compareReducer, initialCompareState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const compare = useCallback(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    dispatch({ type: 'compare:start' });

    comparePublication(publicationId, { signal: controller.signal })
      .then((result) => {
        if (controller.signal.aborted) return;
        dispatch({ type: 'compare:success', result });
      })
      .catch((error: unknown) => {
        if (
          (error as { name?: string } | null)?.name === 'AbortError' ||
          controller.signal.aborted
        ) {
          return;
        }
        dispatch({
          type: 'compare:error',
          error: error instanceof Error ? error : new Error(String(error)),
        });
      });
  }, [publicationId]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: 'compare:reset' });
  }, []);

  return { state, compare, reset };
}
