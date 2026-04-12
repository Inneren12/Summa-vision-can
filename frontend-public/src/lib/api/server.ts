// Used ONLY in Server Components and generateMetadata()
// NOT imported by any 'use client' component

import type { PaginatedResponse, PublicationResponse } from '../types/publication';

export type { PaginatedResponse, PublicationResponse };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchPublishedGraphics(
  limit = 24,
  offset = 0,
): Promise<PaginatedResponse> {
  const res = await fetch(
    `${API_URL}/api/v1/public/graphics?limit=${limit}&offset=${offset}&sort=newest`,
    { next: { revalidate: 3600 } },
  );
  if (!res.ok) throw new Error(`Gallery fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchGraphic(id: number | string): Promise<PublicationResponse | null> {
  const res = await fetch(`${API_URL}/api/v1/public/graphics/${id}`, {
    next: { revalidate: 3600 },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch graphic ${id}: ${res.status}`);
  return res.json();
}
