import type { CanonicalDocument } from '../types';
import type { PresetId } from '../config/sizes';
import { SIZES } from '../config/sizes';

/**
 * QA outcome per preset in the ZIP manifest.
 *
 * - "pass"     — preset rendered successfully, included in ZIP
 * - "warning"  — preset rendered with non-blocking warnings (currently unused
 *                in PR#3; reserved for PR#4 per-preset QA evaluator integration)
 * - "skipped"  — preset NOT included in ZIP (e.g. long_infographic exceeded
 *                4000px cap, RenderCapExceededError caught by orchestrator)
 */
export type PresetQaStatus = 'pass' | 'warning' | 'skipped';

export interface ManifestPresetEntry {
  id: PresetId;
  filename: string;
  width: number;
  height: number;
  qa_status: PresetQaStatus;
}

export interface ZipManifest {
  schemaVersion: 1;
  publication_id: null;
  templateId: string;
  generated_at: string;
  presets: ManifestPresetEntry[];
}

export interface PresetRenderResult {
  presetId: PresetId;
  status: 'pass' | 'skipped';
  blob?: Blob;
  skipReason?: string;
  measuredHeight?: number;
}

/**
 * Builds the ZIP manifest from per-preset render results.
 *
 * Per recon Q-2.1-7. schemaVersion=1 lets Phase 2.2 forward-extend with
 * distribution.json fields (UTM tags, social captions, channel overrides)
 * by bumping to schemaVersion=2.
 *
 * Order of `presets` array matches the order of `results` input — caller
 * (orchestrator) feeds results in `doc.page.exportPresets` order, which
 * is itself stabilized by `normalizeExportPresets` per PR#2 fix2 order
 * contract. This guarantees same document → same manifest order on every
 * export (ARCHITECTURE_INVARIANTS.md §8 deterministic-export).
 *
 * Pure function — no I/O, no clock reads.
 */
export function buildManifest(
  doc: CanonicalDocument,
  results: readonly PresetRenderResult[],
  generatedAt: Date,
): ZipManifest {
  return {
    schemaVersion: 1,
    publication_id: null,
    templateId: doc.templateId,
    generated_at: generatedAt.toISOString(),
    presets: results.map((r) => {
      const sz = SIZES[r.presetId];
      return {
        id: r.presetId,
        filename: `${r.presetId}.png`,
        width: sz.w,
        height: r.measuredHeight ?? sz.h,
        qa_status: r.status,
      };
    }),
  };
}
