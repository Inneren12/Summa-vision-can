import type { CanonicalDocument, PlatformId } from '../types';
import { buildChannelCaption } from './builder';
import { CAPTION_CHAR_LIMIT } from './captionLength';
import { buildUtmUrl } from './utm';

export interface ChannelDistribution {
  share_url: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  caption: string;
  char_count: number;
  char_limit: number;
}

export interface DistributionJson {
  schemaVersion: 1;
  publication: {
    lineage_key: string;
    slug: string;
    canonical_url: string;
    headline: string;
  };
  channels: {
    reddit: ChannelDistribution;
    twitter: ChannelDistribution;
    linkedin: ChannelDistribution;
  };
  generated_at: string;
}

export interface BuildDistributionJsonOptions {
  doc: CanonicalDocument;
  lineage_key: string;
  slug: string;
  baseUrl: string;
  now?: Date;
}

function getHeadline(doc: CanonicalDocument): string {
  const block = Object.values(doc.blocks).find((candidate) => candidate.type === 'headline_editorial');
  const raw = block?.props?.text;
  return typeof raw === 'string' && raw.trim().length > 0 ? raw : '';
}

function buildChannelDistribution(
  platform: PlatformId,
  canonicalUrl: string,
  headline: string,
  lineageKey: string,
): ChannelDistribution {
  const utm_source = platform;
  const utm_medium = 'social';
  const utm_campaign = 'publish_kit';
  const utm_content = lineageKey;
  const share_url = buildUtmUrl({ canonicalUrl, utm_source, utm_medium, utm_campaign, utm_content });
  const caption = buildChannelCaption({ platform, headline, shareUrl: share_url });

  return {
    share_url,
    utm_source,
    utm_medium,
    utm_campaign,
    utm_content,
    caption,
    char_count: caption.length,
    char_limit: CAPTION_CHAR_LIMIT[platform],
  };
}

export function buildDistributionJson(options: BuildDistributionJsonOptions): DistributionJson {
  const { doc, lineage_key, slug, now } = options;
  const baseUrl = options.baseUrl.replace(/\/+$/, '');
  const canonical_url = `${baseUrl}/p/${slug}`;
  const headline = getHeadline(doc);

  return {
    schemaVersion: 1,
    publication: {
      lineage_key,
      slug,
      canonical_url,
      headline,
    },
    channels: {
      reddit: buildChannelDistribution('reddit', canonical_url, headline, lineage_key),
      twitter: buildChannelDistribution('twitter', canonical_url, headline, lineage_key),
      linkedin: buildChannelDistribution('linkedin', canonical_url, headline, lineage_key),
    },
    generated_at: (now ?? new Date()).toISOString(),
  };
}
