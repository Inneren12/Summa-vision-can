/**
 * Phase 3.1d Slice 3a — admin discovery clients.
 *
 * Wraps three same-origin proxy routes that surface backend discovery
 * endpoints to the binding editor. The browser does NOT see the admin
 * API key — proxy routes (under app/api/admin/discovery/) read
 * process.env.ADMIN_API_KEY server-side and forward via X-API-KEY header.
 *
 * Backend endpoints (proxied):
 * - GET /api/v1/admin/cubes/search                — cube search-as-you-type
 * - GET /api/v1/admin/semantic-mappings?cube_id=  — list semantic_keys
 * - GET /api/v1/admin/cube-metadata/{cube_id}     — dims + members
 *
 * Per Recon Delta 01, the cube selector uses search-as-you-type rather
 * than list-all (D-01). Dim/member retrieval is one-shot via cube-metadata
 * (D-02).
 */

const PROXY_BASE = '/api/admin/discovery';

// ---- response types (match backend Pydantic shapes) -------------------------

export interface CubeSearchResult {
  product_id: string;
  cube_id_statcan: number;
  title_en: string;
  subject_en: string;
  frequency: string;
}

export interface SemanticMappingListItem {
  id: number;
  cube_id: string;
  product_id: number;
  semantic_key: string;
  label: string;
  description: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  updated_by: string | null;
}

export interface SemanticMappingListResponse {
  items: SemanticMappingListItem[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * v1 assumption for `dimensions: dict` shape:
 *   { [dim_key]: { label?, members[] } }
 * Confirm against backend on first integration test; if shape diverges,
 * file Recon Delta 02.
 */
export interface CubeMetadataDimension {
  label?: string;
  members: Array<{ id: string | number; label: string }>;
}

export interface CubeMetadataResponse {
  cube_id: string;
  product_id: number;
  dimensions: Record<string, CubeMetadataDimension>;
  frequency_code: string | null;
  cube_title_en: string | null;
  cube_title_fr: string | null;
}

// ---- error helper -----------------------------------------------------------

class DiscoveryFetchError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'DiscoveryFetchError';
  }
}

async function discoveryFetch<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal, cache: 'no-store' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: unknown })?.detail;
    throw new DiscoveryFetchError(
      res.status,
      typeof detail === 'string'
        ? detail
        : `Discovery fetch failed: ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

// ---- public clients ---------------------------------------------------------

export interface SearchCubesOptions {
  q: string;
  signal?: AbortSignal;
}

export async function searchCubes(
  opts: SearchCubesOptions,
): Promise<CubeSearchResult[]> {
  const params = new URLSearchParams();
  params.set('q', opts.q);
  return discoveryFetch<CubeSearchResult[]>(
    `${PROXY_BASE}/cubes?${params.toString()}`,
    opts.signal,
  );
}

export interface ListSemanticMappingsOptions {
  cube_id?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

export async function listSemanticMappings(
  opts: ListSemanticMappingsOptions = {},
): Promise<SemanticMappingListResponse> {
  const params = new URLSearchParams();
  if (opts.cube_id) params.set('cube_id', opts.cube_id);
  if (opts.limit !== undefined) params.set('limit', String(opts.limit));
  if (opts.offset !== undefined) params.set('offset', String(opts.offset));
  const qs = params.toString();
  return discoveryFetch<SemanticMappingListResponse>(
    qs
      ? `${PROXY_BASE}/semantic-mappings?${qs}`
      : `${PROXY_BASE}/semantic-mappings`,
    opts.signal,
  );
}

export async function getCubeMetadata(
  cube_id: string,
  signal?: AbortSignal,
): Promise<CubeMetadataResponse> {
  return discoveryFetch<CubeMetadataResponse>(
    `${PROXY_BASE}/cube-metadata/${encodeURIComponent(cube_id)}`,
    signal,
  );
}

export { DiscoveryFetchError };
