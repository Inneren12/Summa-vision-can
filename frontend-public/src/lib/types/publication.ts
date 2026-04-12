export interface PublicationResponse {
  id: number;
  headline: string;
  chart_type: string;
  cdn_url: string;        // NOT presigned URL — this is the CDN URL (R1)
  virality_score: number;
  created_at: string;     // ISO datetime
  version: number;
}

export interface PaginatedResponse {
  items: PublicationResponse[];
  total: number;
  limit: number;
  offset: number;
}
