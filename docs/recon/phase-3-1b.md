# Phase 3.1b Recon — Admin CRUD endpoints + Flutter admin UI

## Scope + method
- Recon-only read pass performed against backend routers/services/repositories, frontend router/network/error/i18n structure, and architecture docs.
- No source edits except this recon artifact.
Date: 2026-05-02  
Branch target: `codex/phase-3-1b-recon`  
Artifact: `docs/recon/phase-3-1b.md`

## Scope and constraints observed

- Recon-only pass completed with read-only inspection of backend + Flutter admin surfaces; no source edits outside this file.
- Note: repo layout uses `frontend/` (Flutter admin app), not `admin-flutter/`.

---

## Part A — Backend

### A1) Existing admin endpoint patterns (auth + structure)
- Admin HTTP modules are split by resource under `backend/src/api/routers/` (e.g., `admin_publications.py`, `admin_jobs.py`, `admin_cubes.py`) rather than one monolithic admin router.
- Existing admin routers rely on global auth middleware (`AuthMiddleware`) rather than per-endpoint `Depends(verify_admin_api_key)`. This is explicitly documented in router docstrings and endpoint response docs as `X-API-KEY` protected.
- `admin_publications` is the closest mutation parallel for 3.1b:
  - route decorator pattern with explicit `response_model`, `status_code`, and `responses` map;
  - dependency injection via helper deps (`_get_repo`, `_get_audit`) wired through `Depends(get_db)`.
- Error conventions are mixed but documented:
  - publication PATCH payload validation uses DEBT-030 nested envelope via custom exception handler;
  - legacy/global `SummaVisionError` still returns flat envelope in some paths (notably auth-side).

**Auth grep evidence:** `X-API-KEY` found in admin routers and network layer docs; no `verify_admin*` dependency symbols found in `backend/src/api`.

### A2) New endpoints — contract proposal aligned to locks
1. `POST /api/v1/admin/semantic-mappings/upsert`
   - Body: `SemanticMappingUpsertRequest` with locked fields, including `if_match_version`.
   - Status:
     - `201` when created, `200` when updated.
     - `400` for validation/cube/dimension/member/product mismatch errors.
     - `409` for version mismatch (`VERSION_CONFLICT` if founder confirms this code name).
     - `401/403` via middleware auth behavior.
   - Error mapping from current service exceptions:
     - `CubeNotInCacheError` -> `400 CUBE_NOT_IN_CACHE`
     - `DimensionMismatchError` -> `400 DIMENSION_NOT_FOUND`
     - `MemberMismatchError` -> `400 MEMBER_NOT_FOUND`
     - `MetadataValidationError` generic -> `400 <error_code carried>`
   - Response envelope should include `result.errors` + `result.resolved_filters` in `detail.details` for inline UI mapping.

2. `GET /api/v1/admin/semantic-mappings`
   - Filters: `cube_id`, `semantic_key`, `is_active`; pagination `limit`/`offset`.
   - Existing admin list precedent is inconsistent (jobs uses `limit` only), so semantic-mappings can introduce offset pagination but this is a divergence to document.

3. `GET /api/v1/admin/semantic-mappings/{id}`
   - `200` row, `404` missing.

4. `DELETE /api/v1/admin/semantic-mappings/{id}`
   - Soft delete only (`is_active=false`) and return row.
   - Idempotent: already inactive returns `200` current row.

5. `GET /api/v1/admin/cube-metadata/{cube_id}`
   - Read-only cache lookup endpoint (`get_cached` semantics preferred for autocomplete read path).
   - `200` cache entry, `404` not cached.
   - **Open decision surfaced:** auto-prime on read vs read-only (recommend read-only + fallback UX).

### A3) Service-layer extension gap analysis
- `SemanticMappingService.upsert_validated` exists and already wraps cache+validation+repo upsert.
- Current signature has **no** `if_match_version`; optimistic concurrency is missing.
- Current service exposes only `upsert_validated`; list/get/delete service methods do not exist.
- Proposed additions:
  - `if_match_version` support on upsert path with `VersionConflictError` (preferred as `MetadataValidationError` subclass for envelope compatibility).
  - new methods `list_mappings`, `get_mapping`, `soft_delete`.
  - new `MappingNotFoundError` for 404 mapping.

### A4) Repository extension gap analysis
- `SemanticMappingRepository` already has `get_by_id`, `get_by_key`, `get_active_for_cube`, `create`, `upsert_by_key`, `update`.
- Missing for 3.1b route surface:
  - generic list with filters + total count
  - soft-delete helper (or service-layer implementation using existing methods)
- `get_by_id` already present; no need to add duplicate.

### A5) Auth integration
- Mirror existing admin pattern: rely on `AuthMiddleware` + `X-API-KEY` header, and include 401/403 response docs like current admin routes.
- Test pattern should re-use existing admin endpoint fixtures/header injection style from API tests.

### A6) OpenAPI/docs integration
- FastAPI will auto-include new endpoints in OpenAPI.
- Manual docs to update in impl PR:
  - `docs/architecture/BACKEND_API_INVENTORY.md`
  - `docs/modules/semantic_mappings.md`

### A7) Optimistic concurrency convention check (critical ambiguity)
- Current publications concurrency is **header-based** (`If-Match` request header + `ETag` response header, `412 PRECONDITION_FAILED`).
- Founder lock for 3.1b requests **body-based** `if_match_version` with `409 VERSION_CONFLICT`.
- This is a real convention divergence and should be explicitly approved before implementation.

### A8) DEBT-030 envelope + error code integration
- `frontend-public/src/lib/api/errorCodes.ts` currently includes semantic-mapping codes from 3.1ab, but **does not** include `VERSION_CONFLICT` or `BULK_VALIDATION_FAILED`.
- Admin Flutter currently maps only graphics/job-related codes in `frontend/lib/l10n/backend_errors.dart`; semantic-mapping codes are not wired there yet.
- Additions needed in impl scope:
  - code dictionaries (TS + Dart)
  - ARB keys EN/RU for `version_conflict` and `bulk_validation_failed` (plus semantic mapping keys in admin app if absent).

### A9) Bulk validated upsert (seed atomicity extension)
- Current module docs explicitly state validated seed path is row-committed and not file-atomic.
- 3.1b recon confirms need for new bulk service path to satisfy file atomicity lock:
  - `upsert_many_validated(items)` with validate-all-then-decide semantics.
  - `BulkValidationError` carrying per-item results.
  - CLI default path migration to bulk method.
  - update docs/tests reflecting atomic semantics shift.
- Two founder decisions surfaced:
  1) whether bulk HTTP endpoint ships now (recommend: no, seed-only this phase)
  2) whether one cube cache failure fails whole batch (recommend: yes, fail whole batch)

---

## Part B — Flutter

### B1) Existing admin app structure
- Active Flutter admin app in this repo is `frontend/` (not `admin-flutter/`).
- App entry (`frontend/lib/main.dart`) uses Riverpod + `MaterialApp.router` + localization delegates and GoRouter from provider.
- Existing top-level route set includes `queue`, `jobs`, `exceptions`, cubes/data/graphics/kpi/editor/preview.

### B2) Navigation entry pattern (inspection-first)
- Router is flat `GoRoute` list (no ShellRoute nesting currently).
- Matching 3.1b entry should therefore be an additional flat route (and optional subordinate routes if desired, but nested child-route pattern is not currently used).
- Drawer/sidebar entry should mirror existing navigation widget integration (existing screens typically expose `AppDrawer`; add semantic mappings there in impl).

### B3) List screen parallel + expected shape
- Existing jobs/queue use list/card style (not DataTable), so DataTable for mappings is a new pattern but acceptable under lock.
- Implement as feature folder with screen + providers + repository analogous to jobs feature structure.
- Filter strategy can mirror jobs provider-driven fetch, with debounce in UI.

### B4) Form screen + submit/error flow
- Form should combine create/edit and include hidden version state.
- Backend error rendering should use centralized error-code mapping helper (new semantic mapping codes must be added to Dart mapper + ARB).
- 409 conflict UX should be explicit modal/reload flow (as locked).

### B5) Cube metadata autocomplete
- Network client already injects `X-API-KEY`; new cube-metadata endpoint can be called with same `Dio` stack.
- `404 => null cache entry` maps cleanly to AsyncValue nullable provider + non-blocking badge.

### B6) `dimension_filters` widget
- No existing reusable widget found for this exact key/value semantic mapping editor.
- Should be introduced as feature-local widget/model with add/remove rows and row-level error state.
- Reordering is out-of-scope (track as UX debt).

### B7) Error rendering integration
- Admin Flutter currently has `mapBackendErrorCode()` with limited switch cases unrelated to semantic mapping.
- Must extend with semantic mapping + version/bulk codes and corresponding l10n keys.
- This is necessary for DEBT-030 parity with frontend-public TS side.

### B8) Riverpod state shape
- Existing pattern in jobs: repository provider + filter state provider + future provider.
- Proposed semantic mappings providers (list/detail/form/cubeMetadata) align with current architecture and can be added without routing paradigm changes.

---

## C) Test plan inventory (implementation target)
- Backend API tests (~9 endpoint-level cases listed in prompt).
- Backend service tests (~7 including bulk path and version conflict).
- Seed CLI tests update to bulk default path + no-partial-persist assertions.
- Flutter widget/provider tests (~8) for table/filter/nav/form/error/modal/autocomplete provider behavior.

---

## D) Docs touch list for implementation PR
- `docs/architecture/BACKEND_API_INVENTORY.md` (5 new endpoints).
- `docs/modules/semantic_mappings.md` (API surface + atomicity section update).
- `docs/architecture/FLUTTER_ADMIN_MAP.md` (new route/screen/providers).
- `docs/architecture/ARCHITECTURE_INVARIANTS.md` only if any invariant-convention decision changes.
- `_DRIFT_DETECTION_TEMPLATE.md` review as part of impl.

---

## E) DEBT proposals
- Repo DEBT max from grep currently ends at `DEBT-052`.
- Proposed new debts (next IDs in impl):
  1. cache-autocomplete read endpoint non-priming UX trade-off.
  2. concurrency convention divergence (If-Match/ETag vs body version) if retained.
  3. no row reorder in dimension_filters editor.
- Use 9-field schema exactly as requested when adding to `DEBT.md` during implementation.

---

## F) Founder open questions (must decide before implementation)
1. **Concurrency convention divergence:** keep locked body `if_match_version` + `409`, or align to existing publications `If-Match` + `ETag` + `412`?
2. **Autocomplete endpoint behavior:** `GET /admin/cube-metadata/{cube_id}` read-only 404 fallback, or auto-prime cache on GET?
3. **Exception class design:** approve adding `VersionConflictError(MetadataValidationError)`?
4. **i18n additions:** approve `errors.backend.version_conflict` EN/RU copy for both frontend-public and Flutter admin localization.
5. **Bulk HTTP endpoint now vs later:** ship seed-CLI-only in 3.1b (recommended) or include admin bulk endpoint now?
6. **Bulk cache miss semantics:** should any `CubeNotInCacheError` fail whole batch (recommended) or allow partial persist?
7. **dimension_filters reorder:** defer as debt or add now?
8. **404 fallback copy:** confirm message text for uncached metadata fallback.
9. **Additional DEBT entries:** confirm whether to add only the three above or expand.

---

## Evidence appendix (commands run)
- `git status --short && git remote -v`
- `find backend/src/api/routers -maxdepth 1 -type f | sort`
- `grep -rn "X-API-KEY\|verify_admin\|admin_api_key" backend/src/api/`
- `grep -rn "if_match_version\|If-Match\|ETag" backend/src/api/`
- `nl -ba backend/src/api/routers/admin_publications.py | sed -n '1,260p'`
- `nl -ba backend/src/repositories/semantic_mapping_repository.py | sed -n '1,260p'`
- `nl -ba backend/src/services/semantic_mappings/service.py | head -320`
- `nl -ba backend/src/services/semantic_mappings/exceptions.py | head -260`
- `nl -ba frontend/lib/main.dart | head -220`
- `nl -ba frontend/lib/core/routing/app_router.dart | head -260`
- `nl -ba frontend/lib/core/network/dio_client.dart | head -220`
- `nl -ba frontend/lib/core/network/auth_interceptor.dart | head -160`
- `nl -ba frontend/lib/l10n/backend_errors.dart | head -220`
- `nl -ba frontend-public/src/lib/api/errorCodes.ts | head -260`
- `grep -oE "DEBT-[0-9]+" DEBT.md | sort -u | tail -5`
### §A1. Existing admin endpoint patterns (auth + structure)

- Admin routers are split one file per resource under `backend/src/api/routers/` (e.g., `admin_publications.py`, `admin_jobs.py`, `admin_cubes.py`). No dedicated `backend/src/api/admin/` directory exists. Pattern is resource routers imported in `main.py`.  
- Auth is middleware-driven, not per-endpoint `Depends(verify_admin_api_key)`: `AuthMiddleware` guards `"/api/v1/admin/*"` and enforces `X-API-KEY`.  
- Middleware bypasses `/docs`, `/openapi.json`, `/redoc`, and `/api/v1/public/*`; admin routes require API key and are rate-limited (10 req/min by key prefix).  
- Common response behavior is mixed today: publications has structured nested envelopes for key error paths (`PATCH` validation + precondition), while global `SummaVisionError` handler still returns a flat envelope (`error_code`, `message`, `detail`).

Parallel endpoint pattern for implementation reference:
- `PATCH /api/v1/admin/publications/{publication_id}` in `admin_publications.py` shows canonical admin router decorator style, response_model usage, dependency injection (`repo`, `audit`), and explicit conflict/precondition handling.

### §A2. New endpoints — contract proposal against current conventions

#### A2.1 POST `/api/v1/admin/semantic-mappings/upsert`

Proposed request model (locked): includes `if_match_version: int | None` body field.

Status mapping proposal aligned to existing structured envelope contract:
- `201` created when `(cube_id, semantic_key)` new
- `200` when existing updated/no-op
- `400` metadata validation failures (`CUBE_NOT_IN_CACHE`, `DIMENSION_NOT_FOUND`, `MEMBER_NOT_FOUND`, `CUBE_PRODUCT_MISMATCH`, generic `METADATA_VALIDATION_FAILED`)
- `409` version mismatch (`VERSION_CONFLICT`) if `if_match_version` present and stale
- `401` missing/invalid API key from middleware

Mapping from existing service exceptions:
- `CubeNotInCacheError` → `400 CUBE_NOT_IN_CACHE`
- `DimensionMismatchError` → `400 DIMENSION_NOT_FOUND`
- `MemberMismatchError` → `400 MEMBER_NOT_FOUND`
- `MetadataValidationError` → `400` with carried `error_code`

Envelope detail recommendation: include both validation `errors` and `resolved_filters` under `detail.details` for field-level Flutter rendering.

#### A2.2 GET `/api/v1/admin/semantic-mappings`

- Query params proposed: `cube_id`, `semantic_key`, `is_active`, `limit`, `offset`.
- Pagination convention in existing admin APIs is inconsistent (`jobs` currently supports `limit` only; publications supports `limit+offset`). For semantic mappings, mirror publications-style `limit+offset` + total response wrapper for operator table UX.

#### A2.3 GET `/api/v1/admin/semantic-mappings/{id}`

- `200` row response, `404` not found.

#### A2.4 DELETE `/api/v1/admin/semantic-mappings/{id}`

- Soft delete only (`is_active=false`), return row.
- Idempotent delete: if already inactive, return current row `200`.

#### A2.5 GET `/api/v1/admin/cube-metadata/{cube_id}`

- `200` cached entry, `404` when absent.
- Recon recommendation: use read-only cache lookup (`get_cached`) and do **not** auto-prime on this read endpoint.

Open question flagged (founder): should autocomplete read endpoint auto-prime (side effect) or remain read-only + fallback.

### §A3. Service-layer extensions needed

Current state:
- `SemanticMappingService` currently exposes only `upsert_validated(...)` and does not accept any concurrency version parameter.

Needed additions:
- Extend `upsert_validated(..., if_match_version: int | None = None)` with version check on existing row.
- Add methods for list/get/delete orchestration:
  - `list_mappings(...) -> tuple[list[SemanticMapping], int]`
  - `get_mapping(id: int) -> SemanticMapping`
  - `soft_delete(id: int) -> SemanticMapping`
- Exception additions:
  - `MappingNotFoundError` for 404 mapping miss
  - `VersionConflictError` (recommended subclass of `MetadataValidationError` or sibling API error class; decision required)

### §A4. Repository extensions

Current `SemanticMappingRepository` already has:
- `get_by_id`, `get_by_key`, `create`, `upsert_by_key`, `update`, and `get_active_for_cube`.

Missing for 3.1b endpoint surface:
- list with filters + pagination + total
- dedicated soft-delete helper (or service-level reuse of `update` with `is_active=false`)

Given current style, adding explicit repo methods is cleanest:
- `list(...) -> tuple[list[SemanticMapping], int]`
- `soft_delete(id) -> SemanticMapping | None`

### §A5. Auth integration

- All new endpoints should rely on existing `AuthMiddleware` path-based admin guard; no per-route dependency needed for parity with existing admin routers.
- Existing tests likely pass/omit `X-API-KEY` depending on test app setup; for endpoint tests, include explicit no-header `401` case plus success path with header fixture.

### §A6. OpenAPI/docs integration

- `/docs`/OpenAPI are enabled only when environment is non-production (`main.py` gates `docs_url`, `redoc_url`, `openapi_url` by `settings.environment`).
- New endpoints will appear automatically once router is included.
- Manual doc updates required in architecture inventories listed in §D.

### §A7. Optimistic concurrency wiring

Observed current convention:
- Publications concurrency uses header-based `If-Match` + ETag with `412 PRECONDITION_FAILED` (`PublicationPreconditionFailedError`).
- No existing `if_match_version` body convention found in backend API/router/service/repository scan.

Ambiguity to surface (high-priority founder decision):
- Lock requests `if_match_version` in body + `409 VERSION_CONFLICT`.
- Existing mature publication path uses `If-Match` header + `412 PRECONDITION_FAILED`.
- Recommend explicit founder confirmation on intentional divergence vs alignment.

### §A8. Error envelope + DEBT-030 integration

- Public frontend TS error code dictionary already includes semantic-mapping validation codes from 3.1ab; `VERSION_CONFLICT` is not present and must be added if 3.1b emits it.
- Flutter admin has separate backend error mapper (`frontend/lib/l10n/backend_errors.dart`) currently only maps graphics/job codes, so semantic mapping codes will need Dart-side mapping + ARB keys in both locales.

---

## Part B — Flutter admin UI

### §B1. Existing admin app structure

- Entry: `frontend/lib/main.dart` with Riverpod `ProviderScope`, bootstrap provider, `MaterialApp.router`, and generated l10n delegates.
- Routing: `frontend/lib/core/routing/app_router.dart` with flat `GoRoute` list (no ShellRoute), current top-level routes include `/queue`, `/jobs`, `/exceptions`, `/kpi`, cubes/editor/preview flows.
- Navigation chrome: `AppDrawer` with nav items, including existing Exceptions screen entry.
- API client: shared Dio in `dio_client.dart`; `AuthInterceptor` injects `X-API-KEY` into all real requests.

Parallel feature to mirror:
- Exceptions module is closest list/filter/operator action workflow (`features/exceptions/*`) with Riverpod filter provider and list provider.

Error handling baseline:
- Flutter uses lightweight code->message mapper in `l10n/backend_errors.dart` for known codes.
- No Dart equivalent of TS `extractBackendErrorPayload` exists yet; semantic-mapping form will likely need one to parse `detail.error_code/message/details` envelopes consistently.

### §B2. Navigation entry (inspection-first)

- Existing router is flat top-level route entries; no nested route trees.
- Existing drawer nav is also top-level tiles.

Recommendation for 3.1b parity:
- Add top-level route `/semantic-mappings` (or `/admin/semantic-mappings`; current app uses short paths like `/jobs`, `/exceptions`).
- Add nav tile in `AppDrawer` parallel to jobs/exceptions.
- For create/edit, existing app pattern tends to use separate screens via direct routes rather than nested child routes; either flat sibling routes (`/semantic-mappings`, `/semantic-mappings/new`, `/semantic-mappings/:id`) or local modal navigation, but flat GoRoute entries keep parity.

### §B3. List screen (lock 6)

- Existing admin list screens use `ListView` + cards, not `DataTable`; introducing `DataTable` is acceptable but will be a new pattern.
- Recommended API-backed state shape:
  - filter provider object (`cubeId`, `semanticKey`, `isActive`, `limit`, `offset`)
  - list provider family fetches paged result
- Include `New mapping` CTA in app bar actions/header row.

### §B4. Form screen (lock 7)

- New create/edit unified form is greenfield in this app.
- Input validation can follow existing Form/TextFormField patterns used in graphics/editor.
- Hidden `version` field should live in form state model; passed as `if_match_version` on submit.

### §B5. Cube metadata autocomplete (lock 8)

- No existing cube-metadata endpoint client in Flutter; add provider family for lookup by cube_id.
- On 404, render non-blocking info copy and keep free-text fields enabled.
- Hybrid preflight check should be local-only when cache present, then always server-submit for authoritative validation.

### §B6. `dimension_filters` editor widget

- New reusable widget required; no similar key-value grid found in current Flutter admin features.
- Maintain row-level validation state to map backend member/dimension errors back to exact row.
- Reordering can stay out of scope (track as low UX debt).

### §B7. Error rendering integration

- Add semantic-mapping + version conflict codes to Flutter-side backend mapper and l10n ARB keys.
- Current generated localization setup supports EN+RU; add keys under existing naming conventions (likely `error*` or `errorsBackend*` style in Dart-gen naming).
- Prefer backend envelope parsing utility in Dart to centralize logic (nested `detail.error_code`).

### §B8. Riverpod shape

Recommended providers:
- `semanticMappingsFilterProvider` (StateProvider)
- `semanticMappingsListProvider(filter)` (FutureProvider/AsyncNotifier)
- `semanticMappingProvider(id)`
- `cubeMetadataProvider(cubeId)`
- form state notifier/provider for mutable draft + backend field errors

Parallel: exceptions/jobs providers demonstrate filter + list invalidation flow, while editor/graphics provide form-state workflows.

---

## §C. Test plan inventory

### Backend (~10)

- New API tests for upsert/list/get/delete/cube-metadata with auth + error envelopes.
- Service tests for list/get/delete plus version conflict behavior.
- Ensure JSON error responses from new handler paths are `jsonable_encoder`-wrapped where needed.

### Flutter (~8)

- Widget tests for table/list rendering, filters, navigation to form, submit happy path.
- Envelope-to-inline error mapping tests (`MEMBER_NOT_FOUND`, `DIMENSION_NOT_FOUND`, `CUBE_NOT_IN_CACHE`, `CUBE_PRODUCT_MISMATCH`, `VERSION_CONFLICT`).
- Provider tests for cube metadata 404 null fallback and paginated list handling.

---

## §D. Docs touch list for implementation PR

- `docs/architecture/BACKEND_API_INVENTORY.md` — add 5 endpoints.
- `docs/modules/semantic_mappings.md` — add API surface + service method extensions.
- `docs/architecture/FLUTTER_ADMIN_MAP.md` — add route/screen/providers for semantic mappings admin.
- `docs/architecture/ARCHITECTURE_INVARIANTS.md` — verify no invariant changes; only update if concurrency contract changes.
- `_DRIFT_DETECTION_TEMPLATE.md` — evaluate in implementation phase.

---

## §E. DEBT proposals

### E1. Current max DEBT ID (repo grep)

Observed max IDs in `DEBT.md`: `DEBT-048`..`DEBT-052` (latest `DEBT-052`).

### E2. Proposed new entries (next IDs)

1. **DEBT-053 (proposed)** — cube metadata autocomplete endpoint stays read-only and does not auto-prime cache.
2. **DEBT-054 (conditional, if divergence approved)** — concurrency contract diverges from publications (`if_match_version` body + 409 vs ETag/If-Match + 412).
3. **DEBT-055 (proposed)** — `dimension_filters` widget has no row reorder UX in 3.1b.

### E3. 9-field schema template for each entry

Use:
`Source / Added / Severity / Category / Status / Description / Impact / Resolution / Target`

---

## §F. Open questions for founder approval

1. **Concurrency convention divergence (high priority).**  
   Evidence: publications currently use `If-Match`/ETag and `412 PRECONDITION_FAILED`; lock asks for body `if_match_version` + `409 VERSION_CONFLICT`.  
   Options: (A) keep lock divergence for semantic mappings; (B) align to publications header pattern.

2. **`GET /admin/cube-metadata/:cube_id` auto-prime or read-only?**  
   Recommendation: read-only (`404` fallback for form autocomplete), keep auto-prime on save path only.

3. **New `VersionConflictError` class shape.**  
   Should it subclass `MetadataValidationError` (uniform contract) or be separate API-layer exception.

4. **i18n additions for `VERSION_CONFLICT`.**  
   Confirm EN+RU copy and key naming in both frontend-public and Flutter ARB ecosystems.

5. **dimension_filters reorder UX.**  
   Confirm defer-to-debt posture for 3.1b.

6. **404 fallback copy text for missing cube metadata.**  
   Confirm operator-facing message tone/content.

7. **Any extra DEBT entries beyond 053–055?**

---

## Evidence index (commands executed)

- `find backend/src/api -maxdepth 3 -type d | sort`
- `find backend/src/api -maxdepth 3 -type f | sort`
- `grep -rn "X-API-KEY\|verify_admin\|admin_api_key" backend/src/api/ backend/src/core`
- `grep -rn "if_match_version\|If-Match\|ETag" backend/src/api/ backend/src/services/ backend/src/repositories/`
- `grep -oE "DEBT-[0-9]+" DEBT.md | sort -u | tail -5`
- plus direct file reads for backend router/middleware/service/repo and Flutter router/network/providers/l10n inventory.
