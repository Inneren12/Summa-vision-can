/**
 * @jest-environment node
 *
 * Phase 3.1d Slice 3b — proxy route tests.
 *
 * The route at /api/admin/resolve/[cubeId]/[semanticKey] is the security
 * boundary that closes DEBT-078: it reads ADMIN_API_KEY server-side and
 * proxies to backend. These tests lock the security invariants
 * (ADMIN_API_KEY read server-side only, X-API-KEY forwarded, unknown
 * query params stripped, path segments URL-encoded, backend status/body/
 * content-type preserved).
 *
 * Without these tests, a refactor could silently:
 *   - swap process.env.ADMIN_API_KEY for NEXT_PUBLIC_ADMIN_API_KEY
 *   - accept client-supplied X-API-KEY
 *   - drop encodeURIComponent on path segments
 *   - leak unknown query params (e.g. cookies, csrf tokens) to backend
 * — and pass the existing test suite. This file prevents that.
 *
 * Test environment: node (not jsdom). next/server's NextRequest depends
 * on Web Request, which jsdom does not expose globally. Node 22+ exposes
 * Request natively so the node test env is the correct fit (and matches
 * how the route handler runs in production).
 */
import { NextRequest } from 'next/server';

import { GET } from '../route';

type FetchArgs = [RequestInfo | URL, RequestInit | undefined];
const fetchMock = jest.fn<Promise<Response>, FetchArgs>();

const ORIGINAL_ENV = { ...process.env };

beforeEach(() => {
  fetchMock.mockReset();
  (globalThis as unknown as { fetch: typeof fetchMock }).fetch = fetchMock;
  process.env = {
    ...ORIGINAL_ENV,
    NEXT_PUBLIC_API_URL: 'http://backend.test',
    ADMIN_API_KEY: 'test-admin-key',
  };
});

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
});

function makeReq(url: string): NextRequest {
  return new NextRequest(new URL(url, 'http://localhost'));
}

function makeCtx(cubeId: string, semanticKey: string) {
  return { params: Promise.resolve({ cubeId, semanticKey }) };
}

function backendResponse(
  body: unknown,
  init: { status?: number; contentType?: string } = {},
): Response {
  const status = init.status ?? 200;
  const contentType = init.contentType ?? 'application/json';
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (k: string) =>
        k.toLowerCase() === 'content-type' ? contentType : null,
    },
    text: async () =>
      typeof body === 'string' ? body : JSON.stringify(body),
  } as unknown as Response;
}

describe('proxy route — env validation', () => {
  it('returns 500 when NEXT_PUBLIC_API_URL is missing', async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    const res = await GET(
      makeReq('/api/admin/resolve/18100004/metric_x'),
      makeCtx('18100004', 'metric_x'),
    );
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/NEXT_PUBLIC_API_URL/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns 500 when ADMIN_API_KEY is missing', async () => {
    delete process.env.ADMIN_API_KEY;
    const res = await GET(
      makeReq('/api/admin/resolve/18100004/metric_x'),
      makeCtx('18100004', 'metric_x'),
    );
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/ADMIN_API_KEY/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns 400 when cubeId or semanticKey is empty', async () => {
    const res = await GET(
      makeReq('/api/admin/resolve//metric_x'),
      makeCtx('', 'metric_x'),
    );
    expect(res.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('proxy route — forwarding', () => {
  it('forwards GET to backend with X-API-KEY header (server-side only)', async () => {
    fetchMock.mockResolvedValueOnce(
      backendResponse({ value: '6.73', cache_status: 'hit' }),
    );
    await GET(
      makeReq('/api/admin/resolve/18100004/metric_x?period=2024-Q3'),
      makeCtx('18100004', 'metric_x'),
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    expect(init?.method).toBe('GET');
    expect(init?.cache).toBe('no-store');
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.['X-API-KEY']).toBe('test-admin-key');
  });

  it('does NOT forward client-supplied X-API-KEY header', async () => {
    // Defence-in-depth: client header is ignored; route always uses
    // process.env.ADMIN_API_KEY. (Route reads only request URL params,
    // not headers, so this is a structural guarantee — but lock it.)
    fetchMock.mockResolvedValueOnce(backendResponse({}));
    const req = makeReq('/api/admin/resolve/c/k');
    // Add a hostile header to the request — route must not propagate.
    req.headers.set('X-API-KEY', 'attacker-key');
    await GET(req, makeCtx('c', 'k'));
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.['X-API-KEY']).toBe('test-admin-key');
    expect(headers?.['X-API-KEY']).not.toBe('attacker-key');
  });

  it('forwards only dim/member/period; strips unknown query params', async () => {
    fetchMock.mockResolvedValueOnce(backendResponse({}));
    await GET(
      makeReq(
        '/api/admin/resolve/c/k?dim=1&member=12&period=2024-Q3&attacker=x&csrf=y',
      ),
      makeCtx('c', 'k'),
    );
    const [target] = fetchMock.mock.calls[0]!;
    const url = new URL(String(target));
    expect(url.searchParams.has('dim')).toBe(true);
    expect(url.searchParams.has('member')).toBe(true);
    expect(url.searchParams.has('period')).toBe(true);
    expect(url.searchParams.has('attacker')).toBe(false);
    expect(url.searchParams.has('csrf')).toBe(false);
  });

  it('preserves repeated dim/member query params positionally', async () => {
    fetchMock.mockResolvedValueOnce(backendResponse({}));
    await GET(
      makeReq(
        '/api/admin/resolve/c/k?dim=1&member=12&dim=2&member=5&period=2024',
      ),
      makeCtx('c', 'k'),
    );
    const [target] = fetchMock.mock.calls[0]!;
    const url = new URL(String(target));
    expect(url.searchParams.getAll('dim')).toEqual(['1', '2']);
    expect(url.searchParams.getAll('member')).toEqual(['12', '5']);
  });

  it('URL-encodes cubeId and semanticKey path segments', async () => {
    fetchMock.mockResolvedValueOnce(backendResponse({}));
    await GET(
      makeReq('/api/admin/resolve/a%2Fb/metric%20x'),
      makeCtx('a/b', 'metric x'),
    );
    const [target] = fetchMock.mock.calls[0]!;
    expect(String(target)).toContain('/api/v1/admin/resolve/a%2Fb/metric%20x');
  });

  it('omits period query param when blank', async () => {
    fetchMock.mockResolvedValueOnce(backendResponse({}));
    await GET(
      makeReq('/api/admin/resolve/c/k?period='),
      makeCtx('c', 'k'),
    );
    const [target] = fetchMock.mock.calls[0]!;
    const url = new URL(String(target));
    expect(url.searchParams.has('period')).toBe(false);
  });
});

describe('proxy route — backend response passthrough', () => {
  it('preserves backend status code', async () => {
    fetchMock.mockResolvedValueOnce(
      backendResponse(
        { detail: { error_code: 'MAPPING_NOT_FOUND', message: 'no mapping' } },
        { status: 404 },
      ),
    );
    const res = await GET(
      makeReq('/api/admin/resolve/c/k'),
      makeCtx('c', 'k'),
    );
    expect(res.status).toBe(404);
  });

  it('preserves backend body', async () => {
    fetchMock.mockResolvedValueOnce(
      backendResponse({ value: '42', cache_status: 'hit' }),
    );
    const res = await GET(
      makeReq('/api/admin/resolve/c/k'),
      makeCtx('c', 'k'),
    );
    const body = await res.json();
    expect(body.value).toBe('42');
    expect(body.cache_status).toBe('hit');
  });

  it('preserves backend Content-Type header', async () => {
    fetchMock.mockResolvedValueOnce(
      backendResponse({ x: 1 }, { contentType: 'application/json; charset=utf-8' }),
    );
    const res = await GET(
      makeReq('/api/admin/resolve/c/k'),
      makeCtx('c', 'k'),
    );
    expect(res.headers.get('Content-Type')).toBe(
      'application/json; charset=utf-8',
    );
  });

  it('falls back to application/json when backend has no Content-Type', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => null },
      text: async () => '{}',
    } as unknown as Response);
    const res = await GET(
      makeReq('/api/admin/resolve/c/k'),
      makeCtx('c', 'k'),
    );
    expect(res.headers.get('Content-Type')).toBe('application/json');
  });

  it('preserves backend 422 array detail body for client extractResolveError', async () => {
    // End-to-end check: ensure proxy doesn't transform the FastAPI 422
    // shape that admin-resolve client's extractResolveError depends on.
    const validation422 = {
      detail: [
        {
          type: 'int_parsing',
          loc: ['query', 'dim', 0],
          msg: 'Input should be a valid integer',
        },
      ],
    };
    fetchMock.mockResolvedValueOnce(backendResponse(validation422, { status: 422 }));
    const res = await GET(
      makeReq('/api/admin/resolve/c/k?dim=geo&member=CA'),
      makeCtx('c', 'k'),
    );
    expect(res.status).toBe(422);
    const body = await res.json();
    expect(Array.isArray(body.detail)).toBe(true);
    expect(body.detail[0].msg).toBe('Input should be a valid integer');
  });
});
