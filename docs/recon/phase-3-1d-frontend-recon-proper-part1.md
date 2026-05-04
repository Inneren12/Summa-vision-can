# Phase 3.1d Frontend Recon-Proper Part 1 — Schema + Scope (§A–§C)

**Type:** Reconnaissance (read-only + design)  
**Branch:** `claude/phase-3-1d-frontend-recon-proper-part1`  
**Date:** 2026-05-04  
**Output:** `docs/recon/phase-3-1d-frontend-recon-proper-part1.md`

---

## §A — Existing frontend surface recap

### §A.1 Editor entry points

- The publication editor route is implemented in Next.js at `frontend-public/src/app/admin/editor/[id]/page.tsx` and performs publication fetch + hydration before rendering the client shell. `AdminEditorPage` calls `fetchAdminPublicationServer(id)`, hydrates `initialDoc`, and returns `<AdminEditorClient publicationId={id} initialDoc={initialDoc} initialEtag={publication.etag} />`. (`frontend-public/src/app/admin/editor/[id]/page.tsx:1-43`)
- The client editor shell imports and renders the canonical editor package from `frontend-public/src/components/editor/index.tsx`, including strict import validation through `validateImportStrict`, and save/load plumbing through `buildUpdatePayload` + `fetchAdminPublication` + `updateAdminPublication`. (`frontend-public/src/components/editor/index.tsx:13-38`)
- Recon context from pre-recon remains consistent: publication CRUD/edit surface is in `frontend-public/` (Next.js), not Flutter publication CRUD. Flutter references are adjacent (content brief view actions, publication chips, mock payloads) rather than owner flows. (`docs/recon/phase-3-1d-frontend-pre-recon.md:385-389`)

### §A.2 `admin.ts` API client

- Current exported API calls are:
  - `fetchAdminPublication(...)` (`frontend-public/src/lib/api/admin.ts:91-110`)
  - `fetchAdminPublicationList(...)` (`frontend-public/src/lib/api/admin.ts:112-130`)
  - `updateAdminPublication(...)` (`frontend-public/src/lib/api/admin.ts:150-197`)
  - `cloneAdminPublication(...)` (`frontend-public/src/lib/api/admin.ts:200-236`)
- `publishAdminPublication` is absent from this file today. (`frontend-public/src/lib/api/admin.ts:1-236`)
- Typed backend error support exists via `BackendApiError` class (`status`, `code`, `details`) and parsing through `extractBackendErrorPayload` from `errorCodes` integration. (`frontend-public/src/lib/api/admin.ts:11,58-75,169-193,214-231`)

### §A.3 CanonicalDocument + Block types

Verbatim from `frontend-public/src/components/editor/types.ts`:

```ts
export interface BlockProps {
  [key: string]: any;
}

export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;
}

export interface CanonicalDocument {
  schemaVersion: number;
  templateId: string;
  page: PageConfig;
  sections: Section[];
  blocks: Record<string, Block>;
  meta: DocMeta;
  review: Review;
}
```

Source lines: (`frontend-public/src/components/editor/types.ts:28-45,123-131`)

Conclusion: `Block.props` remains open dictionary (`[key: string]: any`) at the type level. (`frontend-public/src/components/editor/types.ts:28-30`)

### §A.4 Block registry mechanics

- Block registry `BREG` map is defined in `frontend-public/src/components/editor/registry/blocks.ts` and enumerates the known block types with their default prop shape (`dp`) and guards. (`frontend-public/src/components/editor/registry/blocks.ts:10-47`)
- New document creation (`mkDoc`) is generic over template block types and creates each block with `{ id, type, props, visible }`, where `props` begins from `BREG[type].dp` + overrides and normalization. (`frontend-public/src/components/editor/registry/templates.ts:8-33`)
- `sanitizeBlockProps` is strict-allowlist sanitization against `BREG[type].dp` keys and drops unknown keys by design.

Verbatim sanitizer comment fragment:

> Unknown keys are dropped; type-mismatched values are replaced with defaults. (`frontend-public/src/components/editor/registry/guards.ts:464-466`)

> Unknown keys (not in defaults) are dropped — strict mode (`frontend-public/src/components/editor/registry/guards.ts:527-527`)

Implementation range: (`frontend-public/src/components/editor/registry/guards.ts:468-531`)

### §A.5 Persistence path

- Editor persistence serializes the entire canonical doc into `document_state` through `buildUpdatePayload(doc)`, with:

```ts
const documentState = JSON.stringify(doc);
const payload: UpdateAdminPublicationPayload = {
  document_state: documentState,
  ...
};
```

Source lines: (`frontend-public/src/components/editor/utils/persistence.ts:181-193`)

- `buildUpdatePayload` also emits derived fields (`chart_type`, `visual_config`, `review`, and editorial text columns) alongside `document_state`. (`frontend-public/src/components/editor/utils/persistence.ts:186-207`)

### §A.6 Backend single-value contract recap

- Snapshot table + identity are currently single-row-per-block with unique `(publication_id, block_id)`:
  - ORM model docs: `Identity: UNIQUE(publication_id, block_id)`. (`backend/src/models/publication_block_snapshot.py:35-47`)
  - Migration constraint: `sa.UniqueConstraint("publication_id", "block_id", name="uq_publication_block_snapshot_pub_block")`. (`backend/migrations/versions/20260504_1200_phase_3_1d_publication_block_snapshot.py:67-71`)
- Snapshot row shape includes publication+block identity, semantic context (`cube_id`, `semantic_key`, `coord`, `period`), raw resolve input (`dims_json`, `members_json`), and publish-time fingerprint (`mapping_version_at_publish`, `source_hash_at_publish`, `value_at_publish`, `missing_at_publish`, `is_stale_at_publish`, `captured_at`). (`backend/src/models/publication_block_snapshot.py:54-84`)
- Compare endpoint exists at `POST /{publication_id}/compare` and returns `PublicationComparatorResponse` from `PublicationStalenessService.compare_for_publication(...)`. (`backend/src/api/routers/admin_publications.py:613-655`)
- Publish endpoint supports `bound_blocks` wrapper via `PublicationPublishRequest` (`bound_blocks: list[BoundBlockReference]`) and captures snapshots in best-effort mode when provided. (`backend/src/schemas/staleness.py:173-183`, `backend/src/api/routers/admin_publications.py:560-566,591-603`)
- Phase 3.1d DEBT entries are confirmed as present in pre-recon summary (`DEBT-064..070 entries: YES`). (`docs/recon/phase-3-1d-frontend-pre-recon.md:371-372`)

---

## §B1 — Multi-value storage shape pick

### Constraints to satisfy

1. Backward compatible with shipped single-value rows.
2. Supports N>1 points per block.
3. Supports point-level + block-level comparison semantics.
4. Publish walker can capture all points.
5. Compare can provide aggregate now and per-point details later.
6. Compatible with canonical `Block.binding` typed schema.
7. Reasonable migration from shipped 3.1d state.

---

### Option A — Composite key in existing table

#### 1) Schema sketch

```sql
ALTER TABLE publication_block_snapshot
  ADD COLUMN point_key VARCHAR(128) NULL,
  ADD COLUMN point_kind VARCHAR(32) NULL,
  ADD COLUMN point_meta JSONB NULL;

-- replace old unique
DROP INDEX/CONSTRAINT uq_publication_block_snapshot_pub_block;

CREATE UNIQUE INDEX uq_pub_block_point
  ON publication_block_snapshot(publication_id, block_id, point_key);

-- nullable point_key policy for single-value
-- either NULL + partial unique for single, or sentinel 'default'.
```

#### 2) Single-value compatibility

- Existing rows survive by backfilling `point_key='default'` (recommended over NULL to avoid null-unique edge ambiguity).
- Single-value semantics preserved as one row per block with default point.

#### 3) Multi-value capture path

- Walker resolves binding to point list and emits one upsert per point key.
- Example: `line_editorial` with 3 series × 12 periods writes 36 rows.

#### 4) Compare path

- Compare queries all rows for publication, grouped by `block_id`.
- Each point re-resolved and compared; block severity reduced from point severities (`any stale => stale`, etc.).

#### 5) Indexing requirements

- `INDEX (publication_id)` (already exists).
- `UNIQUE (publication_id, block_id, point_key)`.
- Optional `INDEX (publication_id, block_id)` for block aggregation scan.

#### 6) Migration cost

- Medium/high risk because it mutates shipped identity constraint.
- Data rewrite/backfill required for all existing rows.
- DDL lock risk on hot table (currently small, but non-zero downtime planning required).

#### 7) Per-point detail availability

- Excellent; per-point rows are first-class and directly queriable.

#### 8) Storage size impact

- Highest row amplification among options (row overhead repeated per point).

#### 9) Pros

- Simple relational model for per-point compare.
- Direct SQL filtering for per-point diagnostics.
- No JSON parsing overhead for point traversal.
- Strong uniqueness/integrity at point level.

#### 10) Cons

- Breaks shipped unique contract and requires careful migration.
- Increases write volume and index churn heavily.
- Sentinel/default-point handling adds semantic complexity.
- Harder rollback path due to identity-model change.

---

### Option B — JSONB points array in existing table

#### 1) Schema sketch

```sql
ALTER TABLE publication_block_snapshot
  ADD COLUMN points JSONB NULL;

-- keep UNIQUE(publication_id, block_id)
-- retain existing scalar columns for single-value back-compat during transition
-- eventually treat scalar fields as denormalized convenience or legacy fields.
```

`points` shape (conceptual):

```json
[
  {
    "point_key": "series=primary|period=2024-Q3",
    "period": "2024-Q3",
    "coord": "1.2.44",
    "value_at_publish": "6.73",
    "missing_at_publish": false,
    "is_stale_at_publish": false,
    "source_hash_at_publish": "...",
    "mapping_version_at_publish": 12,
    "captured_at": "2026-05-04T00:00:00Z"
  }
]
```

#### 2) Single-value compatibility

- Keep current row identity untouched.
- Existing single-value rows can be lazily interpreted as one implicit point, then optionally migrated to explicit `points=[...]`.

#### 3) Multi-value capture path

- Walker produces normalized point list and writes one row per block with full `points` array.
- Publish capture remains one upsert per block, not N upserts.

#### 4) Compare path

- Compare loads each block row, iterates `points` array in service layer, resolves/recompares each point.
- Aggregate severity computed in memory with optional per-point detail payload.

#### 5) Indexing requirements

- Existing `INDEX (publication_id)` remains primary fetch path.
- Optional GIN on `points` only if later server-side JSON querying becomes necessary.
- Most compare workloads remain publication-scoped, so wide JSON index may be unnecessary initially.

#### 6) Migration cost

- Medium/low operational risk.
- Additive migration only; no unique constraint change.
- Backfill can be online and incremental.

#### 7) Per-point detail availability

- Good future-proofing: per-point details available from JSON array; can be emitted by compare endpoint without schema redesign.

#### 8) Storage size impact

- Medium: JSON overhead per point, but avoids repeated fixed row/index overhead.

#### 9) Pros

- Preserves shipped table identity and backward compatibility.
- Minimal migration blast radius.
- Publish capture remains block-centric (aligns with current flow).
- Keeps compare aggregate response natural while enabling point detail payload.

#### 10) Cons

- JSON validation/invariants enforced mostly in app code.
- Harder SQL-only ad hoc analytics on point-level history.
- Potential larger row payloads for very dense blocks.
- Requires careful schema/versioning discipline for point object shape.

---

### Option C — New point table

#### 1) Schema sketch

```sql
-- keep publication_block_snapshot unchanged

CREATE TABLE publication_block_point_snapshot (
  id BIGSERIAL PRIMARY KEY,
  publication_id INT NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
  block_id VARCHAR(128) NOT NULL,
  point_key VARCHAR(128) NOT NULL,
  cube_id VARCHAR(50) NOT NULL,
  semantic_key VARCHAR(200) NOT NULL,
  coord VARCHAR(50) NOT NULL,
  period VARCHAR(20) NULL,
  value_at_publish TEXT NULL,
  missing_at_publish BOOLEAN NOT NULL,
  is_stale_at_publish BOOLEAN NOT NULL,
  mapping_version_at_publish INT NULL,
  source_hash_at_publish VARCHAR(64) NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (publication_id, block_id, point_key)
);

CREATE INDEX ix_pbps_pub ON publication_block_point_snapshot(publication_id);
CREATE INDEX ix_pbps_pub_block ON publication_block_point_snapshot(publication_id, block_id);
```

#### 2) Single-value compatibility

- Fully compatible; existing single-value table untouched.
- Single-value blocks may remain on legacy table only.

#### 3) Multi-value capture path

- Walker routes: single-value bindings to legacy table, multi-value bindings to point table.
- For uniformity, optional duplication to summary row in legacy table may be needed.

#### 4) Compare path

- Compare must union/branch across two storage sources.
- Aggregation logic becomes dual-path (legacy rows + point rows).

#### 5) Indexing requirements

- New table needs pub and pub+block indexes plus unique key.
- Legacy indexes remain.

#### 6) Migration cost

- Low risk to existing data; purely additive table.
- Higher service complexity and dual-source maintenance.

#### 7) Per-point detail availability

- Excellent, same as Option A with first-class rows.

#### 8) Storage size impact

- High for point-heavy blocks (similar to A); also duplicates some semantics across two tables.

#### 9) Pros

- Zero-touch to shipped table constraints.
- Clean relational shape for point-level operations.
- Easy to query/debug per-point rows.
- Clear phased rollout (start multi-value only).

#### 10) Cons

- Dual storage model increases cognitive and code complexity.
- Compare/publish logic bifurcates by binding type forever (or until consolidation).
- Potential drift/inconsistency between summary and point layers.
- Higher long-term maintenance burden than single-store option.

---

### §B1 Recommendation

**RECOMMENDED — Option B (JSONB points array), pending founder approval at final gate.**

Rationale: Option B best balances constraints **(1)** backward compatibility with shipped single-value identity, **(4)** block-oriented publish walker flow, and **(7)** reasonable migration risk by avoiding unique-key rewrites. It also satisfies **(2)** multi-point capture and supports **(3)/(5)** point-level compare with block-level aggregate in service code while retaining future per-point API detail output.

Secondary driver is founder rollout strategy (sliced, low-risk progression) plus existing 3.1d backend stability lock. Option B avoids introducing permanent dual-path complexity of Option C while avoiding the heavier identity migration burden of Option A.

---

## §B2 — Canonical typed binding schema

### §B2.1 Top-level location decision

**Decision: add top-level `Block.binding` (sibling of `props`), not `props.binding`.**

Trade-offs:

- Avoids collision with strict prop sanitizer allowlist (`sanitizeBlockProps`) that drops unknown keys under `props`. (`frontend-public/src/components/editor/registry/guards.ts:464-466,527-531`)
- Separates editorial render props from data-resolve plumbing, keeping existing `BREG[type].dp` focused on visual defaults.
- Minimizes per-block registry churn (no need to add binding keys to every bindable block’s `dp`).
- Cleaner forward compatibility for typed union evolution (`kind` discriminator) without modifying each block prop guard.

### §B2.2 Single-value binding shape

```ts
interface SingleValueBinding {
  kind: 'single';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>; // dim_id -> member_id
  period: string; // e.g. '2024-Q3' or 'latest'
  format?: string;
}
```

Resolver contract alignment inputs:
- publish-time bound block payload currently serializes to `dims: list[int]`, `members: list[int]`, `period?: str` at backend ingress. (`backend/src/schemas/staleness.py:162-170`)
- existing resolve endpoint path remains `GET /api/v1/admin/resolve/{cube_id}/{semantic_key}` with filters/period represented as query parameters in resolver flow (Phase 3.1c router/service path). (`backend/src/api/routers/admin_resolve.py:5,57-58`)

### §B2.3 Multi-value binding shapes

Given §B1 recommendation (Option B), v1 frontend schema should define explicit multi-value kinds now, with one deferred for staged rollout:

```ts
interface TimeSeriesBinding {
  kind: 'time_series';
  cube_id: string;
  semantic_key: string;
  filters: Record<string, string>;
  period_range: { from: string; to: string } | { last_n: number };
  series_dim?: string;
  format?: string;
}

interface MultiMetricBinding {
  kind: 'multi_metric';
  cube_id: string;
  metrics: Array<{ semantic_key: string; label?: string }>;
  filters: Record<string, string>;
  period: string;
  format?: string;
}

interface TabularBinding {
  kind: 'tabular';
  cube_id: string;
  columns: Array<{ semantic_key: string; label?: string }>;
  row_dim: string;
  filters: Record<string, string>;
  period: string;
  format?: string;
}
```

Decision:
- Define all three (`time_series`, `multi_metric`, `tabular`) in schema now.
- Ship only `single` in 3.1d v1 frontend behavior.
- Activate multi-value kinds in 3.1e dependency phase.

### §B2.4 Discriminated union + Block field

```ts
type Binding =
  | SingleValueBinding
  | TimeSeriesBinding
  | MultiMetricBinding
  | TabularBinding;

interface BlockProps {
  [key: string]: any;
}

interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;
  binding?: Binding;
}
```

Discriminator rule: `binding.kind` is mandatory for all variants; runtime dispatch in compare/walker/editor is `switch (binding.kind)`.

### §B2.5 `document_state` migration impact

- Because persistence already writes full `CanonicalDocument` JSON (`document_state: JSON.stringify(doc)`), adding optional `binding` field is forward-compatible. Old docs simply omit it. (`frontend-public/src/components/editor/utils/persistence.ts:181-188`)
- `sanitizeBlockProps` does not need changes for top-level `binding` because it only sanitizes `rawProps` against `BREG[type].dp`. (`frontend-public/src/components/editor/registry/guards.ts:468-531`)
- `validateImportStrict` / hydration pipeline should be updated in Part 2 to accept and type-check optional `block.binding` sibling field during document validation, rather than dropping/rejecting it.
  - validator/sanitizer touch surface: `frontend-public/src/components/editor/registry/guards.ts` (`validateImportStrict` + hydration pipeline in same module; `sanitizeBlockProps` unaffected).

### §B2.6 Resolver invocation contract

Canonical transport transformation proposal:

1. Editor binding stores semantic filters as `Record<string, string>` (`dim_id -> member_id`) for UX ergonomics.
2. Resolver-preview adapter maps this shape into current resolve query shape for `GET /admin/resolve/{cube_id}/{semantic_key}`.
3. Publish capture adapter maps same binding to `BoundBlockReference` (`dims[]`, `members[]`, `period`) per backend schema. (`backend/src/schemas/staleness.py:162-170`)

Dependency note:
- Current resolver is singular-value oriented; multi-value bindings (`time_series`, `multi_metric`, `tabular`) will require either resolver iteration strategy client/server-side or a new batch resolve contract in 3.1e. Track as Part 3 DEBT candidate (backend dependency), not a 3.1d v1 blocker.

---

## §C — Block binding capability scope

### §C.1 In-scope (binding-capable) block types — v1 catalog

| Block type | In scope? | Binding kind | Rationale |
|---|---|---|---|
| `hero_stat` | Yes | `single` | Canonical single-value hero metric; maps directly to existing 3.1d snapshot model. |
| `delta_badge` | Yes | `single` | Single derived/comparison display value; can bind one resolved numeric then format for delta text. |
| `comparison_kpi` | Yes (phase-gated) | `multi_metric` | Natural fit for multiple KPI cards from one cube context with metric list. |
| `bar_horizontal` | Yes (phase-gated) | `time_series` | Represents repeated point set by category/period; requires N-point capture. |
| `line_editorial` | Yes (phase-gated) | `time_series` | Multi-point temporal series; core 3.1e candidate. |
| `table_enriched` | Yes (phase-gated) | `tabular` | Table semantics are clearer as rows/columns contract than forced time-series encoding. |
| `small_multiple` | Yes (phase-gated) | `time_series` | Multiple panels from grouped dimension with shared period range. |

Block definitions source: (`frontend-public/src/components/editor/registry/blocks.ts:17-47`)

### §C.2 Out-of-scope (not bindable) — v1

- `eyebrow_tag`: editorial text label, static authoring surface. (`frontend-public/src/components/editor/registry/blocks.ts:11-12`)
- `headline_editorial`: editorial headline copy. (`frontend-public/src/components/editor/registry/blocks.ts:13-14`)
- `subtitle_descriptor`: editorial subtitle copy. (`frontend-public/src/components/editor/registry/blocks.ts:15-16`)
- `body_annotation`: editorial annotation copy. (`frontend-public/src/components/editor/registry/blocks.ts:21-22`)
- `source_footer`: source/method text, not data-resolve target in v1. (`frontend-public/src/components/editor/registry/blocks.ts:23-24`)
- `brand_stamp`: branding/layout marker. (`frontend-public/src/components/editor/registry/blocks.ts:25-26`)

### §C.3 Open scope questions resolved (5/5)

1. **`delta_badge.value` typing**  
   Decision: use typed numeric resolve result + formatter at binding layer; keep rendered prop string for now. This avoids hardwiring locale/formatting in snapshot fingerprints and keeps compare drift numeric-safe.

2. **`comparison_kpi` binding shape**  
   Decision: one `multi_metric` binding per block (single shared cube/filters/period + list of metrics), not per-card independent bindings. This keeps block-level aggregation coherent and avoids fragmented UX.

3. **`table_enriched` schema**  
   Decision: introduce `TabularBinding` (generic tabular contract), not domain-specific hardcoding. This decision is reflected in §B2.3.

4. **`small_multiple` per-panel binding**  
   Decision: grouped-by-dimension model (`time_series` + `series_dim`) rather than independent per-panel bindings, to keep one coherent query context and predictable compare aggregation.

5. **Binding location**  
   Decision cross-reference: top-level `Block.binding` (from §B2.1), not nested inside `props`.

### §C.4 Sanitizer impact summary

- With top-level `Block.binding`, strict prop sanitizer remains unchanged because it only governs `props` keys against `BREG[type].dp`. (`frontend-public/src/components/editor/registry/guards.ts:468-531`)
- Therefore no per-type `dp` expansions are required for binding metadata.
- Part 2/3 work should focus on document validator/type guard acceptance of optional `binding` sibling field.

### §C.5 Phase split lock

- **Phase 3.1d v1 frontend ships:** `hero_stat`, `delta_badge` only (single-value path on shipped backend snapshot design).
- **Phase 3.1e dependency phase (or 3.1d v2 + backend dep):** `comparison_kpi`, `bar_horizontal`, `line_editorial`, `table_enriched`, `small_multiple`.

This split aligns with §B1 recommendation because Option B can onboard multi-value incrementally without altering shipped 3.1d single-value identity semantics.

---

## Cross-reference check (GATE-F)

- §B1 storage pick (Option B) aligns with §B2.3 by carrying multi-value point collections naturally in block-level payloads.
- §B2.1 binding location (`Block.binding`) aligns with §C.4 sanitizer impact (no `dp` mutation burden).
- §C.3 Q3 (`table_enriched`) introduced `TabularBinding`, and §B2.3 includes it.
- §C.5 phase split matches §B1 migration-cost framing (low-risk additive path first, multi-value later).

---

## Glossary additions flagged for Part 3 i18n mapping

`docs/i18n-glossary.md` already includes **refresh** and **compare** terms in workflow/action section. (`docs/i18n-glossary.md:207-209`)

Proposed new glossary term entries to add in Part 3 i18n planning:

- stale
- fresh
- drift
- snapshot
- republish
- unknown
- point-level
- aggregate severity
- binding
- unbound

(Flag-only in this part; no key map authored here.)
