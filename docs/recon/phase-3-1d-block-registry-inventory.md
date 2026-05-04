# Phase 3.1d Frontend — Block Registry Inventory

**Status:** discovery (read-only, micro pre-recon)  
**Branch:** claude/phase-3-1d-block-registry-inventory  
**Date:** 2026-05-04  
**Purpose:** anchor §C of upcoming recon-proper — list block types and classify binding capability before recon-proper drafts schema design.

---

## §A — Registered block types (complete list)

| Block type ID | Definition file | Notes |
|---|---|---|
| eyebrow_tag | `frontend-public/src/components/editor/registry/blocks.ts` | Text tag string (`text`). |
| headline_editorial | `frontend-public/src/components/editor/registry/blocks.ts` | Headline text with align control. |
| subtitle_descriptor | `frontend-public/src/components/editor/registry/blocks.ts` | Supporting subtitle text. |
| hero_stat | `frontend-public/src/components/editor/registry/blocks.ts` | Hero stat value + label. |
| delta_badge | `frontend-public/src/components/editor/registry/blocks.ts` | Delta string + direction semantic. |
| body_annotation | `frontend-public/src/components/editor/registry/blocks.ts` | Editorial annotation text. |
| source_footer | `frontend-public/src/components/editor/registry/blocks.ts` | Source/method text footer. |
| brand_stamp | `frontend-public/src/components/editor/registry/blocks.ts` | Brand placement struct prop. |
| bar_horizontal | `frontend-public/src/components/editor/registry/blocks.ts` | Ranked bar chart data array. |
| line_editorial | `frontend-public/src/components/editor/registry/blocks.ts` | Line-series time chart data. |
| comparison_kpi | `frontend-public/src/components/editor/registry/blocks.ts` | KPI cards list (value+delta). |
| table_enriched | `frontend-public/src/components/editor/registry/blocks.ts` | Enriched rows/columns table data. |
| small_multiple | `frontend-public/src/components/editor/registry/blocks.ts` | Multi-panel series array. |

Total: 13 block types.

Verbatim grep evidence:
```bash
grep -rn "BlockType\|BLOCK_TYPES\|block_type:\|blockType:" frontend-public/src/components/editor/ frontend-public/src/lib/types/ 2>/dev/null
frontend-public/src/components/editor/registry/guards.ts:409:  const requiredBlockTypes = new Set(["source_footer", "brand_stamp", "headline_editorial"]);
...
```

```bash
grep -rn "type: ['\"]\|'type':" frontend-public/src/components/editor/registry/ 2>/dev/null
# (no output)
```

```bash
ls frontend-public/src/components/editor/registry/
blocks.ts
guards.ts
templates.ts
```

```bash
sed -n '1,220p' frontend-public/src/components/editor/registry/blocks.ts
# (BREG map contains all 13 keys listed above)
```

---

## §B — Per-block props inventory

### eyebrow_tag
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props (verbatim from source):
  ```ts
  dp:{text:"STATISTICS CANADA · TABLE 18-10-0004"}
  ```
- Data semantics: editorial label text.
- Existing binding-like fields: no.

### headline_editorial
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{text:"Canadian Mortgage Rates\nHit 15-Year High",align:"left"}
  ```
- Data semantics: editorial headline text.
- Existing binding-like fields: no.

### subtitle_descriptor
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{text:"Average 5-year fixed rate, March 2026"}
  ```
- Data semantics: editorial subtitle text.
- Existing binding-like fields: no.

### hero_stat
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{value:"6.73%",label:"5-year fixed rate"}
  ```
- Data semantics: single displayed metric value with label.
- Existing binding-like fields: no.

### delta_badge
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{value:"+247 bps since Jan 2022",direction:"negative"}
  ```
- Data semantics: one comparative delta descriptor.
- Existing binding-like fields: no.

### body_annotation
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{text:"Rates represent posted rates from chartered banks"}
  ```
- Data semantics: editorial/context text.
- Existing binding-like fields: no.

### source_footer
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{text:"Source: Statistics Canada, Table 18-10-0004-01",methodology:""}
  ```
- Data semantics: source attribution/method text.
- Existing binding-like fields: no.

### brand_stamp
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{position:"bottom-right"}
  ```
- Data semantics: layout/branding placement.
- Existing binding-like fields: no.

### bar_horizontal
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{items:[{label:"Vancouver",value:12.8,flag:"🇨🇦",highlight:true},...],unit:"×",benchmarkValue:5.0,benchmarkLabel:"Affordable threshold",showBenchmark:true}
  ```
- Data semantics: multi-item numeric series chart.
- Existing binding-like fields: no.

### line_editorial
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{series:[{label:"CPI All Items",data:[1.9,0.7,3.4,6.8,3.9,2.7,2.4,2.1],role:"primary"},{label:"BoC Target",data:[2,2,2,2,2,2,2,2],role:"benchmark"}],xLabels:["2019","2020","2021","2022","2023","2024","2025","2026"],yUnit:"%",showArea:true}
  ```
- Data semantics: multi-point time/categorical series chart.
- Existing binding-like fields: no.

### comparison_kpi
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{items:[{label:"Population Growth",value:"3.2%",delta:"+1.4pp YoY",direction:"positive"},...]}
  ```
- Data semantics: repeated KPI values (N cards).
- Existing binding-like fields: no.

### table_enriched
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{columns:["Country","Individual","Corporate","Property","Consumption","Score"],rows:[{country:"Estonia",flag:"🇪🇪",vals:[2,2,1,18,100.0],rank:1},...]}
  ```
- Data semantics: multi-row, multi-column numeric dataset.
- Existing binding-like fields: no.

### small_multiple
- File: `frontend-public/src/components/editor/registry/blocks.ts`
- Props:
  ```ts
  dp:{items:[{label:"New York",flag:"🇺🇸",data:[-0.5,-1.2,-3.1,-4.5,-5.8,-6.2,-5.1,-4.8]},...],yUnit:"%"}
  ```
- Data semantics: multiple series groups (N panels × M points).
- Existing binding-like fields: no.

---

## §C — Binding capability classification

| Block type | Class | Future binding shape | Notes |
|---|---|---|---|
| hero_stat | DATA — single-value | SingleValueBinding | Single `value` + label field. |
| delta_badge | DATA — single-value | SingleValueBinding | One value string + direction enum. |
| comparison_kpi | DATA — multi-value | TimeSeriesBinding (or multi-metric list binding) | `items[]` contains repeated KPI values/deltas. |
| bar_horizontal | DATA — multi-value | TimeSeriesBinding | `items[]` numeric values per label. |
| line_editorial | DATA — multi-value | TimeSeriesBinding | `series[].data[]` against `xLabels[]`. |
| table_enriched | DATA — multi-value | TimeSeriesBinding | `rows[].vals[]` matrix-like data. |
| small_multiple | DATA — multi-value | TimeSeriesBinding | `items[].data[]` for multiple entities. |
| eyebrow_tag | TEXT/EDITORIAL | — | Plain text tag. |
| headline_editorial | TEXT/EDITORIAL | — | Plain text headline. |
| subtitle_descriptor | TEXT/EDITORIAL | — | Plain text subtitle. |
| body_annotation | TEXT/EDITORIAL | — | Plain text annotation. |
| source_footer | TEXT/EDITORIAL | — | Attribution/method text. |
| brand_stamp | MEDIA | — | Branding/layout position only. |

Counts:
- DATA single-value: 2
- DATA multi-value: 5
- TEXT/EDITORIAL: 5
- MEDIA: 1
- UNCERTAIN: 0

---

## §D — Block registry mechanics

### Block creation flow
New documents are created via `mkDoc(...)` in `registry/templates.ts`; for each template `blockTypes[]`, it resolves `BREG[bt]`, clones `reg.dp`, applies template/override props, normalizes data via `normalizeBlockData(...)`, and creates block objects of shape `{ id, type, props, visible }`. This is generic typed creation from `{type, props}` via registry defaults, not type-specific constructors.

### Props validation/sanitization on import
`sanitizeBlockProps(...)` in `registry/guards.ts` enforces strict default-key sanitization: starts from `reg.dp`, keeps only keys that exist in defaults, type-checks/coerces values by default type, and drops unknown keys (“Unknown keys … are dropped — strict mode”). This means import hydration is allowlist-by-default-shape, despite `BlockProps` being open (`[key: string]: any`) at type level.

### Implication for adding `Block.binding` field
Inventory implication only: if binding metadata is stored inside `block.props`, each binding-capable block type must include that binding key in `BREG[type].dp` (or sanitizer behavior must be changed), otherwise import/hydration drops it. Additionally, `mkDoc` defaults and any block-data normalization paths should tolerate that field.

Verbatim grep evidence:
```bash
grep -rn "defaultProps\|DEFAULT_PROPS\|createDefaultBlock\|mkBlock\|mkDoc" frontend-public/src/components/editor/registry/ 2>/dev/null
frontend-public/src/components/editor/registry/templates.ts:8:export function mkDoc(tid: string, tpl: TemplateEntry, over: Record<string, BlockProps> = {}): CanonicalDocument {
```

```bash
grep -rn "sanitizeBlockProps\|allowedProps\|propAllowlist" frontend-public/src/components/editor/registry/ 2>/dev/null
frontend-public/src/components/editor/registry/guards.ts:468:function sanitizeBlockProps(
frontend-public/src/components/editor/registry/guards.ts:676:        props: sanitizeBlockProps(type, key, b.props, warnings),
```

---

## §E — Open questions for recon-proper

1. `delta_badge.value` and `comparison_kpi.items[].value` are string-typed display values, not numeric-typed (`number`). Should v1 binding resolve to formatted strings or typed numerics with formatting layer?
2. For `comparison_kpi`, does v1 bind one shared query with multiple selected metrics, or one binding per item card?
3. For `table_enriched`, should binding target a generic tabular dataset (`rows/columns`) or a fixed domain schema matching current `country/vals/rank` shape?
4. For `small_multiple`, should each `items[]` panel support independent series binding, or should all panels derive from one query grouped by dimension?
5. Given strict prop sanitization on import, should binding metadata live in `block.props` per-type defaults or at top-level `Block` (`Block.binding`) to avoid per-type prop-key updates?

---

## Summary Report

PHASE 3.1d BLOCK REGISTRY INVENTORY (micro pre-recon)

Branch: claude/phase-3-1d-block-registry-inventory (off main)  
New commit: TBD

Files actually viewed:
- frontend-public/src/components/editor/types.ts
- frontend-public/src/components/editor/registry/guards.ts
- frontend-public/src/components/editor/registry/blocks.ts
- frontend-public/src/components/editor/registry/templates.ts
- frontend-public/src/components/editor/renderer/blocks.ts
- frontend-public/src/components/editor/validation/block-data.ts
- docs/recon/phase-3-1d-frontend-pre-recon.md

Inventory totals:
- Block types found: 13
- DATA single-value candidates: 2
- DATA multi-value candidates: 5
- TEXT/EDITORIAL: 5
- MEDIA: 1
- UNCERTAIN (need founder review): 0

Open questions for recon-proper: 5
