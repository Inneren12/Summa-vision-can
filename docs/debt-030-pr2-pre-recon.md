# 1. Stack inventory

- Next.js (`frontend-public/`): Calls publication PATCH/publish/unpublish: **PARTIAL** (PATCH only; no publish/unpublish caller found) — see §2.
- Flutter (`frontend/`): Calls publication PATCH/publish/unpublish: **NO** — see §3.

# 2. Next.js call-sites

## 2.1 Mandatory search procedure results (commands run + hit summaries)

Literal commands were run exactly as requested first. In this environment, `rg --type tsx` is unsupported, so those literal runs failed with `rg: unrecognized file type: tsx`. I then reran equivalent searches with `-g '*.ts' -g '*.tsx'` to complete the audit.

- `rg -n --type ts --type tsx 'admin/publications' frontend-public/`
  - Hits (key runtime code):
    - `frontend-public/src/lib/api/admin.ts:12,32,56,91`
    - `frontend-public/src/app/api/admin/publications/[...path]/route.ts:3`
    - `frontend-public/src/lib/api/admin-server.ts:25,52`
  - Tests also hit (`frontend-public/tests/...`), omitted here as non-runtime call-sites.
- `rg -n --type ts --type tsx '/publish|/unpublish' frontend-public/`
  - No endpoint call-site hits for admin publication publish/unpublish in runtime source.
- `rg -n --type ts --type tsx 'publications/\$\{|publications/\${' frontend-public/`
  - Literal regex errored (`repetition quantifier expects a valid decimal`); no usable result.
- `rg -n --type ts --type tsx 'publications/\[' frontend-public/`
  - No runtime call-site hits.
- `rg -n --type ts --type tsx 'method:\s*[\x27"]PATCH[\x27"]' frontend-public/`
  - `frontend-public/src/lib/api/admin.ts:92`
- `rg -n --type ts --type tsx '\.patch\(|\.post\(.*publish' frontend-public/`
  - No runtime hits for publish/unpublish calls.
- `rg -n --type ts --type tsx 'error_code|errorCode' frontend-public/`
  - No runtime parser usage for `error_code`.
- `rg -n --type ts --type tsx 'response\.detail|res\.detail|data\.detail' frontend-public/`
  - `frontend-public/src/components/forms/InquiryForm.tsx:109` (unrelated form endpoint).

## 2.2 Publication endpoint call-sites (runtime)

### Call-site N1 (actual frontend mutation layer)
- File + lines: `frontend-public/src/lib/api/admin.ts:86-108`
- HTTP method + endpoint pattern (verbatim):
  - `method: 'PATCH'`
  - `fetch(
      `${PROXY_BASE}/${encodeURIComponent(id)}`,
    )` with `PROXY_BASE = '/api/admin/publications'`
- Response consumption:
  - Returns `Promise<AdminPublicationResponse>` on success.
  - Throws `AdminPublicationNotFoundError` for 404.
  - Throws generic `Error(body?.detail ?? fallback)` for other non-OK statuses.
- Where errors surface to user:
  - Upstream in editor autosave flow (`frontend-public/src/components/editor/index.tsx:549-597`):
    - 404 (`AdminPublicationNotFoundError`) maps to localized `tPublication('not_found.reload')` and dispatches `SAVE_FAILED`.
    - Other errors use raw exception message (`err.message`) and dispatch `SAVE_FAILED`.
  - UI presentation in `NotificationBanner` (`frontend-public/src/components/editor/components/NotificationBanner.tsx:80-127`) as banner text (`state.saveError`).
- `error_code` currently read?
  - **NO**. Error extraction is `body?.detail` only; no `body.detail.error_code` and no top-level `body.error_code` handling.

### Call-site N2 (server proxy seam for all admin publication verbs)
- File + lines: `frontend-public/src/app/api/admin/publications/[...path]/route.ts:3-80`
- HTTP method + endpoint pattern (verbatim):
  - Forwards `GET|POST|PATCH|DELETE` to `${apiUrl}/api/v1/admin/publications${tail}${search}`.
- Response consumption:
  - Transparent passthrough; returns backend body/status/content-type unchanged.
- Where errors surface to user:
  - Not directly user-facing; consumer sees whatever downstream API client does.
- `error_code` currently read?
  - **NO**. Proxy does not parse payloads.

## 2.3 Publish/unpublish endpoint coverage in Next.js

No runtime call-site was found that issues:
- `POST /api/v1/admin/publications/{id}/publish`
- `POST /api/v1/admin/publications/{id}/unpublish`

The proxy would forward these paths if called, but no caller currently constructs those URLs.

# 3. Flutter call-sites

## 3.1 Mandatory search procedure results (commands run + hit summaries)

All requested Flutter commands were run literally.

- `rg -n --type dart 'admin/publications' frontend/`
  - Only hit: `frontend/lib/features/editor/domain/editor_notifier.dart:58` (comment text: “future save/publish/unpublish backend actions”).
- `rg -n --type dart '/publish|/unpublish' frontend/`
  - Same comment-only hit in `editor_notifier.dart`.
- `rg -n --type dart 'publications/\$' frontend/`
  - No hits.
- `rg -n --type dart 'class.*Publication.*Client|PublicationRepo|PublicationApi' frontend/`
  - No publication API client/repo class hits.
- `rg -n --type dart 'errorCode|error_code' frontend/lib/`
  - Multiple hits in graphics/jobs pipeline; none tied to admin publications endpoints.
- `rg -n --type dart 'backend_errors\.dart' frontend/`
  - Found and used by graphics screens only.
- `sed -n '40,80p' frontend/lib/features/editor/**/editor_notifier.dart ...`
  - Confirmed reserved-hook comment at lines 57-61; notifier has no backend action methods.

## 3.2 Publication endpoint call-sites (runtime)

No runtime Flutter call-site found for:
- `PATCH /api/v1/admin/publications/{id}`
- `POST /api/v1/admin/publications/{id}/publish`
- `POST /api/v1/admin/publications/{id}/unpublish`

Closest related runtime API usage:
- `frontend/lib/features/queue/data/queue_repository.dart:13-17` uses `GET /api/v1/admin/queue`.
- Editor screen (`frontend/lib/features/editor/presentation/editor_screen.dart:55-80`) surfaces queue load errors and “brief not found” from local queue filtering, not from publication PATCH/publish/unpublish endpoints.

# 4. Existing error-handling patterns

## 4.1 Next.js

- API layer (`frontend-public/src/lib/api/admin.ts`) throws typed 404 (`AdminPublicationNotFoundError`) for publication fetch/update; all other failures are generic `Error` using `body?.detail` fallback string.
- Editor autosave (`frontend-public/src/components/editor/index.tsx:565-589`):
  - 404 → localized fixed key `publication.not_found.reload`.
  - non-404 → raw message passthrough (`err.message`).
- UI surface (`frontend-public/src/components/editor/components/NotificationBanner.tsx:80-127`): save errors rendered in a high-priority alert banner (`state.saveError`).
- `error_code` handling status:
  - No parsing of either envelope variant:
    - publication contract shape (`detail.error_code`)
    - auth/rate-limit shape (top-level `error_code`)

## 4.2 Flutter

- No editor publication action pipeline exists yet; `EditorNotifier` is local form state only.
- Existing structured `error_code` handling exists in a different domain (graphics/jobs):
  - mapper function `mapBackendErrorCode(String?, AppLocalizations)` in `frontend/lib/l10n/backend_errors.dart:13-25`.
  - consumed by graphics UI flows (e.g., chart config / preview) with fallback to backend message.
- For editor flow today:
  - backend call is queue fetch (`/api/v1/admin/queue`), surfaced via localized wrapper `editorLoadBriefError(err.toString())` on provider error; if brief missing in fetched list, shows `editorBriefNotFound`.

# 5. Localization infrastructure

## 5.1 Next.js

- `next-intl` is already configured and active:
  - plugin setup: `frontend-public/next.config.ts:1-5,60`
  - request config and message loading: `frontend-public/src/i18n/request.ts:1-12`
  - catalogs exist: `frontend-public/messages/en.json`, `frontend-public/messages/ru.json`
- Existing key naming pattern: nested namespaces (e.g., `publication.not_found.reload`, `publication.load_failed.fallback`, `qa.mode.publish`).
- Example existing keys:
  - `publication.not_found.reload`
  - `publication.load_failed.fallback`
  - `publications.title`

## 5.2 Flutter

- ARB files confirmed:
  - `frontend/lib/l10n/app_en.arb`
  - `frontend/lib/l10n/app_ru.arb`
- `backend_errors.dart` confirmed and current shape:
  - top-level helper function:
    - `String? mapBackendErrorCode(String? errorCode, AppLocalizations l10n)`
  - implemented as a `switch` over `errorCode` returning localized strings.
- Full currently mapped backend codes:
  - `CHART_EMPTY_DF`
  - `CHART_INSUFFICIENT_COLUMNS`
  - `UNHANDLED_ERROR`
  - `COOL_DOWN_ACTIVE`
  - `NO_HANDLER_REGISTERED`
  - `INCOMPATIBLE_PAYLOAD_VERSION`
  - `UNKNOWN_JOB_TYPE`
- Pattern type confirmation:
  - It is a **top-level helper function**, not a class/static method and not an extension.

# 6. PR2 scope recommendation

**Recommendation: Scenario B — Next.js only.**

Evidence:
- Next.js has active PATCH call chain for admin publications (`updateAdminPublication` + editor autosave + notification banner).
- Next.js currently does not parse structured `error_code` from either envelope variant.
- Flutter has no runtime call-sites for publication PATCH/publish/unpublish; only a reserved comment hook exists in `editor_notifier.dart`.
- Publish/unpublish endpoints have no active caller in either stack at present.

Implication for PR2 scope:
- Implement structured error-code extraction and mapping in Next.js publication mutation path first.
- Flutter publication-action wiring is not implementable in PR2 without introducing new backend calls (which is out of scope for this audit).

# 7. Open questions for founder

1. Next.js proxy route supports POST forwarding to `/api/v1/admin/publications/{id}/...`, but no runtime caller exists for `/publish` and `/unpublish`. Should PR2 still add parser support for these codes in shared error parsing now (future-proof), or strictly limit to active PATCH flow only?
2. In Next.js save flow, non-404 failures currently surface raw backend message (`err.message`) in banner. For 422 (`PUBLICATION_UPDATE_PAYLOAD_INVALID`), should PR2 keep current fallback message passthrough when code is unmapped, or enforce a mandatory localized generic for all recognized codes?
