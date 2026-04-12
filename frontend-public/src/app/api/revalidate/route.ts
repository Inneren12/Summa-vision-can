import { NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';

export async function POST(request: Request) {
  try {
    let secret;
    let paths;
    try {
      const body = await request.json();
      secret = body.secret;
      paths = body.paths;
    } catch {
      // Empty or invalid body is fine if header secret is provided
    }

    const headerSecret = request.headers.get('Authorization')?.replace('Bearer ', '');
    const providedSecret = secret || headerSecret;
    const expectedSecret = process.env.REVALIDATION_SECRET;

    if (!expectedSecret || providedSecret !== expectedSecret) {
      return NextResponse.json({ message: 'Invalid secret' }, { status: 401 });
    }

    if (Array.isArray(paths) && paths.length > 0) {
      paths.forEach((path) => {
        if (typeof path === 'string') {
          revalidatePath(path);
        }
      });
      return NextResponse.json({ revalidated: true, paths });
    }

    // Default to revalidating the home page gallery
    revalidatePath('/');
    return NextResponse.json({ revalidated: true, paths: ['/'] });

  } catch {
    return NextResponse.json({ message: 'Error processing request' }, { status: 400 });
  }
}
