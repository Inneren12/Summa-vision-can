// Used ONLY in 'use client' components
// No next.revalidate — plain browser fetch

import type { UtmAttribution } from '../attribution/utm';
import type { PaginatedResponse, PublicationResponse } from '../types/publication';

export type { PaginatedResponse, PublicationResponse };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface LeadCaptureResponse {
  message: string;
}

const UTM_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_content',
] as const;

/**
 * Filter a UTM attribution to only the four canonical, non-empty keys.
 * Stops runtime-only extra keys from leaking into the request body
 * (the backend rejects unknown keys via ``extra="forbid"``) and drops
 * empty strings so the backend's whitespace normalizer does not have
 * to deal with frontend-induced noise.
 */
function pickUtm(utm: UtmAttribution | undefined): UtmAttribution {
  if (!utm) return {};
  const out: UtmAttribution = {};
  for (const key of UTM_KEYS) {
    const value = utm[key];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length > 0) out[key] = trimmed;
    }
  }
  return out;
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
      // Only present, non-empty UTM keys are spread into the request body.
      // Backend's ``extra="forbid"`` schema rejects unknown keys; whitespace-
      // only values are normalized server-side via ``field_validator``.
      ...pickUtm(utm),
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
