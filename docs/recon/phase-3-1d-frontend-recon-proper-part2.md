# Phase 3.1d Frontend Recon-Proper Part 2 — UI Surface (§D–§F)

## §D — Compare API client + TypeScript types

### §D.1 Existing `admin.ts` structure recap
- File: `frontend-public/src/lib/api/admin.ts` currently exports `fetchAdminPublication`, `fetchAdminPublicationList`, `updateAdminPublication`, and `cloneAdminPublication`; there is no `publishAdminPublication` export yet.【F:frontend-public/src/lib/api/admin.ts†L91-L236】
- `BackendApiError` is defined locally with `{ status, code, details }` and is thrown from mutation paths that parse backend envelopes via `extractBackendErrorPayload`.【F:frontend-public/src/lib/api/admin.ts†L58-L75】【F:frontend-public/src/lib/api/admin.ts†L167-L194】
- Error envelope helpers are in `frontend-public/src/lib/api/errorCodes.ts`: `extractBackendErrorPayload` and `getBackendErrorI18nKey` (plus known-code registries).【F:frontend-public/src/lib/api/errorCodes.ts†L17-L153】
- Existing ETag mutation precedent: `updateAdminPublication` applies optional `If-Match` header and returns parsed document + read `ETag` header in `AdminPublicationWithEtag`.【F:frontend-public/src/lib/api/admin.ts†L23-L37】【F:frontend-public/src/lib/api/admin.ts†L150-L197】

### §D.2 New TypeScript types (proposed)
**Placement choice:** keep API-wire shapes inside `frontend-public/src/lib/api/admin.ts` for fetch coupling; keep shared view-model/domain helpers (aggregate severity union including `partial`) in new `frontend-public/src/lib/types/compare.ts`.

#### Backend-verified comparator schema (verbatim shape to mirror)
Backend response model fields are:
- `publication_id`
- `overall_status`
- `overall_severity`
- `compared_at`
- `block_results` (each block has `block_id`, `cube_id`, `semantic_key`, `stale_status`, `stale_reasons`, `severity`, `compared_at`, `snapshot`, `current`, `compare_basis`).【F:backend/src/schemas/staleness.py†L129-L155】

`stale_status` enum values are `fresh | stale | unknown` (no `missing` literal in backend enum); stale reasons include `snapshot_missing` and `compare_failed`.【F:backend/src/schemas/staleness.py†L27-L41】

#### Proposed TS types (verbatim for Part 3 implementation)
```ts
export type StaleStatus = 'fresh' | 'stale' | 'unknown';
export type StaleReason =
  | 'mapping_version_changed'
  | 'source_hash_changed'
  | 'value_changed'
  | 'missing_state_changed'
  | 'cache_row_stale'
  | 'compare_failed'
  | 'snapshot_missing';

export type Severity = 'info' | 'warning' | 'blocking';

export type CompareKind = 'drift_check' | 'snapshot_missing' | 'compare_failed';

export interface SnapshotFingerprint {
  mapping_version: number | null;
  source_hash: string;
  value: string | null;
  missing: boolean;
  is_stale: boolean;
  captured_at: string;
}

export interface ResolveFingerprint {
  mapping_version: number | null;
  source_hash: string;
  value: string | null;
  missing: boolean;
  is_stale: boolean;
  resolved_at: string;
}

export interface DriftCheckBasis {
  compare_kind: 'drift_check';
  matched_fields: string[];
  drift_fields: string[];
}

export interface SnapshotMissingBasis {
  compare_kind: 'snapshot_missing';
  cause: 'no_snapshot_row';
}

export interface CompareFailedBasis {
  compare_kind: 'compare_failed';
  resolve_error: 'MAPPING_NOT_FOUND' | 'RESOLVE_CACHE_MISS' | 'RESOLVE_INVALID_FILTERS' | 'UNEXPECTED';
  details: {
    exception_type: string;
    message: string;
  };
}

export type CompareBasis = DriftCheckBasis | SnapshotMissingBasis | CompareFailedBasis;

export interface BlockComparatorResult {
  block_id: string;
  cube_id: string;
  semantic_key: string;
  stale_status: StaleStatus;
  stale_reasons: StaleReason[];
  severity: Severity;
  compared_at: string;
  snapshot: SnapshotFingerprint | null;
  current: ResolveFingerprint | null;
  compare_basis: CompareBasis;
}

export interface CompareResponse {
  publication_id: number;
  overall_status: StaleStatus;
  overall_severity: Severity;
  compared_at: string;
  block_results: BlockComparatorResult[];
}

export interface BoundBlockReference {
  block_id: string;
  cube_id: string;
  semantic_key: string;
  dims: number[];
  members: number[];
  period?: string | null;
}

export interface PublishPayload {
  bound_blocks?: BoundBlockReference[];
}

export type CompareBadgeSeverity = 'fresh' | 'stale' | 'missing' | 'unknown' | 'partial';
```

#### Binding types reference
Binding union itself remains locked from Part 1 (§B2.3/§B2.4) and should be imported from the Part 3 location chosen there, not redefined here.

### §D.3 New API client functions
Backend routes verified:
- `POST /api/v1/admin/publications/{publication_id}/compare` with `PublicationComparatorResponse` response model, 200/404 documented in route decorator.【F:backend/src/api/routers/admin_publications.py†L613-L655】
- `POST /api/v1/admin/publications/{publication_id}/publish` accepts optional body `PublicationPublishRequest | None` (`bound_blocks` default `[]`), returns `PublicationResponse` (200/404 documented).【F:backend/src/api/routers/admin_publications.py†L536-L606】【F:backend/src/schemas/staleness.py†L173-L183】

Proposed additions in `frontend-public/src/lib/api/admin.ts`:
```ts
export async function comparePublication(
  id: number,
  options?: { signal?: AbortSignal },
): Promise<CompareResponse>;

export async function publishAdminPublication(
  id: number,
  payload: PublishPayload,
  options?: { signal?: AbortSignal; ifMatch?: string },
): Promise<{ etag: string | null; document: AdminPublicationResponse }>;
```

Request/response notes:
- `comparePublication` POSTs with no body (`body: undefined`); the route declares no body parameter, and sending an empty `{}` is unnecessary surface area (CORS preflight, content-type negotiation, future route signature drift). Parse `CompareResponse` from JSON response.
- `publishAdminPublication` should POST JSON body; if no bindings are present send `{}` (or omitted `bound_blocks`), because backend wrapper defaults to empty list and treats `null`/no body/object body as back-compatible empty state.【F:backend/src/api/routers/admin_publications.py†L560-L563】【F:backend/src/schemas/staleness.py†L176-L183】
- ETag handling should mirror `updateAdminPublication`: optional `If-Match` request header + `readEtag(res)` response capture.【F:frontend-public/src/lib/api/admin.ts†L33-L37】【F:frontend-public/src/lib/api/admin.ts†L155-L197】

Resolve preview client reuse check:
- No existing frontend client helper for `/admin/resolve` found under `frontend-public/src/lib`; define `previewBindingResolve(cubeId, semanticKey, params)` in Part 3 and proxy through Next route if required by existing architecture.
- Backend resolver contract is `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}` with query `dim`, `member`, optional `period`.【F:backend/src/api/routers/admin_resolve.py†L113-L137】

### §D.4 Error code mapping
Verified codes from relevant backend/frontend contracts:
- Existing global/local known codes include `PRECONDITION_FAILED`, `PUBLICATION_NOT_FOUND`, `INTERNAL_ERROR` (for resolve generic 500), `MAPPING_NOT_FOUND`, `RESOLVE_INVALID_FILTERS`, `RESOLVE_CACHE_MISS` via resolver detail payloads.【F:frontend-public/src/lib/api/errorCodes.ts†L17-L35】【F:backend/src/api/routers/admin_resolve.py†L138-L192】
- Comparator partial failures are encoded in per-block `stale_reasons: ['compare_failed']` plus `compare_basis.compare_kind === 'compare_failed'`; there is **no top-level backend error code `COMPARE_FAILED`** in comparator response schema.【F:backend/src/schemas/staleness.py†L33-L41】【F:backend/src/schemas/staleness.py†L107-L155】

Mapping table (proposed i18n keys for Part 3):
- `PRECONDITION_FAILED` → `publication.errors.precondition_failed`
- `PUBLICATION_NOT_FOUND` → `publication.errors.not_found`
- `MAPPING_NOT_FOUND` → `publication.binding.resolve.mapping_not_found`
- `RESOLVE_INVALID_FILTERS` → `publication.binding.resolve.invalid_filters`
- `RESOLVE_CACHE_MISS` → `publication.binding.resolve.cache_miss`
- `INTERNAL_ERROR` → `publication.errors.internal_error`
- comparator partial condition (not error_code): `compare_failed` reason → `publication.compare.partial`

## §E — Compare badge UI design

### §E.1 Surface inventory
1. **Editor top toolbar (`TopBar`)**: right-aligned action row already contains clone/export buttons and status glyphs; compare button + badge can slot between clone and export without layout model changes (`display:flex; gap:5px`).【F:frontend-public/src/components/editor/components/TopBar.tsx†L127-L187】
2. **Editor page shell (`index.tsx`)**: `TopBar` is mounted once and is the right place for compare state wiring props/callbacks passed from editor container state machine.【F:frontend-public/src/components/editor/index.tsx†L1325-L1357】
3. **Publication list page**: cards currently show only publication `status` and `virality_score`; compare summary badge can fit in card meta row (line 30 block).【F:frontend-public/src/app/admin/page.tsx†L23-L39】
4. **Per-block visual surface**: canvas renderer uses block-type renderers in `renderer/blocks.ts`; no current staleness hook exists, so per-block tint must be injected at composition/overlay stage in Part 3 (likely wrapper around render pass, not per-renderer duplication).【F:frontend-public/src/components/editor/renderer/blocks.ts†L22-L134】

Reusable component check:
- Existing reusable badge: `StatusBadge` (workflow-oriented) and QA badge pattern in `ExportPresetsSection` are available as style references.【F:frontend-public/src/components/editor/components/StatusBadge.tsx†L7-L55】【F:frontend-public/src/components/editor/components/ExportPresetsSection.tsx†L170-L219】
- Inspector already uses inline “chip” styling for block status tags, useful for compare badge style parity.【F:frontend-public/src/components/editor/components/Inspector.tsx†L99-L103】

### §E.2 Severity → visual mapping (Q4 icon + label + color)
Icon library verification: no lucide import in current editor surfaces; existing status chips primarily use text/emoji glyphs. Recommend adding a lightweight icon set in Part 3 or text-icon fallbacks.

**Token verification constraint:** `docs/DESIGN_SYSTEM_v3.2.md` does not define `--color-success-fg` style names; it defines raw semantic tokens like `--data-positive`, `--data-warning`, `--destructive`, `--text-secondary`, `--bg-surface-active`. Therefore mapping below uses verified tokens only.【F:docs/DESIGN_SYSTEM_v3.2.md†L726-L756】

| Severity | Icon | EN | RU | FG token | BG token |
|---|---|---|---|---|---|
| `fresh` | check-circle | Fresh | Свежие | `--data-positive` | `--accent-muted` |
| `stale` | alert-triangle | Stale | Устарели | `--data-warning` | `--bg-surface-active` |
| `missing` | x-circle | Missing | Отсутствуют | `--destructive` | `--bg-surface-active` |
| `unknown` | help-circle | Unknown | Не проверено | `--text-secondary` | `--bg-surface` |
| `partial` | clock-alert | Partial | Частично | `--data-warning` | `--bg-surface-active` |

### §E.3 Manual trigger UX (Q2)
State UX:
- Idle: compare button active, badge shows “Not compared”.
- Loading: disable button and replace text with “Comparing…”.
- Success full: badge from aggregate function + relative time string.
- Success partial: badge forced to `partial`, adjacent retry action.
- Error: toast/notice, button re-enabled.

Proposed state machine:
```ts
type CompareState =
  | { kind: 'idle' }
  | { kind: 'loading'; startedAt: number }
  | { kind: 'success'; result: CompareResponse; comparedAt: string; aggregate: CompareBadgeSeverity }
  | { kind: 'partial'; result: CompareResponse; comparedAt: string; failedBlockIds: string[] }
  | { kind: 'error'; error: BackendApiError | Error };
```

### §E.4 Aggregate severity rule
Use backend payload-first precedence:
1. If any block has `stale_reasons` including `compare_failed` → `partial` (Q8-style UI state).
2. Else if any block has `stale_reasons` including `snapshot_missing` → `missing` (UI semantic bucket).
3. Else reduce by `overall_status` for top badge; keep per-block from each `stale_status`.

This aligns with backend not having literal `missing` stale_status while still supporting founder’s desired missing UI bucket via stale reasons.【F:backend/src/schemas/staleness.py†L27-L41】【F:backend/src/schemas/staleness.py†L149-L155】

### §E.5 Per-block decision (Q7)

**Decision: aggregate only in v1.** No per-block tint, no inline annotations, no drilldown in Phase 3.1d v1.

Rationale: Q7 founder decision = aggregate-only v1. A per-block tint, even subtle and non-interactive, is a per-block visual surface that contradicts the aggregate-only constraint and expands v1 with renderer wrapper, block status mapping, canvas overlay logic, edge cases for selected/locked/hidden states, and visual regression tests.

**Deferred to post-v1:**
- Subtle per-block tint wrapper → Phase 3.1e or UX polish milestone
- Point/block drilldown → after backend point-level response shape stabilizes

### §E.6 Partial retry CTA (Q8)
- If partial detected, show “Retry failed blocks” button near compare badge.
- Retry still calls full `comparePublication` endpoint (no per-block API exists currently).
- Repeat partial keeps warning state + non-blocking toast.

### §E.7 Pre-compare state
Default mount state: unknown/not compared chip in top bar and optional muted status on list cards.

## §F — Binding editor UI design

### §F.1 Inspector panel surface
`Inspector` component is the selected-block prop surface, already handling block controls and specialized data editors; this is the insertion point for a new “Data binding” collapsible section after standard controls and before meta footer.【F:frontend-public/src/components/editor/components/Inspector.tsx†L121-L153】

Visibility policy choice:
- Show section for all 7 bindable types; enable edit only for `hero_stat` + `delta_badge` in v1.
- For deferred 3.1e types, show read-only notice: “Multi-value bindings available in Phase 3.1e.”

### §F.2 Empty state
When `block.binding` absent:
- Title: Data binding
- Body: static explanatory text
- CTA button: Add binding
- Inline expansion (not modal) to match existing inspector edit rhythm and reduce context switching.

### §F.3.0 Preflight Gate — Binding discovery endpoints

**This is a HALT condition for Slice 3a, NOT a routine debt.** Without discovery endpoints, the picker chain cannot be implemented at all.

Before Slice 3a implementation can begin, ALL of the following must be verified to exist on the backend:
1. Endpoint listing all available cubes (e.g. `GET /admin/cubes`)
2. Endpoint listing semantic keys / mappings per cube (e.g. `GET /admin/cubes/{cube_id}/semantic-keys` or equivalent)
3. Endpoint or metadata source returning dimensions and members for a given semantic key
4. Auth path supports browser→Next-route-handler proxy (server-only admin key), not browser-direct admin secret

If any endpoint is absent:
- **STOP frontend Slice 3a implementation.**
- File a backend implementation slice as Phase 3.1d prerequisite (or document as Phase 3.1e dependency if scope expansion preferred).
- Resume Slice 3a only after backend endpoints land.

If all endpoints are present:
- Add `listCubes`, `listSemanticKeys`, `listSemanticKeyDimensions` (or equivalent) to `frontend-public/src/lib/api/admin.ts` as part of Slice 3a.
- Wire pickers to these clients.

The verification gate is run by the founder/agent driving Slice 3a; outcome is recorded in the Slice 3a kickoff prompt as a pre-implementation gate result.

### §F.3 Picker chain (v1 single-value)
1. **Cube picker** (`cube_id`): currently no confirmed frontend client call under `lib/api/admin.ts`; Part 3 should add list-cubes admin client if backend endpoint exists.
2. **Semantic key picker** (`semantic_key` scoped by cube): no confirmed frontend client yet; Part 3 to add.
3. **Dimension/member filters**: editor model stores `Record<string,string>`; publish adapter converts to numeric `dims[]/members[]` for `BoundBlockReference`.
4. **Period picker**: explicit period dropdown/text (avoid symbolic “latest” unless resolver semantics are explicitly documented).
5. **Formatter picker** (block-type dependent):
   - `hero_stat`: `passthrough | percent | currency_cad`
   - `delta_badge`: `delta_bps | delta_percent | bps | percent`

Formatter enum (v1): `passthrough`, `percent`, `bps`, `delta_bps`, `delta_percent`, `currency_cad`.

### §F.4 Resolve preview
Use existing resolver route contract:
- `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}?dim=...&member=...&period=...`.
- Handle backend-documented resolver failures:
  - `MAPPING_NOT_FOUND` (404)
  - `RESOLVE_INVALID_FILTERS` (400)
  - `RESOLVE_CACHE_MISS` (404)
  - `INTERNAL_ERROR` (500).【F:backend/src/api/routers/admin_resolve.py†L138-L192】

State machine:
```ts
type ResolvePreviewState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; value: string | null; resolvedAt: string; mappingVersion: number | null }
  | { kind: 'error'; error: BackendApiError | Error }
  | { kind: 'stale_local' };
```

### §F.5 Modify/remove flow
- Existing binding summary chips (cube/key/period).
- Edit opens pre-filled picker chain.
- Remove binding confirmation sets `binding` undefined and keeps static prop rendering.

### §F.6 Validation + sanitization integration
`validateImportStrict` pipeline in `guards.ts` currently validates canonical document shape and block props. Part 3 extends block validation to include optional top-level `binding` with kind-discriminated schema guard.

**Invalid binding policy (explicit, NOT silent-drop):**

| Scenario | Behavior |
|---|---|
| External import (e.g. paste from foreign doc, JSON import) | Strip invalid binding, emit diagnostic warning to console + import warnings collection. Document loads without binding. |
| Internal saved-doc round-trip (autosave reload) | Test must FAIL if a previously valid binding is lost or mutated. Implementation: compare pre-save and post-hydrate binding fields for equality. |
| Publish walker (see §G.6) | Skip invalid binding, surface in confirm modal warnings list. User sees explicit count before publish. |
| Dev mode | Loud warning (console.error) + dev-only banner if invalid binding detected during hydration. |

This avoids the silent-drop failure mode where operator-configured bindings disappear without trace. Round-trip integrity is enforced at the test level.

Integration point: `frontend-public/src/components/editor/registry/guards.ts:187-240` (block loop in shape assertion / hydration path).

### §F.7 Visibility matrix (13 rows)
| Block type | Data binding section visible | Editable in v1 | Reason |
|---|---:|---:|---|
| `hero_stat` | yes | yes | v1 single-value scope |
| `delta_badge` | yes | yes | v1 single-value scope |
| `comparison_kpi` | yes | no | deferred 3.1e multi-value |
| `bar_horizontal` | yes | no | deferred 3.1e multi-value |
| `line_editorial` | yes | no | deferred 3.1e multi-value |
| `table_enriched` | yes | no | deferred 3.1e multi-value |
| `small_multiple` | yes | no | deferred 3.1e multi-value |
| `eyebrow_tag` | no | no | non-bindable editorial |
| `headline_editorial` | no | no | non-bindable editorial |
| `subtitle_descriptor` | no | no | non-bindable editorial |
| `body_annotation` | no | no | non-bindable editorial |
| `source_footer` | no | no | non-bindable editorial |
| `brand_stamp` | no | no | non-bindable editorial |

### §F.8 Visible strings inventory
- Data binding
- Add binding
- Edit binding
- Remove binding
- This block is not bound to live data. Static content from props.
- Cube
- Metric
- Filters
- Period
- Format
- Preview
- Resolved value:
- Formatted value:
- Resolution time:
- Source: {cube_id} / {semantic_key} / {period}
- Loading…
- Retry
- Cube unavailable. Retry.
- Member not found
- Invalid filter set
- Mapping not found
- Cache miss (no row after prime)
- Multi-value bindings available in Phase 3.1e.

## Gate checks
- GATE-A: completed (Part 1 line count + head/tail captured externally for report).
- GATE-B: all repo claims cite file lines.
- GATE-C: backend field names kept exact to schemas/routes; unknown compare top-level partial flag explicitly not invented.
- GATE-D: reusable components searched (`StatusBadge`, inspector chips, QA badge pattern).
- GATE-E: design token mismatch flagged; used verified v3.2 tokens only.
- GATE-F: consistent mapping between compare types, UI severity bucket, binding editor payloads.
- GATE-G: no TODO/FIXME markers.
- GATE-H: all gates pass with explicit flagging where backend/frontend endpoints are not yet exposed in client.
