import { zipSync, strToU8 } from 'fflate';
import type { CanonicalDocument, Palette } from '../types';
import type { PresetId } from '../config/sizes';
import { renderDocumentToBlob, RenderCapExceededError } from './renderToBlob';
import { buildManifest, type PresetRenderResult } from './manifest';
import { buildZipFilename } from './zipFilename';
import { buildDistributionJson } from '../distribution/distributionJson';
import { buildPublishKitTxt } from '../distribution/publishKitTxt';
import { deferRevoke } from '../utils/download';
import { validatePresetSize } from '../validation/validate';

export type ZipExportPhase =
  | { phase: 'rendering'; current: number; total: number }
  | { phase: 'packing' }
  | { phase: 'done'; result: ZipExportResult }
  | { phase: 'error'; error: unknown };

export interface ZipExportResult {
  filename: string;
  totalPresets: number;
  passCount: number;
  skippedCount: number;
  skipped: ReadonlyArray<{
    presetId: PresetId;
    skipReason: string;
    measuredHeight?: number;
  }>;
}

export interface ZipExportOptions {
  doc: CanonicalDocument;
  pal: Palette;
  /** Per-row UUID v7 from backend; populates utm_content in distribution URLs. */
  lineage_key: string;
  /** Per-row URL slug from backend; populates canonical_url path /p/{slug}. */
  slug: string;
  /** Public site base URL, e.g. https://summa.vision; from NEXT_PUBLIC_SITE_URL. */
  baseUrl: string;
  onProgress?: (phase: ZipExportPhase) => void;
}

/**
 * Phase 2.1 PR#3 — Multi-preset ZIP export orchestrator.
 *
 * Sequential per-preset rendering (recon §1 — Variant A). No Web Workers,
 * no parallel renders.
 *
 * Snapshots `doc` via `structuredClone` at entry per Q-2.1-6 — operator
 * may continue editing during render; the ZIP reflects doc state at click
 * time. Future edits flow into the next ZIP, not this one.
 *
 * Per-preset cap-exceeded behavior (Q-2.1-10 / approval gate A4):
 * `RenderCapExceededError` is caught and the preset is marked
 * `qa_status: "skipped"` in manifest. Other presets continue normally.
 * Other unexpected errors propagate via `onProgress({ phase: 'error' })`
 * and reject the function — the orchestrator does NOT swallow generic
 * errors as "skipped".
 *
 * Returns when ZIP download has been triggered. Caller is responsible for
 * showing a toast based on the resolved `ZipExportResult`.
 */
export async function exportZip(
  options: ZipExportOptions,
): Promise<ZipExportResult> {
  const { pal, onProgress } = options;
  // Snapshot at entry — Q-2.1-6 cancellation semantics. MUST happen before
  // any await; awaiting first would let mid-flight edits leak into the snap.
  const doc = structuredClone(options.doc);

  // Enabled presets = doc.page.exportPresets, already normalized by reducer
  // (PR#2 fix1 invariant: includes current size, no unknowns).
  const enabled = doc.page.exportPresets;
  const total = enabled.length;

  if (total === 0) {
    // Defensive: should never happen because normalizeExportPresets always
    // includes current size. If it does happen, fail loud rather than
    // produce an empty ZIP.
    throw new Error('No presets enabled for export');
  }

  const results: PresetRenderResult[] = [];

  try {
    for (let i = 0; i < total; i += 1) {
      const presetId = enabled[i];
      onProgress?.({ phase: 'rendering', current: i + 1, total });

      // PR#4 pre-render QA gate. validatePresetSize runs the same checks the
      // Inspector badge shows; any error-level entry skips the render call
      // entirely and marks the preset skipped in the manifest. Warnings/info
      // do NOT cause skip — only errors do. The runtime catch below stays as
      // defense-in-depth for any size-dep rule the validator misses.
      const presetValidation = validatePresetSize(doc, presetId);
      if (presetValidation.errors.length > 0) {
        const firstError = presetValidation.errors[0];
        const measuredParam = firstError.params?.measured;
        const measuredHeight =
          typeof measuredParam === 'number' ? measuredParam : undefined;
        results.push({
          presetId,
          status: 'skipped',
          skipReason: firstError.key,
          measuredHeight,
        });
        continue;
      }

      try {
        const blob = await renderDocumentToBlob(doc, pal, presetId);
        results.push({ presetId, status: 'pass', blob });
      } catch (err) {
        if (err instanceof RenderCapExceededError) {
          results.push({
            presetId,
            status: 'skipped',
            skipReason: err.i18nKey,
            measuredHeight: err.measuredHeight,
          });
        } else {
          throw err;
        }
      }
    }

    onProgress?.({ phase: 'packing' });

    const generatedAt = new Date();
    const manifest = buildManifest(doc, results, generatedAt);

    const zipEntries: Record<string, Uint8Array> = {};
    for (const r of results) {
      if (r.status === 'pass' && r.blob) {
        const bytes = new Uint8Array(await r.blob.arrayBuffer());
        zipEntries[`${r.presetId}.png`] = bytes;
      }
    }
    zipEntries['manifest.json'] = strToU8(JSON.stringify(manifest, null, 2));

    const distribution = buildDistributionJson({
      doc,
      lineage_key: options.lineage_key,
      slug: options.slug,
      baseUrl: options.baseUrl,
    });
    zipEntries['distribution.json'] = strToU8(
      JSON.stringify(distribution, null, 2),
    );
    zipEntries['publish_kit.txt'] = strToU8(
      buildPublishKitTxt({ distribution }),
    );

    const zipBytes = zipSync(zipEntries, { level: 6 });
    const zipBlob = new Blob([zipBytes as BlobPart], { type: 'application/zip' });
    const filename = buildZipFilename(doc, generatedAt);

    const url = URL.createObjectURL(zipBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    deferRevoke(url);

    const skipped = results
      .filter((r) => r.status === 'skipped')
      .map((r) => ({
        presetId: r.presetId,
        skipReason: r.skipReason!,
        measuredHeight: r.measuredHeight,
      }));

    const result: ZipExportResult = {
      filename,
      totalPresets: total,
      passCount: results.filter((r) => r.status === 'pass').length,
      skippedCount: skipped.length,
      skipped,
    };

    onProgress?.({ phase: 'done', result });
    return result;
  } catch (err) {
    onProgress?.({ phase: 'error', error: err });
    throw err;
  }
}
