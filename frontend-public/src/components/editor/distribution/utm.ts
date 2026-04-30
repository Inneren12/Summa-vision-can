export interface BuildUtmUrlOptions {
  canonicalUrl: string;
  utm_source: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content: string;
}

export function buildUtmUrl(options: BuildUtmUrlOptions): string {
  const {
    canonicalUrl,
    utm_source,
    utm_medium = 'social',
    utm_campaign = 'publish_kit',
    utm_content,
  } = options;

  const url = new URL(canonicalUrl);
  url.searchParams.set('utm_source', utm_source);
  url.searchParams.set('utm_medium', utm_medium);
  url.searchParams.set('utm_campaign', utm_campaign);
  url.searchParams.set('utm_content', utm_content);

  return url.toString();
}
