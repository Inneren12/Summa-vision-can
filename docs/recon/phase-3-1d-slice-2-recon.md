# Phase 3.1d Slice 2 — Recon (Part A: Block shape + Binding ownership inventory)

> **Scope:** Part A of 3 (read-only inventory).
> Sections §A and §B only. §C–§I are deferred stubs to Parts B and C.
> No design decisions, no impl code, no DEBT/locale/CHANGELOG edits.
>
> **Locked architectural decisions** (context only; not relitigated in Part A):
> 1. Field name `Block.binding`, top-level sibling of `props`, optional.
> 2. Universal validation across 5 binding kinds.
> 3. `Binding` union moves to `frontend-public/src/components/editor/binding/types.ts`.
> 4. No schemaVersion bump. Clone preserves binding. No UI in Slice 2. No backend changes.
> 5. Slice 1a imports redirect via re-export shim from `lib/types/compare.ts`.

---

## Pre-flight verification

- Branch: `claude/block-shape-binding-inventory-yqAXn` (per harness directive). Working tree clean.
- `frontend-public/src/lib/types/compare.ts` exists.
- `frontend-public/src/components/editor/types.ts` exists.
- `frontend-public/src/components/editor/registry/guards.ts` exists.
- `frontend-public/src/components/editor/binding/` directory does **not** yet exist (`find` returned no match) — clean ground for Slice 2.

Recon inputs read:

| Doc | Lines |
|---|---|
| `docs/recon/phase-3-1d-frontend-recon-proper-part1.md` | 578 |
| `docs/recon/phase-3-1d-frontend-recon-proper-part2.md` | 369 |
| `docs/recon/phase-3-1d-frontend-recon-proper-part3.md` | 498 |
| `docs/recon/phase-3-1d-slice-1b-recon.md` | 499 |

§B2 spec block (`docs/recon/phase-3-1d-frontend-recon-proper-part1.md:367-491`):

- First 5 lines (367–371):
  ```
  ## §B2 — Canonical typed binding schema

  ### §B2.1 Top-level location decision

  **Decision: add top-level `Block.binding` (sibling of `props`), not `props.binding`.**
  ```
- Last 5 lines (488–492):
  ```
  3. Publish capture adapter maps same binding to `BoundBlockReference` (`dims[]`, `members[]`, `period`) per backend schema. (`backend/src/schemas/staleness.py:162-170`)

  Dependency note:
  - Current resolver is singular-value oriented; multi-value bindings (`time_series`, `categorical_series`, `multi_metric`, `tabular`) will require either resolver iteration strategy client/server-side or a new batch resolve contract in 3.1e. Track as Part 3 DEBT candidate (backend dependency), not a 3.1d v1 blocker.
  ```

---

## §A — Current canonical Block shape

### §A.1 Block interface inventory

Sole canonical definition: `frontend-public/src/components/editor/types.ts:32-45`.

```ts
export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;   // Phase 1.6, additive
}
```

`grep -rn "interface Block\b\|export interface Block\b\|type Block =\|^export type Block "
frontend-public/src/components/editor/` returns **only** the line above — no derived
`BlockState`, `BlockSnapshot`, or other shadow shapes exist.

Comparison with `docs/architecture/EDITOR_BLOCK_ARCHITECTURE.md:117-129` documented shape:
**identical**. The architecture doc lists exactly `id`, `type`, `props`, `visible`,
`locked?`. **No divergence.** GATE-E honest-stop NOT triggered.

### §A.2 BlockProps shape

Defined at `frontend-public/src/components/editor/types.ts:28-30`:

```ts
export interface BlockProps {
  [key: string]: any;
}
```

`BlockProps` is an **open index map**, not a discriminated union. Per-type prop
shape is enforced via the registry `BREG[type].dp` defaults plus a `guard`
function (`frontend-public/src/components/editor/types.ts:167-176`), not via the
TypeScript union itself. `sanitizeBlockProps`
(`frontend-public/src/components/editor/registry/guards.ts:468-531`) drops keys
absent from `BREG[type].dp`.

Block-type catalog confirmed at `frontend-public/src/components/editor/registry/blocks.ts:11-47`
(13 entries total):

- **DATA-bindable (7 — `Block.binding` will apply):** `hero_stat`,
  `delta_badge`, `comparison_kpi`, `bar_horizontal`, `line_editorial`,
  `table_enriched`, `small_multiple`. Cross-ref recon-proper Part 1 §C.1
  (`phase-3-1d-frontend-recon-proper-part1.md:497-509`).
- **TEXT/MEDIA (6 — `Block.binding` not applicable):** `eyebrow_tag`,
  `headline_editorial`, `subtitle_descriptor`, `body_annotation`,
  `source_footer`, `brand_stamp`. Cross-ref §C.2
  (`phase-3-1d-frontend-recon-proper-part1.md:511-518`).

### §A.3 Block consumer call sites

`grep -rn "doc\.blocks\|blocks\[" frontend-public/src/components/editor/` returns
many matches; representative consumers classified:

| Consumer | File:line | Class |
|---|---|---|
| Editor entry / context menu | `components/editor/index.tsx:303,411,588,1493-1510` | Read-through |
| LeftPanel block list | `components/editor/components/LeftPanel.tsx:107,159` | Read-through |
| ReviewPanel | `components/editor/components/ReviewPanel.tsx:124,359,498` | Read-through |
| Renderer engine | `components/editor/renderer/engine.ts:41` | Read-through |
| Renderer measure | `components/editor/renderer/measure.ts:126` | Read-through |
| Validation `validate.ts` | `components/editor/validation/validate.ts:29,81,90,182` | Read-through |
| Invariants | `components/editor/validation/invariants.ts:26,44-45,58,71,95-96` | Validation/serialization |
| Contrast checker | `components/editor/validation/contrast.ts:185` | Read-through |
| Reducer (mutations) | `components/editor/store/reducer.ts:60,74,91,337-340,345-419` | Mutation |
| `validateImportStrict` hydration | `components/editor/registry/guards.ts:660-689` | Validation/serialization |

Slice 2 impact (Part B/C will design specifics):
- **Read-through** consumers don't need changes; an extra optional `binding` field
  passes through harmlessly.
- **Mutation** path (`store/reducer.ts` DUPLICATE_BLOCK at 345-419) is the clone
  surface where binding-preservation behaviour is decided in Part B.
- **Validation/serialization** paths (`registry/guards.ts:660-689` and
  `validation/invariants.ts`) are the points that must accept the new sibling
  field after Slice 2 — they currently neither reject nor preserve unknown
  block-level keys.

### §A.4 Phase 1.6 `Block.locked` precedent

The pattern Slice 2 will mirror.

- **Type addition** (`components/editor/types.ts:32-45`): added
  `locked?: boolean` as an optional sibling — no schemaVersion bump,
  forward-compatible.
- **Hydration / `validateImportStrict`** (`components/editor/registry/guards.ts:678-682`):
  ```ts
  ...(typeof b.locked === "boolean" ? { locked: b.locked } : {}),
  ```
  Optional spread — accepted only when typeof matches; absent or malformed
  values silently coalesce to `undefined` (`=== true` checks at usage sites
  treat that as `false`).
- **`sanitizeBlockProps`** (`components/editor/registry/guards.ts:468-531`):
  unchanged. Only governs `props` keys against `BREG[type].dp`. Top-level
  sibling fields are not touched.
- **Reducer permission gate** (`components/editor/store/reducer.ts:60,74,91`):
  three explicit `block.locked === true` short-circuits for `UPDATE_PROP`,
  `UPDATE_DATA`, `TOGGLE_VIS`. `TOGGLE_LOCK` action at lines 337-341.
- **DUPLICATE_BLOCK behaviour** (`components/editor/store/reducer.ts:403-411`):
  by explicit comment "duplicate ... does NOT inherit `locked` — the operator
  gets a fresh, editable copy." The new-block literal at 406-411 omits the
  `locked` key entirely. **This is the divergence point Slice 2 will document
  vs. its own clone-preserves-binding rule (Part B §D).**
- **Architecture doc citation** (`docs/architecture/EDITOR_BLOCK_ARCHITECTURE.md:122-128`):
  changelog entry "additive: `Block.locked?: boolean` (no schemaVersion bump)".

---

## §B — Current `Binding` types ownership

### §B.1 Where Binding lives now

Sole location: `frontend-public/src/lib/types/compare.ts:114-169`. Verified by
exhaustive grep across `frontend-public/src/` for each of the 5 interface names
plus the union — only the file above matched.

Per-symbol line ranges in `lib/types/compare.ts`:

| Symbol | Lines |
|---|---|
| `SingleValueBinding` | 114–122 |
| `TimeSeriesBinding` | 124–132 |
| `CategoricalSeriesBinding` | 134–143 |
| `MultiMetricBinding` | 145–152 |
| `TabularBinding` | 154–162 |
| `Binding` (union) | 164–169 |

Full file exports (`lib/types/compare.ts:1-186`): `StaleStatus`, `StaleReason`,
`Severity`, `CompareKind`, `SnapshotFingerprint`, `ResolveFingerprint`,
`DriftCheckBasis`, `SnapshotMissingBasis`, `CompareFailedBasis`, `CompareBasis`,
`BlockComparatorResult`, `CompareResponse`, `BoundBlockReference`,
`PublishPayload`, the 5 binding interfaces, `Binding` union,
`CompareBadgeSeverity`. No exported functions.

### §B.2 Binding shape vs recon-proper Part 1 §B2

Field-by-field comparison between
`docs/recon/phase-3-1d-frontend-recon-proper-part1.md:380-457` (spec) and
`frontend-public/src/lib/types/compare.ts:114-169` (actual):

| Kind | Discriminator | Field set match | Optionality match | Verdict |
|---|---|---|---|---|
| `single` | `kind: 'single'` | `cube_id`, `semantic_key`, `filters`, `period`, `format?` | match | ✅ identical |
| `time_series` | `kind: 'time_series'` | `cube_id`, `semantic_key`, `filters`, `period_range`, `series_dim?`, `format?` | match | ✅ identical |
| `categorical_series` | `kind: 'categorical_series'` | `cube_id`, `semantic_key`, `category_dim`, `filters`, `period`, `sort?`, `limit?` | match | ✅ identical |
| `multi_metric` | `kind: 'multi_metric'` | `cube_id`, `metrics`, `filters`, `period`, `format?` | match | ✅ identical |
| `tabular` | `kind: 'tabular'` | `cube_id`, `columns`, `row_dim`, `filters`, `period`, `format?` | match | ✅ identical |

`Binding` union (`lib/types/compare.ts:164-169`) lists exactly the 5 members in
the same order as spec §B2.4 (`phase-3-1d-frontend-recon-proper-part1.md:451-457`).
**No divergence.** GATE-E honest-stop NOT triggered.

### §B.3 Existing Binding consumers

`grep -rn "\bBinding\b\|\bBoundBlockReference\b" frontend-public/src/` (excluding
tests) returns **no consumer outside `lib/types/compare.ts` itself**. Slice 1a
defined the union; no Slice 1a/1b code imports it yet. Implication for Part C
import migration: zero in-tree call sites need rewriting at Slice 2 — the
re-export shim is purely a public-API safety net (locked decision #10).

Compare-related imports of `lib/types/compare.ts` (these are NOT binding-related;
class **(b) Compare-related types only**, no migration needed):

| File:line | Imports |
|---|---|
| `frontend-public/src/components/editor/components/CompareBadge.tsx:14` | `CompareBadgeSeverity` |
| `frontend-public/src/components/editor/hooks/compareReducer.ts:10-13` | `CompareResponse`, `CompareBadgeSeverity` |
| `frontend-public/src/lib/utils/compareSeverity.ts:15-18` | `CompareResponse`, `CompareBadgeSeverity`, `StaleReason` |
| `frontend-public/src/lib/api/admin.ts:11` | `CompareResponse`, `PublishPayload` |
| `frontend-public/src/components/editor/components/__tests__/TopBar.compare.test.tsx:5` | `CompareResponse` |
| `frontend-public/src/components/editor/hooks/__tests__/compareReducer.test.ts:6` | `CompareResponse` |
| `frontend-public/src/components/editor/hooks/__tests__/useCompareState.test.tsx:3` | `CompareResponse` |
| `frontend-public/src/lib/utils/__tests__/compareSeverity.test.ts:11` | `CompareResponse`, `CompareBadgeSeverity`, `StaleReason` |

No file imports class **(a) Binding-related** or class **(c) both** today.

### §B.4 `BoundBlockReference` vs `Binding` distinction

`BoundBlockReference` lives at `frontend-public/src/lib/types/compare.ts:99-106`:

```ts
export interface BoundBlockReference {
  block_id: string;
  cube_id: string;
  semantic_key: string;
  dims: number[];
  members: number[];
  period?: string | null;
}
```

Structural differences from `Binding`:
- Field shape is **wire-shape** (`dims: number[]`, `members: number[]`) per
  `backend/src/schemas/staleness.py:162-170`, not the editor-ergonomic
  `filters: Record<string, string>` carried by every `Binding` variant.
- `BoundBlockReference` carries `block_id` (publish-time identification);
  `Binding` does not (it lives ON the block, identification is implicit).
- No `kind` discriminator on `BoundBlockReference` — single shape only.

No shared sub-types between the two. The mapping between them is the
publish-capture adapter described in
`phase-3-1d-frontend-recon-proper-part1.md:484-488`.

Confirmation: `BoundBlockReference` **stays** in `lib/types/compare.ts` (it is an
API/wire concern). `Binding` + 5 interfaces **move** to
`components/editor/binding/types.ts` (editor-domain concern). No ambiguity
discovered; no Part C founder review needed on this point.

### §B.5 P3-033 fix sketch context

`polish.md:949-973` (verbatim):

```
## P3-033 — Split `Binding` union out of `compare.ts`

- Source: Phase 3.1d Slice 1a PR review (post-merge)
- Added: 2026-05-04
- Severity: P2
- Category: architecture / domain separation
- Files:
  - frontend-public/src/lib/types/compare.ts (remove Binding types)
  - frontend-public/src/components/editor/binding/types.ts (NEW —
    Binding union)
- Description: Slice 1a placed Binding discriminated union (5 kinds) in
  lib/types/compare.ts alongside backend wire types (CompareResponse,
  BoundBlockReference, etc.). Long-term, Binding is editor-domain concern
  (consumed by Inspector, ResolvePreview, walker), not API-wire concern.
  Split improves layer hygiene.
- Fix sketch: move SingleValueBinding, TimeSeriesBinding,
  CategoricalSeriesBinding, MultiMetricBinding, TabularBinding, and Binding
  union to components/editor/binding/types.ts. Update Slice 1a imports.
  Keep BoundBlockReference in compare.ts (it IS wire-type).
- Status: pending
- Note: fix trigger — ship in Slice 2 (Block schema extension) when
  Block.binding field lands and validateBinding consumes the union —
  natural co-location point.
```

Slice 2 IS the P3-033 closure event. Recon Part A documents the move plan
inventory; Parts B/C draft the move itself; closure happens at Slice 2 impl
PR merge.

---

## §C — Schema validator inventory — DEFERRED to Part B

## §D — Clone / copy / paste / import / export — DEFERRED to Part B

## §E — Binding union design — DEFERRED to Part B

## §F — File structure plan — DEFERRED to Part C

## §G — Test plan — DEFERRED to Part C

## §H — Founder questions — DEFERRED to Part C

## §I — Anti-hallucination gates — DEFERRED to Part C
