import {
  publishAdminPublication,
  AdminPublicationNotFoundError,
  BackendApiError,
} from '@/lib/api/admin';

const originalFetch = global.fetch;

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
});

const okPublication = { id: '42', status: 'PUBLISHED', headline: 'h' };

function mockOk(etag: string | null = null) {
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: (k: string) => (k.toLowerCase() === 'etag' ? etag : null) },
    json: async () => okPublication,
  });
}

describe('publishAdminPublication', () => {
  it('returns { etag, document } on 200 with empty bound_blocks', async () => {
    mockOk('"v1"');
    const result = await publishAdminPublication('42', { bound_blocks: [] });
    expect(result.etag).toBe('"v1"');
    expect(result.document.id).toBe('42');
  });

  it('serializes bound_blocks payload as JSON body with Content-Type header', async () => {
    mockOk();
    const payload = {
      bound_blocks: [
        {
          block_id: 'b1',
          cube_id: 'c1',
          semantic_key: 'sk1',
          dims: [1, 2],
          members: [10, 20],
          period: '2024-Q3',
        },
      ],
    };
    await publishAdminPublication('42', payload);
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe('/api/admin/publications/42/publish');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual(payload);
    expect((init.headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  it('uses empty object as default payload when omitted', async () => {
    mockOk();
    await publishAdminPublication('42');
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.body).toBe('{}');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  it('forwards AbortSignal to fetch', async () => {
    mockOk();
    const controller = new AbortController();
    await publishAdminPublication('42', {}, { signal: controller.signal });
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.signal).toBe(controller.signal);
  });

  it('sends If-Match header when ifMatch option is provided', async () => {
    mockOk();
    await publishAdminPublication('42', {}, { ifMatch: '"abc"' });
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.headers['If-Match']).toBe('"abc"');
  });

  it('omits If-Match header when ifMatch is not provided', async () => {
    mockOk();
    await publishAdminPublication('42', {});
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.headers['If-Match']).toBeUndefined();
  });

  it('throws BackendApiError with PRECONDITION_FAILED on 412', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 412,
      json: async () => ({
        detail: { error_code: 'PRECONDITION_FAILED', message: 'etag mismatch' },
      }),
    });

    await expect(
      publishAdminPublication('42', {}, { ifMatch: '"old"' }),
    ).rejects.toMatchObject({
      name: 'BackendApiError',
      code: 'PRECONDITION_FAILED',
      status: 412,
    } as Partial<BackendApiError>);
  });

  it('throws AdminPublicationNotFoundError on 404 with code', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: { error_code: 'PUBLICATION_NOT_FOUND' } }),
    });

    await expect(publishAdminPublication('999', {})).rejects.toThrow(
      AdminPublicationNotFoundError,
    );
  });

  it('throws AdminPublicationNotFoundError on shapeless 404', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    await expect(publishAdminPublication('999', {})).rejects.toThrow(
      AdminPublicationNotFoundError,
    );
  });

  it('throws BackendApiError on 500', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    });

    await expect(publishAdminPublication('1', {})).rejects.toThrow(BackendApiError);
  });

  it('returns null etag when ETag header is absent', async () => {
    mockOk(null);
    const result = await publishAdminPublication('42', {});
    expect(result.etag).toBeNull();
  });
});
