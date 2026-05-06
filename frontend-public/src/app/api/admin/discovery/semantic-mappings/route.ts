import { NextRequest, NextResponse } from 'next/server';

const BACKEND_PATH = '/api/v1/admin/semantic-mappings';
const HARD_LIMIT_CAP = 200;

export async function GET(request: NextRequest) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const apiKey = process.env.ADMIN_API_KEY;

  if (!apiUrl) {
    return NextResponse.json(
      { error: 'NEXT_PUBLIC_API_URL not configured' },
      { status: 500 },
    );
  }
  if (!apiKey) {
    return NextResponse.json(
      { error: 'ADMIN_API_KEY not configured' },
      { status: 500 },
    );
  }

  // Defence in depth: forward only `cube_id`, `limit`, `offset`. Hard-cap limit.
  const sp = request.nextUrl.searchParams;
  const params = new URLSearchParams();
  const cubeId = sp.get('cube_id');
  if (cubeId) params.set('cube_id', cubeId);
  const limitRaw = sp.get('limit');
  if (limitRaw !== null) {
    const n = Number.parseInt(limitRaw, 10);
    if (Number.isFinite(n) && n > 0) {
      params.set('limit', String(Math.min(n, HARD_LIMIT_CAP)));
    }
  }
  const offsetRaw = sp.get('offset');
  if (offsetRaw !== null) {
    const n = Number.parseInt(offsetRaw, 10);
    if (Number.isFinite(n) && n >= 0) params.set('offset', String(n));
  }
  const qs = params.toString();
  const target = `${apiUrl}${BACKEND_PATH}${qs ? `?${qs}` : ''}`;

  const backendRes = await fetch(target, {
    method: 'GET',
    headers: { 'X-API-KEY': apiKey },
    cache: 'no-store',
  });

  const responseBody = await backendRes.text();
  return new NextResponse(responseBody, {
    status: backendRes.status,
    headers: {
      'Content-Type':
        backendRes.headers.get('Content-Type') ?? 'application/json',
    },
  });
}
