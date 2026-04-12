import { POST } from '@/app/api/revalidate/route';
import { revalidatePath } from 'next/cache';
import { NextResponse } from 'next/server';

jest.mock('next/cache', () => ({
  revalidatePath: jest.fn(),
}));

jest.mock('next/server', () => ({
  NextResponse: {
    json: jest.fn((body, init) => {
      return {
        status: init?.status ?? 200,
        json: async () => body,
      };
    }),
  },
}));

describe('POST /api/revalidate', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.clearAllMocks();
    process.env = { ...originalEnv, REVALIDATION_SECRET: 'test-secret' };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  function createMockRequest(body: any, headers: Record<string, string> = {}) {
    return {
      json: jest.fn().mockResolvedValue(body),
      headers: {
        get: jest.fn().mockImplementation((key) => headers[key] || null),
      },
    } as unknown as Request;
  }

  it('rejects missing secret', async () => {
    const req = createMockRequest({});
    const res: any = await POST(req);

    expect(res.status).toBe(401);
    const data = await res.json();
    expect(data.message).toBe('Invalid secret');
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it('rejects invalid secret', async () => {
    const req = createMockRequest({ secret: 'wrong-secret' });
    const res: any = await POST(req);

    expect(res.status).toBe(401);
    expect(revalidatePath).not.toHaveBeenCalled();
  });

  it('accepts valid secret in body and revalidates default path', async () => {
    const req = createMockRequest({ secret: 'test-secret' });
    const res: any = await POST(req);

    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.revalidated).toBe(true);
    expect(data.paths).toEqual(['/']);
    expect(revalidatePath).toHaveBeenCalledWith('/');
  });

  it('accepts valid secret in header and revalidates specific paths', async () => {
    const req = createMockRequest(
      { paths: ['/graphics/1', '/graphics/2'] },
      { Authorization: 'Bearer test-secret' }
    );
    const res: any = await POST(req);

    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.revalidated).toBe(true);
    expect(data.paths).toEqual(['/graphics/1', '/graphics/2']);

    expect(revalidatePath).toHaveBeenCalledWith('/graphics/1');
    expect(revalidatePath).toHaveBeenCalledWith('/graphics/2');
    expect(revalidatePath).toHaveBeenCalledTimes(2);
  });

  it('rejects malformed JSON request if header secret is also missing', async () => {
    const req = {
      json: jest.fn().mockRejectedValue(new Error('Invalid JSON')),
      headers: { get: jest.fn().mockReturnValue(null) }
    } as unknown as Request;

    const res: any = await POST(req);
    expect(res.status).toBe(401);
    const data = await res.json();
    expect(data.message).toBe('Invalid secret');
  });

  it('accepts malformed/empty JSON request if header secret is valid', async () => {
    const req = {
      json: jest.fn().mockRejectedValue(new Error('Invalid JSON')),
      headers: { get: jest.fn().mockReturnValue('Bearer test-secret') }
    } as unknown as Request;

    const res: any = await POST(req);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.revalidated).toBe(true);
    expect(data.paths).toEqual(['/']);
  });
});
