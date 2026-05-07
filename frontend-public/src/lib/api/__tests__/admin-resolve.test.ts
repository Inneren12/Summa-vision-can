/**
 * Phase 3.1d Slice 3b — admin-resolve client unit tests.
 * Mocks `fetch` directly; tests the typed wrapper layer (URL construction
 * with repeated dim/member pairs, AbortSignal forwarding, error code
 * mapping per backend error envelope). Proxy routes are out of scope.
 */
import {
  fetchResolvedValue,
  ResolveFetchError,
  type ResolvedValueResponse,
} from '../admin-resolve';
import type { SingleValueBinding } from '@/components/editor/binding/types';

type FetchArgs = [RequestInfo | URL, RequestInit | undefined];
const fetchMock = jest.fn<Promise<Response>, FetchArgs>();

beforeEach(() => {
  fetchMock.mockReset();
  (globalThis as unknown as { fetch: typeof fetchMock }).fetch = fetchMock;
});

function jsonResponse(
  body: unknown,
  init: { status?: number; ok?: boolean } = { status: 200 },
): Response {
  // jsdom may not provide a global Response constructor; duck-type instead.
  const status = init.status ?? 200;
  return {
    ok: init.ok ?? (status >= 200 && status < 300),
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function rawJsonRejectingResponse(status: number): Response {
  // For the "non-JSON body" error path. Our client does
  // `await res.json().catch(() => ({}))`, so the catch branch is what we
  // need to exercise.
  return {
    ok: false,
    status,
    json: async () => {
      throw new SyntaxError('not json');
    },
    text: async () => '<html>oops</html>',
  } as unknown as Response;
}

const SUCCESS: ResolvedValueResponse = {
  cube_id: '18100004',
  semantic_key: 'metric_x',
  coord: '1.1.0.0.0.0.0.0.0.0',
  period: '2024-Q3',
  value: '6.73',
  missing: false,
  resolved_at: '2026-05-07T00:00:00Z',
  source_hash: 'abc123',
  is_stale: false,
  units: 'percent',
  cache_status: 'hit',
  mapping_version: 1,
};

function makeBinding(
  overrides: Partial<SingleValueBinding> = {},
): SingleValueBinding {
  return {
    kind: 'single',
    cube_id: '18100004',
    semantic_key: 'metric_x',
    filters: {},
    period: '2024-Q3',
    ...overrides,
  };
}

describe('fetchResolvedValue — URL construction', () => {
  it('builds URL with period only when filters are empty', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    await fetchResolvedValue(makeBinding({ filters: {} }));
    const [url] = fetchMock.mock.calls[0]!;
    const parsed = new URL(String(url), 'http://x');
    expect(parsed.pathname).toBe('/api/admin/resolve/18100004/metric_x');
    expect(parsed.searchParams.getAll('dim')).toEqual([]);
    expect(parsed.searchParams.getAll('member')).toEqual([]);
    expect(parsed.searchParams.get('period')).toBe('2024-Q3');
  });

  it('builds URL with one filter + period', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    await fetchResolvedValue(makeBinding({ filters: { geo: 'CA' } }));
    const parsed = new URL(String(fetchMock.mock.calls[0]![0]), 'http://x');
    expect(parsed.searchParams.getAll('dim')).toEqual(['geo']);
    expect(parsed.searchParams.getAll('member')).toEqual(['CA']);
    expect(parsed.searchParams.get('period')).toBe('2024-Q3');
  });

  it('emits filters in alphabetical key order (deterministic)', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    await fetchResolvedValue(
      makeBinding({ filters: { industry: '11', geo: 'CA' } }),
    );
    const parsed = new URL(String(fetchMock.mock.calls[0]![0]), 'http://x');
    expect(parsed.searchParams.getAll('dim')).toEqual(['geo', 'industry']);
    expect(parsed.searchParams.getAll('member')).toEqual(['CA', '11']);
  });

  it('still alphabetizes when input object has reverse insertion order', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    await fetchResolvedValue(
      makeBinding({ filters: { zeta: 'z', alpha: 'a', mu: 'm' } }),
    );
    const parsed = new URL(String(fetchMock.mock.calls[0]![0]), 'http://x');
    expect(parsed.searchParams.getAll('dim')).toEqual(['alpha', 'mu', 'zeta']);
    expect(parsed.searchParams.getAll('member')).toEqual(['a', 'm', 'z']);
  });

  it('encodes special chars in cube_id and semantic_key path segments', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    await fetchResolvedValue(
      makeBinding({ cube_id: 'a/b', semantic_key: 'metric x' }),
    );
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain('/api/admin/resolve/a%2Fb/metric%20x');
  });

  it('omits period when binding.period is empty string (defensive)', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    // SingleValueBinding.period is non-empty by validation, but clients
    // may pass partial-typed bindings during unit tests; we exercise the
    // empty-period guard.
    await fetchResolvedValue(makeBinding({ period: '' as string }));
    const parsed = new URL(String(fetchMock.mock.calls[0]![0]), 'http://x');
    expect(parsed.searchParams.has('period')).toBe(false);
  });

  it('forwards AbortSignal to fetch', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    const ctrl = new AbortController();
    await fetchResolvedValue(makeBinding(), { signal: ctrl.signal });
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.signal).toBe(ctrl.signal);
    expect(init?.cache).toBe('no-store');
  });
});

describe('fetchResolvedValue — success', () => {
  it('returns parsed ResolvedValueResponse on 200', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(SUCCESS));
    const result = await fetchResolvedValue(makeBinding());
    expect(result).toEqual(SUCCESS);
    expect(result.cache_status).toBe('hit');
    expect(result.value).toBe('6.73');
  });
});

describe('fetchResolvedValue — error mapping', () => {
  it('maps RESOLVE_INVALID_FILTERS (400)', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            error_code: 'RESOLVE_INVALID_FILTERS',
            message: 'bad filters',
          },
        },
        { status: 400 },
      ),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 400,
      code: 'RESOLVE_INVALID_FILTERS',
      message: 'bad filters',
    });
  });

  it('maps MAPPING_NOT_FOUND (404)', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        { detail: { error_code: 'MAPPING_NOT_FOUND', message: 'no mapping' } },
        { status: 404 },
      ),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 404,
      code: 'MAPPING_NOT_FOUND',
    });
  });

  it('maps RESOLVE_CACHE_MISS (404)', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            error_code: 'RESOLVE_CACHE_MISS',
            message: 'no row after prime',
            details: { prime_attempted: true },
          },
        },
        { status: 404 },
      ),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 404,
      code: 'RESOLVE_CACHE_MISS',
    });
  });

  it('maps unknown error_code to UNKNOWN', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        { detail: { error_code: 'WAT', message: 'wat' } },
        { status: 500 },
      ),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 500,
      code: 'UNKNOWN',
      message: 'wat',
    });
  });

  it('falls back to status-based message when detail lacks message', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({}, { status: 503 }),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 503,
      code: 'UNKNOWN',
      message: 'Resolve fetch failed: 503',
    });
  });

  it('handles non-JSON error body without throwing parse error', async () => {
    fetchMock.mockResolvedValueOnce(rawJsonRejectingResponse(502));
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 502,
      code: 'UNKNOWN',
    });
  });

  it('maps FastAPI 422 array detail to RESOLVE_INVALID_FILTERS with joined msgs', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: [
            {
              type: 'int_parsing',
              loc: ['query', 'dim', 0],
              msg: 'Input should be a valid integer',
            },
            {
              type: 'int_parsing',
              loc: ['query', 'member', 0],
              msg: 'Input should be a valid integer',
            },
          ],
        },
        { status: 422 },
      ),
    );
    await expect(fetchResolvedValue(makeBinding())).rejects.toMatchObject({
      name: 'ResolveFetchError',
      status: 422,
      code: 'RESOLVE_INVALID_FILTERS',
      message:
        'Input should be a valid integer; Input should be a valid integer',
    });
  });
});

describe('ResolveFetchError', () => {
  it('exposes status, code, and name', () => {
    const err = new ResolveFetchError(404, 'MAPPING_NOT_FOUND', 'gone');
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(404);
    expect(err.code).toBe('MAPPING_NOT_FOUND');
    expect(err.name).toBe('ResolveFetchError');
  });
});
