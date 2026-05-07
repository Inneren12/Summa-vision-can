/**
 * Phase 3.1d Slice 3b — admin resolve preview client.
 *
 * Wraps the same-origin proxy route at /api/admin/resolve/[cubeId]/[semanticKey]
 * which forwards to backend GET /api/v1/admin/resolve/{cube_id}/{semantic_key}.
 * The browser does NOT see the admin API key — proxy route reads
 * process.env.ADMIN_API_KEY server-side and forwards via X-API-KEY header.
 *
 * Per founder decision (Phase 3.1d Slice 3b prompt), preview uses the existing
 * backend handler with default behavior (auto-prime ON on cache miss). Strict
 * side-effect-free mode (cached_only) is service-layer-supported but not
 * exposed at HTTP — track as DEBT if needed.
 *
 * Response shape locked per Recon Delta 02 D-01 to match
 * `backend/src/schemas/resolve.py:20` `ResolvedValueResponse` exactly.
 */

import type { SingleValueBinding } from '@/components/editor/binding/types';

const PROXY_BASE = '/api/admin/resolve';

// ---- response types (match backend backend/src/schemas/resolve.py) ----------

export type CacheStatus = 'hit' | 'primed';

export interface ResolvedValueResponse {
  cube_id: string;
  semantic_key: string;
  /** Service-derived StatCan coordinate string echoed from cache row. */
  coord: string;
  /** Resolved period token (ref_period). */
  period: string;
  /** Canonical stringified numeric value; null when missing/suppressed. */
  value: string | null;
  /** Raw passthrough from cache row; True when observation absent. */
  missing: boolean;
  /** ISO datetime — alias of cache row fetched_at. */
  resolved_at: string;
  /** Opaque cache provenance hash. */
  source_hash: string;
  /** Persisted stale marker from cache row. */
  is_stale: boolean;
  /** Unit from mapping.config.unit if string, else null. */
  units: string | null;
  cache_status: CacheStatus;
  /** Optional semantic mapping version. */
  mapping_version: number | null;
}

// ---- error types -------------------------------------------------------------

export type ResolveErrorCode =
  | 'MAPPING_NOT_FOUND'
  | 'RESOLVE_CACHE_MISS'
  | 'RESOLVE_INVALID_FILTERS'
  | 'UNKNOWN';

class ResolveFetchError extends Error {
  constructor(
    public status: number,
    public code: ResolveErrorCode,
    message: string,
  ) {
    super(message);
    this.name = 'ResolveFetchError';
  }
}

function mapErrorCode(raw: unknown): ResolveErrorCode {
  if (raw === 'MAPPING_NOT_FOUND') return 'MAPPING_NOT_FOUND';
  if (raw === 'RESOLVE_CACHE_MISS') return 'RESOLVE_CACHE_MISS';
  if (raw === 'RESOLVE_INVALID_FILTERS') return 'RESOLVE_INVALID_FILTERS';
  return 'UNKNOWN';
}

// ---- client function ---------------------------------------------------------

export interface FetchResolvedValueOptions {
  signal?: AbortSignal;
}

/**
 * Fetch the resolved value for a SingleValueBinding via the same-origin
 * admin proxy. Builds repeated ?dim=&member= pairs from the binding's
 * filters dict in alphabetical key order (deterministic; Slice 2
 * canonicalFilters already sorted alphabetically — the re-sort here is
 * defensive against runtime mutation).
 *
 * Per Recon Delta 02 D-02, filter values are forwarded verbatim. Backend
 * expects integer position_id / member_id pairs (`backend/src/services/
 * resolve/filters.py`). If the picker emits non-numeric filters (current
 * Slice 3a state per Delta 02 F-03), backend returns 422; client maps
 * to `code: 'UNKNOWN'` and surfaces the raw message in the UI.
 */
export async function fetchResolvedValue(
  binding: SingleValueBinding,
  opts: FetchResolvedValueOptions = {},
): Promise<ResolvedValueResponse> {
  const params = new URLSearchParams();
  const sortedKeys = Object.keys(binding.filters).sort();
  for (const key of sortedKeys) {
    params.append('dim', key);
    params.append('member', binding.filters[key]);
  }
  if (binding.period) {
    params.set('period', binding.period);
  }
  const qs = params.toString();
  const url = `${PROXY_BASE}/${encodeURIComponent(binding.cube_id)}/${encodeURIComponent(binding.semantic_key)}${qs ? `?${qs}` : ''}`;

  const res = await fetch(url, { signal: opts.signal, cache: 'no-store' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // Backend error envelope: { detail: { error_code, message, details? } }
    // (admin_resolve.py raises HTTPException with a dict detail).
    const detail = (body as { detail?: { error_code?: unknown; message?: unknown } })
      ?.detail;
    const code = mapErrorCode(detail?.error_code);
    const message =
      typeof detail?.message === 'string'
        ? detail.message
        : `Resolve fetch failed: ${res.status}`;
    throw new ResolveFetchError(res.status, code, message);
  }
  return res.json() as Promise<ResolvedValueResponse>;
}

export { ResolveFetchError };
