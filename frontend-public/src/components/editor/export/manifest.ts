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
  /**
   * Absolute filename of the per-preset PNG inside the ZIP archive.
   * `null` when the preset is skipped (e.g. RenderCapExceededError) — the
   * PNG is NOT in the archive in that case, so referencing a non-existent
   * filename would be a broken contract for downstream consumers.
   */
  filename: string | null;
  width: number;
  height: number;
  qa_status: PresetQaStatus;
  /**
   * Machine-readable i18n key explaining why the preset was skipped.
   * Present only when `qa_status === 'skipped'`. Sourced from the helper
   * that raised the skip (e.g. `RenderCapExceededError.i18nKey`).
   *
   * Phase 2.2 distribution layer can map this to channel-specific fallback
   * behavior (drop the social post entirely vs. publish without that
   * preset). EN-only English text in the underlying `error.message` is
   * not suitable for that purpose.
   */
  skipped_reason?: string;
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
      // Skipped entries (e.g. RenderCapExceededError) MUST NOT reference a
      // PNG filename that is not in the ZIP — see fix1 rationale. The PNG
      // is only emitted by the orchestrator's pack loop when status === 'pass'.
      const filename: string | null =
        r.status === 'pass' ? `${r.presetId}.png` : null;
      const entry: ManifestPresetEntry = {
        id: r.presetId,
        filename,
        width: sz.w,
        height: r.measuredHeight ?? sz.h,
        qa_status: r.status,
      };
      if (r.status === 'skipped' && r.skipReason) {
        entry.skipped_reason = r.skipReason;
      }
      return entry;
    }),
  };
}
