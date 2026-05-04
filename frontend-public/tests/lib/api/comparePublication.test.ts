import {
  comparePublication,
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

const validResponse = {
  publication_id: 42,
  overall_status: 'fresh',
  overall_severity: 'info',
  compared_at: '2026-05-04T12:00:00Z',
  block_results: [],
};

describe('comparePublication', () => {
  it('returns parsed CompareResponse on 200', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validResponse,
    });

    const result = await comparePublication('42');
    expect(result.publication_id).toBe(42);
    expect(result.overall_status).toBe('fresh');
    expect(result.block_results).toEqual([]);
  });

  it('POSTs with no body, no headers, and cache: no-store', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validResponse,
    });

    await comparePublication('42');
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe('/api/admin/publications/42/compare');
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
    expect(init.headers).toBeUndefined();
    expect(init.cache).toBe('no-store');
  });

  it('throws AdminPublicationNotFoundError on 404 with code', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: { error_code: 'PUBLICATION_NOT_FOUND' } }),
    });

    await expect(comparePublication('999')).rejects.toThrow(AdminPublicationNotFoundError);
  });

  it('throws AdminPublicationNotFoundError on shapeless 404', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    await expect(comparePublication('999')).rejects.toThrow(AdminPublicationNotFoundError);
  });

  it('throws BackendApiError on 500', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    });

    await expect(comparePublication('1')).rejects.toThrow(BackendApiError);
  });

  it('forwards AbortSignal to fetch', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => validResponse,
    });

    const controller = new AbortController();
    await comparePublication('42', { signal: controller.signal });
    const [, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(init.signal).toBe(controller.signal);
  });
});
