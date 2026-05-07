/**
 * Phase 3.1d Slice 4b R2 — admin.ts publishAdminPublication header forwarding.
 *
 * Reviewer P2: hook-level tests verify usePublishAction calls the API client
 * with `{ ifMatch: null }`, but did not verify that the API client itself
 * translates `null`/`undefined` → header absent (vs. emitting a literal
 * "If-Match: null" header). These tests close that gap by asserting on the
 * actual fetch call.
 */
import { publishAdminPublication } from '../admin';

type FetchArgs = [RequestInfo | URL, RequestInit | undefined];
const fetchMock = jest.fn<Promise<Response>, FetchArgs>();

beforeEach(() => {
  fetchMock.mockReset();
  (globalThis as unknown as { fetch: typeof fetchMock }).fetch = fetchMock;
});

function publishOkResponse(): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ ETag: '"new-etag"' }),
    json: async () => ({ id: 1, headline: 'h' }) as unknown,
    text: async () => '{}',
  } as unknown as Response;
}

function headersFromInit(init: RequestInit | undefined): Headers {
  return new Headers((init?.headers ?? {}) as HeadersInit);
}

describe('publishAdminPublication — If-Match header forwarding (Slice 4b R2)', () => {
  it('omits If-Match header when ifMatch is null', async () => {
    fetchMock.mockResolvedValueOnce(publishOkResponse());
    await publishAdminPublication('p1', { bound_blocks: [] }, { ifMatch: null });
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = headersFromInit(init);
    expect(headers.has('If-Match')).toBe(false);
  });

  it('omits If-Match header when ifMatch is undefined', async () => {
    fetchMock.mockResolvedValueOnce(publishOkResponse());
    await publishAdminPublication('p1', { bound_blocks: [] }, {});
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = headersFromInit(init);
    expect(headers.has('If-Match')).toBe(false);
  });

  it('omits If-Match header when options omitted entirely', async () => {
    fetchMock.mockResolvedValueOnce(publishOkResponse());
    await publishAdminPublication('p1', { bound_blocks: [] });
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = headersFromInit(init);
    expect(headers.has('If-Match')).toBe(false);
  });

  it('forwards If-Match header verbatim when ifMatch is a strong-etag string', async () => {
    fetchMock.mockResolvedValueOnce(publishOkResponse());
    await publishAdminPublication(
      'p1',
      { bound_blocks: [] },
      { ifMatch: '"current-etag"' },
    );
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = headersFromInit(init);
    expect(headers.get('If-Match')).toBe('"current-etag"');
  });

  it('returns ETag from response headers on success', async () => {
    fetchMock.mockResolvedValueOnce(publishOkResponse());
    const result = await publishAdminPublication(
      'p1',
      { bound_blocks: [] },
      { ifMatch: '"prev"' },
    );
    expect(result.etag).toBe('"new-etag"');
  });
});
