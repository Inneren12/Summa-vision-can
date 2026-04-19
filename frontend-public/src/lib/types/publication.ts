import type { CanonicalDocument } from '@/components/editor/types';

/**
 * Public gallery publication shape — returned by the unauthenticated
 * `/api/v1/public/graphics` endpoints. NEVER includes review/workflow
 * metadata; admin-only fields are stripped server-side.
 */
export interface PublicationResponse {
  id: number;
  headline: string;
  chart_type: string;
  cdn_url: string | null;
  virality_score: number | null;
  created_at: string;
  version: number;
}

export interface PaginatedResponse {
  items: PublicationResponse[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Typed branding block persisted alongside the publication.
 * Mirrors `backend/src/schemas/publication.py::BrandingConfig`.
 */
export interface BrandingConfig {
  show_top_accent: boolean;
  show_corner_mark: boolean;
  accent_color: string;
}

/**
 * Visual configuration persisted on `Publication.visual_config` as a JSON
 * string. Mirrors `backend/src/schemas/publication.py::VisualConfig`.
 */
export interface VisualConfig {
  layout: string;
  palette: string;
  background: string;
  size: string;
  custom_primary?: string | null;
  branding: BrandingConfig;
}

/**
 * Review subtree persisted on `Publication.review`. The editor owns this
 * shape — see `CanonicalDocument['review']`. The backend accepts it
 * verbatim and does not deep-validate nested entries.
 */
export type ReviewPayload = CanonicalDocument['review'];

/**
 * Admin-facing publication representation. Matches
 * `backend/src/schemas/publication.py::PublicationResponse` (version as
 * of Stage 3 PR 4). Includes `visual_config` and `review` subtrees.
 *
 * `id` is a string (not number) to match the backend's forward-compat
 * signature — the admin id is treated opaquely in the frontend.
 */
export interface AdminPublicationResponse {
  id: string;
  headline: string;
  chart_type: string;
  eyebrow?: string | null;
  description?: string | null;
  source_text?: string | null;
  footnote?: string | null;
  visual_config?: VisualConfig | null;
  review?: ReviewPayload | null;
  virality_score?: number | null;
  status: string;
  cdn_url?: string | null;
  created_at: string;
  updated_at?: string | null;
  published_at?: string | null;
}
