import type { CanonicalDocument } from '../../types';
import { buildDistributionJson } from '../distributionJson';
import { buildPublishKitTxt } from '../publishKitTxt';

const baseDoc: CanonicalDocument = {
  schemaVersion: 3,
  templateId: 'editorial_v1',
  page: { size: 'instagram_1080', background: 'bg1', palette: 'pal1', exportPresets: ['instagram_1080'] },
  sections: [],
  blocks: {
    h1: {
      id: 'h1',
      type: 'headline_editorial',
      visible: true,
      props: {
        text: 'A'.repeat(400),
      },
    },
  },
  meta: {
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
    version: 1,
    history: [],
  },
  review: {
    workflow: 'draft',
    history: [],
    comments: [],
  },
};

describe('distribution builders', () => {
  it('buildDistributionJson builds schema, urls, channels and char metadata without truncation', () => {
    const distribution = buildDistributionJson({
      doc: baseDoc,
      lineage_key: 'ln_abc123',
      slug: 'my-post',
      baseUrl: 'https://example.com/',
      now: new Date('2026-04-30T12:00:00.000Z'),
    });

    expect(distribution.schemaVersion).toBe(1);
    expect(distribution.publication.canonical_url).toBe('https://example.com/p/my-post');
    expect(distribution.generated_at).toBe('2026-04-30T12:00:00.000Z');
    expect(distribution.channels.reddit).toBeDefined();
    expect(distribution.channels.twitter).toBeDefined();
    expect(distribution.channels.linkedin).toBeDefined();

    const channels = Object.values(distribution.channels);
    for (const channel of channels) {
      expect(channel.utm_content).toBe('ln_abc123');
      expect(channel.char_count).toBe(channel.caption.length);
    }

    expect(distribution.channels.twitter.char_count).toBeGreaterThan(distribution.channels.twitter.char_limit);
  });

  it('buildPublishKitTxt formats sections in order with caption/url and trailing newline', () => {
    const distribution = buildDistributionJson({
      doc: baseDoc,
      lineage_key: 'ln_abc123',
      slug: 'my-post',
      baseUrl: 'https://example.com',
      now: new Date('2026-04-30T12:00:00.000Z'),
    });

    const out = buildPublishKitTxt({ distribution });

    expect(out).toContain('=== Reddit ===');
    expect(out).toContain('=== X / Twitter ===');
    expect(out).toContain('=== LinkedIn ===');

    const redditIndex = out.indexOf('=== Reddit ===');
    const twitterIndex = out.indexOf('=== X / Twitter ===');
    const linkedinIndex = out.indexOf('=== LinkedIn ===');
    expect(redditIndex).toBeLessThan(twitterIndex);
    expect(twitterIndex).toBeLessThan(linkedinIndex);

    expect(out).toContain(distribution.channels.reddit.caption);
    expect(out).toContain(distribution.channels.reddit.share_url);
    expect(out).toContain(distribution.channels.twitter.caption);
    expect(out).toContain(distribution.channels.twitter.share_url);
    expect(out).toContain(distribution.channels.linkedin.caption);
    expect(out).toContain(distribution.channels.linkedin.share_url);
    expect(out.endsWith('\n')).toBe(true);
  });
});
