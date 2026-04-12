export interface PublicationResponse {
  id: number;
  headline: string;
  chart_type: string;
  cdn_url: string | null;        // could be null for drafts that slipped through
  virality_score: number | null; // could be null for manually created publications
  created_at: string;            // ISO datetime
  version: number;
}

export interface PaginatedResponse {
  items: PublicationResponse[];
  total: number;
  limit: number;
  offset: number;
}
