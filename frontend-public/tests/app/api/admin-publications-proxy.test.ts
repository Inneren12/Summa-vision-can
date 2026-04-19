/**
 * Tests for the admin publications proxy route handler.
 *
 * The proxy lives at `src/app/api/admin/publications/[...path]/route.ts`
 * and forwards requests to the backend admin API, injecting the server-
 * only `X-API-KEY` header from `ADMIN_API_KEY`. Client-supplied auth
 * headers are never propagated.
 */

jest.mock('next/server', () => {
  class MockNextResponse {
    status: number;
    private readonly bodyText: string;
    readonly headers: Map<string, string>;
    constructor(body: string, init?: { status?: number; headers?: Record<string, string> }) {
      this.bodyText = body;
      this.status = init?.status ?? 200;
      this.headers = new Map(Object.entries(init?.headers ?? {}));
    }
    async text() {
      return this.bodyText;
    }
    async json() {
      return JSON.parse(this.bodyText);
    }
    static json(body: unknown, init?: { status?: number }) {
      return new MockNextResponse(JSON.stringify(body), {
        status: init?.status ?? 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }
  return { NextResponse: MockNextResponse, NextRequest: class {} };
});

import { GET, PATCH } from '@/app/api/admin/publications/[...path]/route';

interface FakeRequestOptions {
  search?: string;
  bodyText?: string;
  headers?: Record<string, string>;
}

function makeRequest(url: string, opts: FakeRequestOptions = {}) {
  const u = new URL(url);
  return {
    nextUrl: { search: opts.search ?? u.search },
    text: jest.fn(async () => opts.bodyText ?? ''),
    headers: {
      get: (k: string) => opts.headers?.[k] ?? null,
    },
  } as any;
}

function ctx(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

const originalFetch = global.fetch;
const originalEnv = process.env;

beforeEach(() => {
  jest.clearAllMocks();
  process.env = {
    ...originalEnv,
    NEXT_PUBLIC_API_URL: 'http://backend:8000',
    ADMIN_API_KEY: 'test-admin-key',
  };
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  process.env = originalEnv;
});

const mockFetch = () =>
  global.fetch as jest.MockedFunction<typeof global.fetch>;

describe('admin publications proxy route', () => {
  it('returns 500 when NEXT_PUBLIC_API_URL is missing', async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    const req = makeRequest('http://localhost:3000/api/admin/publications/42');
    const res = await GET(req, ctx(['42']));
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({
      error: 'NEXT_PUBLIC_API_URL not configured',
    });
    expect(mockFetch()).not.toHaveBeenCalled();
  });

  it('returns 500 when ADMIN_API_KEY is missing', async () => {
    delete process.env.ADMIN_API_KEY;
    const req = makeRequest('http://localhost:3000/api/admin/publications/42');
    const res = await GET(req, ctx(['42']));
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({
      error: 'ADMIN_API_KEY not configured',
    });
    expect(mockFetch()).not.toHaveBeenCalled();
  });

  it('forwards GET /42 to backend with X-API-KEY and returns body', async () => {
    mockFetch().mockResolvedValue({
      status: 200,
      text: async () => JSON.stringify({ id: '42', headline: 'ok' }),
      headers: new Map([['Content-Type', 'application/json']]),
    } as any);

    const req = makeRequest('http://localhost:3000/api/admin/publications/42');
    const res = await GET(req, ctx(['42']));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ id: '42', headline: 'ok' });

    const [calledUrl, init] = mockFetch().mock.calls[0] as any;
    expect(calledUrl).toBe('http://backend:8000/api/v1/admin/publications/42');
    expect(init.method).toBe('GET');
    expect(init.headers['X-API-KEY']).toBe('test-admin-key');
    expect(init.cache).toBe('no-store');
  });

  it('preserves search parameters on forward', async () => {
    mockFetch().mockResolvedValue({
      status: 200,
      text: async () => '[]',
      headers: new Map([['Content-Type', 'application/json']]),
    } as any);

    const req = makeRequest(
      'http://localhost:3000/api/admin/publications?status=draft&limit=10',
      { search: '?status=draft&limit=10' },
    );
    const res = await GET(req, ctx([]));
    expect(res.status).toBe(200);

    const [calledUrl] = mockFetch().mock.calls[0] as any;
    expect(calledUrl).toBe(
      'http://backend:8000/api/v1/admin/publications?status=draft&limit=10',
    );
  });

  it('PATCH forwards JSON body and sets Content-Type', async () => {
    const backendBody = JSON.stringify({ id: '42', headline: 'new' });
    mockFetch().mockResolvedValue({
      status: 200,
      text: async () => backendBody,
      headers: new Map([['Content-Type', 'application/json']]),
    } as any);

    const req = makeRequest(
      'http://localhost:3000/api/admin/publications/42',
      { bodyText: '{"headline":"new"}' },
    );
    const res = await PATCH(req, ctx(['42']));
    expect(res.status).toBe(200);

    const [, init] = mockFetch().mock.calls[0] as any;
    expect(init.method).toBe('PATCH');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.headers['X-API-KEY']).toBe('test-admin-key');
    expect(init.body).toBe('{"headline":"new"}');
  });

  it('strips client-provided X-API-KEY header (server always injects own)', async () => {
    mockFetch().mockResolvedValue({
      status: 200,
      text: async () => '{}',
      headers: new Map([['Content-Type', 'application/json']]),
    } as any);

    const req = makeRequest(
      'http://localhost:3000/api/admin/publications/42',
      { headers: { 'X-API-KEY': 'client-attempted-override' } },
    );
    await GET(req, ctx(['42']));

    const [, init] = mockFetch().mock.calls[0] as any;
    // Server value wins unconditionally; client override never reaches backend.
    expect(init.headers['X-API-KEY']).toBe('test-admin-key');
    expect(init.headers['X-API-KEY']).not.toBe('client-attempted-override');
  });

  it('forwards non-200 status codes verbatim', async () => {
    mockFetch().mockResolvedValue({
      status: 404,
      text: async () => JSON.stringify({ detail: 'Publication not found' }),
      headers: new Map([['Content-Type', 'application/json']]),
    } as any);

    const req = makeRequest('http://localhost:3000/api/admin/publications/999');
    const res = await GET(req, ctx(['999']));
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ detail: 'Publication not found' });
  });
});
