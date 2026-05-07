import { NextRequest, NextResponse } from 'next/server';

const BACKEND_PATH = '/api/v1/admin/resolve';

interface Ctx {
  params: Promise<{ cubeId: string; semanticKey: string }>;
}

export async function GET(request: NextRequest, ctx: Ctx) {
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

  const { cubeId, semanticKey } = await ctx.params;
  if (!cubeId.trim() || !semanticKey.trim()) {
    return NextResponse.json(
      { error: 'cubeId and semanticKey are required' },
      { status: 400 },
    );
  }

  // Defence in depth: forward only `dim`, `member`, `period`; ignore any
  // other params. `dim` and `member` are repeated query keys preserving
  // order — backend pairs them positionally (dim[i] ↔ member[i]).
  const sp = request.nextUrl.searchParams;
  const params = new URLSearchParams();
  for (const dim of sp.getAll('dim')) params.append('dim', dim);
  for (const member of sp.getAll('member')) params.append('member', member);
  const period = sp.get('period');
  if (period !== null && period !== '') params.set('period', period);

  const qs = params.toString();
  const target = `${apiUrl}${BACKEND_PATH}/${encodeURIComponent(cubeId)}/${encodeURIComponent(semanticKey)}${qs ? `?${qs}` : ''}`;

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
