## 1) Recap of locked decisions
Dictionary covers all 6 codes, even though only PATCH-active codes wire into UI today; auth codes + future publish/unpublish 404s are covered via the same dictionary/extractor. If extractor returns a known code and dictionary has a key for it, UI must render localized text and must never pass through `err.message` for known codes. If extractor returns a code but dictionary has no key, emit `console.warn` and render backend `message` as last-ditch fallback. If no code exists at all (legacy shape/network/no-JSON 5xx), preserve existing behavior (`err.message` or `publication.load_failed.fallback`). Ignore `details.validation_errors` in PR2 UI (single generic 422 message only). Migrate 404 detection from status-first to code-first: throw `AdminPublicationNotFoundError` when extracted code is `PUBLICATION_NOT_FOUND`, with `response.status === 404` as backstop for shape-less 404s.

## 2) Code dictionary proposal

| Code | EN message | RU message | Surfaced via |
|---|---|---|---|
| `PUBLICATION_NOT_FOUND` | Publication not found. Reload the page to continue. | Публикация не найдена. Перезагрузите страницу, чтобы продолжить. | `admin.ts PATCH`; future publish/unpublish |
| `PUBLICATION_UPDATE_PAYLOAD_INVALID` | Changes were rejected. Review the publication fields and try again. | Изменения отклонены. Проверьте поля публикации и повторите попытку. | `admin.ts PATCH` |
| `PUBLICATION_INTERNAL_SERIALIZATION_ERROR` | Publication could not be saved due to a server data format issue. | Не удалось сохранить публикацию из-за ошибки формата данных на сервере. | none (reserved) |
| `AUTH_API_KEY_MISSING` | Admin authentication failed. Contact an administrator. | Ошибка аутентификации администратора. Обратитесь к администратору. | AuthMiddleware (any admin call) |
| `AUTH_API_KEY_INVALID` | Admin authentication failed. Verify API access settings. | Ошибка аутентификации администратора. Проверьте настройки доступа API. | AuthMiddleware (any admin call) |
| `AUTH_ADMIN_RATE_LIMITED` | Too many admin requests. Wait a moment and try again. | Слишком много запросов администратора. Подождите и повторите попытку. | AuthMiddleware (any admin call) |

### Notes per code
- `PUBLICATION_NOT_FOUND`: emitted by publication exceptions as 404 with nested envelope (`detail.error_code/message`) and also used by publish/unpublish 404 paths in contract. User action is reload/re-open context. **Reuse existing key** `publication.not_found.reload` (already used by autosave catch branch).
- `PUBLICATION_UPDATE_PAYLOAD_INVALID`: emitted by PATCH validation path with nested envelope and `details.validation_errors`. User action is correct fields and retry; PR2 keeps generic banner (no field-level output).
- `PUBLICATION_INTERNAL_SERIALIZATION_ERROR`: reserved invariant error in backend exception class; not currently observed in active PATCH happy path but included in dictionary to prevent unmapped known-code UX once activated.
- `AUTH_API_KEY_MISSING`: middleware emits flat `{error,error_code}` with 401 when header missing. User action is operational: check server/admin config; editor end-user cannot self-fix.
- `AUTH_API_KEY_INVALID`: middleware emits flat 401 when key mismatch. User action is operational verification of API key configuration.
- `AUTH_ADMIN_RATE_LIMITED`: middleware emits flat 429 when admin key exceeds limiter window. User action is wait then retry.

### Glossary alignment check
Glossary terms used: **публикация**, **поля**, **сохранить**, **ошибка**, **формат данных**, **аутентификация**, **администратор**, **настройки**, **доступ**, **повторить попытку** (see product/workflow terminology in glossary).

## 3) i18n catalog placement proposal

### Recommendation
Recommend **Option C (hybrid)**: keep publication keys under existing `publication.*` subtree for compatibility with current `tPublication('not_found.reload')` call in autosave (`index.tsx` lines 566-576), and place auth/system-coded messages under `errors.backend.*` so future non-publication consumers can share stable code-key mapping without bloating `publication.*` namespace. Existing keys confirmed: `publication.not_found.reload` and `publication.load_failed.fallback` in both catalogs.

### Exact JSON diff preview
```diff
--- a/frontend-public/messages/en.json
+++ b/frontend-public/messages/en.json
@@
   "publication": {
     "load_failed": {
       "fallback": "Failed to load publication — using template defaults. {error}"
     },
     "not_found": {
       "reload": "Publication not found — reload the page"
+    },
+    "payload_invalid": {
+      "message": "Changes were rejected. Review the publication fields and try again."
+    },
+    "serialization_error": {
+      "message": "Publication could not be saved due to a server data format issue."
     }
+  },
+  "errors": {
+    "backend": {
+      "auth_api_key_missing": "Admin authentication failed. Contact an administrator.",
+      "auth_api_key_invalid": "Admin authentication failed. Verify API access settings.",
+      "auth_admin_rate_limited": "Too many admin requests. Wait a moment and try again."
+    }
   },
 
--- a/frontend-public/messages/ru.json
+++ b/frontend-public/messages/ru.json
@@
   "publication": {
     "load_failed": {
       "fallback": "Не удалось загрузить публикацию — применены настройки по умолчанию. {error}"
     },
     "not_found": {
       "reload": "Публикация не найдена — перезагрузите страницу"
+    },
+    "payload_invalid": {
+      "message": "Изменения отклонены. Проверьте поля публикации и повторите попытку."
+    },
+    "serialization_error": {
+      "message": "Не удалось сохранить публикацию из-за ошибки формата данных на сервере."
     }
+  },
+  "errors": {
+    "backend": {
+      "auth_api_key_missing": "Ошибка аутентификации администратора. Обратитесь к администратору.",
+      "auth_api_key_invalid": "Ошибка аутентификации администратора. Проверьте настройки доступа API.",
+      "auth_admin_rate_limited": "Слишком много запросов администратора. Подождите и повторите попытку."
+    }
   },
 ```

### Reuse vs introduce
For `PUBLICATION_NOT_FOUND`, **reuse** `publication.not_found.reload` (do not introduce a replacement key in PR2). It is already wired in autosave flow and semantically aligned.

## 4) Extractor utility proposal

### File path
Use `frontend-public/src/lib/api/errorCodes.ts` (shared for PATCH now and publish/unpublish/auth consumers later; keeps `admin.ts` focused on transport and typed throws).

### Type definitions
```ts
export const KNOWN_BACKEND_ERROR_CODES = [
  'PUBLICATION_NOT_FOUND',
  'PUBLICATION_UPDATE_PAYLOAD_INVALID',
  'PUBLICATION_INTERNAL_SERIALIZATION_ERROR',
  'AUTH_API_KEY_MISSING',
  'AUTH_API_KEY_INVALID',
  'AUTH_ADMIN_RATE_LIMITED',
] as const;

export type BackendErrorCode = (typeof KNOWN_BACKEND_ERROR_CODES)[number];

export type BackendErrorPayload = {
  code: string | null;
  message: string | null;
  details: Record<string, unknown> | null;
  envelope: 'nested' | 'flat' | 'none';
};
```
Decision: `code` is `string | null` (not union-only) so unknown backend codes survive extraction/logging/fallback. `message` is nullable because no message may exist in malformed/legacy bodies.

### Function signature
```ts
export function extractBackendErrorPayload(body: unknown): BackendErrorPayload;
```
Choose payload-level extractor (not code-only) so call-sites can use code-first localization + message fallback + details passthrough without reparsing.

### Behavior contract
- Input: any `unknown` JSON parse output.
- Lookup order: (1) nested `body.detail.error_code`; (2) flat `body.error_code`; (3) none.
- Nested path also extracts `body.detail.message` and `body.detail.details` if object-shaped.
- Flat path extracts `body.error` as message fallback (middleware emits `error`), and sets `details` null.
- Never throws on non-object input (`null`, string, array, number, boolean).
- Unknown code strings are returned as-is in `payload.code`; caller logs `console.warn('[backend] unknown error_code:', code)` when dictionary lookup misses.

### Translation lookup
Keep translation at call-site but expose a pure mapper in `errorCodes.ts`:
```ts
export const BACKEND_ERROR_I18N_KEYS: Record<BackendErrorCode, string> = {
  PUBLICATION_NOT_FOUND: 'publication.not_found.reload',
  PUBLICATION_UPDATE_PAYLOAD_INVALID: 'publication.payload_invalid.message',
  PUBLICATION_INTERNAL_SERIALIZATION_ERROR: 'publication.serialization_error.message',
  AUTH_API_KEY_MISSING: 'errors.backend.auth_api_key_missing',
  AUTH_API_KEY_INVALID: 'errors.backend.auth_api_key_invalid',
  AUTH_ADMIN_RATE_LIMITED: 'errors.backend.auth_admin_rate_limited',
};

export function getBackendErrorI18nKey(code: string | null): string | null;
```
Rationale: keeps mapping testable without coupling to `next-intl` `t` function shape.

### Edge cases checklist
- [ ] `body === null`
- [ ] `body === undefined`
- [ ] `body` is a string
- [ ] `body.detail` is a string
- [ ] `body.detail` is an array
- [ ] `body.detail.error_code` exists but is not string
- [ ] both nested and flat codes present → nested wins

## 5) Mutation-layer integration proposal

### Current state
Current non-OK handling in `updateAdminPublication` is status-404 branch then generic detail fallback (`admin.ts` lines 98-105): 404 throws `AdminPublicationNotFoundError`; other non-OK throws `Error(body?.detail ?? fallback)`.

### Proposed state (pseudo-diff)
```diff
@@ updateAdminPublication(...)
-  if (res.status === 404) {
-    throw new AdminPublicationNotFoundError(id);
-  }
   if (!res.ok) {
     const body = await res.json().catch(() => ({}));
-    throw new Error(body?.detail ?? `Admin publication update failed: ${res.status}`);
+    const payload = extractBackendErrorPayload(body);
+
+    if (payload.code === 'PUBLICATION_NOT_FOUND' || res.status === 404) {
+      throw new AdminPublicationNotFoundError(id);
+    }
+
+    throw new BackendApiError({
+      status: res.status,
+      code: payload.code,
+      message: payload.message ?? body?.detail ?? `Admin publication update failed: ${res.status}`,
+      details: payload.details,
+    });
   }
```

Decisions:
- **Keep `AdminPublicationNotFoundError`** and switch to code-first with status fallback (preserves existing `instanceof` behavior in editor catch path).
- **Add one generic `BackendApiError` class** (instead of many subclasses) carrying `status/code/message/details`; lower boilerplate and enough information for mapped localization.
- **Unknown codes** remain in `BackendApiError.code` raw string for warning + backend message fallback.

### Test impact
Files requiring update/extension:
- `frontend-public/tests/lib/api/admin.test.ts`: add nested/flat extraction behavior for `updateAdminPublication`; adjust 404 test to include code-first and status fallback scenarios.
- `frontend-public/tests/components/editor/autosave.test.tsx`: add end-to-end autosave assertions for localized mapped messages (instead of only raw `Error('boom')` paths).
- `frontend-public/tests/components/editor/error-channels.test.tsx`: optional assertions that saveError priority still holds when saveError contains localized mapped strings.

## 6) Autosave consumer integration proposal

### Current state
In `performSave` catch (`index.tsx` lines 565-593), only `AdminPublicationNotFoundError` maps to `tPublication('not_found.reload')`; all other failures dispatch raw `err.message`.

### Proposed state (pseudo-diff)
```diff
@@ performSave().catch((err) => {
   if (err instanceof AdminPublicationNotFoundError) {
     dispatch({ type: 'SAVE_FAILED', error: tPublication('not_found.reload'), canAutoRetry: false });
     setSaveStatus('error');
     return;
   }
-
-  const msg = err instanceof Error ? err.message : String(err);
-  dispatch({ type: 'SAVE_FAILED', error: msg, canAutoRetry: true });
+  const mapped = err instanceof BackendApiError
+    ? getBackendErrorI18nKey(err.code)
+    : null;
+  const localized = mapped ? t(mapped as never) : null;
+  if (!mapped && err instanceof BackendApiError && err.code) {
+    console.warn('[backend] unmapped error_code:', err.code);
+  }
+  const msg = localized ?? (err instanceof BackendApiError ? err.message : err instanceof Error ? err.message : String(err));
+  dispatch({ type: 'SAVE_FAILED', error: msg, canAutoRetry: true });
   setSaveFailureGen((n) => n + 1);
   setSaveStatus('error');
 })
```
Pattern recommendation: typed error carries **code/message/details**, consumer translates at UI boundary; `state.saveError` remains **rendered string**.

### NotificationBanner impact
No `NotificationBanner.tsx` change required if `state.saveError` stays string (banner currently renders `state.saveError` directly at lines 80-96).

## 7) Test plan proposal

### 7.1 Unit tests (extractor)
- Location: `frontend-public/tests/lib/api/errorCodes.test.ts`.
- Estimated 11 tests covering normal nested/flat extraction + all edge cases from section 4.6 + unknown-code passthrough.

### 7.2 Pipeline integration test (mandatory)
- Location: extend `frontend-public/tests/components/editor/autosave.test.tsx` (or add `frontend-public/tests/components/editor/autosave-backend-codes.test.tsx` for isolation).
- Framework: **Jest + Testing Library** (repo standard).
- Scenarios (mock `updateAdminPublication` rejections with `BackendApiError` equivalents produced by admin-layer tests):
  1. 404 nested `PUBLICATION_NOT_FOUND` → RU + EN localized banner.
  2. 422 nested `PUBLICATION_UPDATE_PAYLOAD_INVALID` (+ validation_errors ignored) → RU + EN localized banner.
  3. 401 flat `AUTH_API_KEY_INVALID` → localized banner.
  4. 429 flat `AUTH_ADMIN_RATE_LIMITED` → localized banner.
  5. 500 no envelope → fallback passthrough (`err.message` / generic).
- Assertion level: prefer banner DOM text (`data-testid="notification-banner"`) to prove full wiring through reducer/UI.

### 7.3 Denied-EN smoke
- Location: `frontend-public/tests/integration/i18n-ru-render-smoke.test.tsx` (append section) or new `frontend-public/tests/i18n/backend-errors-ru-smoke.test.ts`.
- RU denied fingerprints for mapped backend strings: `Publication`, `authentication`, `rate limit`.

### 7.4 Coverage delta
- Estimated additions: ~15-20 tests (11 extractor + 4-6 integration/smoke).
- CI path: `.github/workflows/frontend-public.yml` runs `npm run test` in `frontend-public`, so `tests/lib/api/*.test.ts` and `tests/components/editor/*.test.tsx` patterns are included automatically.

## 8) Open questions for founder
1. **Namespacing confirmation:** approve Option C hybrid (`publication.*` + `errors.backend.*`) or prefer full consolidation under `errors.backend.*` despite existing `tPublication('not_found.reload')` call-site coupling?
2. **Typed error shape confirmation:** approve single `BackendApiError` carrier class (recommended) vs per-code subclasses beyond `AdminPublicationNotFoundError`?
3. **Auth visibility in autosave harness:** should PR2 autosave pipeline test include 401/429 mapped-message assertions even if real editor flow may be short-circuited upstream by middleware/proxy in production? (Recommendation: include via controlled mock to validate dictionary + translation plumbing.)

## 9) DEBT.md update preview
```diff
--- a/DEBT.md
+++ b/DEBT.md
@@
-| DEBT-030 | Frontend publication error handling still status/message based; not aligned to backend error_code envelopes | in-progress | 2026-04-XX | — |
+| DEBT-030 | Frontend publication error handling still status/message based; not aligned to backend error_code envelopes | resolved | 2026-04-XX | PR2: <link-to-pr> |
+
+| DEBT-0XX | Auth middleware still uses flat error envelope while publication endpoints use nested detail envelope | in-progress | 2026-04-XX | Follow-up: migrate auth errors to nested envelope; then simplify frontend extractor by removing flat-branch compatibility |
```
Recommendation: track two-envelope cleanup as a dedicated DEBT row (not inline code comment), because it spans backend contract migration + frontend cleanup.
