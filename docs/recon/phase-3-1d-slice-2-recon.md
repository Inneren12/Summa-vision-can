# Phase 3.1d Slice 2 — Recon (Parts A + B: Block shape, Binding inventory, Validator + Clone + Binding union design)

> **Scope:** Slice 2 recon-proper, Parts A+B+C (full).
> §A–§B inventory, §C–§E design, §F–§I implementation plan and gates for impl prompt.
> No production code changes in this recon commit. No backend/UI/locale/DEBT edits.
> Pseudocode in §E.4 is type-signature-level scaffolding for impl prompt; not committed source.
>
> **Locked architectural decisions** (context only; not relitigated in Part A):
> 1. Field name `Block.binding`, top-level sibling of `props`, optional.
> 2. Universal validation across 5 binding kinds.
> 3. `Binding` union moves to `frontend-public/src/components/editor/binding/types.ts`.
> 4. No schemaVersion bump. Clone preserves binding. No UI in Slice 2. No backend changes.
> 5. **No re-export shim.** Slice 2 cleanly removes Binding union and 5 binding interfaces from `lib/types/compare.ts`. Part A §B.3 confirmed zero in-tree consumers of `Binding` from `compare.ts`, so no shim is needed. Future imports use `editor/binding/types.ts` directly.

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

- **Schema-capable / future binding-capable (7 — schema may carry `Block.binding`; UI/resolver support is phased):** `hero_stat`, `delta_badge`, `comparison_kpi`, `bar_horizontal`, `line_editorial`, `table_enriched`, `small_multiple`. Cross-ref recon-proper Part 1 §C.1 (`phase-3-1d-frontend-recon-proper-part1.md:497-509`). Note: Slice 2 schema accepts `Block.binding` for all 7; Slice 3a/3b UI ships binding editor for `hero_stat` + `delta_badge` only in v1; Phase 3.1e resolver support extends incrementally.
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
re-export shim is purely a public-API safety net (locked decision #5 (no shim — clean removal)).

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

## §C — Schema validator inventory

### §C.1 Validator location and pipeline

Sole canonical home for block / document validation: `frontend-public/src/components/editor/registry/guards.ts`. No `zod` (`grep -rn "z\\.object\\|from \"zod\"" frontend-public/src/components/editor/` → 0 matches); validation is **hand-written, type-narrowing checks**.

Two related top-level entry points (`registry/guards.ts`):

| Function | Lines | Role |
|---|---|---|
| `hydrateImportedDoc(raw)` | 554–690 | Structural hydration. Builds the `CanonicalDocument` literal from raw input; per-block construction at 673–682; emits warnings on coercion. |
| `validateImportStrict(raw)` | 754–771 | Strict gateway — calls `migrateDoc` then `assertCanonicalDocumentV2Shape` + `validateSectionReferences` + `validateRegistryConstraints`; throws on any violation. |

Caller wiring (`frontend-public/src/components/editor/index.tsx:1187-1195`):
```ts
result = hydrateImportedDoc(raw);   // construct + coerce
validated = validateImportStrict(result.doc); // shape/ref/registry assert
```

**Correction to Part A §A.3:** Part A pointed to "`validateImportStrict` at lines 660-689" as the hydration gateway; the actual function at that range is `hydrateImportedDoc`, and `validateImportStrict` lives at 754-771. Substantive Part A claim (Phase 1.6 `locked` optional-spread pattern at 678-682) stands — it just lives inside `hydrateImportedDoc`, which is called *upstream* of `validateImportStrict` by the import flow. **No honest-stop trigger** — the construction-literal pattern Part A relies on is exactly where Part A described it; only the function name needs adjusting going forward.

Other validation surfaces (read-only, no Block-field construction):
- `validation/validate.ts` — `validateDocument` / `validatePresetSize` / `validate` (`:27,172,238`); reads `doc.blocks` for editorial rules. Will not reject unknown block fields.
- `validation/invariants.ts` — `assertDocumentIntegrity` (`:19`); INV-1..5 cover refs, required types, section placement, id≡key. Block-shape oblivious to `binding`.
- `validation/contrast.ts`, `validation/block-data.ts` — read `block.props` only.

→ Slice 2 only needs to touch the **construction literal in `hydrateImportedDoc`**. All read-only validators ignore unknown sibling fields by definition.

### §C.2 `sanitizeBlockProps` deep dive (linchpin)

`registry/guards.ts:468-531`. Signature:

```ts
function sanitizeBlockProps(
  type: string,
  blockId: string,
  rawProps: any,
  warnings: string[],
): Record<string, any>
```

Allowlist source: `BREG[type].dp` (per-block-type default-props map). Construction (`:474-477`):

```ts
const reg = BREG[type];
if (!reg) return rawProps || {};
const defaults = reg.dp || {};
const result: Record<string, any> = { ...defaults };
```

Loop iterates **`Object.entries(defaults)`**, NOT `Object.entries(rawProps)` (`:487`). Each known key is type-coerced (boolean/number/string/array/object) against its default; type mismatches re-warn and substitute the default.

Strict allowlist behaviour confirmed at `:527`:
```ts
// Unknown keys (not in defaults) are dropped — strict mode
```
Because the loop is over `defaults`, any key in `rawProps` that is not in `BREG[type].dp` is silently absent from `result` (no warning emitted).

**Scope confirmation (Part A §A.2 verified):** the function takes `rawProps` (i.e. `b.props`), not a full `Block`. It is called at `:676` as `sanitizeBlockProps(type, key, b.props, warnings)`. Top-level Block fields (`id`, `type`, `visible`, `locked`, future `binding`) are constructed by the caller's literal at 673–682 and never traverse `sanitizeBlockProps`.

→ **No `sanitizeBlockProps` change required for `Block.binding`.** The sanitizer surface for Slice 2 is empty.

### §C.3 `hydrateImportedDoc` block-construction literal — Slice 2 extension point

Verbatim block construction (`registry/guards.ts:673-682`):

```ts
doc.blocks[key] = {
  id: key, // FORCE id to match object key — cannot drift out of sync
  type,
  props: sanitizeBlockProps(type, key, b.props, warnings),
  visible: typeof b.visible === "boolean" ? b.visible : true,
  // Phase 1.6: preserve user-toggled instance lock when present.
  ...(typeof b.locked === "boolean" ? { locked: b.locked } : {}),
};
```

Top-level fields explicitly handled: `id`, `type`, `props`, `visible`, `locked` (optional spread). Anything else on the raw input (e.g. `binding`) is **silently dropped** today.

Slice 2 adds one optional-spread line mirroring the Phase 1.6 pattern:

```ts
...(b.binding !== undefined ? (() => {
  const v = validateBinding(b.binding);
  return v ? { binding: v } : {};
})() : {}),
```

Or equivalent simpler form (impl-prompt to choose). Key constraints:
- Match Phase 1.6 opt-in optional-spread style — never insert `binding: undefined`.
- Run input through `validateBinding` (§E.4); strict-reject malformed → no `binding` key.
- Emit a warning on rejection, mirroring `sanitizeBlockProps` warning pattern (impl-prompt territory).

`validateImportStrict` (754–771) needs **no change** — `assertCanonicalDocumentV2Shape` (197–340) checks top-level doc fields only, never iterates per-block structure to reject unknown keys. `validateRegistryConstraints` checks `block.type` against `BREG`; ignores siblings. `binding` rides through transparently once `hydrateImportedDoc` preserves it.

### §C.4 Migration considerations

`schemaVersion` lives at `editor/types.ts:124` and `:143` (CURRENT = 1 in v1 doc shape, but `CURRENT_SCHEMA_VERSION` import-side is currently 3; see migrations test at `__tests__/migrations.test.ts`). Phase 1.6 `Block.locked?: boolean` was additive optional with **no schemaVersion bump** (`editor/types.ts:43` comment: "no schemaVersion bump in v1").

Slice 2 follows the same precedent:
- Existing documents lacking `binding` validate cleanly (optional sibling).
- New documents with `binding` validate cleanly once §C.3 extension is in place.
- Migrations map (`MIGRATIONS` / `applyMigrations` / `migrateDoc` at 708–738) does not iterate Block fields; existing migration steps are version-bumping doc transforms only.
- → **No schemaVersion bump for Slice 2.** No migration step needed.

If founder/reviewer disagrees (e.g. wants explicit "binding-aware" version marker for forward-compat tooling), surface in Part C §H — but recon recommends no bump.

### §C.5 Other validation surfaces touching block shape

`grep -n "doc\.blocks\|\.blocks\[" frontend-public/src/components/editor/validation/` — `validate.ts` and `invariants.ts` are the only files; both iterate `doc.blocks` for *value* checks (props text, type membership, section placement) and never inspect arbitrary sibling fields. Confirmation: zero impact on `binding` round-trip; no Slice 2 change.

---

## §D — Clone / copy / paste / import / export

### §D.1 Full publication clone (`cloneAdminPublication`)

Frontend caller `components/editor/index.tsx:908` (handleClone) and `:945` (forkLocalSnapshotAsNewDraft). Both forms are **trust-the-backend-response** — frontend hits `cloneAdminPublication(publicationId)`, gets `{ id, etag, ... }` back, then `router.push` to the new editor URL. The receiving editor session re-fetches the document from the backend and runs it through `hydrateImportedDoc → validateImportStrict` like any other load. No frontend manipulation of block contents during clone.

→ For `Block.binding`: per locked decision #7 (clone preserves binding), the *backend* `mutate_document_state_for_clone(workflow=draft, history=[], comments=[])` MUST preserve `binding` on each block. This is a backend contract; frontend just deserializes whatever is returned. **Phase 3.1e backend recon will verify** the contract; if backend strips `binding` today, that's a Phase 3.1e bug, not a Slice 2 blocker.

### §D.2 `DUPLICATE_BLOCK` reducer — asymmetry resolution

`store/reducer.ts:345-422`. Construction literal (`:405-411`):

```ts
const clonedProps = JSON.parse(JSON.stringify(sourceBlock.props));
const newBlock = {
  id: nextId,
  type: sourceBlock.type,
  props: clonedProps,
  visible: sourceBlock.visible,
};
```

Inline comment (`:403-404`):
> Duplicate carries identical props (deep-cloned to break aliasing) but does NOT inherit `locked` — the operator gets a fresh, editable copy.

`locked` is intentionally absent from the new-block literal. Slice 2 must explicitly resolve where `binding` lands relative to this precedent.

**Three options:**

- **Option A — strip `binding` (mirror `locked`).** Rationale: same-data-source duplicates are not what the user wants; mirror the "fresh editable copy" semantic. *Cost:* contradicts the "clone preserves binding" mental model from full publication clone (decision #7), introducing an inconsistency between operations.

- **Option B — preserve `binding` (recommended).** Rationale: a block-level duplicate is a structural copy; preserving binding lets the operator land a fresh visual instance pointing at the same data, then edit the binding to retarget if desired. Aligns with full clone semantics → consistent mental model: *clone (any granularity) preserves binding; user edits afterwards*. `locked` strip remains an *exception* justified by its UX-protection role (locked = "do not touch by accident"); binding has no analogous protective role.

- **Option C — strip and revisit.** Rationale: maximal initial conservatism, defer to user feedback. *Cost:* introduces churn risk in Slice 3a binding-editor UX research.

**Recommendation: Option B (preserve binding on `DUPLICATE_BLOCK`).** Implementation in Slice 2:

```ts
const newBlock = {
  id: nextId,
  type: sourceBlock.type,
  props: clonedProps,
  visible: sourceBlock.visible,
  ...(sourceBlock.binding
    ? { binding: JSON.parse(JSON.stringify(sourceBlock.binding)) as Binding }
    : {}),
};
```

`structuredClone` (or deep-JSON) breaks aliasing, matching the `props` precedent at `:405`. Surface to Part C §H founder review for sign-off.

### §D.3 Other clone-like reducer actions

`grep` of reducer actions surfaced (line numbers from `store/reducer.ts`):

| Action | Line | Block-creation behaviour | binding handling |
|---|---|---|---|
| `DUPLICATE_BLOCK` | 345 | Clones existing block | §D.2 — preserve recommended |
| `REMOVE_BLOCK` | 113 | Deletes only | n/a |
| `SWITCH_TPL` | 149 | Replaces doc from template (`mkDoc`) | New blocks; `binding` undefined by construction |
| `IMPORT` | 156 | Replaces doc with hydrated import | Routed via §C.3 — preserved when present |

No `ADD_BLOCK` / `INSERT_BLOCK` / `COPY_BLOCK` / `PASTE_BLOCK` actions exist today. Block creation outside duplicate/import is template-driven (`mkDoc` from `registry/templates`) and produces blocks with no `binding` field. → No further binding-handling decisions needed at the reducer level.

### §D.4 Import / export round-trip

Export path (`components/editor/index.tsx:617-625`):
```ts
const exportJSON = useCallback(() => {
  const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
  ...
});
```
Plain `JSON.stringify(doc)` — type-agnostic. Whatever sits on each `Block` (including `binding`) flows verbatim into the JSON payload. **No export-side change required.**

Import path: file input → parse → `hydrateImportedDoc` → `validateImportStrict` (`index.tsx:1187-1195`). After §C.3 extension, `binding` is preserved on hydration. Round-trip is closed.

Test surface (Part C §G territory): fixture document with mixed binding/no-binding blocks; export → re-parse → import → assert deep-equal on each `Block.binding`.

### §D.5 ZIP export (Phase 2.2 distribution)

`export/zipExport.ts:62 exportZip(...)` snapshots `doc` via `structuredClone` (`:68`), then composes `manifest.json` + `distribution.json` + `publish-kit.txt` + render blobs. The doc is consumed by `buildManifest(doc, ...)`, `buildDistributionJson({ doc, ... })`, `renderDocumentToBlob(doc, pal, presetId)`. None of these strip block-level fields — they read presentation/distribution-relevant fields (page, sections, blocks for rendering) and serialize at the manifest/distribution layer.

`grep -n "binding" frontend-public/src/components/editor/export/zipExport.ts` → 0 matches (type-agnostic w.r.t. binding). Confirmation: ZIP output preserves `binding` on each block transparently. No Slice 2 change in `zipExport.ts`.

### §D.6 Backend clone preservation expectation

Locked decision #7: clone preserves binding. This is enforced **server-side** by `mutate_document_state_for_clone` (out of scope for Slice 2). Frontend correctness is independent: the editor deserializes whatever the backend returns. Phase 3.1e backend recon to verify the contract; Slice 2 carries no enforcement burden.

---

## §E — Binding union design

### §E.1 5 binding kinds (verbatim from `lib/types/compare.ts:114-169`)

```ts
export interface SingleValueBinding {
  kind: 'single';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  /** Explicit backend-supported period, e.g. '2024-Q3'. Symbolic 'latest' out of scope per recon §J.4. */
  period: string;
  format?: string;
}

export interface TimeSeriesBinding {
  kind: 'time_series';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  period_range: { from: string; to: string } | { last_n: number };
  series_dim?: string;
  format?: string;
}

export interface CategoricalSeriesBinding {
  kind: 'categorical_series';
  cube_id: string;
  semantic_key: string;
  category_dim: string;
  filters: Record<string, string>;
  period: string;
  sort?: 'value_desc' | 'value_asc' | 'source_order';
  limit?: number;
}

export interface MultiMetricBinding {
  kind: 'multi_metric';
  cube_id: string;
  metrics: Array<{ semantic_key: string; label?: string }>;
  filters: Record<string, string>;
  period: string;
  format?: string;
}

export interface TabularBinding {
  kind: 'tabular';
  cube_id: string;
  columns: Array<{ semantic_key: string; label?: string }>;
  row_dim: string;
  filters: Record<string, string>;
  period: string;
  format?: string;
}

export type Binding =
  | SingleValueBinding
  | TimeSeriesBinding
  | CategoricalSeriesBinding
  | MultiMetricBinding
  | TabularBinding;
```

Cross-ref: `docs/recon/phase-3-1d-frontend-recon-proper-part1.md:380-457`. Field-by-field match per Part A §B.2 — no divergence.

After Slice 2 these definitions move to `frontend-public/src/components/editor/binding/types.ts` (per locked decision #3). No re-export shim remains in `lib/types/compare.ts` (per locked decision #5 — Part A §B.3 confirmed zero in-tree consumers).

### §E.2 `NumberFormat` type — does not exist

`grep -rn "NumberFormat\\|interface NumberFormat\\|type NumberFormat" frontend-public/src/` → **0 matches**. The 5 binding interfaces use `format?: string` (a free-form string format token, e.g. `"percent"`, `"currency:CAD"`); there is no structured `NumberFormat` type today.

**Slice 2 implication: no `NumberFormat` to relocate.** Keep the existing `format?: string` shape verbatim on the moved interfaces; `validateBinding` validates `format` as `string | undefined`. If a future slice introduces structured number formatting (`{ style: 'percent', precision: 1, ... }`), that work locates the new `NumberFormat` interface alongside `Binding` in `editor/binding/types.ts` — but recon-proper Part 1 §B2 spec did not require it, so Slice 2 keeps it out.

### §E.3 Per-block-type binding fit (registry territory, NOT schema)

| Block type | Acceptable binding kinds | Slice 2 schema | Phase 3.1e resolver |
|---|---|---|---|
| `hero_stat` | `single` | accepted | supported |
| `delta_badge` | `single` (precomputed delta semantics) | accepted | supported |
| `comparison_kpi` | `multi_metric` | accepted | pending |
| `bar_horizontal` | `categorical_series` | accepted | pending |
| `line_editorial` | `time_series` | accepted | pending |
| `table_enriched` | `tabular` | accepted | pending |
| `small_multiple` | unresolved: `multi_metric` or `categorical_series`; no Slice 3a UI support until dedicated recon | accepted | pending |
| `eyebrow_tag` / `headline_editorial` / `subtitle_descriptor` / `body_annotation` / `source_footer` | none | n/a | n/a |
| `brand_stamp` | none | n/a | n/a |

Cross-ref `phase-3-1d-frontend-recon-proper-part1.md:497-518`.

**Slice 2 schema accepts ALL 5 kinds on ANY block.** Per-type fit is registry-level metadata for the Slice 3a binding-picker UI; schema does not enforce because:
1. Registry mapping evolves without schema migration.
2. UI picker enforces fit at construction time.
3. Schema-level rejection of "wrong" binding would block forward extensibility (e.g. Phase 3.1f could add a kind that retroactively fits an existing block type).

**Impl-prompt note:** do NOT add per-type binding-kind validation to `validateBinding` or to `validateImportStrict`. Universal validation (locked decision #2) is intentional.

### §E.4 `validateBinding` signature + behaviour

Pure function in `editor/binding/types.ts`:

```ts
export function validateBinding(value: unknown): Binding | null;
```

Pseudocode skeleton:

```ts
export function validateBinding(value: unknown): Binding | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;

  const isStr = (x: unknown): x is string => typeof x === 'string';
  const isNonEmptyStr = (x: unknown): x is string =>
    typeof x === 'string' && x.trim().length > 0;
  const isOptStr = (x: unknown) => x === undefined || isStr(x);
  const isOptNonEmptyStr = (x: unknown) =>
    x === undefined || isNonEmptyStr(x);
  const isFilters = (x: unknown): x is Record<string, string> =>
    !!x && typeof x === 'object' && !Array.isArray(x) &&
    Object.values(x as object).every(isNonEmptyStr);
  const isPositiveInt = (x: unknown): x is number =>
    typeof x === 'number' && Number.isInteger(x) && x > 0;

  switch (v.kind) {
    case 'single': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isFilters(v.filters)) return null;
      if (!isNonEmptyStr(v.period)) return null;
      if (!isOptStr(v.format)) return null;
      return v as unknown as SingleValueBinding;
    }
    case 'time_series': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isFilters(v.filters)) return null;
      const pr = v.period_range as any;
      if (!pr || typeof pr !== 'object') return null;
      const hasFromTo =
        isNonEmptyStr(pr.from) && isNonEmptyStr(pr.to) && pr.last_n === undefined;
      const hasLastN =
        isPositiveInt(pr.last_n) && pr.from === undefined && pr.to === undefined;
      if (!(hasFromTo || hasLastN)) return null;
      if (!isOptNonEmptyStr(v.series_dim) || !isOptStr(v.format)) return null;
      return v as unknown as TimeSeriesBinding;
    }
    case 'categorical_series': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.semantic_key)) return null;
      if (!isNonEmptyStr(v.category_dim) || !isNonEmptyStr(v.period)) return null;
      if (!isFilters(v.filters)) return null;
      if (v.sort !== undefined &&
          !['value_desc','value_asc','source_order'].includes(v.sort as string)) return null;
      if (v.limit !== undefined && !isPositiveInt(v.limit)) return null;
      return v as unknown as CategoricalSeriesBinding;
    }
    case 'multi_metric': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.period)) return null;
      if (!isFilters(v.filters)) return null;
      if (!Array.isArray(v.metrics) || !v.metrics.every((m: any) =>
        m && isNonEmptyStr(m.semantic_key) && isOptStr(m.label))) return null;
      if (!isOptStr(v.format)) return null;
      return v as unknown as MultiMetricBinding;
    }
    case 'tabular': {
      if (!isNonEmptyStr(v.cube_id) || !isNonEmptyStr(v.row_dim) || !isNonEmptyStr(v.period)) return null;
      if (!isFilters(v.filters)) return null;
      if (!Array.isArray(v.columns) || !v.columns.every((c: any) =>
        c && isNonEmptyStr(c.semantic_key) && isOptStr(c.label))) return null;
      if (!isOptStr(v.format)) return null;
      return v as unknown as TabularBinding;
    }
    default:
      return null;
  }
}
```

**Strict-reject (`null`) on any malformed input.** Rationale:
- Mirrors `sanitizeBlockProps` strict-allowlist drop (`registry/guards.ts:527`).
- Mirrors `validateImportStrict`/Phase 1.6 optional-spread "include only when valid" pattern (`registry/guards.ts:681`).
- Malformed binding ⇒ treated as no binding (graceful degradation; never throws; never partially-shaped).

Approximate file size: ~80–110 lines including the Binding interfaces themselves.

### §E.5 Helper extraction (style note)

Recon recommends inline checks per case, with two tiny helpers (`isStr`, `isFilters`) to keep cases readable. DRY-extracting per-kind validators (`isValidSingle(v)`, etc.) is a style preference; recon does not see a functional advantage at five short cases. Surface to Part C §H if founder prefers extraction; recon-default is inline.

### §E.6 Forward compatibility

If Phase 3.1f introduces a 6th `kind` (e.g. `'geographic_choropleth'`), older builds running `validateBinding` against new data return `null` for the unknown discriminator (default branch) → frontend treats the block as having no binding. This is **graceful degradation by design** (locked decision #4 universal validation). No version negotiation, no client-version pin, no special handling. Future kinds extend without breaking older clients. Documented for impl-prompt so the universal-validation guarantee is preserved.

---

## §F — File structure plan

Target length in recon doc: 50–80 lines.

### F.1 — New files (Slice 2 creates)

| Path | Purpose | Approx lines |
|---|---|---|
| `frontend-public/src/components/editor/binding/types.ts` | 5 binding interfaces + `Binding` union + `validateBinding` function | ~120 |
| `frontend-public/src/components/editor/binding/__tests__/types.test.ts` | Unit tests for `validateBinding` (5 valid + invalid kinds) | ~150 |

**Note:** original Part A plan included `binding/index.ts` barrel re-export. Recon recommends DROPPING this — single `types.ts` is small enough that a barrel adds no value. Imports use `from '@/components/editor/binding/types'` directly.

If founder prefers the barrel for consistency with other editor subdirs (check `editor/store/index.ts` and `editor/registry/index.ts` if they exist), document. Surface in §H.

### F.2 — Modified files (Slice 2 extends)

| Path | Change | Approx delta |
|---|---|---|
| `frontend-public/src/lib/types/compare.ts` | Remove 5 binding interfaces + Binding union (lines 114-169); no re-export shim | -56 |
| `frontend-public/src/components/editor/types.ts` | Add `binding?: Binding` to Block interface | +2 (and 1 import) |
| `frontend-public/src/components/editor/registry/guards.ts` | Add optional-spread for binding in `hydrateImportedDoc` block construction (~line 681) | +5 |
| `frontend-public/src/components/editor/store/reducer.ts` | DUPLICATE_BLOCK preserves binding via JSON deep-clone (`JSON.parse(JSON.stringify(sourceBlock.binding)) as Binding`) to match `props` precedent | +1-3 |
| Existing test files for hydration / DUPLICATE_BLOCK / round-trip | Add binding-preservation assertions | +30-60 |

**Total: 5 modified files.** Smaller surface than originally planned in Part A draft (which estimated ~5 files but with larger per-file diffs).

### F.3 — Re-export shim strategy (UPDATED based on Part A §B.3 finding)

Originally Part A planned Option A (defensive shim with full re-exports). Part B confirmed **zero in-tree Binding consumers**, which makes Option C cleaner:

**Decision (recommend lock):** Option C — clean removal from `lib/types/compare.ts`, NO re-export shim.

Rationale:
- Zero in-tree imports of Binding types means no breakage to fix (Part A §B.3)
- Re-export shim accumulates technical debt with no benefit (no consumers of the shim path exist)
- Removing types from `lib/types/compare.ts` clarifies layer boundaries (`compare.ts` = wire types only)
- If external/future code accidentally imports from old path, fast-fail at compile time is better than silent re-export

**Caveat:** If Slice 2 impl finds a Binding import that wasn't surfaced in Part A §B.3 (e.g. generated fixture), surface in §H founder review. Part A's grep was exhaustive, so this should not happen.

Surface to §H as confirmation H.1.

### F.4 — Files NOT touched (scope discipline)

- All Slice 1b files (`useCompareState.ts`, `compareReducer.ts`, `CompareBadge.tsx`, etc.) — Slice 2 doesn't touch UI
- `lib/api/admin.ts` — no API changes
- `lib/api/errorCodes.ts` — no error code changes
- Locale files (`messages/en.json`, `messages/ru.json`) — no new locale keys
- Backend files — Phase 3.1e territory
- `validation/validate.ts`, `validation/invariants.ts`, `validation/contrast.ts`, `validation/block-data.ts` — read-only validators that ignore unknown sibling fields (per Part B §C.5)
- `editor/registry/blocks.ts` — block-type catalog unchanged
- `editor/registry/templates.ts` — templates unchanged
- `editor/export/zipExport.ts` — type-agnostic per Part B §D.5
- DEBT.md, CHANGELOG, other recon docs (except this Part C update)
- `polish.md` — P3-033 closure happens at Slice 2 impl PR merge time, not recon time

---

## §G — Test plan

Target length in recon doc: 60–100 lines.

### G.1 — `validateBinding` unit tests (`binding/__tests__/types.test.ts`, NEW)

Test categories:

| Category | Cases | Expected |
|---|---|---|
| Valid SingleValueBinding | 1 | returns same value typed |
| Valid TimeSeriesBinding (`period_range` with `from`/`to`) | 1 | returns same |
| Valid TimeSeriesBinding (`period_range` with `last_n`) | 1 | returns same |
| Valid CategoricalSeriesBinding (no `sort`/`limit`) | 1 | returns same |
| Valid CategoricalSeriesBinding (with `sort` + `limit`) | 1 | returns same |
| Valid MultiMetricBinding | 1 | returns same |
| Valid TabularBinding | 1 | returns same |
| Missing `kind` field | 1 | `null` |
| Unknown `kind` value | 1 | `null` |
| `kind: 'single'` missing `cube_id` | 1 | `null` |
| Wrong field type (`cube_id: 42`) | 1 | `null` |
| `null` / `undefined` / non-object input | 1 | `null` |
| Invalid filters (`Record<string,string>` violation) | 1 | `null` |
| Invalid sort enum value | 1 | `null` |
| Empty `cube_id` rejects | 1 | `null` |
| Empty `period` rejects | 1 | `null` |
| Empty `semantic_key` rejects | 1 | `null` |
| `last_n: 0` rejects | 1 | `null` |
| `last_n: -1` rejects | 1 | `null` |
| `last_n: 1.5` rejects | 1 | `null` |
| `last_n: NaN` rejects | 1 | `null` |
| `limit: 0` rejects | 1 | `null` |
| `limit: -1` rejects | 1 | `null` |
| `limit: 1.5` rejects | 1 | `null` |
| `period_range` with both `from/to` and `last_n` rejects | 1 | `null` |
| Filters with empty member id rejects | 1 | `null` |
| Valid `time_series` on `hero_stat` (universal validation, no per-type rejection) | 1 | `binding` preserved |
| Valid `single` on `table_enriched` (universal validation) | 1 | `binding` preserved |

**~26 cases (after FIX-3 + FIX-7 expansion).** Pure function tests, no mocks. Cover 7 valid configurations across 5 kinds (single, time_series with from/to, time_series with last_n, categorical_series without sort/limit, categorical_series with sort/limit, multi_metric, tabular) + 19 invalid paths (missing/wrong-type/empty-string/non-positive-int/mutex-violation/cross-type-block-type test locks).

### G.2 — `hydrateImportedDoc` extension tests (extend existing)

Add ~5–6 cases in the existing guards hydration test file:

| Case | Expected |
|---|---|
| Block without `binding` hydrates cleanly | block in result has no `binding` key |
| Block with valid `binding` hydrates with binding preserved | `block.binding` deep-equals input |
| Block with malformed `binding` hydrates without binding | block has no `binding` key; warning emitted |
| Block with `binding: undefined` hydrates without binding | no `binding` key (not `binding: undefined`) |
| Block with extra unknown top-level fields | existing strictness unchanged; unknown fields dropped |
| Block with malformed binding emits stable warning text | warning contains "Invalid block binding dropped" and block id |

**~5–6 cases.** Mirrors existing `hydrateImportedDoc` test style.

### G.3 — `sanitizeBlockProps` tests

**Per Part B §C.2:** sanitizer operates on `props` only, top-level fields never traverse it. **No sanitizer test changes needed.** Document this explicitly as a negative finding.

### G.4 — `DUPLICATE_BLOCK` reducer tests (extend existing)

Add ~3 cases in existing reducer tests:

| Case | Expected |
|---|---|
| `DUPLICATE_BLOCK` on block with binding | clone has same binding (deep-equal, not same reference) |
| `DUPLICATE_BLOCK` on block without binding | clone has no binding |
| Mutating duplicated block binding does not mutate source | source binding remains unchanged |

**~3 cases.** Last test prevents shallow-copy regressions.

### G.5 — Import/export round-trip tests (extend existing)

Add ~2 cases in existing import/export suite:

| Case | Expected |
|---|---|
| Export doc with bound blocks → JSON → re-import | `binding` preserved (deep-equal) |
| Round-trip with mixed binding/no-binding blocks | each block’s binding state preserved |

**~2 cases.**

### G.6 — Total test forecast

| Layer | Cases |
|---|---|
| `validateBinding` (NEW) | 14 |
| `hydrateImportedDoc` (extend) | 4–5 |
| `sanitizeBlockProps` | 0 (no change needed per §G.3) |
| `DUPLICATE_BLOCK` reducer (extend) | 3 |
| Import/export round-trip (extend) | 2 |
| **Total** | **36–37 tests** |

Within the 20–25 target range. Most additions are extensions to existing files; only `validateBinding` needs a new test file.

---

## §H — Founder questions

Target length in recon doc: 30–60 lines. **Down from 8 originally planned to 6** because Parts A+B resolved several items.

Resolved items NOT requiring founder review:
- ~~`validateBinding` strictness~~ — locked in §E.4 (strict reject)
- ~~Validator behavior on malformed binding~~ — locked in §C.3 (omit key when invalid; warn)
- ~~NumberFormat location~~ — does not exist; no relocation needed (§E.2)

Items requiring founder review:

### H.1 — Re-export shim strategy (LOCKED in decision #5; founder ack)
Per §F.3, recon now recommends **Option C (clean removal, no shim)** based on Part A §B.3 finding (zero in-tree consumers). Original Part A draft recommended Option A (defensive shim).

Founder confirms Option C OR overrides to Option A if external/future-proofing concern.

### H.2 — `DUPLICATE_BLOCK` preserves binding (NEW from Part B §D.2)
Per Part B §D.2: Option B recommended (preserve binding via `structuredClone`), with documented asymmetry versus `Block.locked` (stripped on duplicate).

Asymmetry rationale:
- `locked` strip: UX-protection role (duplicate starts editable)
- `binding` preserve: data-source pointer users can retarget after duplicate

Founder confirms Option B OR overrides to Option A (strip).

### H.3 — Per-block-type binding fit hints (defer to Slice 3a)
For Slice 3a binding editor UI, registry needs binding-fit metadata by block type (per §E.3 table). Placement options:
- Option A: `BlockRegistryEntry` grows `acceptsBinding?: BindingKind[]`
- Option B: standalone `bindingFitMap` under `editor/binding/`

Recommend **Option A** — registry-co-located metadata adjacent to block definitions.

### H.4 — `binding/index.ts` barrel export (style)
Per §F.1, recon drops the originally planned barrel and uses direct imports from `@/components/editor/binding/types`.

Founder confirms drop OR overrides for style consistency with other editor subdirs.

### H.5 — `format?: string` shape (no `NumberFormat`)
Per Part B §E.2, all 5 binding interfaces use `format?: string` (free-form tokens like `percent`, `currency:CAD`).

Founder confirms preserving this shape as-is, or flags that structured formatting must be introduced now (scope expansion).

### H.6 — P3-033 closure timing
After Slice 2 lands, P3-033 flips from pending to closed. Founder chooses:
- Option A: close inline in Slice 2 implementation PR/commit message
- Option B: close in a separate polish follow-up PR

Recommend **Option A** for single-PR traceability.

---

## §I — Anti-hallucination gates (final matrix for impl prompt)

Target length in recon doc: 30–50 lines.

This section lists gates the **implementation prompt** must enforce.

### I.1 — Pre-flight gates (impl-time)

- Verify branch is `claude/phase-3-1d-slice-2-impl` cut from `main`
- Verify recon Parts A+B+C are merged on `main`
- Verify Slice 1b implementation branch is merged (avoid cross-slice merge conflicts)
- Ignore Slice 1a polish state (Slice 2 does not touch `admin.ts`)
- Record baseline md5 for each file targeted by impl

### I.2 — Construction-pattern gates

- `hydrateImportedDoc` extension must mirror the existing Phase 1.6 `locked` optional-spread style near lines 678–682
- `DUPLICATE_BLOCK` extension preserves precedent's deep-clone pattern uniformly: `JSON.parse(JSON.stringify(sourceBlock.binding)) as Binding` (matches `props` precedent at same line in `store/reducer.ts:405`)
- `validateBinding` must follow §E.4 pseudocode shape (5 cases + 3 helpers; no per-kind extracted validators)

### I.3 — Forbidden patterns (impl-time)

- `import { Binding } from '@/lib/types/compare'`
- `Block.binding: Binding` (required field) instead of optional `binding?: Binding`
- Per-block-type validation logic inside `validateBinding`
- Introducing a new `NumberFormat` interface/type
- Adding `binding/index.ts` barrel
- Bumping `schemaVersion`
- Empty identity strings in binding (`cube_id: ""`, `period: ""`, etc.) — `validateBinding` must reject
- Non-positive or non-integer `last_n` / `limit` — `validateBinding` must reject
- `period_range` containing both `from/to` and `last_n` — `validateBinding` must reject

### I.4 — Required patterns (impl-time)

- Move all 5 binding interfaces from `lib/types/compare.ts` to `editor/binding/types.ts`
- Move/export `Binding` union from `editor/binding/types.ts`
- Export `validateBinding` from `editor/binding/types.ts`
- Extend `Block` in `editor/types.ts` with `binding?: Binding` (plus import)
- DUPLICATE_BLOCK constructs `binding` via `JSON.parse(JSON.stringify(sourceBlock.binding)) as Binding` in optional spread (matches the immediate local precedent at `store/reducer.ts:405` for `props` deep-cloning).
- In `hydrateImportedDoc`, preserve valid binding via optional spread gated by `validateBinding(b.binding)`
- Warning text on malformed binding rejection follows stable format: `"Block <id> (<type>): Invalid block binding dropped (kind=<kind>)"`

### I.5 — Test gates (impl-time)

- `validateBinding` unit tests: ≥26 cases (7 valid configurations + 19 invalid paths including strict numeric/string/mutex checks and universal-validation locks)
- `hydrateImportedDoc` extension tests: ≥5 cases (includes stable warning text assertion)
- `DUPLICATE_BLOCK` extension tests: ≥3 cases
- Import/export round-trip tests: ≥2 cases
- Total additions: ≥36 tests (within 30–40 expanded forecast range)
- Existing suites stay green (no regressions in hydration/duplicate behavior)

### I.6 — Honest stop conditions (impl-time)

- If `Block` interface baseline diverges from §A assumptions, STOP
- If `hydrateImportedDoc` construction shape diverges from §C.3 pattern, STOP
- If `DUPLICATE_BLOCK` shape diverges from §D.2 pattern, STOP
- If new Binding consumers appear in `lib/types/compare.ts` path since recon, STOP and revisit shim decision
- If `editor/binding/types.ts` already exists with nontrivial content, STOP and reassess file plan

### I.7 — Out-of-scope discipline (impl-time)

- No UI changes (Slice 3a/3b)
- No backend changes (Phase 3.1e)
- No locale changes
- No `parseAdminPublicationError` extraction (P3-032 defer)
- No cache-miss locale wording tweak (P3-039 defer)
- No DEBT.md status edits during implementation
