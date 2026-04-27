import { mkDoc, TPLS } from '@/components/editor/registry/templates';
import {
  buildUpdatePayload,
  hydrateDoc,
  HydrationError,
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
    // Phase 2.1 PR#2: backend slug 'twitter' deserializes to the renamed
    // editor preset id 'twitter_landscape' via SIZE_FROM_BACKEND.
    expect(doc.page.size).toBe('twitter_landscape');
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

describe('buildUpdatePayload — document_state + derived fields', () => {
  it('serialises the full doc into document_state as JSON text', () => {
    const doc = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    const payload = buildUpdatePayload(doc);
    expect(typeof payload.document_state).toBe('string');
    const parsed = JSON.parse(payload.document_state!);
    // Round-trip through JSON.parse yields an equivalent value.
    expect(parsed.templateId).toBe(doc.templateId);
    expect(parsed.blocks).toEqual(doc.blocks);
    expect(parsed.review).toEqual(doc.review);
  });
});

describe('hydrateDoc — document_state (lossless) path', () => {
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

  it('parses document_state and returns the full doc when present', () => {
    const authored = mkDoc('single_stat_hero', TPLS.single_stat_hero);
    // Mutate a block-level prop that the legacy field-level hydrate
    // would NOT round-trip — proves we're going through the lossless path.
    const headlineId = Object.keys(authored.blocks).find(
      (id) => authored.blocks[id].type === 'headline_editorial',
    )!;
    authored.blocks[headlineId].props = {
      ...authored.blocks[headlineId].props,
      text: 'Custom block-level text',
      // Arbitrary prop the legacy path has no mirror for:
      customProp: { nested: ['a', 'b', 'c'] },
    };

    const response = baseResponse({
      document_state: JSON.stringify(authored),
    });
    const doc = hydrateDoc(response);
    expect(doc.blocks[headlineId].props.text).toBe('Custom block-level text');
    expect(doc.blocks[headlineId].props.customProp).toEqual({
      nested: ['a', 'b', 'c'],
    });
  });

  it('throws HydrationError when document_state is present but not JSON', () => {
    const response = baseResponse({ document_state: '{not valid json' });
    expect(() => hydrateDoc(response)).toThrow(HydrationError);
  });

  it('propagates validation errors when document_state shape is invalid', () => {
    const response = baseResponse({
      document_state: JSON.stringify({ schemaVersion: 2, bogus: true }),
    });
    // validateImportStrict throws a non-HydrationError with a descriptive
    // message. The caller (server page) re-throws into error.tsx.
    expect(() => hydrateDoc(response)).toThrow();
  });
});

describe('hydrateDoc — legacy path (document_state is null)', () => {
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

  it('uses review.workflow when review is present', () => {
    const review = {
      workflow: 'in_review' as const,
      history: [],
      comments: [],
    };
    const doc = hydrateDoc(baseResponse({ review }));
    expect(doc.review.workflow).toBe('in_review');
  });

  it('derives workflow="published" from status when review is absent (B3 fix)', () => {
    const doc = hydrateDoc(
      baseResponse({ status: 'PUBLISHED', review: null }),
    );
    expect(doc.review.workflow).toBe('published');
  });

  it('derives workflow="draft" from status when review is absent and status is not PUBLISHED', () => {
    const doc = hydrateDoc(baseResponse({ status: 'DRAFT', review: null }));
    expect(doc.review.workflow).toBe('draft');
  });

  it('accepts lower-case status strings too', () => {
    const doc = hydrateDoc(
      baseResponse({ status: 'published', review: null }),
    );
    expect(doc.review.workflow).toBe('published');
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
