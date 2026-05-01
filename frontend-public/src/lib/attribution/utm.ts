/**
 * UTM attribution capture (Phase 2.3).
 *
 * Reads the four publish-kit UTM params from the current URL on first
 * visit and persists them to ``sessionStorage`` so they survive client-
 * side navigation between the landing page and the lead-capture modal.
 *
 * Contract:
 * - ``utm_content`` carries the source publication ``lineage_key``
 *   (Phase 2.2 lock).
 * - All four params are independently optional; we only persist when at
 *   least one is present so a clean visit does not overwrite a prior
 *   attributed session.
 * - When a new attributed URL is encountered, the persisted session
 *   attribution is replaced wholesale (no key-by-key merge) to prevent
 *   mixing UTM params from different publications.
 */

const STORAGE_KEY = 'utm_attribution';

/**
 * sessionStorage key under which the captured UTM attribution is
 * persisted. Exported so tests and callers stay in lockstep with the
 * source of truth — never hardcode this string elsewhere.
 */
export const UTM_STORAGE_KEY = STORAGE_KEY;

const UTM_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_content',
] as const;

export type UtmKey = (typeof UTM_KEYS)[number];

export type UtmAttribution = Partial<Record<UtmKey, string>>;

function readFromUrl(): UtmAttribution {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  const utm: UtmAttribution = {};
  for (const key of UTM_KEYS) {
    const value = params.get(key);
    if (value) utm[key] = value;
  }
  return utm;
}

/**
 * Capture UTM params from the current URL (if any) and persist to
 * sessionStorage. Safe to call repeatedly; idempotent on a clean URL.
 *
 * Replace-on-new-UTM semantics: a fresh attributed landing fully
 * overwrites prior session attribution. This avoids mixing
 * ``utm_source`` from one visit with ``utm_content`` from another,
 * which would otherwise produce wrong cross-publication attribution.
 */
export function captureUtmFromUrl(): UtmAttribution {
  if (typeof window === 'undefined') return {};

  const fromUrl = readFromUrl();

  if (Object.keys(fromUrl).length === 0) {
    // Clean URL — return any previously-stored UTM (survives multi-page nav).
    return getStoredUtm();
  }

  // New attributed landing replaces prior session attribution.
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(fromUrl));
  } catch {
    // sessionStorage may be unavailable (private mode, quota, etc.).
    // Attribution is best-effort; swallow and fall through.
  }

  return fromUrl;
}

/**
 * Read previously-persisted UTM attribution from sessionStorage.
 * Returns ``{}`` when nothing has been captured or storage is unavailable.
 */
export function getStoredUtm(): UtmAttribution {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (parsed === null || typeof parsed !== 'object') return {};
    const out: UtmAttribution = {};
    for (const key of UTM_KEYS) {
      const value = (parsed as Record<string, unknown>)[key];
      if (typeof value === 'string' && value.length > 0) out[key] = value;
    }
    return out;
  } catch {
    return {};
  }
}
