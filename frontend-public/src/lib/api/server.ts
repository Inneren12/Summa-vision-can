import type { PaginatedResponse, PublicationResponse } from '../types/publication';

// Used ONLY in Server Components and generateMetadata()
// NOT imported by any 'use client' component

export async function fetchPublishedGraphics(limit = 24, offset = 0): Promise<PaginatedResponse> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/public/graphics?limit=${limit}&offset=${offset}&sort=newest`,
    { next: { revalidate: 3600 } }
  );
  if (!res.ok) throw new Error(`Gallery fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchGraphic(id: number | string): Promise<PublicationResponse | null> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/public/graphics/${id}`,
    { next: { revalidate: 3600 } }
  );
  if (!res.ok) return null;
  return res.json();
}
