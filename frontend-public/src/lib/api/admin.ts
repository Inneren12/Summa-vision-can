// Admin-side API client. Talks to the same-origin Next.js proxy at
// `/api/admin/publications/*` — the proxy injects the server-only
// `X-API-KEY` on the way to the backend. This module never sees the
// key and must not read `ADMIN_API_KEY`.

import type {
  AdminPublicationResponse,
  VisualConfig,
  ReviewPayload,
} from '@/lib/types/publication';

const PROXY_BASE = '/api/admin/publications';

export interface ListAdminPublicationsOptions {
  status?: 'draft' | 'published' | 'all';
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

export class AdminPublicationNotFoundError extends Error {
  constructor(public readonly id: string) {
    super(`Publication ${id} not found`);
    this.name = 'AdminPublicationNotFoundError';
  }
}

export async function fetchAdminPublication(
  id: string,
  opts: { signal?: AbortSignal } = {},
): Promise<AdminPublicationResponse> {
  const res = await fetch(`${PROXY_BASE}/${encodeURIComponent(id)}`, {
    signal: opts.signal,
    cache: 'no-store',
  });
  if (res.status === 404) {
    throw new AdminPublicationNotFoundError(id);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body?.detail ?? `Admin publication fetch failed: ${res.status}`,
    );
  }
  return res.json();
}

export async function fetchAdminPublicationList(
  opts: ListAdminPublicationsOptions = {},
): Promise<AdminPublicationResponse[]> {
  const params = new URLSearchParams();
  if (opts.status) params.set('status', opts.status);
  if (opts.limit !== undefined) params.set('limit', String(opts.limit));
  if (opts.offset !== undefined) params.set('offset', String(opts.offset));
  const qs = params.toString();
  const url = qs ? `${PROXY_BASE}?${qs}` : PROXY_BASE;

  const res = await fetch(url, { signal: opts.signal, cache: 'no-store' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body?.detail ?? `Admin publication list failed: ${res.status}`,
    );
  }
  return res.json();
}

export interface UpdateAdminPublicationPayload {
  headline?: string;
  eyebrow?: string | null;
  description?: string | null;
  source_text?: string | null;
  footnote?: string | null;
  chart_type?: string;
  visual_config?: VisualConfig | null;
  review?: ReviewPayload | null;
  /**
   * Opaque JSON-serialised full CanonicalDocument — see DEBT-026
   * resolution. The client always sends it alongside the derived
   * editorial fields so search indexing and the public gallery keep
   * working; the backend stores it verbatim.
   */
  document_state?: string | null;
}

export async function updateAdminPublication(
  id: string,
  payload: UpdateAdminPublicationPayload,
  opts: { signal?: AbortSignal } = {},
): Promise<AdminPublicationResponse> {
  const res = await fetch(`${PROXY_BASE}/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: opts.signal,
    cache: 'no-store',
  });
  if (res.status === 404) {
    throw new AdminPublicationNotFoundError(id);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      body?.detail ?? `Admin publication update failed: ${res.status}`,
    );
  }
  return res.json();
}
