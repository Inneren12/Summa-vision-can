# Recon Delta 01 — Slice 3a Discovery Endpoint Reality

**Status:** APPROVED (founder-acked 2026-05-05)
**Triggered by:** HALT-1 preflight inventory (`/mnt/user-data/outputs/slice-3a-preflight.md` execution, 2026-05-05)
**Scope:** Phase 3.1d Slice 3a impl shape — does NOT modify Slice 2 acceptance, does NOT modify milestone wrapper close criteria.

---

## Discovery

HALT-1 preflight (per milestone wrapper §HALTs) inventoried backend discovery surface. Findings:

1. **Cube list endpoint** — only `GET /api/v1/admin/cubes/search` exists (`backend/src/api/routers/admin_cubes.py:33`). No list-all endpoint. Returns `CubeSearchResult` with `product_id`, `cube_id_statcan`, `title_en`, `subject_en`, `frequency`. Auth via `X-API-KEY`.

2. **Semantic_key list endpoint** — `GET /api/v1/admin/semantic-mappings` exists (`backend/src/api/routers/admin_semantic_mappings.py:247`). Optional `cube_id` query param enables cube-scoped filtering. Returns paginated `SemanticMappingListResponse` with `items[].semantic_key`, `cube_id`, `label`, `description`, etc. **No precomputed-delta marker** (no `is_delta`, `kind`, or equivalent field).

3. **Dimension/member metadata** — `GET /api/v1/admin/cube-metadata/{cube_id}` exists (`backend/src/api/routers/admin_cube_metadata.py:56`). Returns single `CubeMetadataCacheEntryResponse` with `dimensions: dict` containing dimensions + members in one shape. **One-shot retrieval** — no separate dim-list / member-list calls needed. No standalone `/dimensions` or `/members` routes.

4. **Frontend admin client** — proxy pattern already established (`frontend-public/src/lib/api/admin.ts` calls same-origin proxy `/api/admin/publications/*`; server-side `admin-server.ts` reads `process.env.ADMIN_API_KEY` and attaches `X-API-KEY` header to backend). No `NEXT_PUBLIC_*` exposure. **HALT-2 status: SAFE.**

5. **delta_badge precomputed-delta data** — backend models support delta-shaped metric vocabulary via `SupportedMetric = Literal["current_value", "year_over_year_change", "previous_period_change"]`, but no precomputed-delta semantic_keys are populated in current cube data (sampled migrations + tests). Schema-supports + no-data state.

6. **`BACKEND_API_INVENTORY.md` documentation gap** — actual file lives at `docs/architecture/BACKEND_API_INVENTORY.md`, NOT repo root as referenced in handoff `/mnt/project/` listing and milestone wrapper. Discovery endpoints (admin_cubes, admin_cube_metadata) are not enumerated in the inventory's endpoint table even when read at the correct path.

7. **Existing frontend discovery UI** — none. No reusable cube/semantic/dim picker patterns in `frontend-public/src/`.

## Contradiction

Milestone wrapper `docs/recon/phase-3-1d-milestone-wrapper.md` HALT-1 contemplates two outcomes when discovery endpoints are absent:

- (a) backend dispatch before Slice 3a, OR
- (b) Recon Delta narrowing scope to "edit only existing/imported bindings (no free picker UI)"

The actual reality is a **third outcome the wrapper did not enumerate:** endpoints exist with shapes that diverge from the picker UX implied by the wrapper. Specifically:

- **Cube discovery is search-only**, not list-all. The wrapper's HALT-1 phrasing ("Cube list endpoint exists and is callable") implies list-all semantics; reality is search.
- **Dim/member metadata is unified into one cube-metadata call**, not separate `/dimensions` and `/members` endpoints. The wrapper said "Dimension/member metadata endpoint or metadata source exists" — `or metadata source` covers this, but the picker design implications need explicit lock.
- **Semantic mappings has no precomputed-delta marker**, so `delta_badge` cannot use a backend-provided filter to populate its dropdown.

Wrapper's "(b) narrow to edit-imported-only" fallback is **too restrictive** — actual endpoint coverage is enough for a working picker, just with different UX shape (search-as-you-type cube selector instead of paginated list).

## Impacted slices

- **Slice 3a (PR-04)** — picker UX shape, discovery client signatures, delta_badge handling. Direct.
- **Slice 3b (PR-05)** — resolve preview proxy. Indirect — confirms HALT-2 SAFE status (already known); preview proxy reuses the same `admin-server.ts` proxy pattern. No design change.
- **Slice 4a (PR-06)** — single-value walker. No impact (walker emits `bound_blocks` from already-validated `binding`; doesn't depend on discovery shape).
- **Milestone close criteria** — criterion #3 ("Binding editor can create/edit valid `single` bindings for `hero_stat` (and `delta_badge` if precomputed delta keys available)") still satisfiable. `delta_badge` clause already conditional; this delta makes it explicit by locking DISABLED state.

## Minimal decisions needed

Founder-approved 2026-05-05:

### D-01: Cube selector UX = search-as-you-type
v1 picker uses `GET /api/v1/admin/cubes/search` with debounced query input. NO requirement for list-all backend endpoint before Slice 3a ships. Backend-list addition tracked as DEBT-079 (new — see below) for post-v1 polish.

### D-02: Dim/member retrieval = single cube-metadata call
v1 picker calls `GET /api/v1/admin/cube-metadata/{cube_id}` once when cube_id changes; parses `dimensions` dict for both dim list and members. NO separate dim-list or member-list calls. NO 1+N pagination loop.

### D-03: delta_badge in v1 picker = DISABLED
- Block remains in editor catalog (visible to operator).
- `acceptsBinding` metadata in registry includes `delta_badge`.
- Picker UI opens for `delta_badge` and shows the standard `single`-binding form.
- Dropdown of valid `semantic_key` options uses **no delta-filter** (no backend marker exists to filter on).
- Result in current data state: dropdown returns 0 valid options OR returns all single-value semantic_keys but operator must self-select a delta-shaped key.
- **Critical guard:** the resolve preview (Slice 3b) and walker (Slice 4a) MUST NOT introduce client-side delta computation regardless of which semantic_key the operator binds. Locked per milestone wrapper "Delta badge rule" — unchanged. `delta_badge` rendering uses the bound semantic_key value verbatim.
- When backend adds an `is_delta` marker (or equivalent) on `SemanticMappingListItem`, picker filters dropdown by it. That is post-v1 polish; tracked as DEBT-080.

### D-04: BACKEND_API_INVENTORY.md path correction
Actual path is `docs/architecture/BACKEND_API_INVENTORY.md`. Memory and future prompts use this path. Inventory itself does not enumerate discovery endpoints (admin_cubes, admin_cube_metadata, admin_semantic_mappings list section); doc-completion is tracked as DEBT-081.

### D-05: HALT-2 confirmed SAFE — reuse existing proxy pattern
Slice 3a discovery clients follow the established proxy pattern: client-side wrapper in `frontend-public/src/lib/api/admin.ts` (or new `admin-discovery.ts`) hits same-origin Next.js Route Handler at `/api/admin/discovery/*`; route handler uses `admin-server.ts` to attach `ADMIN_API_KEY` and proxy to backend. NO `NEXT_PUBLIC_*` env vars introduced.

## Recommended patch to milestone wrapper

Wrapper text remains as-is — this delta becomes the canonical reference instead. Specifically:

- HALT-1 wording ("Cube list endpoint exists") stays. Future readers cross-reference this delta for the search-vs-list nuance.
- HALT-2 wording stays.
- "Delta badge rule (locked)" section stays unchanged. D-03 above is implementation specificity, not new policy.
- Close criterion #3 stays as-is — `delta_badge` clause already conditional.

No wrapper text edit needed.

## New DEBT entries (for founder to add to DEBT.md at convenience)

| ID | Description | Trigger |
|---|---|---|
| DEBT-079 | Backend cube list-all endpoint (currently search-only); enables non-search-driven picker UX | Phase 3.1e or post-v1 polish |
| DEBT-080 | `is_delta` (or equivalent) marker on `SemanticMappingListItem` to enable picker filtering for `delta_badge` | When precomputed-delta semantic_keys are populated in cube data |
| DEBT-081 | `BACKEND_API_INVENTORY.md` discovery section completion (admin_cubes, admin_cube_metadata, semantic-mappings list) | Doc cleanup polish |

## Acceptance

This delta is locked. Slice 3a impl prompt references it via the Recon discipline block. No further recon work on Slice 3a discovery shape.

---

**End of Recon Delta 01.**
