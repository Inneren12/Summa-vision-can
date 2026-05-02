# Phase 3.1b Recon — Admin CRUD endpoints + Flutter admin UI

Date: 2026-05-02  
Branch target: `codex/phase-3-1b-recon`  
Artifact: `docs/recon/phase-3-1b.md`

## Scope and constraints observed

- Recon-only pass completed with read-only inspection of backend + Flutter admin surfaces; no source edits outside this file.
- Note: repo layout uses `frontend/` (Flutter admin app), not `admin-flutter/`.

---

## Part A — Backend

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
