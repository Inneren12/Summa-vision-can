// Used ONLY in 'use client' components
// No next.revalidate — plain browser fetch

import type { PaginatedResponse, PublicationResponse } from '../types/publication';

export type { PaginatedResponse, PublicationResponse };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface LeadCaptureResponse {
  download_url: string;
  message: string;
}

export async function fetchMoreGraphics(
  limit: number,
  offset: number,
): Promise<PaginatedResponse> {
  const res = await fetch(
    `${API_URL}/api/v1/public/graphics?limit=${limit}&offset=${offset}&sort=newest`,
  );
  if (!res.ok) throw new Error(`Load more failed: ${res.status}`);
  return res.json();
}

export async function captureLeadForDownload(
  email: string,
  assetId: number,
): Promise<LeadCaptureResponse> {
  const res = await fetch(`${API_URL}/api/v1/public/leads/capture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, asset_id: assetId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Request failed');
  }
  return res.json();
}
