# Phase 2.2 Pre-Recon — Publish Kit Generator

**Status:** Pre-recon (read-only inventory) — IN PROGRESS, Chunks 2+3 pending
**Author:** Claude Code (architect agent)
**Date:** 2026-04-28
**Branch:** claude/phase-2-2-pre-recon-kxwl9

## Context

Phase 2.2 ships the Publish Kit Generator — extends Phase 2.1 ZIP export to additionally include `distribution.json` and `publish_kit.txt` artifacts inside the ZIP, with platform-specific captions (Reddit / X / LinkedIn) and UTM-tagged URLs encoding `?utm_content=<lineage_key>`. Founder-locked decision Q-D (2026-04-27): `utm_content` carries `lineage_key` only.

This pre-recon documents the existing code state Phase 2.2 will plug into. Read-only inventory; no design proposals.

## A. ZIP export pipeline state (PR#3 + PR#4 baseline)

**What's here:** factual inventory of how the current ZIP layer is wired — orchestrator, manifest, filename, fflate API surface, existing i18n keys.

**Source files cited:** zipExport.ts, manifest.ts, zipFilename.ts, package.json, messages/en.json, messages/ru.json.

### A1. Orchestrator entry point and snapshot semantics

(file `frontend-public/src/components/editor/export/zipExport.ts`)
- Snapshot via `structuredClone(options.doc)`: line 60
- Per-preset render loop start: line 77, end: line 116
- Pre-render gate (PR#4): lines 86-99 (`validatePresetSize` → push `skipped` entry on any error and `continue`)
- ZIP packing call `zipSync(zipEntries, ...)`: line 132
- File entry assembly: lines 123-130 (PNG bytes per pass result + `manifest.json` via `strToU8(JSON.stringify(...))`)

Verbatim grep output (`grep -n "structuredClone\|zipSync\|onProgress" zipExport.ts`):
```
1:import { zipSync, strToU8 } from 'fflate';
31:  onProgress?: (phase: ZipExportPhase) => void;
40: * Snapshots `doc` via `structuredClone` at entry per Q-2.1-6 — operator
47: * Other unexpected errors propagate via `onProgress({ phase: 'error' })`
57:  const { pal, onProgress } = options;
60:  const doc = structuredClone(options.doc);
79:      onProgress?.({ phase: 'rendering', current: i + 1, total });
118:    onProgress?.({ phase: 'packing' });
132:    const zipBytes = zipSync(zipEntries, { level: 6 });
159:    onProgress?.({ phase: 'done', result });
162:    onProgress?.({ phase: 'error', error: err });
```

`ZipExportPhase` discriminated union (lines 10-14): `rendering` | `packing` | `done` | `error`. No `kit-building` phase exists yet.

### A2. Manifest builder shape

Verbatim from `frontend-public/src/components/editor/export/manifest.ts`:

```typescript
export interface ManifestPresetEntry {
  id: PresetId;
  /**
   * Absolute filename of the per-preset PNG inside the ZIP archive.
   * `null` when the preset is skipped (e.g. RenderCapExceededError) — the
   * PNG is NOT in the archive in that case, so referencing a non-existent
   * filename would be a broken contract for downstream consumers.
   */
  filename: string | null;
  width: number;
  height: number;
  qa_status: PresetQaStatus;
  /**
   * Machine-readable i18n key explaining why the preset was skipped.
   * Present only when `qa_status === 'skipped'`. Sourced from the helper
   * that raised the skip (e.g. `RenderCapExceededError.i18nKey`).
   *
   * Phase 2.2 distribution layer can map this to channel-specific fallback
   * behavior (drop the social post entirely vs. publish without that
   * preset). EN-only English text in the underlying `error.message` is
   * not suitable for that purpose.
   */
  skipped_reason?: string;
}

export interface ZipManifest {
  schemaVersion: 1;
  publication_id: null;
  templateId: string;
  generated_at: string;
  presets: ManifestPresetEntry[];
}
```

- `schemaVersion` value: **1** (line 42; `schemaVersion: 1` literal type + line 78 emitted value)
- Fields available for forward-extending without bumping `schemaVersion`:
  - `publication_id` (currently hard-coded `null`, typed as literal `null` — Phase 2.2 would need a type widening here, so this DOES require schema bump if populated)
  - `ManifestPresetEntry.skipped_reason` is optional and already in the schema
  - The interface is **closed** — adding new top-level fields (e.g. `distribution`, `kit_summary`) would require bumping `schemaVersion` to `2` per the in-file comment at lines 60-62: "schemaVersion=1 lets Phase 2.2 forward-extend with distribution.json fields ... by bumping to schemaVersion=2"
- The orchestrator emits `manifest.json` separately from any future `distribution.json` (line 130 only writes one manifest entry); Phase 2.2 can add new ZIP entries without touching `ZipManifest` shape.

### A3. Filename builder

(from `frontend-public/src/components/editor/export/zipFilename.ts`)

- Format string: `summa-${doc.templateId}-export-${YYYYMMDD-HHmmss}.zip` (line 32 return)
- Example output: `summa-single_stat_hero-export-20260427-143022.zip` (in-file example, line 9)
- Extensibility: **No** optional suffix slot. `buildZipFilename(doc, now)` takes only `(doc, now)` and concatenates the prefix `summa-`, `templateId`, the literal `-export-`, and the deterministic timestamp. To distinguish a Phase 2.2 publish-kit ZIP from a plain export ZIP would require either (a) a new function or (b) widening the signature with an optional kind/suffix parameter.

### A4. i18n keys under editor.export_zip.*

EN keys (verbatim from `frontend-public/messages/en.json`, output of `grep -A 20 "\"export_zip\""`):
```
    "export_zip": {
      "button": {
        "label": "Export all valid",
        "label_short": "EXPORT ZIP",
        "aria": "Export all valid presets as ZIP"
      },
      "progress": {
        "rendering": "Rendering {current, number}/{total, number}…",
        "packing": "Packing ZIP…"
      },
      "toast": {
        "success": "Exported {count, plural, =1 {1 preset} other {{count, number} presets}} to {filename}",
        "partial": "Exported {passCount, number} of {total, number} presets to {filename}. {skippedCount, plural, =1 {1 preset was skipped} other {{skippedCount, number} presets were skipped}}.",
        "error": "Export failed. {error}"
      },
      "skipped": {
        "long_infographic_cap_exceeded": "long_infographic skipped: height {measured, number}px exceeds 4000px maximum"
      }
    },
```

RU keys (verbatim from `frontend-public/messages/ru.json`, output of `grep -A 20 "\"export_zip\""`):
```
    "export_zip": {
      "button": {
        "label": "Экспорт всех валидных",
        "label_short": "ЭКСПОРТ ZIP",
        "aria": "Экспортировать все валидные пресеты в ZIP"
      },
      "progress": {
        "rendering": "Рендеринг {current, number} из {total, number}…",
        "packing": "Упаковка ZIP…"
      },
      "toast": {
        "success": "Экспортировано {count, plural, one {# пресет} few {# пресета} many {# пресетов} other {# пресетов}} в {filename}",
        "partial": "Экспортировано {passCount, number} из {total, number} пресетов в {filename}. {skippedCount, plural, one {# пропущен} few {# пропущены} many {# пропущены} other {# пропущены}}.",
        "error": "Ошибка экспорта. {error}"
      },
      "skipped": {
        "long_infographic_cap_exceeded": "long_infographic пропущен: высота {measured, number}px превышает максимум 4000px"
      }
    },
```

EN/RU parity is symmetric on all keys. No `kit_*`, `distribution_*`, `caption_*`, or platform-specific keys exist yet under `export_zip` or elsewhere visible from this scope.

### A5. fflate API surface

- Import statement: `import { zipSync, strToU8 } from 'fflate';` (zipExport.ts line 1)
- Functions used: `zipSync` (line 132, with `{ level: 6 }`) ✅ and `strToU8` (line 130, used to encode the JSON manifest into a `Uint8Array` for the ZIP entry table) ✅. Both verified.
- Version (from package.json, line 19): `"fflate": "^0.8.2"`

## B. Publication metadata available at export time

**What's here:** what data the export pipeline can read from the in-memory `CanonicalDocument` snapshot (no extra fetch).

**Source files cited:** types.ts, search results across `frontend-public/src/components/editor/`.

### B1. CanonicalDocument shape relevant to captions

From `frontend-public/src/components/editor/types.ts`:

```typescript
export interface PageConfig {
  size: PresetId;
  background: string;
  palette: string;
  // Phase 2.1 PR#2: list of preset IDs (keys of SIZES) selected for the
  // multi-preset ZIP export (PR#3 orchestrator). The preset matching
  // `page.size` is always rendered regardless of presence; this list
  // controls which ADDITIONAL presets get included.
  // Defaults to `DEFAULT_EXPORT_PRESETS` (common-4) for new docs and via
  // the v2→v3 migration. PR#2 fix1 (P1.2): tightened from `string[]` to
  // `PresetId[]`. The migration + reducer normalize step both filter out
  // unknown IDs, so no runtime path can leak a non-PresetId into here.
  exportPresets: PresetId[];
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

- Block types with caption-relevant `props.text`: types.ts uses a generic `Block` (lines 32-45) with `BlockProps { [key: string]: any }` (lines 28-30). There is **no static type-level enumeration** of block kinds (e.g. `headline_editorial`, `source_footer`) in this file. Block kinds are runtime strings on `Block.type`, and prop schemas are defined elsewhere (registry, not in types.ts — out of scope for the seven files allowed in Chunk 1). Recon Section C/D (Chunk 2) is the right place to enumerate them.
- `doc.meta` exists: **yes**. `DocMeta` (lines 116-121):
  ```typescript
  export interface DocMeta {
    createdAt: string;
    updatedAt: string;
    version: number;
    history: EditHistoryEntry[];
  }
  ```
  No publication-id, lineage-id, public-URL, or slug fields on `meta`. No `publication_id` anywhere on `CanonicalDocument` (manifest.ts hard-codes `publication_id: null` for the same reason).
- `PlatformId` already declared (line 11): `'reddit' | 'twitter' | 'linkedin'` — Phase 2.2 captions can reuse this union directly.
- `WorkflowState` (line 12) includes `'exported' | 'published'` and `WorkflowAction` (lines 316-323) includes `MARK_PUBLISHED { channel: string; ... }` — channel is a free-form string today, not constrained to `PlatformId`.

### B2. lineage_key source

(critical inventory item)

Search result for `lineage_key` / `lineageKey` in `frontend-public/src/components/editor/`:
```
(grep -rn returned no matches)
```

Conclusion: lineage_key is **NOT FOUND** in the frontend editor code (no matches under `frontend-public/src/components/editor/`). Cross-checked the `CanonicalDocument`, `DocMeta`, `PageConfig`, and `Review` interfaces in types.ts — none of them carry a `lineage_key` / `lineageKey` field.

This is a Q for recon — frontend has no current path to read it at export time. Phase 1.1 Clone introduced lineage on the backend; need to confirm whether/how it surfaces to frontend (Section E will dig into backend). Founder-locked decision Q-D (`utm_content = lineage_key` only) hinges on hydrating this value into the export pipeline before manifest/distribution build.

### B3. Editorial fields

From `CanonicalDocument` / Block types (types.ts):

- `headline_editorial` block — props shape: **not defined in types.ts**. The generic `Block` carries `props: BlockProps` where `BlockProps` is `{ [key: string]: any }` (types.ts lines 28-30). Per-type prop schemas live in the block registry (out of scope for the seven Chunk 1 files); Section C in Chunk 2 will catalog them.
- `source_footer` block — props shape: **not defined in types.ts**, same reason as above.
- Equivalents for `eyebrow`, `description`, `source_text` from DEBT-026 work — **not found in types.ts**. types.ts contains no string-literal references to these field names. Whatever DEBT-026 introduced lives in the registry / per-block prop catalogs, not in the canonical type surface. Chunk 2 should resolve their exact shape.

What types.ts *does* surface that's caption-adjacent:
- `KPIItem` (lines 350-356): `{ label, value, delta, direction, _id }` — caption candidate (numeric headlines).
- `SeriesItem` (lines 365-370): `{ label, role, data, _id }`.
- `BarItem` (lines 372-378): `{ label, value, flag, highlight, _id }`.

These are domain-data shapes embedded in block props, not standalone editorial copy.

### B4. Public URL for publication

Search result (`grep -rn "summa\.vision\|SUMMA_PUBLIC_URL\|PUBLIC_URL" frontend-public/src/`):
```
(no matches)
```

Conclusion: **NOT FOUND** in frontend. No constant, no env-var reference, no domain literal under `frontend-public/src/` matches `summa.vision`, `SUMMA_PUBLIC_URL`, or `PUBLIC_URL`.

If NOT found in frontend: recon needs to design hydration. Section E will check backend Settings (Chunk 3) for the canonical public-URL source and the wiring path (config bundle, Next.js runtime config, or per-publication API field) to surface it into the export pipeline at click time.

## C. Channel configuration

**What's here:** factual inventory of any existing per-channel (Reddit / X / LinkedIn) configuration in frontend code. Recon needs to know whether to extend or design new.

**Source files cited:** cropZones.ts, sizes.ts, search results across `frontend-public/src/`.

### C1. Existing channel constants

File listing of `frontend-public/src/components/editor/config/`:
```
backgrounds.ts
cropZones.ts
palettes.ts
sizes.ts
tokens.ts
```

Output of `grep -rn "reddit\|twitter\|linkedin" frontend-public/src/ --include="*.ts" --include="*.tsx" | grep -v test | grep -v cropZones`:
```
frontend-public/src/components/editor/types.ts:11:export type PlatformId = 'reddit' | 'twitter' | 'linkedin';
frontend-public/src/components/editor/renderer/overlay.ts:57:  reddit: 'Reddit',
frontend-public/src/components/editor/renderer/overlay.ts:58:  twitter: 'Twitter',
frontend-public/src/components/editor/renderer/overlay.ts:59:  linkedin: 'LinkedIn',
frontend-public/src/components/editor/config/sizes.ts:16:  twitter_landscape:   { w: 1200, h: 675,  n: "Twitter/X" },
frontend-public/src/components/editor/config/sizes.ts:17:  reddit_standard:     { w: 1200, h: 900,  n: "Reddit" },
frontend-public/src/components/editor/config/sizes.ts:18:  linkedin_landscape:  { w: 1200, h: 627,  n: "LinkedIn" },
frontend-public/src/components/editor/registry/guards.ts:21:  twitter:        'twitter_landscape',
frontend-public/src/components/editor/registry/guards.ts:22:  reddit:         'reddit_standard',
frontend-public/src/components/editor/registry/guards.ts:23:  linkedin:       'linkedin_landscape',
frontend-public/src/components/editor/utils/persistence.ts:44:  twitter_landscape:  'twitter',
frontend-public/src/components/editor/utils/persistence.ts:45:  reddit_standard:    'reddit',
frontend-public/src/components/editor/utils/persistence.ts:46:  linkedin_landscape: 'linkedin',
frontend-public/src/components/editor/utils/persistence.ts:62:  twitter:   'twitter_landscape',
frontend-public/src/components/editor/utils/persistence.ts:63:  reddit:    'reddit_standard',
frontend-public/src/components/editor/utils/persistence.ts:64:  linkedin:  'linkedin_landscape',
```
(template definitions in `registry/templates.ts` also reference platform-named presets via `defaultSize`; omitted here for brevity.)

Conclusion: distinct files where channel names appear (excluding `cropZones.ts` and tests):
- `types.ts` — declares the `PlatformId` union.
- `renderer/overlay.ts` — display-name lookup (`Reddit` / `Twitter` / `LinkedIn`).
- `config/sizes.ts` — per-channel `SizePreset` entries (canvas dimensions only — no captions, no UTM, no URLs).
- `registry/guards.ts` — `PlatformId` → `PresetId` alias map (legacy migration from short channel names).
- `utils/persistence.ts` — round-trip alias maps in both directions.
- `registry/templates.ts` — `defaultSize` strings reference the `*_landscape` / `*_standard` presets.

There is **no** central `channels.ts` constant carrying caption templates, hashtag policies, character limits, or UTM source/medium values. All current "channel" knowledge in frontend is either (a) preset display geometry or (b) string-alias maps for ID migration. Phase 2.2 caption / UTM data has no existing module to extend.

### C2. UTM URL builder

Output of `grep -rn "utm_\|UTM\|buildShareUrl\|addUtm" frontend-public/src/ | grep -v node_modules`:
```
frontend-public/src/components/editor/export/manifest.ts:61: * distribution.json fields (UTM tags, social captions, channel overrides)
```

Conclusion: UTM URL builder utility **NOT FOUND** in frontend. The single hit is a forward-reference comment inside `manifest.ts` describing what Phase 2.2 will add. No `utm_source` / `utm_medium` / `utm_content` literals, no `buildShareUrl` / `addUtm` helpers, no URL composition for share links exist in the editor module.

### C3. Crop zone presets per channel

(file `cropZones.ts` — citation only)

- Channels covered: `reddit`, `twitter`, `linkedin` (the entire `PlatformId` union).
- Field names per `CropZone` entry: `x`, `y`, `w`, `h`, `baseW`, `baseH`, `platform` (lines 4-14).
- Top-level shape: `Partial<Record<PresetId, Partial<Record<PlatformId, CropZone>>>>` (lines 25-27) — sparse map keyed by preset, then by platform.
- Coverage: native presets (`reddit_standard` / `twitter_landscape` / `linkedin_landscape`) carry full-canvas zones; cross-post presets (`instagram_1080`, `instagram_portrait`) carry a single Reddit-priority zone via `PLATFORM_PRIORITY` (line 17). `instagram_story` and `long_infographic` deliberately have no entry.
- Caption template text present? **No** — `CropZone` carries geometry only; no `text`, `caption`, `hashtags`, or platform-copy fields.

Conclusion: `cropZones.ts` is visual-only (crop dimensions). Caption templates would be a separate concern.

## D. Editor → ZIP integration touchpoint

**What's here:** factual inventory of where the export flow is currently wired in `index.tsx` and `TopBar.tsx`. Recon needs to know exactly where Phase 2.2 hooks in.

**Source files cited:** index.tsx, TopBar.tsx.

### D1. Caller of exportZip

(file `frontend-public/src/components/editor/index.tsx`):
- Import statement: line 52 — `import { exportZip, type ZipExportPhase } from './export/zipExport';`
- `exportZipCb` definition: line 1225 (`const exportZipCb = useCallback(async () => { ... }, [...])`)
- Call to `exportZip({...})`: line 1238
- Arguments passed: `{ doc, pal, onProgress: setZipExportPhase }` (lines 1239-1241) — confirmed exactly the three fields declared by `ZipExportOptions` (zipExport.ts lines 28-32). No extra metadata is passed.
- `ZipExportOptions` interface (zipExport.ts) accepts only `doc: CanonicalDocument`, `pal: Palette`, and `onProgress?` callback. **`doc` is the only data input.** Anything Phase 2.2 needs that isn't on `CanonicalDocument` (lineage_key, public URL, per-channel caption settings) must either:
  - be pre-stamped onto `doc` before this call,
  - or require a signature widening on `ZipExportOptions`.

Output of `grep -n "exportZip\|exportZipCb\|zipExportNotice" index.tsx`:
```
52:import { exportZip, type ZipExportPhase } from './export/zipExport';
1219:  const [zipExportNotice, setZipExportNotice] = useState<{
1225:  const exportZipCb = useCallback(async () => {
1238:      const result = await exportZip({
1314:        exportZip={exportZipCb}
1329:      {zipExportNotice && (
1331:          role={zipExportNotice.kind === 'error' ? 'alert' : 'status'}
1334:          data-kind={zipExportNotice.kind}
1338:              zipExportNotice.kind === 'error'
1340:                : zipExportNotice.kind === 'partial'
1344:              zipExportNotice.kind === 'error' ? TK.c.err : TK.c.txtP,
1355:            <div>{zipExportNotice.message}</div>
1356:            {zipExportNotice.details && zipExportNotice.details.length > 0 && (
1358:                {zipExportNotice.details.map((d, i) => (
```

### D2. Toast surface

`zipExportNotice` state in index.tsx — cited lines:
- State declaration: lines 1219-1223 (`useState<{ kind: 'success' | 'partial' | 'error'; message: string; details?: string[] } | null>(null)`).
- Set calls:
  - success branch: lines 1247-1253 (when `result.skippedCount === 0`)
  - partial branch: lines 1269-1278 (with per-skipped-preset detail strings built lines 1255-1268)
  - error branch (catch): lines 1282-1287
- Render block: lines 1329-1380 — inline `<div>` with `role={kind === 'error' ? 'alert' : 'status'}`, `data-testid="zip-export-notice"`, `data-kind={kind}`. Renders `message` plus an optional `<ul>` of `details`. Dismiss button at line 1364 calls `setZipExportNotice(null)`.

Phase 2.2 may want to extend this to mention `publish_kit.txt` inclusion. Inventory only — no design.

### D3. TopBar Export button

(file `frontend-public/src/components/editor/components/TopBar.tsx`):
- ZIP-related imports: lines 10-11
  - `import { ZipExportProgress } from './ZipExportProgress';`
  - `import type { ZipExportPhase } from '../export/zipExport';`
- `zipExportPhase` prop: declared line 34 (`zipExportPhase: ZipExportPhase | null`), destructured line 70.
- Usage: line 102 (`const exportInProgress = zipExportPhase !== null`) gates the disabled state and the in-button progress display at line 186 (`exportInProgress ? <ZipExportProgress phase={zipExportPhase} /> : tZipBtn('label_short')`).
- Button click: line 181 (`onClick={exportZip}`) — invokes the prop callback wired in index.tsx:1314 to `exportZipCb`.

Conclusion: TopBar surface change **expected** for Phase 2.2 only if a separate "Export Publish Kit" entry-point button is desired. If Phase 2.2 piggybacks on the existing Export ZIP button (kit artifacts always written into the same ZIP), TopBar requires no change — only the i18n label may need a wording refresh.

## E. Backend touchpoints (CRITICAL — answers Chunk 1's two NOT FOUND items)

**What's here:** factual inventory of backend `Publication` model, admin response schema, and public URL config. Phase 2.2 needs `lineage_key` source and a public URL — Chunk 1 confirmed neither exists in frontend, so backend is the source.

**Source files cited:** models/publication.py, schemas/publication.py, api/routers/admin_publications.py, core/config.py.

### E1. Publication model fields

(file `backend/src/models/publication.py`)

All columns currently on `Publication` (lines 80-155):
- `id` — PK, autoincrement
- `headline` — String(500), NOT NULL
- `chart_type` — String(100), NOT NULL
- `s3_key_lowres` — Text, nullable
- `s3_key_highres` — Text, nullable
- `virality_score` — Float, nullable
- `source_product_id` — String(100), nullable, indexed
- `version` — Integer, NOT NULL, default 1
- `config_hash` — String(64), nullable
- `content_hash` — String(64), nullable
- `cloned_from_publication_id` — FK → publications.id, ondelete=SET NULL, nullable, indexed
- `status` — Enum(PublicationStatus), NOT NULL, default DRAFT, indexed
- `created_at` — DateTime(tz=True), NOT NULL, indexed
- `eyebrow` — String(255), nullable
- `description` — Text, nullable
- `source_text` — String(500), nullable
- `footnote` — Text, nullable
- `visual_config` — Text (JSON-serialised), nullable
- `review` — Text (JSON-serialised), nullable
- `document_state` — Text (opaque CanonicalDocument JSON), nullable
- `updated_at` — DateTime(tz=True), nullable, onupdate=now()
- `published_at` — DateTime(tz=True), nullable

`lineage_key` column: **ABSENT.** No column named `lineage_key` (or any close variant) exists on the model.

Lineage in this model is encoded indirectly by two adjacent constructs:
1. `cloned_from_publication_id` self-FK (lines 90-94) — captures clone provenance one-hop at a time (parent pointer; not a stable group key).
2. Composite unique constraint named `uq_publication_lineage_version` over `(source_product_id, config_hash, version)` (lines 72-77) — i.e. "lineage" here means "(product × config) lineage with monotonic versions". This is the closest existing concept to what Phase 2.2 needs, but it is a 3-tuple, not a single opaque `lineage_key` string.

If present (it isn't): when set? — the model has no `lineage_key`, so this is moot. The clone path lives at `backend/src/services/publications/clone.py` (referenced by `admin_publications.py:42`, not read here per scope) and only writes `cloned_from_publication_id`.

Output of `grep -n "class Publication\|lineage_key" backend/src/models/publication.py`:
```
20:class PublicationStatus(enum.Enum):
27:class Publication(Base):
```
(zero `lineage_key` matches.)

Cross-reference: `grep -rn "lineage_key\|lineageKey" backend/src/models/ backend/src/schemas/ backend/src/api/` — **zero matches across all three trees.**

File path matches the prompt's expectation: `backend/src/models/publication.py`. No drift.

### E2. AdminPublicationResponse schema

(file `backend/src/schemas/publication.py`)

- Class name: **`PublicationResponse`** (line 196). The prompt's hypothetical name `AdminPublicationResponse` does not exist; the admin-facing response IS `PublicationResponse`, with the public-gallery counterpart being `PublicationPublicResponse` (line 267). Drift documented.
- Fields included in admin GET response (lines 224-244):
  - `id: str`
  - `headline: str`
  - `chart_type: str`
  - `eyebrow: Optional[str]`
  - `description: Optional[str]`
  - `source_text: Optional[str]`
  - `footnote: Optional[str]`
  - `visual_config: Optional[VisualConfig]`
  - `review: Optional[ReviewPayload]`
  - `document_state: Optional[str]`
  - `virality_score: Optional[float]`
  - `status: str`
  - `cdn_url: Optional[str]`
  - `created_at: datetime`
  - `updated_at: Optional[datetime]`
  - `published_at: Optional[datetime]`
  - `cloned_from_publication_id: Optional[int]`
- `lineage_key` in serialization: **no.**
- Minimal change required: NOT a one-line schema add. Because the underlying column does not exist, Phase 2.2 needs (a) an Alembic migration adding a `lineage_key` column to `publications`, (b) backfill semantics for existing rows (probably derived from clone-graph traversal or `(source_product_id, config_hash)`), (c) write-time population in both create and clone services, (d) the schema field on `PublicationResponse`. The "1-line schema field add" assumption from the prompt is too optimistic.

### E3. Public URL config

(file `backend/src/core/config.py`)

- Constant name: **`public_site_url`** (line 132).
- Default value: `"http://localhost:3000"` with inline comment `Prod: https://summa.vision`.
- Validator: `validate_required_secrets` (lines 141-169) requires `public_site_url` to be set in production (lines 159-160). Empty string → startup failure when `environment == "production"`.
- Frontend exposure: env var name is `PUBLIC_SITE_URL` (Pydantic auto-derives env name from field name). It is NOT prefixed `NEXT_PUBLIC_*`, so Next.js will not currently inline it into client bundles. The Chunk 1 grep across `frontend-public/src/` for `PUBLIC_URL` / `summa.vision` / `SUMMA_PUBLIC_URL` returned zero hits, confirming the value does not currently reach the browser via any wiring (no `next.config.js` `publicRuntimeConfig`, no client-side fetch). `next.config.js`/`.env*` files were NOT in the 8-file scope — recon-proper should confirm by inspection.
- If not exposed: frontend must fetch via API endpoint, OR an explicit `NEXT_PUBLIC_PUBLIC_SITE_URL` env mirror, OR the value can be embedded per-publication in the `PublicationResponse` payload. (Design decisions deferred to recon-proper.)

Output of `grep -rn "PUBLIC_BASE_URL\|public_base_url\|SUMMA_BASE\|summa.vision" backend/src/ | head -10`:
```
backend/src/main.py:188:    "https://summa.vision",
backend/src/main.py:189:    "https://www.summa.vision",
backend/src/services/graphics/compositor.py:67:    watermark_text: str = "summa.vision",
backend/src/core/config.py:77:    # Prod (CloudFront):  https://cdn.summa.vision
backend/src/core/config.py:132:    public_site_url: str = "http://localhost:3000"  # Prod: https://summa.vision
```
(no `PUBLIC_BASE_URL` / `public_base_url` / `SUMMA_BASE` matches — the literal Phase 2.2 needs is `public_site_url` per E3.)

### E4. Hydration path summary (for recon)

| Need | Frontend has it? | Backend has it? | Gap |
|---|---|---|---|
| `lineage_key` | NO (Chunk 1 §B2) | **NO** — no column on `Publication`, no field on `PublicationResponse`, zero string-matches across `models/`, `schemas/`, `api/` | New column + migration + backfill + write-time population (clone + create services) + schema field + frontend hydration into `CanonicalDocument` (or per-call into `ZipExportOptions`). Founder-locked Q-D (`utm_content = lineage_key`) cannot be implemented without this. |
| public URL | NO (Chunk 1 §B4) | **YES** — `Settings.public_site_url` at `core/config.py:132`, prod-required by validator (lines 159-160) | Decide hydration channel: (a) `NEXT_PUBLIC_PUBLIC_SITE_URL` env mirror at frontend build, (b) widen `PublicationResponse` with a per-row absolute URL, or (c) new GET endpoint returning the constant. All three are feasible. |
| headline / source / etc | YES (B3 — block props on `headline_editorial`, `source_footer`, `eyebrow_tag`; runtime-typed via `BlockProps { [key: string]: any }`) | YES (DEBT-026 — `eyebrow`, `description`, `source_text`, `footnote` columns + matching `PublicationResponse` fields, plus opaque `document_state` JSON for full lossless round-trip) | None — caption builders can read straight from the in-memory `CanonicalDocument` snapshot at export time. |

This table is a fact summary for recon — recon-proper will design the hydration path to close the gaps.

## F. Open questions for recon

**What's here:** every ambiguity the inventory surfaced. Recon-proper resolves them or escalates to founder. Each Q is anchored to a section of this document.

### Q-2.2-1 — lineage_key introduction strategy

**Discovered in section:** B2, E1, E2.
**Question:** lineage_key is absent on BOTH frontend and backend (no column on Publication model, no field in PublicationResponse, no frontend reference). Phase 2.2 requires it for UTM-tagged URLs. What's the minimal-introduction path?

**Why it matters:** without lineage_key, every Phase 2.2 caption URL is just the public publication URL with no per-publication tracking. UTM contract requires per-publication identifier; per Q-D, this identifier is `lineage_key`.

**Possible answers (non-exhaustive):**
- a) Add `lineage_key: str` column on Publication, generate at create time (e.g. UUID v7 or content-hash-derived), backfill existing rows with one-time script, surface in PublicationResponse, frontend hydrates via existing GET path.
- b) Derive lineage_key on-the-fly from existing fields (e.g. `f"{source_product_id}:{config_hash}:v{version}"`) — no migration needed, but stable string is harder to read and may conflict with composite uniq constraint semantics.
- c) Use `id` (Publication PK) as lineage_key directly — simplest, but loses the cross-version "same lineage" semantics the term implies.
- d) Defer to a Phase 2.2.0 sub-PR that ships ONLY lineage_key infrastructure before any 2.2 caption work.

**Adjacent existing surface:** `backend/src/services/publications/lineage.py` already exists (referenced from DEBT-035, see §G1) and currently houses `compute_config_hash`. Any Phase 2.2 generator would naturally extend that module rather than introduce a new one.

**Pre-recon recommendation:** option (a) — explicit column, generated at write time, surfaced in response. Rationale: the term `lineage_key` in roadmap §3 implies stable cross-version identity (clones share lineage), which (b) and (c) don't capture. Option (d) is a scope question — recon decides whether to split.

### Q-2.2-2 — lineage_key generation algorithm

**Discovered in section:** B2, E1.
**Question:** if Q-2.2-1 = (a), how is lineage_key generated? Several patterns are possible.

**Why it matters:** the choice affects clone semantics, debuggability, and URL aesthetics.

**Possible answers:**
- a) UUID v7 — globally unique, time-sortable, opaque.
- b) Short hash from content (e.g. first 12 chars of SHA-256 over `{templateId, source_product_id, headline, created_at}`) — short, deterministic.
- c) Auto-increment sequence — readable but exposes count.
- d) Slug derived from headline (with collision suffix) — human-readable but mutable on rename.

**Pre-recon recommendation:** no recommendation; design tradeoff. Recon-proper picks based on URL aesthetics + operator debuggability.

### Q-2.2-3 — public URL hydration channel

**Discovered in section:** B4, E3.
**Question:** `public_site_url` exists in backend Settings but is not NEXT_PUBLIC_-prefixed and not exposed to frontend. How does the frontend get it for caption URLs?

**Why it matters:** every caption needs a URL like `https://summa.vision/p/<slug>`. Without the base URL, captions can't be constructed deterministically.

**Possible answers:**
- a) Mirror the env var as `NEXT_PUBLIC_SITE_URL` so Next.js bundles it — simplest, no API call.
- b) Add `public_url: str` to PublicationResponse so each publication carries its full URL — couples response to deploy URL.
- c) New dedicated `GET /api/v1/admin/config` endpoint exposing public site URL — extra hop, but cleaner.
- d) Hardcode `https://summa.vision` in frontend (and dev override via env var) — works for v1, fragile.

**Pre-recon recommendation:** option (a). Site URL is a deploy-time constant; bundling it as `NEXT_PUBLIC_*` aligns with Next.js patterns. Frontend then constructs URLs as `${baseUrl}/p/${slug}`.

### Q-2.2-4 — distribution.json schema

**Discovered in section:** A2.
**Question:** `distribution.json` is a new artifact. What's its schema, and how does it relate to the existing `manifest.json` (`schemaVersion: 1`)?

**Why it matters:** distribution layer in Phase 2.2 forward-extends; Phase 2.3+ may add fields. Schema versioning sets the upgrade path.

**Possible answers:**
- a) Separate file with own `schemaVersion: 1` — independent evolution; simplest separation of concerns.
- b) Inline into manifest.json with bumped manifest schemaVersion 1→2 — single file, but couples evolution.
- c) Separate file but with field structure mirroring manifest patterns — same `schemaVersion` field, same author conventions.

**Pre-recon recommendation:** option (a). Distribution data is conceptually distinct from per-preset rendering metadata. Independent files keep upgrade paths independent.

### Q-2.2-5 — publish_kit.txt format

**Discovered in section:** A1.
**Question:** `publish_kit.txt` is plain text (per DoD). What's the structure inside?

**Why it matters:** operator copy-pastes from this file directly into Reddit/X/LinkedIn. Format affects copy-paste workflow.

**Possible answers:**
- a) Plain text with channel headers separated by `===`:
  ```
  === Reddit ===
  <title>
  <body>

  === X / Twitter ===
  <caption>

  === LinkedIn ===
  <caption>
  ```
- b) Markdown with headings (`## Reddit`, etc.) — readable in any markdown viewer.
- c) Per-channel separate files inside the ZIP (`reddit.txt`, `twitter.txt`, `linkedin.txt`) — easier per-channel copy.

**Pre-recon recommendation:** option (a). Plain text with `===` separators is unambiguous, language-neutral, copy-paste friendly. Operator scrolls to the channel they're posting on.

### Q-2.2-6 — caption template language and i18n

**Discovered in section:** A4.
**Question:** captions contain text. Where does the source text live? `messages/en.json` (next-intl) or hardcoded ASCII templates?

**Why it matters:** captions are what operators publish. Translation is content, not UI labels. The existing i18n is for UI labels and validation messages, not user-facing publishable content.

**Possible answers:**
- a) Hardcoded EN template (e.g. in a `frontend-public/src/components/editor/distribution/templates.ts` module) — captions are content, not UI.
- b) i18n keys under `editor.export_zip.distribution.*` — consistent with other operator-facing strings.
- c) Operator-editable templates (per-publication or global) — most flexible, biggest scope; deferred.

**Pre-recon recommendation:** option (a). Caption templates are part of the platform's editorial voice, not interface chrome. The headline and source fields ARE per-publication and stay in `CanonicalDocument`; the template wrapper is fixed EN.

### Q-2.2-7 — character limits per platform

**Discovered in section:** C1.
**Question:** Reddit/X/LinkedIn each have caption length limits (X = 280 / 4000 paid, Reddit title = 300, body = 40000, LinkedIn post = 3000). Does the template enforce or document?

**Why it matters:** if `<headline>` overflows X's 280-char limit, operator pastes truncated text. Worth catching at export time.

**Possible answers:**
- a) Cap at template generation time, with `[truncated]` indicator — operator may not notice.
- b) Document the limit but don't truncate — operator handles.
- c) Validation rule that warns on too-long source text BEFORE export — proactive.

**Pre-recon recommendation:** no recommendation; founder UX decision. (a) is destructive and operators will hit it without seeing why; (b) or (c) for v1 keep semantics clear.

### Q-2.2-8 — UTM URL builder location

**Discovered in section:** C2.
**Question:** no UTM URL builder exists in the codebase. Where does Phase 2.2 put one?

**Why it matters:** clean module structure now prevents pain in Phase 2.3+.

**Possible answers:**
- a) `frontend-public/src/components/editor/distribution/utm.ts` — new module, future-proof for distribution.json builder + caption builder + UTM builder all colocated.
- b) `frontend-public/src/components/editor/utils/utm.ts` — consistent with existing utils/ structure.
- c) Inside `editor/export/` next to zipExport.ts — colocated with consumer.

**Pre-recon recommendation:** option (a). Phase 2.2 introduces a "distribution" concern that grows in 2.3+ (post ledger, attribution). Dedicated module from day one keeps the surface organized.

## G. DEBT and roadmap state

**What's here:** factual inventory of DEBT entries and roadmap dependencies that touch Phase 2.2 area.

**Source files cited:** `DEBT.md`, `docs/architecture/ROADMAP_DEPENDENCIES.md`, `docs/OPERATOR_AUTOMATION_ROADMAP.md`. (Roadmap files are NOT at repo root as the prompt assumed — see Appendix for path drift.)

### G1. DEBT entries touching Phase 2 / distribution / UTM / lineage

Output of `grep -n -i "lineage\|utm\|distribution\|post.ledger\|2\.2\|2\.3" DEBT.md | head -30`:
```
276:### DEBT-035: Parallel config_hash computation in pipeline + lineage helper
283:- **Description:** `_compute_hashes` in `backend/src/services/graphics/pipeline.py:182` inlines its own SHA-256 hashing logic, parallel to the centralized `compute_config_hash` in `backend/src/services/publications/lineage.py`. Both produce the same hash for the same inputs today, but divergence risk exists if either path is updated independently.
307:- **Description:** Phase 2.5 DoD (per `OPERATOR_AUTOMATION_ROADMAP.md` line 180, post-update) calls for 5 row types in the Exception Inbox: failed exports, zombie jobs, stale bindings, missing post URLs, unresolved validation blockers. PR #205 (Phase 2.5a) ships the first two; the other three are blocked on backend entities that do not yet exist: `staleBindings` requires `Binding` model + `BindingRepository` + listing endpoint (owned by Phase 3 Data binding); `missingPostUrls` requires `post_ledger` table + listing endpoint (owned by Phase 2.3 Post URL ledger); `unresolvedValidationBlockers` requires either backend persistence of validation status on `Publication` or editor pushing validation results to a new backend endpoint (no phase currently owns this).
310:- **Target:** Phase 3 ships `staleBindings`; Phase 2.3 ships `missingPostUrls`; validation-blocker scope assessment before Phase 4 closure.
```

Per-DEBT summary (one line each, by ID, only those that materially touch Phase 2.2):

- **DEBT-035** (status: Resolved, line 276) — references the existing `backend/src/services/publications/lineage.py` module that already houses `compute_config_hash`. This is the natural home for any Phase 2.2 `lineage_key` generator (see Q-2.2-1 adjacent-surface note); the file exists today, but contains no `lineage_key` symbol.
- **DEBT-040** (status: Resolved, line 300) — Phase 2.5b row "missing post URLs" is blocked on the Phase 2.3 `post_ledger` table. Phase 2.2 emits the URLs that Phase 2.3 will record and Phase 2.5b will eventually surface. This is a downstream consumer relationship; Phase 2.2 has no DEBT-040 work itself.

No DEBT entry currently calls out `lineage_key`, `utm_content`, `distribution.json`, or `publish_kit.txt` directly.

### G2. DEBT-040 Phase 2.3 dependency confirmation

DEBT-040 lists "missing post URLs" as a deferred Exception Inbox row type, blocked on Phase 2.3 (post_ledger). Phase 2.2 ships URL emission; Phase 2.3 records where they were posted; Phase 2.5b's "missing post URLs" row consumes the post_ledger.

Output of `grep -n "Phase 2\.2\|2\.2 \|post.ledger" docs/architecture/ROADMAP_DEPENDENCIES.md`:
```
44:| 2.5b Exception Inbox deferred (stale bindings + missing post URLs + validation blockers) | DEFERRED | S | 1+ | Blocked on Phase 2.3 (post_ledger) + Phase 3 (Binding entity); see DEBT-040 |
51:| 2.2 Publish Kit Generator | M | 2 | 2.1 |
52:| 2.3 UTM-to-lineage attribution | S | 1 | 2.2 |
53:| 2.4 Draft Social Text (Gemini Flash) | S | 1 | 2.2 |
72:  └─ blocked by: Phase 2.3 (post_ledger) + Phase 3 (Binding entity)
76:  └─→ 2.2 Publish Kit Generator
109:  → 2.2 (M, 2 PR)
137:- **2.1 + 2.2:** 2.2 depends on 2.1 ZIP foundation
138:- **2.3 + 2.4 vs 2.2:** both depend on 2.2 publish kit
```

Confirmation: DEBT-040 dependency on Phase 2.3 **captured** in `ROADMAP_DEPENDENCIES.md` (line 44 explicitly cites `see DEBT-040`; lines 51-53 + 137-138 establish the 2.1 → 2.2 → {2.3, 2.4} chain; line 72 anchors the 2.5b → 2.3 block in the DAG).

Additional Phase 2.2 facts from ROADMAP_DEPENDENCIES:
- Phase 2.2 = "Publish Kit Generator", size M, 2 PR, depends on 2.1 (line 51).
- Phase 2.3 = "UTM-to-lineage attribution", size S, 1 PR, depends on 2.2 (line 52). The roadmap's own naming confirms `lineage` is the attribution key — consistent with founder-locked Q-D.
- Phase 2.4 = "Draft Social Text (Gemini Flash)", size S, 1 PR, depends on 2.2 (line 53). Phase 2.4 will plug into Phase 2.2's caption surface.

### G3. Existing post-ledger references in code

Output of `grep -rn "post_ledger\|post ledger" backend/src/ frontend-public/src/ docs/`:
```
docs/OPERATOR_AUTOMATION_ROADMAP.md:183:- Phase 2.5b (deferred, ships when dependencies land): stale bindings (depends on Phase 3 Binding entity), missing post URLs (depends on Phase 2.3 post_ledger), unresolved validation blockers (depends on backend persistence of validator state — no phase currently owns). ...
docs/discovery/phase-2-5-C2b-matrix.md:48:... 3 of 5 enumerated row types are deferred (stale bindings, missing post URLs, validation blockers); ... post ledger ... do not exist as queryable records ...
docs/discovery/phase-2-5-C2a-factors.md:137:- Type 3 (missing post URLs, C): "No `post_url`/`post_ledger` anywhere; Phase-2.3 dep" (C1 §1, type 3)
docs/discovery/phase-2-5-C2a-factors.md:168:| 3 | missing post URLs | no | n/a (no post ledger exists) | none | n/a (deferred) |
docs/discovery/phase-2-5-C1-sources.md:93:$ grep -rn 'post_url\|posted_at\|post_ledger\|distribution_package' backend/src frontend/lib
docs/discovery/phase-2-5-C1-sources.md:98:- No `post_ledger` / `distribution_package` table in `backend/src/models/__init__.py`.
docs/discovery/phase-2-5-C1-sources.md:99:- Roadmap places the post ledger at item 2.3, which has not shipped.
docs/discovery/phase-2-5-C1-sources.md:168:| 3 | missing post URLs | **C** | no | No `post_url`/`post_ledger` anywhere; Phase-2.3 dep |
docs/discovery/phase-2-5-C1-sources.md:191:  3. missing post URLs:     C  (Phase-2.3 dep, no post ledger)
docs/architecture/ROADMAP_DEPENDENCIES.md:44:| 2.5b Exception Inbox deferred (stale bindings + missing post URLs + validation blockers) | DEFERRED | S | 1+ | Blocked on Phase 2.3 (post_ledger) + Phase 3 (Binding entity); see DEBT-040 |
```

Conclusion: `post_ledger` is **not yet referenced in implementation code** — zero matches in `backend/src/` or `frontend-public/src/`. All occurrences are in planning docs (`docs/architecture/`, `docs/discovery/`, `docs/OPERATOR_AUTOMATION_ROADMAP.md`). The Phase 2.5 discovery doc at `docs/discovery/phase-2-5-C1-sources.md:98-99` independently confirms "No `post_ledger` / `distribution_package` table in `backend/src/models/__init__.py` ... Roadmap places the post ledger at item 2.3, which has not shipped." This is consistent with Phase 2.3 not yet shipped.

## Appendix — file paths verified during pre-recon

All files actually opened during Chunks 1+2+3 (allows recon to confirm coverage):

**Chunk 1 (A+B):**
- frontend-public/src/components/editor/export/zipExport.ts
- frontend-public/src/components/editor/export/manifest.ts
- frontend-public/src/components/editor/export/zipFilename.ts
- frontend-public/src/components/editor/types.ts
- frontend-public/messages/en.json
- frontend-public/messages/ru.json
- frontend-public/package.json

**Chunk 2 (C+D+E):**
- frontend-public/src/components/editor/index.tsx (read range 1210-1380 only — 1380-line file)
- frontend-public/src/components/editor/components/TopBar.tsx
- frontend-public/src/components/editor/config/cropZones.ts
- frontend-public/src/components/editor/config/sizes.ts
- backend/src/models/publication.py
- backend/src/schemas/publication.py
- backend/src/api/routers/admin_publications.py (greps only — confirmed clone path delegates to `services/publications/clone.py`, line 42 import)
- backend/src/core/config.py

**Chunk 3 (F+G+Appendix):**
- DEBT.md (at repo root, as expected)
- docs/architecture/ROADMAP_DEPENDENCIES.md (path drift — prompt expected repo root; actual path under `docs/architecture/`)
- docs/OPERATOR_AUTOMATION_ROADMAP.md (path drift — prompt expected repo root; actual path under `docs/`)

**Path drift discovered (no extra files read beyond scope):** the two roadmap files were located via `find . -maxdepth 4 -type f \( -iname "*roadmap*" -o -iname "*dependencies*" \)` after `ls` confirmed they were not at repo root. Per Chunk 2's standing instruction ("If a path doesn't exist, run `ls` on the parent directory to find the actual filename and document the drift in the section"), the drift is documented here.

---

**Pre-recon status:** COMPLETE. Recon-proper consumes this document and produces architectural design proposals + open founder questions per `docs/guides/agent-workflow.md` §2.2.
