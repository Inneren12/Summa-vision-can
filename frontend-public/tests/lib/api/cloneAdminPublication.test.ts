import {
  cloneAdminPublication,
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

describe('cloneAdminPublication', () => {
  it('returns response on 201', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: '42', status: 'DRAFT', cloned_from_publication_id: 1 }),
    });

    const result = await cloneAdminPublication('1');
    expect(result.id).toBe('42');
  });

  it('throws AdminPublicationNotFoundError on 404 with code', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: { error_code: 'PUBLICATION_NOT_FOUND' } }),
    });

    await expect(cloneAdminPublication('999')).rejects.toThrow(AdminPublicationNotFoundError);
  });

  it('throws AdminPublicationNotFoundError on shapeless 404', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    await expect(cloneAdminPublication('999')).rejects.toThrow(AdminPublicationNotFoundError);
  });

  it('throws BackendApiError with code on 409', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        detail: {
          error_code: 'PUBLICATION_CLONE_NOT_ALLOWED',
          message: 'cannot clone draft',
          details: { current_status: 'DRAFT' },
        },
      }),
    });

    await expect(cloneAdminPublication('1')).rejects.toMatchObject({
      name: 'BackendApiError',
      code: 'PUBLICATION_CLONE_NOT_ALLOWED',
      status: 409,
    } as Partial<BackendApiError>);
  });

  it('throws BackendApiError on 500', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal server error' }),
    });

    await expect(cloneAdminPublication('1')).rejects.toThrow(BackendApiError);
  });
});
