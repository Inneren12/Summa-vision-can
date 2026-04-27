import {
  fetchAdminPublication,
  fetchAdminPublicationList,
  updateAdminPublication,
  AdminPublicationNotFoundError,
} from '@/lib/api/admin';

const originalFetch = global.fetch;

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
});

const mockFetch = () =>
  global.fetch as jest.MockedFunction<typeof global.fetch>;

function okResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function errorResponse(status: number, body: unknown = {}) {
  return {
    ok: false,
    status,
    json: async () => body,
  } as Response;
}

describe('fetchAdminPublication', () => {
  it('GETs /api/admin/publications/:id and returns parsed JSON with etag null when header absent', async () => {
    mockFetch().mockResolvedValue(okResponse({ id: '42', headline: 'x' }));
    const result = await fetchAdminPublication('42');
    expect(result).toEqual({ id: '42', headline: 'x', etag: null });
    const [url, init] = mockFetch().mock.calls[0] as any;
    expect(url).toBe('/api/admin/publications/42');
    expect(init.cache).toBe('no-store');
  });

  it('throws AdminPublicationNotFoundError on 404', async () => {
    mockFetch().mockResolvedValue(errorResponse(404, { detail: 'not found' }));
    await expect(fetchAdminPublication('missing')).rejects.toBeInstanceOf(
      AdminPublicationNotFoundError,
    );
  });

  it('throws generic Error with parsed detail on other errors', async () => {
    mockFetch().mockResolvedValue(errorResponse(500, { detail: 'boom' }));
    await expect(fetchAdminPublication('42')).rejects.toThrow('boom');
  });

  it('encodes special characters in id', async () => {
    mockFetch().mockResolvedValue(okResponse({ id: 'a/b' }));
    await fetchAdminPublication('a/b');
    const [url] = mockFetch().mock.calls[0] as any;
    expect(url).toBe('/api/admin/publications/a%2Fb');
  });

  it('propagates AbortSignal to fetch', async () => {
    mockFetch().mockResolvedValue(okResponse({ id: '42' }));
    const controller = new AbortController();
    await fetchAdminPublication('42', { signal: controller.signal });
    const [, init] = mockFetch().mock.calls[0] as any;
    expect(init.signal).toBe(controller.signal);
  });
});

describe('fetchAdminPublicationList', () => {
  it('builds querystring from options', async () => {
    mockFetch().mockResolvedValue(okResponse([]));
    await fetchAdminPublicationList({ status: 'draft', limit: 5, offset: 10 });
    const [url] = mockFetch().mock.calls[0] as any;
    expect(url).toBe('/api/admin/publications?status=draft&limit=5&offset=10');
  });

  it('omits querystring when no options provided', async () => {
    mockFetch().mockResolvedValue(okResponse([]));
    await fetchAdminPublicationList();
    const [url] = mockFetch().mock.calls[0] as any;
    expect(url).toBe('/api/admin/publications');
  });

  it('throws on non-ok with parsed detail', async () => {
    mockFetch().mockResolvedValue(
      errorResponse(500, { detail: 'list boom' }),
    );
    await expect(fetchAdminPublicationList()).rejects.toThrow('list boom');
  });
});

describe('updateAdminPublication', () => {
  it('PATCHes with JSON body and returns response with etag null when header absent', async () => {
    mockFetch().mockResolvedValue(
      okResponse({ id: '42', headline: 'new' }),
    );
    const result = await updateAdminPublication('42', { headline: 'new' });
    expect(result).toEqual({ id: '42', headline: 'new', etag: null });

    const [url, init] = mockFetch().mock.calls[0] as any;
    expect(url).toBe('/api/admin/publications/42');
    expect(init.method).toBe('PATCH');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body)).toEqual({ headline: 'new' });
    // No If-Match was passed → header not set.
    expect(init.headers['If-Match']).toBeUndefined();
  });

  it('forwards opts.ifMatch as If-Match header when provided', async () => {
    mockFetch().mockResolvedValue(okResponse({ id: '42', headline: 'x' }));
    await updateAdminPublication(
      '42',
      { headline: 'x' },
      { ifMatch: 'W/"abc1234567890"' },
    );
    const [, init] = mockFetch().mock.calls[0] as any;
    expect(init.headers['If-Match']).toBe('W/"abc1234567890"');
  });

  it('captures ETag response header into result.etag when present', async () => {
    const headers = new Headers({ ETag: 'W/"feedfacef00d0001"' });
    mockFetch().mockResolvedValue({
      ok: true,
      status: 200,
      headers,
      json: async () => ({ id: '42', headline: 'x' }),
    } as Response);
    const result = await updateAdminPublication('42', { headline: 'x' });
    expect(result.etag).toBe('W/"feedfacef00d0001"');
  });

  it('throws AdminPublicationNotFoundError on 404', async () => {
    mockFetch().mockResolvedValue(errorResponse(404));
    await expect(
      updateAdminPublication('missing', { headline: 'x' }),
    ).rejects.toBeInstanceOf(AdminPublicationNotFoundError);
  });

  it('throws generic Error on 422', async () => {
    mockFetch().mockResolvedValue(
      errorResponse(422, { detail: 'Unknown field' }),
    );
    await expect(
      updateAdminPublication('42', { headline: 'x' }),
    ).rejects.toThrow('Unknown field');
  });

  it('propagates AbortSignal', async () => {
    mockFetch().mockResolvedValue(okResponse({ id: '42' }));
    const controller = new AbortController();
    await updateAdminPublication(
      '42',
      { headline: 'x' },
      { signal: controller.signal },
    );
    const [, init] = mockFetch().mock.calls[0] as any;
    expect(init.signal).toBe(controller.signal);
  });
});
