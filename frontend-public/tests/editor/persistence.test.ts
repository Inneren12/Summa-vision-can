import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import {
  buildUpdatePayload,
  hydrateDoc,
} from '@/components/editor/utils/persistence';
import type { AdminPublicationResponse } from '@/lib/types/publication';

describe('buildUpdatePayload', () => {
  it('extracts headline, eyebrow, source_text from standard template blocks', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(typeof payload.headline).toBe('string');
    expect(payload.headline!.length).toBeGreaterThan(0);
    expect(typeof payload.eyebrow).toBe('string');
    expect(typeof payload.source_text).toBe('string');
  });

  it('sends review subtree verbatim', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(payload.review).toBe(doc.review);
    expect(payload.review!.workflow).toBe('draft');
  });

  it('derives visual_config from doc.page and templateId', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(payload.visual_config).toBeDefined();
    expect(payload.visual_config!.palette).toBe(doc.page.palette);
    expect(payload.visual_config!.background).toBe(doc.page.background);
    expect(payload.visual_config!.layout).toBe('single_stat');
    // instagram_1080 maps to backend size 'instagram'
    expect(payload.visual_config!.size).toBe('instagram');
  });

  it('derives chart_type from templateId', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(payload.chart_type).toBe('infographic');
  });

  it('includes default branding block', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(payload.visual_config!.branding).toEqual({
      show_top_accent: true,
      show_corner_mark: true,
      accent_color: '#FBBF24',
    });
  });

  it('omits fields whose block types are not present', () => {
    // `single_stat_minimal` has no eyebrow_tag (see templates.ts).
    const doc = mkDoc('single_stat_minimal', TPLS.single_stat_minimal);
    const payload = buildUpdatePayload(doc);
    expect(payload.eyebrow).toBeUndefined();
  });
});

describe('hydrateDoc', () => {
  function baseResponse(
    overrides: Partial<AdminPublicationResponse> = {},
  ): AdminPublicationResponse {
    return {
      id: '42',
      headline: 'Test Headline',
      chart_type: 'infographic',
      status: 'DRAFT',
      created_at: '2026-04-19T00:00:00Z',
      ...overrides,
    };
  }

  it('seeds from default template when no visual_config / review', () => {
    const doc = hydrateDoc(baseResponse());
    expect(doc.templateId).toBe('single_stat_hero');
    expect(doc.review.workflow).toBe('draft');
  });

  it('overlays headline into the headline_editorial block', () => {
    const doc = hydrateDoc(baseResponse({ headline: 'Overlaid Headline' }));
    const headlineBlock = Object.values(doc.blocks).find(
      (b) => b.type === 'headline_editorial',
    );
    expect(headlineBlock).toBeDefined();
    expect(headlineBlock!.props.text).toBe('Overlaid Headline');
  });

  it('overlays eyebrow into eyebrow_tag block', () => {
    const doc = hydrateDoc(baseResponse({ eyebrow: 'CUSTOM TAG' }));
    const eyebrowBlock = Object.values(doc.blocks).find(
      (b) => b.type === 'eyebrow_tag',
    );
    expect(eyebrowBlock!.props.text).toBe('CUSTOM TAG');
  });

  it('overlays source_text into source_footer block', () => {
    const doc = hydrateDoc(baseResponse({ source_text: 'Source: X' }));
    const sourceBlock = Object.values(doc.blocks).find(
      (b) => b.type === 'source_footer',
    );
    expect(sourceBlock!.props.text).toBe('Source: X');
  });

  it('maps visual_config.palette/background/size into doc.page', () => {
    const doc = hydrateDoc(
      baseResponse({
        visual_config: {
          layout: 'single_stat',
          palette: 'government',
          background: 'solid_dark',
          size: 'twitter',
          custom_primary: null,
          branding: {
            show_top_accent: true,
            show_corner_mark: true,
            accent_color: '#FBBF24',
          },
        },
      }),
    );
    expect(doc.page.palette).toBe('government');
    expect(doc.page.background).toBe('solid_dark');
    expect(doc.page.size).toBe('twitter');
  });

  it('round-trips review subtree losslessly', () => {
    const review = {
      workflow: 'in_review' as const,
      history: [
        {
          ts: '2026-04-19T00:00:00Z',
          action: 'created',
          summary: 'Document created',
          author: 'you',
          fromWorkflow: null,
          toWorkflow: 'draft' as const,
        },
      ],
      comments: [],
    };
    const doc = hydrateDoc(baseResponse({ review }));
    expect(doc.review.workflow).toBe('in_review');
    expect(doc.review.history).toEqual(review.history);
    expect(doc.review.comments).toEqual([]);
  });
});

describe('buildUpdatePayload ∘ hydrateDoc (approximate round-trip)', () => {
  it('preserves review through a round-trip', () => {
    const response: AdminPublicationResponse = {
      id: '42',
      headline: 'Round-trip',
      chart_type: 'infographic',
      status: 'DRAFT',
      created_at: '2026-04-19T00:00:00Z',
      review: {
        workflow: 'approved',
        history: [],
        comments: [],
      },
    };
    const doc = hydrateDoc(response);
    const payload = buildUpdatePayload(doc);
    expect(payload.review!.workflow).toBe('approved');
  });

  it('preserves headline through a round-trip', () => {
    const response: AdminPublicationResponse = {
      id: '42',
      headline: 'Round-trip Headline',
      chart_type: 'infographic',
      status: 'DRAFT',
      created_at: '2026-04-19T00:00:00Z',
    };
    const doc = hydrateDoc(response);
    const payload = buildUpdatePayload(doc);
    expect(payload.headline).toBe('Round-trip Headline');
  });
});
