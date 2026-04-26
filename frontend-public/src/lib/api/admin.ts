// Admin-side API client. Talks to the same-origin Next.js proxy at
// `/api/admin/publications/*` — the proxy injects the server-only
// `X-API-KEY` on the way to the backend. This module never sees the
// key and must not read `ADMIN_API_KEY`.

import type {
  AdminPublicationResponse,
  VisualConfig,
  ReviewPayload,
} from '@/lib/types/publication';
import { extractBackendErrorPayload } from './errorCodes';

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

/**
 * Carries a backend error_code + status + optional details for callers
 * that want to react to specific codes. Distinct from AdminPublicationNotFoundError
 * which is a typed branch for the very common 404-on-publication case.
 */
export class BackendApiError extends Error {
  public readonly status: number;
  public readonly code: string | null;
  public readonly details: Record<string, unknown> | null;

  constructor(args: {
    status: number;
    code: string | null;
    message: string;
    details: Record<string, unknown> | null;
  }) {
    super(args.message);
    this.name = 'BackendApiError';
    this.status = args.status;
    this.code = args.code;
    this.details = args.details;
  }
}

/**
 * Intentionally not migrated to errorCodes.ts in DEBT-030.
 *
 * `fetchAdminPublication` is a load-time call (used by the editor on
 * mount + admin list views), not a user-action mutation. Load failures
 * fall back to the `publication.load_failed` key in messages/*.json,
 * which gives operators a uniformly localized recovery message
 * regardless of the underlying error code.
 *
 * Migration to error_code-aware handling would only be valuable if
 * load-error UX needs distinction by code (e.g., "archived" vs "not
 * found" on initial load). Tracked under DEBT-034 follow-up if/when
 * that need surfaces.
 */
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
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const payload = extractBackendErrorPayload(body);

    // Code-first detection: backend has a structured contract.
    if (payload.code === 'PUBLICATION_NOT_FOUND') {
      throw new AdminPublicationNotFoundError(id);
    }

    // Shape-less 404 backstop: only fires when there is NO structured
    // payload (e.g., gateway/CDN intercept returning HTML or empty
    // body). When a payload exists, trust the code — future codes like
    // PUBLICATION_ARCHIVED on a 404 status must NOT be misclassified
    // as not-found.
    if (!payload.code && res.status === 404) {
      throw new AdminPublicationNotFoundError(id);
    }

    throw new BackendApiError({
      status: res.status,
      code: payload.code,
      message:
        payload.message ??
        (typeof body?.detail === 'string' ? body.detail : null) ??
        `Admin publication update failed: ${res.status}`,
      details: payload.details,
    });
  }
  return res.json();
}
