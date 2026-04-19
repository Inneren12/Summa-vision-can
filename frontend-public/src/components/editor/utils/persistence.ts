// Persistence seam between the editor's `CanonicalDocument` and the
// backend admin PATCH payload. Pure functions; no I/O, no Date/Math/
// randomness. Invariant: `buildUpdatePayload(hydrateDoc(pub))` produces
// a payload consistent with `pub` (modulo fields that don't round-trip;
// see DEBT-026 for the lossy set).

import type {
  CanonicalDocument,
  Block,
  PageConfig,
} from '../types';
import { mkDoc } from '../registry/templates';
import { TPLS } from '../registry/templates';
import type {
  UpdateAdminPublicationPayload,
} from '@/lib/api/admin';
import type {
  AdminPublicationResponse,
  BrandingConfig,
  VisualConfig,
} from '@/lib/types/publication';

// Editor `size` slug (e.g. `instagram_1080`) to backend `size` slug
// (e.g. `instagram`). Backend accepts a narrower set — see
// `backend/src/schemas/publication.py::VisualConfig`.
const SIZE_TO_BACKEND: Record<string, string> = {
  instagram_1080: 'instagram',
  instagram_port: 'instagram',
  twitter: 'twitter',
  reddit: 'reddit',
  linkedin: 'linkedin',
  story: 'story',
};

// Inverse mapping for hydration. Lossy: `instagram` collapses to the
// 1:1 default since `instagram_port` can't be recovered from the
// backend's coarser `size` slug. See DEBT-026.
const SIZE_FROM_BACKEND: Record<string, string> = {
  instagram: 'instagram_1080',
  twitter: 'twitter',
  reddit: 'reddit',
  linkedin: 'linkedin',
  story: 'story',
};

const DEFAULT_BRANDING: BrandingConfig = {
  show_top_accent: true,
  show_corner_mark: true,
  accent_color: '#FBBF24',
};

function blockByType(
  doc: CanonicalDocument,
  type: string,
): Block | undefined {
  return Object.values(doc.blocks).find((b) => b.type === type);
}

function blockTextByType(
  doc: CanonicalDocument,
  type: string,
): string | undefined {
  const block = blockByType(doc, type);
  if (!block) return undefined;
  const text = block.props?.text;
  return typeof text === 'string' ? text : undefined;
}

// TODO(DEBT-026): layout → chart_type and editorial-text-block →
// top-level publication fields are best-effort approximations. The
// editor's block graph is richer than the backend's flat columns, so
// some edits (e.g. multi-line block-level props) are stored in
// `visual_config` but no backend column exists to round-trip them.
function deriveChartType(templateId: string): string {
  if (templateId.startsWith('single_stat')) return 'infographic';
  if (templateId.startsWith('bar')) return 'bar';
  if (templateId.startsWith('line')) return 'line';
  return 'infographic';
}

function deriveLayout(templateId: string): string {
  if (templateId.startsWith('single_stat')) return 'single_stat';
  if (templateId.startsWith('bar')) return 'bar_editorial';
  if (templateId.startsWith('line')) return 'line_editorial';
  if (templateId.startsWith('comparison')) return 'comparison';
  return 'single_stat';
}

/**
 * Extract a backend-compatible PATCH payload from a CanonicalDocument.
 *
 * Fields are OMITTED from the payload when the source data is absent
 * (undefined), since the backend's `exclude_unset=True` treats omitted
 * fields as "unchanged". Only `null` is sent when a field was
 * explicitly cleared — see DEBT-026 for the fields this task does not
 * yet distinguish explicit-clear from never-set.
 */
export function buildUpdatePayload(
  doc: CanonicalDocument,
): UpdateAdminPublicationPayload {
  const headline = blockTextByType(doc, 'headline_editorial');
  const eyebrow = blockTextByType(doc, 'eyebrow_tag');
  const sourceText = blockTextByType(doc, 'source_footer');
  const footnote = blockTextByType(doc, 'body_annotation');
  const description = blockTextByType(doc, 'subtitle_descriptor');

  const page: PageConfig = doc.page;
  const backendSize = SIZE_TO_BACKEND[page.size] ?? 'instagram';

  const visualConfig: VisualConfig = {
    layout: deriveLayout(doc.templateId),
    palette: page.palette,
    background: page.background,
    size: backendSize,
    custom_primary: null,
    branding: DEFAULT_BRANDING,
  };

  const payload: UpdateAdminPublicationPayload = {
    chart_type: deriveChartType(doc.templateId),
    visual_config: visualConfig,
    review: doc.review,
  };
  if (headline !== undefined) payload.headline = headline;
  if (eyebrow !== undefined) payload.eyebrow = eyebrow;
  if (sourceText !== undefined) payload.source_text = sourceText;
  if (footnote !== undefined) payload.footnote = footnote;
  if (description !== undefined) payload.description = description;

  return payload;
}

/**
 * Reconstruct a CanonicalDocument from an AdminPublicationResponse so
 * the editor can be seeded. This is a loose inverse of
 * `buildUpdatePayload` — the backend schema cannot express every
 * nuance of the editor's block graph, so we start from the default
 * template and overlay what the backend preserved.
 *
 * Round-trip guarantee is limited to `review` (exact) and
 * `visual_config.palette/background/size` (mapped). Block-level props
 * beyond the well-known editorial text blocks are reset to template
 * defaults. See DEBT-026.
 */
export function hydrateDoc(
  pub: AdminPublicationResponse,
): CanonicalDocument {
  // Start from the default template. This reseeds every block to its
  // registry default — acceptable for Task 0 scope.
  const base = mkDoc('single_stat_hero', TPLS.single_stat_hero);

  const vc = pub.visual_config;
  if (vc) {
    base.page = {
      size: SIZE_FROM_BACKEND[vc.size] ?? base.page.size,
      background: vc.background || base.page.background,
      palette: vc.palette || base.page.palette,
    };
  }

  // Overlay editorial text blocks when we recognise the block type.
  overlayBlockText(base, 'headline_editorial', pub.headline);
  overlayBlockText(base, 'eyebrow_tag', pub.eyebrow ?? undefined);
  overlayBlockText(base, 'source_footer', pub.source_text ?? undefined);
  overlayBlockText(base, 'body_annotation', pub.footnote ?? undefined);
  overlayBlockText(base, 'subtitle_descriptor', pub.description ?? undefined);

  // Review subtree round-trips losslessly.
  if (pub.review) {
    base.review = {
      workflow: pub.review.workflow,
      history: pub.review.history ?? [],
      comments: pub.review.comments ?? [],
    };
  }

  return base;
}

function overlayBlockText(
  doc: CanonicalDocument,
  blockType: string,
  text: string | undefined,
): void {
  if (text === undefined) return;
  const block = Object.values(doc.blocks).find((b) => b.type === blockType);
  if (!block) return;
  block.props = { ...block.props, text };
}
