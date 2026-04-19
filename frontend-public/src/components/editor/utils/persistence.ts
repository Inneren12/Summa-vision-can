// Persistence seam between the editor's `CanonicalDocument` and the
// backend admin PATCH payload. Pure functions; no I/O, no Date/Math/
// randomness.
//
// DEBT-026 closure (Stage 4 Task 0 full close):
// - `document_state` is the source of truth. `buildUpdatePayload` sends
//   the full doc as a JSON string; the backend stores it verbatim.
// - Derived editorial columns (headline/chart_type/eyebrow/description/
//   source_text/footnote/visual_config/review) are kept in sync on every
//   PATCH for search indexing and public gallery preview.
// - `hydrateDoc` prefers `document_state` (lossless); when absent (legacy
//   rows created before the column existed) it falls back to the
//   field-level mapping, which is known-lossy for block-level props.

import type {
  CanonicalDocument,
  Block,
  PageConfig,
  WorkflowState,
} from '../types';
import { mkDoc } from '../registry/templates';
import { TPLS } from '../registry/templates';
import { validateImportStrict } from '../registry/guards';
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

// Inverse mapping used only by the legacy hydrate path. `instagram`
// collapses to the 1:1 default since `instagram_port` can't be
// recovered from the backend's coarser `size` slug — irrelevant once a
// row has `document_state`, which stores the full editor slug.
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

// ---------------------------------------------------------------------------
// Derived-field helpers. Used both by `buildUpdatePayload` (to keep the
// backend's denormalised editorial columns in sync) and by the legacy
// hydrate path (to rebuild a doc from scalar columns when `document_state`
// is absent). Pure — never touch global state.
// ---------------------------------------------------------------------------

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

function extractHeadline(doc: CanonicalDocument): string | undefined {
  return blockTextByType(doc, 'headline_editorial');
}

function extractEyebrow(doc: CanonicalDocument): string | undefined {
  return blockTextByType(doc, 'eyebrow_tag');
}

function extractSourceText(doc: CanonicalDocument): string | undefined {
  return blockTextByType(doc, 'source_footer');
}

function extractFootnote(doc: CanonicalDocument): string | undefined {
  return blockTextByType(doc, 'body_annotation');
}

function extractDescription(doc: CanonicalDocument): string | undefined {
  return blockTextByType(doc, 'subtitle_descriptor');
}

function extractChartType(doc: CanonicalDocument): string {
  const tid = doc.templateId;
  if (tid.startsWith('single_stat')) return 'infographic';
  if (tid.startsWith('bar')) return 'bar';
  if (tid.startsWith('line')) return 'line';
  return 'infographic';
}

function deriveLayout(templateId: string): string {
  if (templateId.startsWith('single_stat')) return 'single_stat';
  if (templateId.startsWith('bar')) return 'bar_editorial';
  if (templateId.startsWith('line')) return 'line_editorial';
  if (templateId.startsWith('comparison')) return 'comparison';
  return 'single_stat';
}

function extractVisualConfig(doc: CanonicalDocument): VisualConfig {
  const page: PageConfig = doc.page;
  const backendSize = SIZE_TO_BACKEND[page.size] ?? 'instagram';
  return {
    layout: deriveLayout(doc.templateId),
    palette: page.palette,
    background: page.background,
    size: backendSize,
    custom_primary: null,
    branding: DEFAULT_BRANDING,
  };
}

// ---------------------------------------------------------------------------
// Hydration error — thrown by `hydrateDoc` when `document_state` is
// present but malformed. Callers (the admin editor server page) should
// re-throw so Next.js renders error.tsx.
// ---------------------------------------------------------------------------

export class HydrationError extends Error {
  public readonly publicationId: string;

  constructor(message: string, publicationId: string) {
    super(message);
    this.name = 'HydrationError';
    this.publicationId = publicationId;
  }
}

// ---------------------------------------------------------------------------
// buildUpdatePayload — emits the opaque full document + derived fields.
// ---------------------------------------------------------------------------

/**
 * Build a PATCH payload from the current canonical document.
 *
 * Post-DEBT-026, `document_state` is the source of truth: the full
 * serialised CanonicalDocument as JSON text. Derived editorial fields
 * (headline, chart_type, etc.) are included alongside so backend search
 * indexing and the public gallery (which queries those columns) keep
 * working.
 *
 * Pure function: no I/O, no Date.now, no Math.random.
 */
export function buildUpdatePayload(
  doc: CanonicalDocument,
): UpdateAdminPublicationPayload {
  const documentState = JSON.stringify(doc);

  const payload: UpdateAdminPublicationPayload = {
    document_state: documentState,
    // Derived fields — denormalised for indexing/preview:
    chart_type: extractChartType(doc),
    visual_config: extractVisualConfig(doc),
    review: doc.review,
  };

  const headline = extractHeadline(doc);
  const eyebrow = extractEyebrow(doc);
  const sourceText = extractSourceText(doc);
  const footnote = extractFootnote(doc);
  const description = extractDescription(doc);

  if (headline !== undefined) payload.headline = headline;
  if (eyebrow !== undefined) payload.eyebrow = eyebrow;
  if (sourceText !== undefined) payload.source_text = sourceText;
  if (footnote !== undefined) payload.footnote = footnote;
  if (description !== undefined) payload.description = description;

  return payload;
}

// ---------------------------------------------------------------------------
// hydrateDoc — lossless primary path + legacy fallback.
// ---------------------------------------------------------------------------

/**
 * Reconstruct a CanonicalDocument from a persisted publication.
 *
 * Priority:
 *   1. If `document_state` is present, parse + validate it. This is the
 *      lossless path.
 *   2. Otherwise, fall back to the legacy field-level hydrate (known-lossy
 *      for block-level props; used only for rows that predate the
 *      `document_state` column).
 *
 * Throws `HydrationError` if `document_state` is present but is not
 * valid JSON. Callers should surface this via error.tsx rather than
 * silently falling back — a corrupt column is a data-integrity issue,
 * not a legacy row.
 */
export function hydrateDoc(
  pub: AdminPublicationResponse,
): CanonicalDocument {
  if (pub.document_state != null) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(pub.document_state);
    } catch (err) {
      throw new HydrationError(
        `document_state is present but not valid JSON: ${err instanceof Error ? err.message : String(err)}`,
        pub.id,
      );
    }
    // validateImportStrict throws on invalid shape; let it propagate —
    // the caller (server page) re-throws into error.tsx.
    return validateImportStrict(parsed);
  }

  return hydrateFromLegacyFields(pub);
}

/**
 * Derive a `review.workflow` value for legacy rows that have no review
 * payload. Closes blocker B3: without this fallback the editor would
 * hydrate with `workflow = "draft"` (template default), and the first
 * Ctrl+S would send `review.workflow = "draft"` — which the backend's
 * workflow-sync logic interprets as a demotion on a PUBLISHED row,
 * flipping status back to DRAFT.
 *
 * Mapping mirrors `PublicationStatus` string values:
 *   "PUBLISHED" / "published" → "published"
 *   anything else             → "draft"
 * We accept either case because the admin response marshals the enum's
 * `.value` (upper-case in Python) but tests and legacy code have
 * historically used lower-case strings. Matching both keeps the
 * fallback robust across either convention.
 */
function deriveWorkflowFromStatus(status: string): WorkflowState {
  return status.toLowerCase() === 'published' ? 'published' : 'draft';
}

/**
 * Legacy hydrate: rebuild a CanonicalDocument from scalar editorial
 * fields. Known-lossy — block-level props (chart data, per-block
 * overrides, brand_stamp position, etc.) reset to template defaults.
 *
 * Used only when `document_state` is absent. First PATCH after opening
 * a legacy row writes `document_state` → from that point on the row is
 * lossless.
 */
function hydrateFromLegacyFields(
  pub: AdminPublicationResponse,
): CanonicalDocument {
  const base = mkDoc('single_stat_hero', TPLS.single_stat_hero);

  const vc = pub.visual_config;
  if (vc) {
    base.page = {
      size: SIZE_FROM_BACKEND[vc.size] ?? base.page.size,
      background: vc.background || base.page.background,
      palette: vc.palette || base.page.palette,
    };
  }

  overlayBlockText(base, 'headline_editorial', pub.headline);
  overlayBlockText(base, 'eyebrow_tag', pub.eyebrow ?? undefined);
  overlayBlockText(base, 'source_footer', pub.source_text ?? undefined);
  overlayBlockText(base, 'body_annotation', pub.footnote ?? undefined);
  overlayBlockText(base, 'subtitle_descriptor', pub.description ?? undefined);

  if (pub.review) {
    base.review = {
      workflow: pub.review.workflow,
      history: pub.review.history ?? [],
      comments: pub.review.comments ?? [],
    };
  } else {
    // B3 fix — derive workflow from publication.status so a legacy
    // PUBLISHED row does not get silently demoted to DRAFT on first save.
    const derived = deriveWorkflowFromStatus(pub.status);
    base.review = {
      workflow: derived,
      history: [],
      comments: [],
    };
    if (process.env.NODE_ENV !== 'production') {
      console.warn(
        `[hydrateDoc] Legacy publication ${pub.id} has no review; derived workflow="${derived}" from status="${pub.status}"`,
      );
    }
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
