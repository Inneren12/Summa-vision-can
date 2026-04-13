/** Client-side METR API functions (browser fetch, no revalidate). */

import type {
  METRCalculateParams,
  METRCalculateResponse,
  METRCurveParams,
  METRCurveResponse,
} from '../types/metr';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchMETRCalculation(
  params: METRCalculateParams,
): Promise<METRCalculateResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('income', String(params.income));
  if (params.province) searchParams.set('province', params.province);
  if (params.family_type) searchParams.set('family_type', params.family_type);
  if (params.n_children != null)
    searchParams.set('n_children', String(params.n_children));
  if (params.children_under_6 != null)
    searchParams.set('children_under_6', String(params.children_under_6));

  const res = await fetch(
    `${API_URL}/api/v1/public/metr/calculate?${searchParams.toString()}`,
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'METR calculation failed');
  }
  return res.json();
}

export async function fetchMETRCurve(
  params: METRCurveParams = {},
): Promise<METRCurveResponse> {
  const searchParams = new URLSearchParams();
  if (params.province) searchParams.set('province', params.province);
  if (params.family_type) searchParams.set('family_type', params.family_type);
  if (params.n_children != null)
    searchParams.set('n_children', String(params.n_children));
  if (params.children_under_6 != null)
    searchParams.set('children_under_6', String(params.children_under_6));
  if (params.income_min != null)
    searchParams.set('income_min', String(params.income_min));
  if (params.income_max != null)
    searchParams.set('income_max', String(params.income_max));
  if (params.step != null) searchParams.set('step', String(params.step));

  const qs = searchParams.toString();
  const url = `${API_URL}/api/v1/public/metr/curve${qs ? `?${qs}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'METR curve fetch failed');
  }
  return res.json();
}
