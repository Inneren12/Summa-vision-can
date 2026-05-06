import { NextRequest, NextResponse } from 'next/server';

const BACKEND_PATH = '/api/v1/admin/cube-metadata';

interface Ctx {
  params: Promise<{ cubeId: string }>;
}

export async function GET(_request: NextRequest, ctx: Ctx) {
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

  const { cubeId } = await ctx.params;
  // Defence in depth: do NOT forward query params (`prime`, `product_id` are
  // admin-cache-management features, not discovery). v1 reads cached metadata.
  const target = `${apiUrl}${BACKEND_PATH}/${encodeURIComponent(cubeId)}`;

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
