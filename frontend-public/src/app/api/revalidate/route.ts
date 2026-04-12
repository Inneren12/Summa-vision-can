import { NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';

const ALLOWED_REVALIDATION_PREFIXES = ['/', '/graphics'];

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
      // Validate all paths before revalidating any
      const invalidPaths = paths.filter((p: string) =>
        !ALLOWED_REVALIDATION_PREFIXES.some(prefix => p === prefix || p.startsWith(prefix + '/'))
      );

      if (invalidPaths.length > 0) {
        return NextResponse.json(
          { message: `Invalid paths: ${invalidPaths.join(', ')}. Allowed prefixes: ${ALLOWED_REVALIDATION_PREFIXES.join(', ')}` },
          { status: 400 },
        );
      }

      for (const path of paths) {
        if (typeof path === 'string') {
          revalidatePath(path);
        }
      }
      return NextResponse.json({ revalidated: true, paths });
    }

    // Default to revalidating the home page gallery
    revalidatePath('/');
    return NextResponse.json({ revalidated: true, paths: ['/'] });

  } catch {
    return NextResponse.json({ message: 'Error processing request' }, { status: 400 });
  }
}
