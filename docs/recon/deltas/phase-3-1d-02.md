# Recon Delta 02 — Slice 3b Resolve Endpoint Reality

**Status:** ACKED (founder accepted 2026-05-07; fix batch resolves F-01, F-02, F-03 inline in same PR)
**Triggered by:** Slice 3b (PR-05) preflight inspection of
`backend/src/schemas/resolve.py`, `backend/src/api/routers/admin_resolve.py`,
`backend/src/services/resolve/filters.py` (this session, 2026-05-07).
**Scope:** Phase 3.1d Slice 3b impl shape — does NOT modify Slice 2 acceptance,
does NOT modify milestone wrapper close criteria, does NOT modify DEBT-078
resolution path.

---

## Discovery

The Slice 3b impl prompt's TS mirror (`ResolvedValueResponse`) and the
prompt's claim about backend dim/member query semantics ("backend accepts
dimension KEYS as `dim` values") both diverge from code reality. Two distinct
divergences surfaced under GATE-G honest-stop conditions #1 and #5:

### F-01: ResolvedValueResponse field shape

The prompt's TS interface specifies:

```ts
{
  cube_id: string;
  semantic_key: string;
  coord: number[] | null;
  value: string | null;
  units: string | null;
  scalar_factor: string | null;
  ref_period: string | null;
  release_time: string | null;
  source_hash: string | null;
  missing: boolean;
  is_stale: boolean;
  cache_status: 'hit' | 'primed';
}
```

Actual backend Pydantic shape (`backend/src/schemas/resolve.py:20`):

```python
class ResolvedValueResponse(BaseModel):
    cube_id: str
    semantic_key: str
    coord: str                          # service-derived StatCan coord string
    period: str                         # ref_period (renamed)
    value: str | None
    missing: bool
    resolved_at: datetime               # alias of cache row fetched_at
    source_hash: str                    # required, non-null
    is_stale: bool
    units: str | None
    cache_status: Literal["hit", "primed"]
    mapping_version: int | None
```

Specific divergences:

| Field (prompt) | Field (backend) | Note |
|---|---|---|
| `coord: number[] \| null` | `coord: str` (required) | Coord is a positional string, not an array; never null per backend contract |
| `ref_period: string \| null` | `period: str` (required) | Renamed; never null |
| `release_time: string \| null` | `resolved_at: datetime` (required) | Renamed; never null; ISO datetime |
| `scalar_factor: string \| null` | (not present) | Field absent on backend |
| `source_hash: string \| null` | `source_hash: str` (required) | Never null per backend |
| (not present) | `mapping_version: int \| null` | Optional new field absent from prompt mirror |

### F-02: dim/member query parameter semantics

Prompt claims (Files to create §CREATE 2 inline note):

> "The backend's resolve endpoint maps `dim` to dimension position id
> resolution by name in the cube — it accepts dimension KEYS as `dim`
> values (per preflight TASK 1)."

Actual backend signature (`backend/src/api/routers/admin_resolve.py:120-122`):

```python
dim: list[int] = Query(default_factory=list),
member: list[int] = Query(default_factory=list),
```

And the parser (`backend/src/services/resolve/filters.py:33-83`) explicitly
expects `dimension_position_id` (1..10) and `member_id` (int). The
`ResolvedDimensionFilter` DTO populates `dimension_name`/`member_name` with
empty strings — downstream (`derive_coord`) reads numeric IDs only.

This means:
- `?dim=geo&member=CA` (string keys) → backend 422 Unprocessable Entity
  (FastAPI rejects pre-handler).
- `?dim=1&member=12` (int) → backend processes as
  `dimension_position_id=1, member_id=12`.

### F-03: SingleValueBinding.filters end-to-end semantics

Slice 2 `SingleValueBinding.filters: Record<string, string>` (canonicalized,
sorted keys) is populated by Slice 3a `BindingEditor.tsx:323-339` from
`cubeMetadata.dimensions`:

```tsx
{Object.entries(cubeMetadata.dimensions).map(([dimKey, dim]) => (
  <select onChange={(e) => updateFilter(dimKey, e.target.value)}>
    {dim.members.map((m) => (
      <option value={String(m.id)}>{m.label}</option>
    ))}
  </select>
))}
```

So filter shape is: `{ <dimKey>: <String(member.id)> }`. The dim KEYS are
whatever `Object.keys(cubeMetadata.dimensions)` yields. Slice 3a's
`CubeMetadataResponse.dimensions: Record<string, CubeMetadataDimension>` is
itself a v1 *assumption* (per `admin-discovery.ts:54` "Confirm against
backend on first integration test; if shape diverges, file Recon Delta 02").

Backend stores the cached `dimensions` JSONB as a flat dict (model
`CubeMetadataCacheEntry.dimensions: Mapped[dict]`,
repository `cube_metadata_cache_repository.py:44`), populated via
`normalize_dimensions(payload)` in
`backend/src/services/statcan/metadata_cache.py:131-155`:

```python
def normalize_dimensions(payload: CubeMetadataResponse) -> dict:
    dims: list[dict] = []
    for dim in payload.dimensions:
        members = [
            {"member_id": m.member_id, "name_en": ..., "name_fr": ...}
            for m in dim.members
        ]
        dims.append({
            "position_id": dim.dimension_position_id,
            "name_en": ...,
            "name_fr": ...,
            "has_uom": ...,
            "members": members,
        })
    return {"dimensions": dims}
```

So the backend response shape is `{"dimensions": [<dim object>...]}` (list,
not dict-keyed-by-name). Slice 3a's `Record<string, CubeMetadataDimension>`
TS interface does NOT match this — Slice 3a's own integration with backend
data is unverified end-to-end.

This means **the binding picker → preview → backend chain is not
end-to-end functional today**, regardless of how Slice 3b is shaped.
Surfacing here is appropriate; Slice 3a integration shape is its own
prior issue (Slice 3a comment at `admin-discovery.ts:54` already
flags this).

**RESOLUTION (this fix batch):** F-03 resolved inline by Slice 3b fix batch:
1. `CubeMetadataResponse.dimensions` TS interface in `admin-discovery.ts`
   rewritten from `Record<string, CubeMetadataDimension>` to
   `CubeMetadataDimension[]` matching backend `normalize_dimensions` output.
2. `BindingEditor.tsx` filter render rewritten to consume the array,
   storing `String(position_id)` as filter keys and `String(member_id)`
   as filter values. `binding.filters` content semantics now align with
   backend `?dim=<int>&member=<int>` query params.
3. Preview path is end-to-end functional for picker-built bindings.
4. Existing 3a tests (filter render, cube change reset) updated to new shape.

## Contradiction

Per the milestone wrapper §HALT and prompt §"Recon discipline":

- HALT-1 (resolve endpoint exists) was satisfied by preflight (endpoint
  IS present). The divergence is internal to the endpoint contract,
  not its existence.
- "Locked" recon (`phase-3-1d-recon.md` §3.2 cached-only mode) was for
  context only, not Slice 3b's contract; Slice 3b uses the auto-prime
  endpoint per founder decision 1.
- Prompt's TS `ResolvedValueResponse` mirror was drafted from
  `BACKEND_API_INVENTORY.md` (which `Recon Delta 01 D-04` flagged as
  doc-incomplete; tracked DEBT-081). Drift between the inventory
  document and the actual Pydantic class is the root cause.

## Impacted slices

- **Slice 3b (PR-05)** — TS mirror corrected to match
  `backend/src/schemas/resolve.py`. Client URL construction documented
  with the dim/member-must-be-int caveat. Direct.
- **Slice 3a (PR-04)** — `CubeMetadataResponse.dimensions` shape lock is
  unverified end-to-end. Not in 3b scope; recommend founder file separate
  P3-NN polish item to verify (and adjust either Slice 3a interface OR
  add a backend response transformer at the proxy layer).
- **Slice 4a (PR-06)** — single-value walker. Same dim/member-must-be-int
  invariant applies when the walker emits to backend. Walker has not
  been built yet; this delta carries forward as a constraint.
- **Milestone close criteria** — criterion #3 ("Binding editor can
  create/edit valid `single` bindings"). The picker UI builds a
  syntactically-valid `SingleValueBinding` regardless of dim/member
  semantic correctness; close criterion is not invalidated by this
  delta. The resolve preview will surface RESOLVE_INVALID_FILTERS
  (or 422) when filters are non-numeric — operator sees the gap
  inline, which is appropriate v1 behaviour.

## Minimal decisions taken in Slice 3b

Provisional, ack-required:

### D-01: TS `ResolvedValueResponse` mirror corrected

`frontend-public/src/lib/api/admin-resolve.ts` exports an interface that
matches `backend/src/schemas/resolve.py` exactly:

```ts
export interface ResolvedValueResponse {
  cube_id: string;
  semantic_key: string;
  coord: string;
  period: string;
  value: string | null;
  missing: boolean;
  resolved_at: string;            // ISO datetime
  source_hash: string;
  is_stale: boolean;
  units: string | null;
  cache_status: 'hit' | 'primed';
  mapping_version: number | null;
}
```

`ResolvePreview.tsx` displays `value`/`units`/`period`/`cache_status`
accordingly. No `release_time`, `ref_period`, `scalar_factor`, or
`coord: number[]` references in shipped code.

### D-02: Client forwards numeric position_id/member_id pairs

`fetchResolvedValue(binding)` builds `?dim=<position_id_str>&member=<member_id_str>`
pairs in alphabetical key order from `binding.filters`. The picker UI
(BindingEditor.tsx, post-fix) emits `binding.filters` with stringified
integer keys (`String(position_id)`) and stringified integer values
(`String(member_id)`). Backend resolve service (`backend/src/api/routers/
admin_resolve.py:120-122`) accepts these as `dim: list[int]` + `member: list[int]`
via FastAPI int coercion.

Slice 2 `SingleValueBinding.filters: Record<string, string>` type is unchanged —
the SEMANTIC constraint (numeric stringified content) is enforced by:
- the picker UI (renders only `position_id` keys + `member_id` values),
- backend runtime validation (FastAPI 422 on non-int input),
- 422 array-detail parsing in `admin-resolve.ts` (`extractResolveError`).

This is the production-correct path. The earlier "verbatim forwarding +
surface 422 to operator" approach is REJECTED in favor of this fix.

**Known limitation accepted by founder:** if a hand-edited or imported
binding (rare; not via picker) carries non-numeric filters, preview
surfaces RESOLVE_INVALID_FILTERS via 422-array parsing. UI displays
operator-friendly locale + raw msg. This is acceptable v1 behavior; no
upstream guard added in 3b (not within Slice 3b scope to validate
Binding.filters semantic constraints — Slice 2's `validateBinding`
ensures *type* correctness, not numeric content).

### D-03: No locale changes

Existing `publication.binding.resolve.{cache_miss,mapping_not_found,invalid_filters}`
keys are reused. UNKNOWN errors fall back to raw backend message
(dev-facing; acceptable per founder out-of-scope deferral on locale
extraction).

## Recommended follow-up

1. **F-03 root cause** — Slice 3a interface vs backend shape. Founder to
   decide post-3b: add backend transformer at proxy OR adjust Slice 3a
   TS interface OR adjust backend response shape. Tracked as a NEW
   polish item (suggested ID P3-NN-RESOLVE-FILTERS-INTEGRATION).
2. **F-02 picker translation** — once F-03 is resolved, the picker
   should emit `binding.filters` with numeric position_ids as keys and
   numeric member_ids as values OR a translation layer should sit
   between the picker and the resolve client.
3. **F-01** — corrected mirror is locked in 3b. No carry-forward.
4. **DEBT-081** (BACKEND_API_INVENTORY.md gap) — this delta reinforces
   the existing tracked item.

## Acceptance

ACKED 2026-05-07. F-01, F-02, F-03 all resolved inline in same PR
(Slice 3b PR-05). Carry-forward to Slice 4a: walker emits to backend
using the same numeric-stringified `binding.filters` shape established
here — no contract drift.

DEBT-081 (BACKEND_API_INVENTORY discovery section) closes by way of
Recon Delta 01 + Recon Delta 02 reconciling the truth at TS-interface
level and committing fixed code.

---

**End of Recon Delta 02.**
