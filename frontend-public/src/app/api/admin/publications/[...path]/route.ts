import { NextRequest, NextResponse } from 'next/server';

const BACKEND_ADMIN_PREFIX = '/api/v1/admin/publications';

async function forward(
  request: NextRequest,
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  pathParts: string[],
) {
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

  const tail = pathParts.length > 0 ? `/${pathParts.join('/')}` : '';
  const search = request.nextUrl.search;
  const target = `${apiUrl}${BACKEND_ADMIN_PREFIX}${tail}${search}`;

  // Defence in depth: server injects the key; any client-supplied
  // X-API-KEY / Authorization is ignored.
  const headers: Record<string, string> = {
    'X-API-KEY': apiKey,
  };

  let body: BodyInit | undefined;
  if (method === 'PATCH' || method === 'POST') {
    headers['Content-Type'] = 'application/json';
    body = await request.text();
  }

  const backendRes = await fetch(target, {
    method,
    headers,
    body,
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

interface Ctx {
  params: Promise<{ path?: string[] }>;
}

export async function GET(request: NextRequest, ctx: Ctx) {
  const { path = [] } = await ctx.params;
  return forward(request, 'GET', path);
}

export async function PATCH(request: NextRequest, ctx: Ctx) {
  const { path = [] } = await ctx.params;
  return forward(request, 'PATCH', path);
}

export async function POST(request: NextRequest, ctx: Ctx) {
  const { path = [] } = await ctx.params;
  return forward(request, 'POST', path);
}

export async function DELETE(request: NextRequest, ctx: Ctx) {
  const { path = [] } = await ctx.params;
  return forward(request, 'DELETE', path);
}
