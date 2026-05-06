'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { Block } from '../types';
import {
  validateBinding,
  type Binding,
  type SingleValueBinding,
} from './types';
import {
  searchCubes,
  listSemanticMappings,
  getCubeMetadata,
  type CubeSearchResult,
  type SemanticMappingListItem,
  type CubeMetadataResponse,
} from '@/lib/api/admin-discovery';

interface BindingEditorProps {
  block: Block;
  onChange: (binding: Binding | undefined) => void;
}

const SEARCH_DEBOUNCE_MS = 250;

export function BindingEditor({ block, onChange }: BindingEditorProps) {
  const initial = useMemo<SingleValueBinding | null>(() => {
    const v = block.binding;
    if (v && v.kind === 'single') return v;
    return null;
  }, [block.binding]);

  const [cubeId, setCubeId] = useState<string>(initial?.cube_id ?? '');
  const [semanticKey, setSemanticKey] = useState<string>(initial?.semantic_key ?? '');
  const [filters, setFilters] = useState<Record<string, string>>(
    initial?.filters ?? {},
  );
  const [period, setPeriod] = useState<string>(initial?.period ?? '');
  const [format, setFormat] = useState<string>(initial?.format ?? '');

  // Phase 3.1d Slice 3a fix: `touched` gate prevents two destructive paths:
  //   1. Mount-time emit when form is empty/invalid would clear an existing
  //      binding via onChange(undefined).
  //   2. When Inspector selection moves to another bindable block, this
  //      component does NOT remount — the prev block's state would emit
  //      onto the new block. The `block.id` sync effect below resets state
  //      AND resets `touched` to false, blocking emit until user interacts.
  // User-initiated invalid form (e.g. clearing period) DOES emit undefined
  // — that is the intended destructive action.
  const [touched, setTouched] = useState(false);

  const [cubeQuery, setCubeQuery] = useState<string>('');
  const [cubeResults, setCubeResults] = useState<CubeSearchResult[]>([]);
  const [cubeLoading, setCubeLoading] = useState(false);
  const cubeAbortRef = useRef<AbortController | null>(null);
  const cubeDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [semanticMappings, setSemanticMappings] = useState<SemanticMappingListItem[]>([]);
  const [semanticLoading, setSemanticLoading] = useState(false);

  const [cubeMetadata, setCubeMetadata] = useState<CubeMetadataResponse | null>(null);

  // Debounced cube search.
  useEffect(() => {
    if (cubeDebounceRef.current) clearTimeout(cubeDebounceRef.current);
    if (cubeQuery.trim().length === 0) {
      setCubeResults([]);
      cubeAbortRef.current?.abort();
      // Phase 3.1d Slice 3a fix (Codex P2): the in-flight finally block only
      // clears cubeLoading for non-aborted requests, so clearing the search
      // box mid-flight could leave the indicator stuck. Clear it explicitly.
      setCubeLoading(false);
      return;
    }
    cubeDebounceRef.current = setTimeout(() => {
      cubeAbortRef.current?.abort();
      const ctrl = new AbortController();
      cubeAbortRef.current = ctrl;
      setCubeLoading(true);
      searchCubes({ q: cubeQuery, signal: ctrl.signal })
        .then((results) => {
          if (!ctrl.signal.aborted) setCubeResults(results);
        })
        .catch((err: unknown) => {
          if ((err as { name?: string })?.name !== 'AbortError') {
            setCubeResults([]);
          }
        })
        .finally(() => {
          if (!ctrl.signal.aborted) setCubeLoading(false);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      if (cubeDebounceRef.current) clearTimeout(cubeDebounceRef.current);
    };
  }, [cubeQuery]);

  // Load semantic mappings + cube metadata when cubeId changes.
  useEffect(() => {
    if (!cubeId) {
      setSemanticMappings([]);
      setCubeMetadata(null);
      return;
    }
    const ctrl = new AbortController();
    setSemanticLoading(true);
    Promise.all([
      listSemanticMappings({ cube_id: cubeId, limit: 100, signal: ctrl.signal }),
      getCubeMetadata(cubeId, ctrl.signal),
    ])
      .then(([sm, md]) => {
        if (!ctrl.signal.aborted) {
          setSemanticMappings(sm.items);
          setCubeMetadata(md);
        }
      })
      .catch((err: unknown) => {
        if ((err as { name?: string })?.name !== 'AbortError') {
          setSemanticMappings([]);
          setCubeMetadata(null);
        }
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setSemanticLoading(false);
      });
    return () => ctrl.abort();
  }, [cubeId]);

  // Emit binding on every change AFTER user has interacted (touched=true).
  // validateBinding either returns a canonical Binding (valid) or null
  // (invalid → emit undefined). User-initiated invalid form is a deliberate
  // clear; mount-time invalid is gated by `touched` to prevent silent data loss.
  // JSON.stringify(filters) is a deliberate object-equality fingerprint;
  // filter values are flat strings so this is safe.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!touched) return;
    const candidate: Partial<SingleValueBinding> = {
      kind: 'single',
      cube_id: cubeId.trim(),
      semantic_key: semanticKey.trim(),
      filters,
      period: period.trim(),
      ...(format.trim() ? { format: format.trim() } : {}),
    };
    const validated = validateBinding(candidate);
    onChange(validated ?? undefined);
  }, [touched, cubeId, semanticKey, JSON.stringify(filters), period, format, onChange]);

  // Phase 3.1d Slice 3a fix: when the inspector switches to a different
  // bindable block, this component instance is NOT remounted. We must
  // explicitly resync form state from the new block's binding and reset the
  // touched gate. Without this, the previous block's form state could
  // emit onto the new block and overwrite its binding.
  // Tracks block.id (not block.binding) — same block + binding-mutation-via-emit
  // is a normal in-place edit, NOT a re-sync trigger.
  useEffect(() => {
    const v = block.binding;
    const seed = v && v.kind === 'single' ? v : null;
    setCubeId(seed?.cube_id ?? '');
    setSemanticKey(seed?.semantic_key ?? '');
    setFilters(seed?.filters ?? {});
    setPeriod(seed?.period ?? '');
    setFormat(seed?.format ?? '');
    setTouched(false);
    // Also clear search/results UI state — those are global to the component.
    setCubeQuery('');
    setCubeResults([]);
    setSemanticMappings([]);
    setCubeMetadata(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [block.id]);

  const isDeltaBadge = block.type === 'delta_badge';

  const updateFilter = (dimKey: string, memberId: string) => {
    setTouched(true);
    setFilters((prev) => {
      const next = { ...prev };
      if (memberId) next[dimKey] = memberId;
      else delete next[dimKey];
      return next;
    });
  };

  return (
    <div
      data-testid="binding-editor"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        padding: '8px',
        border: '1px solid #ddd',
        borderRadius: '3px',
        fontSize: '10px',
      }}
    >
      <div style={{ fontSize: '8px', textTransform: 'uppercase', letterSpacing: '0.3px', opacity: 0.7 }}>
        Data binding
      </div>

      {isDeltaBadge && (
        <div
          data-testid="binding-editor-delta-advisory"
          style={{
            fontSize: '9px',
            padding: '6px 8px',
            background: '#fff8e1',
            border: '1px solid #f0c36d',
            borderRadius: '3px',
            lineHeight: 1.4,
          }}
        >
          Pick a precomputed delta semantic_key (e.g. <code>*_change_pct</code>).
          Frontend does not compute deltas.
        </div>
      )}

      <label style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '8px', textTransform: 'uppercase', opacity: 0.6 }}>
          Cube (search):
        </span>
        <input
          type="text"
          value={cubeQuery}
          onChange={(e) => setCubeQuery(e.target.value)}
          placeholder="Type to search cubes..."
          aria-label="Cube search"
          style={{ width: '100%', padding: '4px 6px', fontSize: '10px', boxSizing: 'border-box' }}
        />
      </label>
      {cubeLoading && (
        <div data-testid="binding-editor-cube-loading" style={{ fontSize: '9px', opacity: 0.6 }}>
          Searching...
        </div>
      )}
      {cubeResults.length > 0 && (
        <ul
          data-testid="binding-editor-cube-results"
          style={{ listStyle: 'none', margin: 0, padding: 0, maxHeight: '160px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '3px' }}
        >
          {cubeResults.map((c) => (
            <li
              key={c.product_id}
              role="button"
              tabIndex={0}
              onClick={() => {
                setTouched(true);
                setCubeId(c.product_id);
                setSemanticKey('');
                setFilters({});
                setFormat('');
                setCubeQuery('');
                setCubeResults([]);
                // metadata + mappings will reload via cubeId effect; clear
                // the stale UI immediately to avoid showing prev-cube options.
                setSemanticMappings([]);
                setCubeMetadata(null);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setTouched(true);
                  setCubeId(c.product_id);
                  setSemanticKey('');
                  setFilters({});
                  setFormat('');
                  setCubeQuery('');
                  setCubeResults([]);
                  setSemanticMappings([]);
                  setCubeMetadata(null);
                }
              }}
              style={{
                padding: '4px 6px',
                cursor: 'pointer',
                background: cubeId === c.product_id ? '#e6f1ff' : 'transparent',
                borderBottom: '1px solid #eee',
              }}
            >
              <div style={{ fontWeight: 500 }}>{c.title_en}</div>
              <div style={{ fontSize: '8px', opacity: 0.6 }}>
                {c.product_id} · {c.subject_en} · {c.frequency}
              </div>
            </li>
          ))}
        </ul>
      )}
      {cubeId && (
        <div data-testid="binding-editor-selected-cube" style={{ fontSize: '9px' }}>
          Selected cube: <code>{cubeId}</code>
        </div>
      )}

      <label style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '8px', textTransform: 'uppercase', opacity: 0.6 }}>
          Semantic key:
        </span>
        <select
          value={semanticKey}
          onChange={(e) => {
            setTouched(true);
            setSemanticKey(e.target.value);
          }}
          disabled={!cubeId || semanticLoading}
          aria-label="Semantic key"
          data-testid="binding-editor-semantic-key"
          style={{ width: '100%', padding: '4px 6px', fontSize: '10px', boxSizing: 'border-box' }}
        >
          <option value="">— select —</option>
          {semanticMappings.map((sm) => (
            <option key={sm.id} value={sm.semantic_key}>
              {sm.label} ({sm.semantic_key})
            </option>
          ))}
        </select>
      </label>

      {cubeMetadata && (
        <div data-testid="binding-editor-filters" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ fontSize: '8px', textTransform: 'uppercase', opacity: 0.6 }}>Filters:</div>
          {Object.entries(cubeMetadata.dimensions).map(([dimKey, dim]) => (
            <label key={dimKey} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span style={{ fontSize: '8px', opacity: 0.6 }}>{dim.label ?? dimKey}:</span>
              <select
                value={filters[dimKey] ?? ''}
                onChange={(e) => updateFilter(dimKey, e.target.value)}
                aria-label={`Filter ${dimKey}`}
                data-testid={`binding-editor-filter-${dimKey}`}
                style={{ width: '100%', padding: '4px 6px', fontSize: '10px', boxSizing: 'border-box' }}
              >
                <option value="">— any —</option>
                {dim.members.map((m) => (
                  <option key={String(m.id)} value={String(m.id)}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      )}

      <label style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '8px', textTransform: 'uppercase', opacity: 0.6 }}>Period:</span>
        <input
          type="text"
          value={period}
          onChange={(e) => {
            setTouched(true);
            setPeriod(e.target.value);
          }}
          placeholder="e.g. 2024-Q3"
          aria-label="Period"
          data-testid="binding-editor-period"
          style={{ width: '100%', padding: '4px 6px', fontSize: '10px', boxSizing: 'border-box' }}
        />
      </label>

      <label style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <span style={{ fontSize: '8px', textTransform: 'uppercase', opacity: 0.6 }}>
          Format (optional):
        </span>
        <input
          type="text"
          value={format}
          onChange={(e) => {
            setTouched(true);
            setFormat(e.target.value);
          }}
          placeholder="e.g. percent, currency:CAD"
          aria-label="Format"
          data-testid="binding-editor-format"
          style={{ width: '100%', padding: '4px 6px', fontSize: '10px', boxSizing: 'border-box' }}
        />
      </label>
      <button
        type="button"
        data-testid="binding-editor-clear"
        onClick={() => {
          setTouched(true);
          setCubeId('');
          setSemanticKey('');
          setFilters({});
          setPeriod('');
          setFormat('');
          setCubeQuery('');
          setCubeResults([]);
          setSemanticMappings([]);
          setCubeMetadata(null);
          onChange(undefined);
        }}
        disabled={!block.binding}
        style={{
          marginTop: '4px',
          padding: '4px 8px',
          fontSize: '9px',
          background: 'transparent',
          border: '1px solid #c66',
          color: '#c66',
          borderRadius: '3px',
          cursor: block.binding ? 'pointer' : 'not-allowed',
          opacity: block.binding ? 1 : 0.4,
        }}
      >
        Clear binding
      </button>
    </div>
  );
}
