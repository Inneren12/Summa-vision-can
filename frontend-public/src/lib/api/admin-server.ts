// Server-only admin API helpers — reads `ADMIN_API_KEY` directly from
// the environment and talks to the backend with `X-API-KEY` attached.
// The `typeof window` guard throws if anything imports this module
// client-side, keeping the key out of the browser bundle.

if (typeof window !== 'undefined') {
  throw new Error('admin-server.ts must not be imported client-side');
}

import type { AdminPublicationResponse } from '@/lib/types/publication';

function getConfig(): { apiUrl: string; adminKey: string } {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const adminKey = process.env.ADMIN_API_KEY;
  if (!apiUrl) throw new Error('NEXT_PUBLIC_API_URL not configured');
  if (!adminKey) throw new Error('ADMIN_API_KEY not configured');
  return { apiUrl, adminKey };
}

/**
 * Server-side fetch return shape augmented with the backend's ``ETag``
 * header. Phase 1.3 Blocker 2: the editor seeds ``etagRef.current`` from
 * this value so the very first autosave PATCH carries an ``If-Match``,
 * preserving lost-update protection from the first edit of a session.
 */
export type AdminPublicationServerResult = AdminPublicationResponse & {
  etag: string | null;
};

export async function fetchAdminPublicationServer(
  id: string,
): Promise<AdminPublicationServerResult | null> {
  const { apiUrl, adminKey } = getConfig();
  const res = await fetch(
    `${apiUrl}/api/v1/admin/publications/${encodeURIComponent(id)}`,
    {
      headers: { 'X-API-KEY': adminKey },
      cache: 'no-store',
    },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Admin fetch failed: ${res.status}`);
  const publication = (await res.json()) as AdminPublicationResponse;
  const etag = res.headers.get('etag');
  return { ...publication, etag };
}

export interface ListServerOptions {
  status?: 'draft' | 'published' | 'all';
  limit?: number;
  offset?: number;
}

export async function fetchAdminPublicationListServer(
  opts: ListServerOptions = {},
): Promise<AdminPublicationResponse[]> {
  const { apiUrl, adminKey } = getConfig();
  const params = new URLSearchParams();
  if (opts.status) params.set('status', opts.status);
  if (opts.limit !== undefined) params.set('limit', String(opts.limit));
  if (opts.offset !== undefined) params.set('offset', String(opts.offset));
  const qs = params.toString();
  const res = await fetch(
    `${apiUrl}/api/v1/admin/publications${qs ? `?${qs}` : ''}`,
    {
      headers: { 'X-API-KEY': adminKey },
      cache: 'no-store',
    },
  );
  if (!res.ok) throw new Error(`Admin list failed: ${res.status}`);
  return res.json();
}
