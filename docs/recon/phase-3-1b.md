# Phase 3.1b Recon — Admin CRUD endpoints + Flutter admin UI

## Scope + method
- Recon-only read pass performed against backend routers/services/repositories, frontend router/network/error/i18n structure, and architecture docs.
- No source edits except this recon artifact.

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
