/**
 * Backend error code dictionary + envelope extractor.
 *
 * Backend emits two envelope shapes:
 *   1. Nested (publication exceptions):
 *        { detail: { error_code, message, details? } }
 *   2. Flat (auth middleware):
 *        { error: "...", error_code: "..." }
 *
 * The extractor checks nested first, then flat. Unknown codes are
 * preserved as raw strings so callers can console.warn before
 * falling back to a non-localized message.
 *
 * See docs/debt-030-pr2-recon.md for design rationale.
 */

export const KNOWN_BACKEND_ERROR_CODES = [
  'PUBLICATION_NOT_FOUND',
  'PUBLICATION_UPDATE_PAYLOAD_INVALID',
  'PUBLICATION_CLONE_NOT_ALLOWED',
  'PUBLICATION_INTERNAL_SERIALIZATION_ERROR',
  'AUTH_API_KEY_MISSING',
  'AUTH_API_KEY_INVALID',
  'AUTH_ADMIN_RATE_LIMITED',
  'PRECONDITION_FAILED',
] as const;

export type BackendErrorCode = (typeof KNOWN_BACKEND_ERROR_CODES)[number];

export type BackendErrorPayload = {
  /** Raw code string from backend; may be a known code, an unknown string, or null. */
  code: string | null;
  /** Backend-supplied human-readable message (fallback only — UI prefers localized). */
  message: string | null;
  /** Optional structured details (FastAPI validation errors, etc.). */
  details: Record<string, unknown> | null;
  /** Which envelope shape produced this payload — useful for logging/diagnostics. */
  envelope: 'nested' | 'flat' | 'none';
};

/**
 * Map known codes to next-intl key paths. Used by getBackendErrorI18nKey().
 * Adding a new known code requires both:
 *   1. Append to KNOWN_BACKEND_ERROR_CODES.
 *   2. Add the i18n key here.
 *   3. Add EN+RU strings in messages/{en,ru}.json.
 */
export const BACKEND_ERROR_I18N_KEYS: Record<BackendErrorCode, string> = {
  PUBLICATION_NOT_FOUND: 'publication.not_found.reload',
  PUBLICATION_UPDATE_PAYLOAD_INVALID: 'publication.payload_invalid.message',
  PUBLICATION_CLONE_NOT_ALLOWED: 'errors.backend.publicationCloneNotAllowed',
  PUBLICATION_INTERNAL_SERIALIZATION_ERROR: 'publication.serialization_error.message',
  AUTH_API_KEY_MISSING: 'errors.backend.auth_api_key_missing',
  AUTH_API_KEY_INVALID: 'errors.backend.auth_api_key_invalid',
  AUTH_ADMIN_RATE_LIMITED: 'errors.backend.auth_admin_rate_limited',
  PRECONDITION_FAILED: 'errors.backend.precondition_failed',
};

const EMPTY_PAYLOAD: BackendErrorPayload = {
  code: null,
  message: null,
  details: null,
  envelope: 'none',
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Extract a backend error payload from an arbitrary parsed JSON body.
 *
 * Lookup precedence:
 *   1. body.detail.error_code (nested envelope, publication contract).
 *   2. body.error_code (flat envelope, auth middleware).
 *   3. None — return empty payload with envelope='none'.
 *
 * Never throws. Never returns undefined.
 */
export function extractBackendErrorPayload(body: unknown): BackendErrorPayload {
  if (!isPlainObject(body)) {
    return EMPTY_PAYLOAD;
  }

  // 1. Nested envelope.
  const detail = body.detail;
  if (isPlainObject(detail)) {
    const code = typeof detail.error_code === 'string' ? detail.error_code : null;
    if (code !== null) {
      const message = typeof detail.message === 'string' ? detail.message : null;
      const details = isPlainObject(detail.details) ? detail.details : null;
      return { code, message, details, envelope: 'nested' };
    }
  }

  // 2. Flat envelope.
  const flatCode = typeof body.error_code === 'string' ? body.error_code : null;
  if (flatCode !== null) {
    const message = typeof body.error === 'string' ? body.error : null;
    return { code: flatCode, message, details: null, envelope: 'flat' };
  }

  return EMPTY_PAYLOAD;
}

/**
 * Look up the i18n key for a backend code. Returns null for unknown codes
 * — callers should console.warn and fall back to the backend message.
 */
export function getBackendErrorI18nKey(code: string | null): string | null {
  if (code === null) {
    return null;
  }
  if ((KNOWN_BACKEND_ERROR_CODES as readonly string[]).includes(code)) {
    return BACKEND_ERROR_I18N_KEYS[code as BackendErrorCode];
  }
  return null;
}

/**
 * Localize a backend error code to a UI string.
 *
 * Centralizes the `as never` cast required by next-intl's strict-typed
 * `t()` when the key is dynamic (computed at runtime, not a literal).
 * The cast is unsafe in principle but bounded in practice: the key
 * comes from {@link BACKEND_ERROR_I18N_KEYS}, which is statically
 * checked against {@link KNOWN_BACKEND_ERROR_CODES}.
 *
 * @param t - next-intl translation function (root-level, not scoped).
 *            Accept any function with `(key: string) => string` shape;
 *            keeps this helper testable without a NextIntlProvider.
 * @param code - backend error code (or null/unknown).
 * @returns localized string for known codes, null otherwise.
 *          Caller should fall back to the backend `message` field
 *          when this returns null (and may want to console.warn for
 *          a non-null but unknown code).
 */
export function translateBackendError(
  t: (key: never) => string,
  code: string | null,
): string | null {
  const key = getBackendErrorI18nKey(code);
  return key ? t(key as never) : null;
}
