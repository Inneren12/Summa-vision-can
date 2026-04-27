# Phase 1.3 Pre-Recon Part B — Frontend Inventory

**Type:** READ-ONLY DISCOVERY
**Scope:** Next.js admin/editor code that the 412 client-side handling will touch.
**Git remote:** `http://local_proxy@127.0.0.1:44233/git/Inneren12/Summa-vision-can`
**Generated:** 2026-04-27

---

## §1.1 admin.ts — current PATCH wiring + BackendApiError

### File location

```
$ find frontend-public/src -name 'admin.ts'
frontend-public/src/lib/api/admin.ts
```

### Symbol grep

```
$ grep -n 'class BackendApiError\|extractBackendErrorPayload\|getBackendErrorI18nKey\|KNOWN_BACKEND_ERROR_CODES' frontend-public/src/lib/api/admin.ts frontend-public/src/lib/api/errorCodes.ts

frontend-public/src/lib/api/admin.ts:11:import { extractBackendErrorPayload } from './errorCodes';
frontend-public/src/lib/api/admin.ts:34:export class BackendApiError extends Error {
frontend-public/src/lib/api/admin.ts:139:    const payload = extractBackendErrorPayload(body);
frontend-public/src/lib/api/admin.ts:183:    const payload = extractBackendErrorPayload(body);
frontend-public/src/lib/api/errorCodes.ts:17:export const KNOWN_BACKEND_ERROR_CODES = [
frontend-public/src/lib/api/errorCodes.ts:108:export function getBackendErrorI18nKey(code: string | null): string | null {
```

### PATCH function signature (autosave call site)

`frontend-public/src/lib/api/admin.ts:125`

```ts
export async function updateAdminPublication(
  id: string,
  payload: UpdateAdminPublicationPayload,
  opts: { signal?: AbortSignal } = {},
): Promise<AdminPublicationResponse>
```

Gloss: Sends `PATCH /api/admin/publications/{id}` with JSON body. No `If-Match`/version header today.

### `BackendApiError` class (verbatim, lines 34–51)

```ts
export class BackendApiError extends Error {
  public readonly status: number;
  public readonly code: string | null;
  public readonly details: Record<string, unknown> | null;

  constructor(args: {
    status: number;
    code: string | null;
    message: string;
    details: Record<string, unknown> | null;
  }) {
    super(args.message);
    this.name = 'BackendApiError';
    this.status = args.status;
    this.code = args.code;
    this.details = args.details;
  }
}
```

Gloss: Carries `{status, code, message, details}`. Both `code` and `details` are nullable. Constructor takes a single named-args object.

### Status-vs-code detection (DEBT-030 alignment)

`frontend-public/src/lib/api/admin.ts:137–164` (verbatim error branch)

```ts
if (!res.ok) {
  const body = await res.json().catch(() => ({}));
  const payload = extractBackendErrorPayload(body);

  // Code-first detection: backend has a structured contract.
  if (payload.code === 'PUBLICATION_NOT_FOUND') {
    throw new AdminPublicationNotFoundError(id);
  }

  // Shape-less 404 backstop: only fires when there is NO structured
  // payload (e.g., gateway/CDN intercept returning HTML or empty
  // body). When a payload exists, trust the code — future codes like
  // PUBLICATION_ARCHIVED on a 404 status must NOT be misclassified
  // as not-found.
  if (!payload.code && res.status === 404) {
    throw new AdminPublicationNotFoundError(id);
  }

  throw new BackendApiError({
    status: res.status,
    code: payload.code,
    message:
      payload.message ??
      (typeof body?.detail === 'string' ? body.detail : null) ??
      `Admin publication update failed: ${res.status}`,
    details: payload.details,
  });
}
```

Gloss: **Code-first** with a `status === 404` fallback that only fires when no structured `error_code` is present. Per DEBT-030, status is a backstop for shape-less responses, never a primary discriminator.

### `KNOWN_BACKEND_ERROR_CODES` (verbatim, errorCodes.ts:17–25)

```ts
export const KNOWN_BACKEND_ERROR_CODES = [
  'PUBLICATION_NOT_FOUND',
  'PUBLICATION_UPDATE_PAYLOAD_INVALID',
  'PUBLICATION_CLONE_NOT_ALLOWED',
  'PUBLICATION_INTERNAL_SERIALIZATION_ERROR',
  'AUTH_API_KEY_MISSING',
  'AUTH_API_KEY_INVALID',
  'AUTH_ADMIN_RATE_LIMITED',
] as const;
```

Gloss: 7 entries. **No `PRECONDITION_FAILED`** (or any 412 code) present today.

---

## §1.2 errorCodes.ts — i18n key resolution

### File

`frontend-public/src/lib/api/errorCodes.ts` (143 lines).

### `getBackendErrorI18nKey` signature + body (verbatim, lines 104–116)

```ts
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
```

### Namespace pattern (`BACKEND_ERROR_I18N_KEYS`, lines 47–55)

```ts
export const BACKEND_ERROR_I18N_KEYS: Record<BackendErrorCode, string> = {
  PUBLICATION_NOT_FOUND: 'publication.not_found.reload',
  PUBLICATION_UPDATE_PAYLOAD_INVALID: 'publication.payload_invalid.message',
  PUBLICATION_CLONE_NOT_ALLOWED: 'errors.backend.publicationCloneNotAllowed',
  PUBLICATION_INTERNAL_SERIALIZATION_ERROR: 'publication.serialization_error.message',
  AUTH_API_KEY_MISSING: 'errors.backend.auth_api_key_missing',
  AUTH_API_KEY_INVALID: 'errors.backend.auth_api_key_invalid',
  AUTH_ADMIN_RATE_LIMITED: 'errors.backend.auth_admin_rate_limited',
};
```

Gloss: **Hybrid (DEBT-030 Option C) confirmed.** Publication-specific UX messages live under `publication.*` (4 mappings); cross-cutting auth/system codes live under `errors.backend.*` (3 mappings). `translateBackendError(t, code)` (lines 136–142) wraps the lookup and applies the `as never` cast for next-intl strict typing.

---

## §1.3 Autosave consumer — where 412 must branch

### Component

`frontend-public/src/components/editor/index.tsx` (single autosave consumer; calls `updateAdminPublication`).

### Imports (lines 31–43)

```ts
import {
  updateAdminPublication,
  ...
  BackendApiError,
  ...
} from '@/lib/api/admin';
...
import { NotificationBanner } from './components/NotificationBanner';
```

### Failure handler (verbatim, lines 568–627)

```ts
const performSave = useCallback(() => {
  if (!dirty || !publicationId || savingRef.current) return;

  setSaveStatus('saving');
  const snapshotDoc = doc;
  savingRef.current = true;

  const payload = buildUpdatePayload(snapshotDoc);
  updateAdminPublication(publicationId, payload)
    .then(() => {
      dispatch({ type: "SAVED_IF_MATCHES", snapshotDoc });
      setSaveStatus('idle');
    })
    .catch((err: unknown) => {
      if (err instanceof AdminPublicationNotFoundError) {
        // Terminal condition. Do NOT auto-retry.
        dispatch({
          type: "SAVE_FAILED",
          error: tPublication('not_found.reload'),
          canAutoRetry: false,
        });
        setSaveStatus('error');
        return;
      }

      // Transient / unknown failure — retry with backoff.
      const localized = err instanceof BackendApiError
        ? translateBackendError(t, err.code)
        : null;
      if (!localized && err instanceof BackendApiError && err.code) {
        console.warn('[backend] unmapped error_code:', err.code);
      }
      const msg = localized
        ?? (err instanceof BackendApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err));
      dispatch({ type: "SAVE_FAILED", error: msg, canAutoRetry: true });
      setSaveFailureGen((n) => n + 1);
      setSaveStatus('error');
    })
    .finally(() => { savingRef.current = false; });
}, [dirty, doc, dispatch, publicationId, t, tPublication]);
```

Gloss:
- **Inspects `error.errorCode`?** Yes — via `err instanceof BackendApiError` then `err.code` passed to `translateBackendError(t, err.code)`. Currently only `PUBLICATION_NOT_FOUND` (via the typed `AdminPublicationNotFoundError` branch) gets a terminal-error treatment; everything else falls through to the auto-retry branch with `canAutoRetry: true`.
- **Current UX for save errors:** `NotificationBanner` (`frontend-public/src/components/editor/components/NotificationBanner.tsx`) — an in-editor banner with auto-retry countdown (`retryCountdownMs`) and a "Retry now" button (`onManualRetry`). Banner priority: `saveError > importError > _lastRejection > warnings`. **No modal exists today** — all save errors are surfaced as banner messages.
- **Where a 412-specific modal would naturally live:** the `.catch` branch at `frontend-public/src/components/editor/index.tsx:584–623` is the single chokepoint. A new component file `frontend-public/src/components/editor/components/StaleVersionModal.tsx` (alongside `NotificationBanner.tsx`) would mirror the current convention; it would be triggered from `performSave`'s `.catch` when `err instanceof BackendApiError && err.code === 'PRECONDITION_FAILED'` (terminal — must NOT enter the auto-retry branch). Lifted state for "modal open" would live next to `setSaveStatus`/`setSaveFailureGen` in `index.tsx`.

### Secondary consumer (clone, lines 793–818)

```ts
const handleClone = useCallback(async () => {
  ...
  } catch (err: unknown) {
    if (err instanceof AdminPublicationNotFoundError) {
      setImportError(tPublication('not_found.reload'));
    } else {
      const localized = err instanceof BackendApiError
        ? translateBackendError(t, err.code)
        : null;
      setImportError(
        localized
          ?? (err instanceof BackendApiError
            ? err.message
            : err instanceof Error ? err.message : String(err)),
      );
    }
  } ...
});
```

Gloss: Same code-first translation pattern; routes to `importError` instead of `saveError`. Not on the autosave path — out of scope for 1.3, but uses identical translation plumbing.

---

## §1.4 i18n keys — existing publication.* and errors.backend.*

### File paths

```
$ find frontend-public -name 'en.json' -o -name 'ru.json' | head -5
frontend-public/messages/en.json
frontend-public/messages/ru.json
```

(No `locales/` or `i18n/` directory — `messages/` is the next-intl convention used here.)

### Existing leaf keys under `publication.*` (verbatim, en.json:15–28)

```json
"publication": {
  "load_failed":          { "fallback":  "Failed to load publication — using template defaults. {error}" },
  "not_found":            { "reload":    "Publication not found — reload the page" },
  "payload_invalid":      { "message":   "Changes were rejected. Review the publication fields and try again." },
  "serialization_error":  { "message":   "Publication could not be saved due to a server data format issue." }
}
```

Leaf paths (4):
- `publication.load_failed.fallback`
- `publication.not_found.reload`
- `publication.payload_invalid.message`
- `publication.serialization_error.message`

### Existing leaf keys under `errors.backend.*` (verbatim, en.json:625–632)

```json
"errors": {
  "backend": {
    "auth_api_key_missing":         "Admin authentication failed. Contact an administrator.",
    "auth_api_key_invalid":         "Admin authentication failed. Verify API access settings.",
    "auth_admin_rate_limited":      "Too many admin requests. Wait a moment and try again.",
    "publicationCloneNotAllowed":   "This publication cannot be cloned because it is not yet published."
  }
}
```

Leaf paths (4):
- `errors.backend.auth_api_key_missing`
- `errors.backend.auth_api_key_invalid`
- `errors.backend.auth_admin_rate_limited`
- `errors.backend.publicationCloneNotAllowed`

### RU parity (ru.json:15–28, 625–632)

Same shape; all 8 leaf paths populated with Russian translations (verified via inspection — see ru.json offsets above). DEBT-030 hybrid (Option C) is fully in place across both locales.

### Naming-style inconsistency (observation, not a proposal)

Most keys use `snake_case` (e.g., `auth_api_key_missing`, `payload_invalid.message`). The single key `publicationCloneNotAllowed` is `camelCase`. Flagging because any new 412 key choice will inherit one convention or the other.

---

## §1.5 Existing 412 / precondition handling

### Greps run

```
$ grep -rn 'PRECONDITION\|412\|If-Match\|stale.*version\|conflict' frontend-public/src
(no matches)

$ grep -rn '\b412\b' frontend-public/src
(no matches)

$ grep -rn 'PRECONDITION\|If-Match\|stale\|conflict' frontend-public/src
frontend-public/src/components/editor/index.tsx:664:      // Either nothing to save or no backend target. Drop a stale
frontend-public/src/components/editor/store/dev-assert.ts:10: * stale undo entry, etc. This runs after every reducer step in dev so that
```

Gloss: The two `stale` matches are unrelated (one is a debounce-status comment, one is a dev-assert reducer comment). **No existing precondition handling, no `If-Match` header reads/writes, no version-conflict UX, no 412 status branches anywhere in `frontend-public/src`.** Greenfield.

---

## 3. Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:44233/git/Inneren12/Summa-vision-can
DOC PATH:   docs/recon/phase-1-3-B-frontend-inventory.md

§1.1 admin.ts:                 frontend-public/src/lib/api/admin.ts:125
  PATCH function name: updateAdminPublication
  BackendApiError class found: yes (admin.ts:34)
  KNOWN_BACKEND_ERROR_CODES count: 7
  KNOWN codes verbatim: PUBLICATION_NOT_FOUND, PUBLICATION_UPDATE_PAYLOAD_INVALID,
    PUBLICATION_CLONE_NOT_ALLOWED, PUBLICATION_INTERNAL_SERIALIZATION_ERROR,
    AUTH_API_KEY_MISSING, AUTH_API_KEY_INVALID, AUTH_ADMIN_RATE_LIMITED
  Detection: code-first (status===404 fallback only when payload.code is null)

§1.2 errorCodes.ts:            frontend-public/src/lib/api/errorCodes.ts:108
  Namespace: hybrid (publication.* + errors.backend.*) — DEBT-030 Option C confirmed

§1.3 Autosave consumer:        frontend-public/src/components/editor/index.tsx:568 (performSave)
  Inspects error.errorCode: yes (via BackendApiError.code → translateBackendError)
  Current UX: in-editor banner (NotificationBanner) with auto-retry countdown + "Retry now"
  Proposed 412 modal location: frontend-public/src/components/editor/components/StaleVersionModal.tsx
    (triggered from performSave .catch at index.tsx:584; terminal — bypasses auto-retry)

§1.4 i18n files:
  EN: frontend-public/messages/en.json, RU: frontend-public/messages/ru.json
  publication.* leaf keys: 4
  errors.backend.* leaf keys: 4
  Note: mixed snake_case/camelCase under errors.backend.*

§1.5 Existing 412 handling: NONE (no PRECONDITION/412/If-Match/version-conflict references in src)

VERDICT: COMPLETE
```

---

**End of Part B.**
