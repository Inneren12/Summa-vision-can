# Frontend Autosave Architecture (Next.js Editor)

**Status:** Living document — update on every Next.js editor / admin.ts impl PR
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-27
**Source:** Phase 1.3 pre-recon Part B (`docs/recon/phase-1-3-B-frontend-inventory.md`)
**Related architecture:** `BACKEND_API_INVENTORY.md` §5 (error envelope contract)

**Maintenance rule:** any PR that touches `admin.ts`, `errorCodes.ts`, the autosave consumer, or adds a new backend error code requires update to this file in the same commit. Drift signal: if a memory item references a `BackendApiError` field, error code, or i18n key not listed here, this file is stale.

## How to use this file

- Pre-recon and recon prompts SHOULD read this file FIRST when scope touches admin Next.js or autosave error handling.
- Sections track: PATCH/autosave wiring, `BackendApiError` class shape, known error codes registry, autosave consumer integration points, i18n key namespaces.
- For corresponding backend handler patterns see `BACKEND_API_INVENTORY.md`.

---

## 1. admin.ts — PATCH/autosave wiring

**File:** `frontend-public/src/lib/api/admin.ts`

### Public API
- `updateAdminPublication(id, payload, opts)` — signature (admin.ts:125):
  ```ts
  export async function updateAdminPublication(
    id: string,
    payload: UpdateAdminPublicationPayload,
    opts: { signal?: AbortSignal } = {},
  ): Promise<AdminPublicationResponse>
  ```
  Sends `PATCH /api/admin/publications/{id}` with JSON body. **No `If-Match`/version header today.**
- `publishAdminPublication(id, payload, options)` — signature (admin.ts:247):
  ```ts
  export async function publishAdminPublication(
    id: string,
    payload: PublishPayload = {},
    options: { signal?: AbortSignal; ifMatch?: string | null } = {},
  ): Promise<{ etag: string | null; document: AdminPublicationResponse }>
  ```
  Sends `POST /api/admin/publications/{id}/publish` with JSON body
  containing optional `bound_blocks: BoundBlockReference[]` (Phase 3.1d
  Slice 4a). Empty body (no `bound_blocks` or `[]`) is backward-compatible:
  publish succeeds with no snapshot capture; first compare returns
  `unknown + [snapshot_missing] + info`. 404 surfaces as
  `AdminPublicationNotFoundError` (terminal — no auto-retry, manual reload
  via `publication.not_found.reload`). Other failures throw `BackendApiError`
  carrying `code` / `details` / `status`. Supports `If-Match` for ETag
  concurrency (Phase 1.3 pattern); since Phase 3.1d Slice 4b (Recon Delta 03)
  ReviewPanel forwards `etagRef.current` as `ifMatch` and surfaces 412
  via the `PreconditionFailedModal` publish-source variant (see §7).

### BackendApiError class
**Location:** `frontend-public/src/lib/api/admin.ts:34–51`

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

Key fields:
- `status: number` — HTTP status of the failed response.
- `code: string | null` — populated from response `detail.error_code` (DEBT-030 envelope). **Field is named `code`, not `errorCode`.** Nullable when the backend returned no structured envelope.
- `message: string` — populated from `detail.message`, falling back to `body.detail` (string) and finally to a synthesized `Admin publication update failed: <status>` string. Surfaced via `Error.message`.
- `details: Record<string, unknown> | null` — populated from response `detail.details`. Nullable.
- Constructor takes a single named-args object.

### Status-to-error mapping
Detection strategy (per B.1.1): **code-first with shape-less status backstop.**

`frontend-public/src/lib/api/admin.ts:137–164` (verbatim):

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

- Code-first: response body's `detail.error_code` is read first; status code is backstop.
- Reference: DEBT-030 PR2 established this pattern. 404 detection uses code-first with status backstop (only fires when `payload.code` is null).
- The second `extractBackendErrorPayload` call site is at admin.ts:183 (clone path).

---

## 2. KNOWN_BACKEND_ERROR_CODES

**File:** `frontend-public/src/lib/api/errorCodes.ts:17–25`

### Current registered codes
(Verbatim from B.1.1)

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

| Code | i18n key | Source PR | Notes |
|---|---|---|---|
| `PUBLICATION_NOT_FOUND` | `publication.not_found.reload` | TBD | Domain-specific; routed via typed `AdminPublicationNotFoundError`, terminal (no auto-retry). |
| `PUBLICATION_UPDATE_PAYLOAD_INVALID` | `publication.payload_invalid.message` | TBD | Domain-specific. |
| `PUBLICATION_CLONE_NOT_ALLOWED` | `errors.backend.publicationCloneNotAllowed` | TBD | Cross-cutting namespace; **only `camelCase` leaf** under `errors.backend.*`. |
| `PUBLICATION_INTERNAL_SERIALIZATION_ERROR` | `publication.serialization_error.message` | TBD | Domain-specific. |
| `AUTH_API_KEY_MISSING` | `errors.backend.auth_api_key_missing` | TBD | Cross-cutting auth. |
| `AUTH_API_KEY_INVALID` | `errors.backend.auth_api_key_invalid` | TBD | Cross-cutting auth. |
| `AUTH_ADMIN_RATE_LIMITED` | `errors.backend.auth_admin_rate_limited` | TBD | Cross-cutting auth. |

Total: **7** codes. **No `PRECONDITION_FAILED`** (or any 412 code) present today — see §7 / Phase 1.3 Part B §1.5.

### Adding a new code
When a new backend error code is added:
1. Append to `KNOWN_BACKEND_ERROR_CODES` array (`errorCodes.ts:17`).
2. Add the mapping in `BACKEND_ERROR_I18N_KEYS` (`errorCodes.ts:47`).
3. Add EN + RU i18n entries in `frontend-public/messages/en.json` and `frontend-public/messages/ru.json`.
4. Update this table.
5. Update `BACKEND_API_INVENTORY.md` §5.

---

## 3. errorCodes.ts — i18n key resolution

**File:** `frontend-public/src/lib/api/errorCodes.ts` (143 lines)

### Public API
- `extractBackendErrorPayload(body)` — pulls `detail.error_code`, `detail.message`, `detail.details` out of a parsed fetch response body. Imported by `admin.ts:11` and called at admin.ts:139 and admin.ts:183.
- `getBackendErrorI18nKey(code: string | null): string | null` — returns the i18n key for a given backend error code; returns `null` for unknown codes (callers should `console.warn` and fall back to backend message). Verbatim body (errorCodes.ts:108–116):
  ```ts
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
- `translateBackendError(t, code)` (errorCodes.ts:136–142) — wraps the lookup and applies the `as never` cast for next-intl strict typing.

### Namespace pattern (DEBT-030 Option C hybrid)
- Domain-specific publication UX: `publication.*` (4 mappings).
- Cross-cutting backend / auth / system: `errors.backend.*` (3 mappings via `BACKEND_ERROR_I18N_KEYS`; 4 leaf keys total in JSON, the 4th being `publicationCloneNotAllowed`).
- Confirmed in B.1.2: **yes — DEBT-030 Option C hybrid is in place.**

`BACKEND_ERROR_I18N_KEYS` (verbatim, errorCodes.ts:47–55):

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

---

## 4. Autosave consumer (editor integration)

**File:** `frontend-public/src/components/editor/index.tsx` (single autosave consumer; calls `updateAdminPublication`)

### Component
- Function name: `performSave` (`useCallback` at index.tsx:568).
- Imports `updateAdminPublication`, `BackendApiError`, and `AdminPublicationNotFoundError` from `@/lib/api/admin` (lines 31–43); imports `NotificationBanner` from `./components/NotificationBanner`.
- Inspects `error.code` (the actual class field, not `errorCode`): **yes** — via `err instanceof BackendApiError` then `err.code` passed to `translateBackendError(t, err.code)`.
- Current error UX: **in-editor banner** (`NotificationBanner` at `frontend-public/src/components/editor/components/NotificationBanner.tsx`) with auto-retry countdown (`retryCountdownMs`) and a "Retry now" button (`onManualRetry`). Banner priority: `saveError > importError > _lastRejection > warnings`. **No modal exists today** — all save errors are surfaced as banner messages.

### Error branching pattern
When `PATCH` fails with `BackendApiError`, in `performSave.catch` (index.tsx:584–623):

- **Terminal branch:** if `err instanceof AdminPublicationNotFoundError`, dispatch `SAVE_FAILED` with `error: tPublication('not_found.reload')` and `canAutoRetry: false`. Set `saveStatus = 'error'` and return — does NOT auto-retry.
- **Generic / transient branch:** otherwise, compute
  ```ts
  const localized = err instanceof BackendApiError
    ? translateBackendError(t, err.code)
    : null;
  ```
  If `localized` is null AND the error has a `code`, `console.warn('[backend] unmapped error_code:', err.code)`. Final message falls through `localized ?? err.message ?? String(err)`. Dispatch `SAVE_FAILED` with `canAutoRetry: true`, increment `setSaveFailureGen`, set `saveStatus = 'error'`.
- **Code-specific branches today:** only `PUBLICATION_NOT_FOUND` (via the typed `AdminPublicationNotFoundError`) gets the terminal treatment. Every other code falls through to the auto-retry branch.

Verbatim (index.tsx:568–627) is reproduced in Phase 1.3 Part B §1.3.

### Where to add new error-code modal
File path proposal for any new dedicated error UI: `frontend-public/src/components/editor/components/StaleVersionModal.tsx` (alongside `NotificationBanner.tsx`, mirroring the existing convention). Triggered from `performSave`'s `.catch` chokepoint at index.tsx:584; for example, for a future 412 code: `err instanceof BackendApiError && err.code === 'PRECONDITION_FAILED'` — terminal, must NOT enter the auto-retry branch. Lifted "modal open" state would live next to `setSaveStatus`/`setSaveFailureGen` in `index.tsx`.

### Secondary consumer (out of autosave scope)
`handleClone` at index.tsx:793–818 uses the identical `translateBackendError(t, err.code)` plumbing but routes the localized string into `setImportError` instead of `saveError`. Not on the autosave path.

---

## 5. i18n key inventory

### Source files
- EN: `frontend-public/messages/en.json` (next-intl `messages/` convention; no `locales/` or `i18n/` directory).
- RU: `frontend-public/messages/ru.json` (RU parity verified — all 8 leaf paths populated).

### Existing namespaces

| Namespace | Key count | Notes |
|---|---|---|
| `publication.*` | 4 | Domain-specific: `load_failed.fallback`, `not_found.reload`, `payload_invalid.message`, `serialization_error.message`. Lines 15–28 of en.json. |
| `errors.backend.*` | 4 | Cross-cutting backend errors (DEBT-030 hybrid): `auth_api_key_missing`, `auth_api_key_invalid`, `auth_admin_rate_limited`, `publicationCloneNotAllowed`. Lines 625–632 of en.json. |

Total mapped via `BACKEND_ERROR_I18N_KEYS`: 7 (one entry, `PUBLICATION_NOT_FOUND`, points at the existing `publication.not_found.reload` key). Total leaf keys across both namespaces: 8.

### Naming-style inconsistency (observation, not a proposal)
Most keys use `snake_case` (e.g. `auth_api_key_missing`, `payload_invalid.message`). The single key `publicationCloneNotAllowed` is `camelCase`. Any new key choice will inherit one convention or the other — flag for design.

### Adding new keys
When adding a backend error code, both EN and RU entries MUST be added in the same PR. Founder approves RU translations (do NOT auto-translate).

---

## 6. Test patterns

### Real-wire integration tests (memory items #5, #21)
For HTTP→state→UI pipelines, integration tests MUST mock `fetch` at the network boundary, **not** the consumer module. One scenario is sufficient to prove pipeline integrity.

Example: testing autosave 412 handling
- Mock `fetch` to return 412 with the DEBT-030 envelope (`{ detail: { error_code, message, details } }`).
- Render the autosave consumer component (`frontend-public/src/components/editor/index.tsx`).
- Trigger the save action (dirty + `performSave`).
- Assert the UI surfaces the correct i18n key string (banner today; modal in the future).

### Anti-pattern (do not use)
Mocking `admin.ts` (the consumer module) hides pipeline drift. Slice 3.8 lesson: mapper tested in isolation + widget tests with manually-built state passed 285+ tests while notifier `_poll` never copied `errorCode` (the conceptual field, mapped to `code` here). A real-wire test would have caught it.

---

## 7. 412 Precondition Failed handling

**Status:** Active as of Phase 1.3.

### Discriminator

```typescript
err instanceof BackendApiError && err.code === 'PRECONDITION_FAILED'
```

In the `performSave` `.catch` chokepoint at `frontend-public/src/components/editor/index.tsx`. Branch is **terminal** — `return` early; no `setSaveFailureGen` bump; no auto-retry. Distinct from `NotificationBanner`'s transient-retry path.

### ETag round-trip

`admin.ts` extends `fetchAdminPublication`, `updateAdminPublication`, and `cloneAdminPublication` to read the `ETag` response header into `result.etag` (returning `AdminPublicationWithEtag`). `updateAdminPublication` also accepts `opts.ifMatch` and forwards it as the `If-Match` request header. The editor keeps an `etagRef` ref that is updated on every successful PATCH and seeded at fork-time from `cloneAdminPublication`'s response. The first PATCH in a session may carry no `If-Match`; the backend tolerates this per Q3=(a) (see DEBT-042).

### Modal trigger

```typescript
setPreconditionFailedModal({ open: true, serverEtag });
```

Modal lives at `frontend-public/src/components/editor/components/PreconditionFailedModal.tsx`. Canonical name mirrors the backend `error_code` 1:1.

### Two-button UX (Q4=(a))

- **Reload (lose my changes)** — default focus. Calls `fetchAdminPublication(publicationId)`, dispatches `IMPORT` with the freshly hydrated doc, refreshes the captured `etagRef`.
- **Save as new draft** — calls `cloneAdminPublication(originalId)` then a fresh `updateAdminPublication(cloneId, ...)` PATCH using the clone's freshly returned ETag as `If-Match`. The editor navigates to the clone via `router.push('/admin/editor/${clone.id}')`.

### Esc / backdrop dismissal

Non-resolving but non-looping. The modal closes and `saveStatus` flips to `'conflict'`. The autosave debounce effect guards on `saveStatus !== 'conflict'`, so the dismissed conflict freezes autosave until the next user edit. A new edit re-marks the doc dirty and resets status to `'pending'` — at which point a fresh PATCH fires and re-triggers the modal if the conflict is still real. User-initiated retry, not auto-loop.

### Fork-path failure recovery

Three cases handled by `handleForkFailure` inside `forkLocalSnapshotAsNewDraft`:
1. Clone fails (e.g. 422 `PUBLICATION_CLONE_NOT_ALLOWED`) — translate via the existing pattern, surface as `importError` banner; user remains on the original.
2. Clone succeeds, fork-PATCH 422 (validator-blocking error) — surface the `errors.backend.precondition_failed.fork_partial` banner so the user knows the clone exists but their edits did not stick; the editor still navigates to the clone.
3. Clone succeeds, fork-PATCH fails for another reason — surface a generic localized error banner.

### i18n keys

Under `errors.backend.precondition_failed.*` (cross-cutting protocol namespace per the hybrid policy in §6, NOT `publication.*`). Six keys: `title`, `body`, **`body_publish`** (Phase 3.1d Slice 4b), `button_reload`, `button_save_as_draft`, `fork_partial`. EN + RU parity verified.

### Phase 3.1d Slice 4b — Publish path mount + auto-refresh sequencing (Recon Delta 03)

`PreconditionFailedModal` now serves two write paths via a `source: 'patch' | 'publish'` discriminator on the modal state in `editor/index.tsx`:

- `source: 'patch'` (default, preserves Phase 1.3 UX) — mounted from `performSave`'s 412 catch branch; renders the `body` key.
- `source: 'publish'` — mounted from `usePublishAction.onPreconditionFailed` (forwarded up through `ReviewPanel` and `RightRail`); renders the `body_publish` key.

Publish flow with auto-refresh (sequencing per Recon Delta 03):

1. Operator clicks `MARK_PUBLISHED` transition in `ReviewPanel` → `usePublishAction.initiate()` opens `PublishConfirmModal`.
2. Operator confirms → `confirm(walkerResult)` → `publishAdminPublication(id, { bound_blocks }, { ifMatch: etag })` where `etag` is sourced from the editor's `etagRef` and forwarded down through `RightRail → ReviewPanel`.
3. **On 200** → `onPublishSuccess(newEtag)` runs three side-effects, in order:
   1. `onEtagUpdate(newEtag)` — refreshes `etagRef.current` so any subsequent PATCH carries the post-publish ETag.
   2. `onCompareRequest()` — invokes the lifted `useCompareState.compare()` so the badge transitions to "Comparing…" immediately.
   3. `dispatch({ type: 'MARK_PUBLISHED', channel: 'manual' })` — workflow advances synchronously.
4. **On 412** → `onPreconditionFailed({ serverEtag })` opens `PreconditionFailedModal` with `source: 'publish'`. Compare is **not** invoked; workflow does **not** advance.
5. **On 404** → existing `SAVE_FAILED` toast (unchanged).

`useCompareState` was lifted from `TopBar` to the editor root in Slice 4b so a single hook instance can be driven both by the user's manual Compare button click (via `TopBar`) and by the publish-success auto-trigger. Initial-mount auto-trigger is **not** introduced — recon §2.3's "compare is operator-triggered" invariant is preserved for the no-publish case.

---

## 8. Maintenance log

| Date | PR | Sections touched | Notes |
|---|---|---|---|
| 2026-04-27 | initial | all | Created from Phase 1.3 Part B input (`docs/recon/phase-1-3-B-frontend-inventory.md`). |
| 2026-04-27 | Phase 1.3 impl | §2, §3, §4, §5, §7 | `PRECONDITION_FAILED` added to `KNOWN_BACKEND_ERROR_CODES` with i18n key `errors.backend.precondition_failed`; new `PreconditionFailedModal` component; autosave catch branch + fork-path implementation; 5 EN + 5 RU keys added under `errors.backend.precondition_failed.*`. `admin.ts` returns `AdminPublicationWithEtag`. |
| 2026-05-07 | PR-07 Slice 4b (Recon Delta 03) | §7 | `PreconditionFailedModal` extended with `source: 'patch' \| 'publish'` discriminator; `body_publish` i18n key added EN+RU. `usePublishAction` now forwards `If-Match` and surfaces `onPreconditionFailed`. `useCompareState` lifted from `TopBar` to editor root; on publish-success the editor refreshes `etagRef`, fires `compare()`, then dispatches `MARK_PUBLISHED` (in that order). Backend POST `/publish` honors `If-Match` (412 on mismatch; v1 tolerates absent header per DEBT-079). |
