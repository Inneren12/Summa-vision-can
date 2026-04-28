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
