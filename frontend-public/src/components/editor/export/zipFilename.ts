import type { CanonicalDocument } from '../types';

/**
 * Builds a deterministic ZIP filename for multi-preset export.
 *
 * Format: `summa-${doc.templateId}-export-${YYYYMMDD-HHmmss}.zip`
 *
 * Examples:
 * - `summa-single_stat_hero-export-20260427-143022.zip`
 * - `summa-ranked_bar-export-20260427-090015.zip`
 *
 * Per recon Q-2.1-3:
 * - Stays consistent with single-PNG naming prefix `summa-${templateId}-`
 *   (operators recognize the family).
 * - No preset id in filename — preset is INSIDE the ZIP.
 * - No publication slug — avoids backend coupling for one filename token.
 * - YYYYMMDD-HHmmss avoids timezone/locale ambiguity in filesystem sort.
 *
 * Pure function. Same (doc, now) → same string.
 */
export function buildZipFilename(
  doc: CanonicalDocument,
  now: Date = new Date(),
): string {
  const yyyy = now.getFullYear().toString().padStart(4, '0');
  const mm = (now.getMonth() + 1).toString().padStart(2, '0');
  const dd = now.getDate().toString().padStart(2, '0');
  const hh = now.getHours().toString().padStart(2, '0');
  const mi = now.getMinutes().toString().padStart(2, '0');
  const ss = now.getSeconds().toString().padStart(2, '0');
  const stamp = `${yyyy}${mm}${dd}-${hh}${mi}${ss}`;
  return `summa-${doc.templateId}-export-${stamp}.zip`;
}
