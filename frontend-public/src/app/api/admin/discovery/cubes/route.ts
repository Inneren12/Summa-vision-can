import { NextRequest, NextResponse } from 'next/server';

const BACKEND_PATH = '/api/v1/admin/cubes/search';

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

  // Defence in depth: forward only `q`. Reject any other params.
  const q = request.nextUrl.searchParams.get('q') ?? '';
  const search = `?q=${encodeURIComponent(q)}`;
  const target = `${apiUrl}${BACKEND_PATH}${search}`;

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
