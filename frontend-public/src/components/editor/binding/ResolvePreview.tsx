'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  fetchResolvedValue,
  ResolveFetchError,
  type ResolvedValueResponse,
  type ResolveErrorCode,
} from '@/lib/api/admin-resolve';
import type { SingleValueBinding } from './types';

interface ResolvePreviewProps {
  binding: SingleValueBinding | null;
}

const RESOLVE_DEBOUNCE_MS = 300;

type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; data: ResolvedValueResponse }
  | { kind: 'error'; code: ResolveErrorCode; message: string };

function bindingFingerprint(b: SingleValueBinding): string {
  // Stable string for deps comparison — Slice 2 canonicalFilters already
  // sorted, JSON.stringify is deterministic on canonical objects.
  return JSON.stringify(b);
}

export function ResolvePreview({ binding }: ResolvePreviewProps) {
  const t = useTranslations('publication.binding.resolve');
  const [state, setState] = useState<State>({ kind: 'idle' });
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fingerprint = binding ? bindingFingerprint(binding) : null;

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    abortRef.current?.abort();

    if (!binding) {
      setState({ kind: 'idle' });
      return;
    }

    setState({ kind: 'loading' });

    debounceRef.current = setTimeout(() => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      fetchResolvedValue(binding, { signal: ctrl.signal })
        .then((data) => {
          if (!ctrl.signal.aborted) setState({ kind: 'success', data });
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name === 'AbortError') return;
          if (err instanceof ResolveFetchError) {
            setState({ kind: 'error', code: err.code, message: err.message });
          } else {
            setState({
              kind: 'error',
              code: 'UNKNOWN',
              message: (err as Error)?.message ?? 'Unknown error',
            });
          }
        });
    }, RESOLVE_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fingerprint]);

  if (!binding || state.kind === 'idle') {
    return null;
  }

  return (
    <div
      data-testid="resolve-preview"
      style={{
        marginTop: '6px',
        padding: '6px 8px',
        border: '1px solid #cce',
        borderRadius: '3px',
        background: '#f5f8ff',
        fontSize: '10px',
      }}
    >
      <div
        style={{
          fontSize: '8px',
          textTransform: 'uppercase',
          opacity: 0.6,
          marginBottom: '4px',
        }}
      >
        Preview
      </div>
      {state.kind === 'loading' && (
        <div data-testid="resolve-preview-loading" style={{ opacity: 0.6 }}>
          Resolving…
        </div>
      )}
      {state.kind === 'success' && (
        <div data-testid="resolve-preview-success">
          {state.data.missing ? (
            <span style={{ color: '#a66' }}>missing</span>
          ) : state.data.value === null ? (
            <span style={{ color: '#a66' }}>null</span>
          ) : (
            <span style={{ fontWeight: 500 }}>
              {state.data.value}
              {state.data.units ? (
                <span style={{ opacity: 0.6 }}> {state.data.units}</span>
              ) : null}
            </span>
          )}
          {state.data.period ? (
            <span
              style={{ marginLeft: '6px', opacity: 0.6, fontSize: '9px' }}
            >
              ({state.data.period})
            </span>
          ) : null}
          <span
            data-testid="resolve-preview-cache-status"
            style={{
              marginLeft: '8px',
              fontSize: '8px',
              padding: '1px 4px',
              borderRadius: '2px',
              background:
                state.data.cache_status === 'hit' ? '#dfe' : '#ffe',
              color: '#555',
            }}
          >
            {state.data.cache_status}
          </span>
        </div>
      )}
      {state.kind === 'error' && (
        <div
          data-testid={`resolve-preview-error-${state.code.toLowerCase()}`}
          role="alert"
          style={{ color: '#a44' }}
        >
          {state.code === 'MAPPING_NOT_FOUND' && t('mapping_not_found')}
          {state.code === 'RESOLVE_CACHE_MISS' && t('cache_miss')}
          {state.code === 'RESOLVE_INVALID_FILTERS' && t('invalid_filters')}
          {state.code === 'UNKNOWN' && (
            <>
              {t('unknown')}
              {state.message ? (
                <span
                  data-testid="resolve-preview-error-detail"
                  style={{
                    display: 'block',
                    marginTop: '2px',
                    opacity: 0.7,
                    fontSize: '9px',
                  }}
                >
                  {state.message}
                </span>
              ) : null}
            </>
          )}
        </div>
      )}
    </div>
  );
}
