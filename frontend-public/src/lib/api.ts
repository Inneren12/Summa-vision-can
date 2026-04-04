const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface Publication {
  id: number;
  headline: string;
  chart_type: string;
  virality_score: number;
  status: string;
  preview_url: string | null;
  created_at: string;
}

export interface LeadCaptureResponse {
  download_url: string;
  message: string;
}

export async function fetchPublishedGraphics(
  limit = 12,
  offset = 0,
): Promise<Publication[]> {
  const res = await fetch(
    `${API_URL}/api/v1/public/graphics?limit=${limit}&offset=${offset}&sort=newest`,
    { next: { revalidate: 3600 } },
  );
  if (!res.ok) throw new Error('Failed to fetch graphics');
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
