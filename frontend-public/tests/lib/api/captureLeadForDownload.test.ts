/**
 * Phase 2.3 — captureLeadForDownload UTM body shape tests.
 *
 * Asserts the wire format the backend's ``LeadCaptureRequest`` schema
 * is contracted to receive:
 * - UTM keys sent only when present (``extra="forbid"`` on the backend
 *   would reject ``utm_source: ""`` etc., so the client must omit them).
 * - Required fields always present in the body.
 */
import { captureLeadForDownload } from '@/lib/api/client';

const originalFetch = global.fetch;

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
});

function okResponse(body: unknown = { message: 'ok' }) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  } as Response;
}

function bodyOfFirstCall(): Record<string, unknown> {
  const fetchMock = global.fetch as jest.MockedFunction<typeof global.fetch>;
  const init = fetchMock.mock.calls[0][1] as RequestInit;
  return JSON.parse(init.body as string) as Record<string, unknown>;
}

describe('captureLeadForDownload', () => {
  it('includes UTM in POST body when present', async () => {
    (global.fetch as jest.MockedFunction<typeof global.fetch>).mockResolvedValue(
      okResponse(),
    );

    await captureLeadForDownload('user@company.ca', 1, 'token', {
      utm_source: 'reddit',
      utm_content: 'ln_abc123',
    });

    const body = bodyOfFirstCall();
    expect(body.email).toBe('user@company.ca');
    expect(body.asset_id).toBe(1);
    expect(body.turnstile_token).toBe('token');
    expect(body.utm_source).toBe('reddit');
    expect(body.utm_content).toBe('ln_abc123');
    // Keys not present in attribution must be absent from the body
    // (backend rejects extra="" via extra="forbid").
    expect(body.utm_medium).toBeUndefined();
    expect(body.utm_campaign).toBeUndefined();
  });

  it('forwards all four UTM keys when all are present', async () => {
    (global.fetch as jest.MockedFunction<typeof global.fetch>).mockResolvedValue(
      okResponse(),
    );

    await captureLeadForDownload('user@company.ca', 1, 'token', {
      utm_source: 'reddit',
      utm_medium: 'social',
      utm_campaign: 'publish_kit',
      utm_content: 'ln_xyz',
    });

    const body = bodyOfFirstCall();
    expect(body.utm_source).toBe('reddit');
    expect(body.utm_medium).toBe('social');
    expect(body.utm_campaign).toBe('publish_kit');
    expect(body.utm_content).toBe('ln_xyz');
  });

  it('omits UTM keys from body when attribution is empty', async () => {
    (global.fetch as jest.MockedFunction<typeof global.fetch>).mockResolvedValue(
      okResponse(),
    );

    await captureLeadForDownload('user@company.ca', 1, 'token');

    const body = bodyOfFirstCall();
    expect(body.email).toBe('user@company.ca');
    expect(body.utm_source).toBeUndefined();
    expect(body.utm_medium).toBeUndefined();
    expect(body.utm_campaign).toBeUndefined();
    expect(body.utm_content).toBeUndefined();
  });

  it('omits UTM keys from body when attribution is explicit {}', async () => {
    (global.fetch as jest.MockedFunction<typeof global.fetch>).mockResolvedValue(
      okResponse(),
    );

    await captureLeadForDownload('user@company.ca', 1, 'token', {});

    const body = bodyOfFirstCall();
    expect(body.utm_source).toBeUndefined();
    expect(body.utm_content).toBeUndefined();
  });

  it('throws on non-2xx response', async () => {
    (global.fetch as jest.MockedFunction<typeof global.fetch>).mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'validation error' }),
    } as Response);

    await expect(
      captureLeadForDownload('user@company.ca', 1, 'token'),
    ).rejects.toThrow('validation error');
  });
});
