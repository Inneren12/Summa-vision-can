/**
 * Phase 3.1d Slice 3a — admin-discovery client unit tests.
 * Mocks `fetch` directly; tests the typed wrapper layer (URL construction,
 * AbortSignal forwarding, error mapping). Proxy routes are out of scope.
 */
import {
  searchCubes,
  listSemanticMappings,
  getCubeMetadata,
  DiscoveryFetchError,
} from '../admin-discovery';

type FetchArgs = [RequestInfo | URL, RequestInit | undefined];
const fetchMock = jest.fn<Promise<Response>, FetchArgs>();

beforeEach(() => {
  fetchMock.mockReset();
  (globalThis as unknown as { fetch: typeof fetchMock }).fetch = fetchMock;
});

function jsonResponse(
  body: unknown,
  init: { status?: number } = { status: 200 },
): Response {
  // jsdom may not provide a global Response constructor; duck-type instead.
  const status = init.status ?? 200;
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe('searchCubes', () => {
  it('hits same-origin proxy with q query param URL-encoded', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));
    await searchCubes({ q: 'mortgage rate' });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toBe('/api/admin/discovery/cubes?q=mortgage+rate');
    expect(init?.cache).toBe('no-store');
  });

  it('returns parsed cube list on success', async () => {
    const payload = [
      {
        product_id: '18100004',
        cube_id_statcan: 18100004,
        title_en: 'Posted rates',
        subject_en: 'Finance',
        frequency: 'M',
      },
    ];
    fetchMock.mockResolvedValueOnce(jsonResponse(payload));
    const result = await searchCubes({ q: 'rate' });
    expect(result).toEqual(payload);
  });

  it('throws DiscoveryFetchError on non-OK with backend detail', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: 'backend exploded' }, { status: 500 }),
    );
    await expect(searchCubes({ q: 'x' })).rejects.toMatchObject({
      name: 'DiscoveryFetchError',
      status: 500,
      message: 'backend exploded',
    });
  });

  it('forwards AbortSignal to fetch', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([]));
    const ctrl = new AbortController();
    await searchCubes({ q: 'x', signal: ctrl.signal });
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.signal).toBe(ctrl.signal);
  });
});

describe('listSemanticMappings', () => {
  it('hits proxy with no query params when called with no opts', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, limit: 0, offset: 0 }),
    );
    await listSemanticMappings();
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toBe('/api/admin/discovery/semantic-mappings');
  });

  it('forwards cube_id, limit, offset', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, limit: 100, offset: 0 }),
    );
    await listSemanticMappings({ cube_id: '18100004', limit: 100, offset: 0 });
    const [url] = fetchMock.mock.calls[0]!;
    const parsed = new URL(String(url), 'http://x');
    expect(parsed.pathname).toBe('/api/admin/discovery/semantic-mappings');
    expect(parsed.searchParams.get('cube_id')).toBe('18100004');
    expect(parsed.searchParams.get('limit')).toBe('100');
    expect(parsed.searchParams.get('offset')).toBe('0');
  });

  it('returns paginated response on success', async () => {
    const payload = {
      items: [
        {
          id: 1,
          cube_id: 'cube_a',
          product_id: 18100004,
          semantic_key: 'metric_x',
          label: 'Metric X',
          description: null,
          config: {},
          is_active: true,
          version: 1,
          created_at: '2026-01-01',
          updated_at: '2026-01-01',
          updated_by: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    };
    fetchMock.mockResolvedValueOnce(jsonResponse(payload));
    const result = await listSemanticMappings({ cube_id: 'cube_a' });
    expect(result.items).toHaveLength(1);
    expect(result.total).toBe(1);
  });

  it('throws DiscoveryFetchError with fallback message when no detail', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, { status: 404 }));
    await expect(listSemanticMappings({ cube_id: 'cube_x' })).rejects.toMatchObject({
      name: 'DiscoveryFetchError',
      status: 404,
    });
  });
});

describe('getCubeMetadata', () => {
  it('encodes cube_id in path', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        cube_id: 'a/b',
        product_id: 1,
        dimensions: {},
        frequency_code: null,
        cube_title_en: null,
        cube_title_fr: null,
      }),
    );
    await getCubeMetadata('a/b');
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toBe('/api/admin/discovery/cube-metadata/a%2Fb');
  });

  it('returns parsed metadata', async () => {
    const md = {
      cube_id: 'cube_a',
      product_id: 18100004,
      dimensions: {
        geo: {
          label: 'Geography',
          members: [{ id: 'CA', label: 'Canada' }],
        },
      },
      frequency_code: 'M',
      cube_title_en: 'Posted rates',
      cube_title_fr: null,
    };
    fetchMock.mockResolvedValueOnce(jsonResponse(md));
    const result = await getCubeMetadata('cube_a');
    expect(result.dimensions.geo?.members[0]?.label).toBe('Canada');
  });

  it('forwards AbortSignal', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        cube_id: 'c',
        product_id: 1,
        dimensions: {},
        frequency_code: null,
        cube_title_en: null,
        cube_title_fr: null,
      }),
    );
    const ctrl = new AbortController();
    await getCubeMetadata('c', ctrl.signal);
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.signal).toBe(ctrl.signal);
  });

  it('propagates AbortError without wrapping', async () => {
    const abortErr = new Error('aborted');
    abortErr.name = 'AbortError';
    fetchMock.mockRejectedValueOnce(abortErr);
    await expect(getCubeMetadata('c')).rejects.toMatchObject({ name: 'AbortError' });
  });
});

describe('DiscoveryFetchError', () => {
  it('exposes status and name', () => {
    const err = new DiscoveryFetchError(503, 'unavailable');
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(503);
    expect(err.name).toBe('DiscoveryFetchError');
  });
});
