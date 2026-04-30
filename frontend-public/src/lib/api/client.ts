// Used ONLY in 'use client' components
// No next.revalidate — plain browser fetch

import type { UtmAttribution } from '../attribution/utm';
import type { PaginatedResponse, PublicationResponse } from '../types/publication';

export type { PaginatedResponse, PublicationResponse };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface LeadCaptureResponse {
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
  turnstileToken: string,
  utm: UtmAttribution = {},
): Promise<LeadCaptureResponse> {
  const res = await fetch(`${API_URL}/api/v1/public/leads/capture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      asset_id: assetId,
      turnstile_token: turnstileToken,
      // Phase 2.3 UTM attribution. Only present keys are sent so the
      // backend's ``extra="forbid"`` schema does not reject empty strings.
      ...utm,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Request failed');
  }
  return res.json();
}

export function getDownloadUrl(token: string): string {
  return `${API_URL}/api/v1/public/download?token=${encodeURIComponent(token)}`;
}
