# Editor Block Architecture — Schema, Migrations, Rendering

**Status:** Living document — update on every editor block / template / schema change
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Sources:** Memory items aggregated from editor Stage 1-2 work, EDITOR_ARCHITECTURE.md (in-repo)
**Related:** `EDITOR_ARCHITECTURE.md` (full design), `ARCHITECTURE_INVARIANTS.md` §8 (template lock + deterministic export rules)

**Maintenance rule:** any PR that adds a block type, template, schema field, migration step, or render pipeline change MUST update this file in the same commit. Drift signal: if memory items reference a block type, schema field, or migration count not listed here, this file is stale.

## Scope

This file captures recurring patterns:
- §2 — strict-template architecture (lock rules)
- §3 — block types catalog
- §4 — template families
- §5 — canonical document schema
- §6 — `applyMigrations` pipeline
- §7 — render pipeline (`measureLayout`, `RenderResult`)
- §8 — history and undo
- §9 — keyboard shortcut conventions
- §10 — export pipeline rules

For full architecture rationale, see in-repo `EDITOR_ARCHITECTURE.md`.

## 2. Strict-template architecture

### Template lock

The editor is template-driven. Free-form canvas is NOT a substitute. Adding a new layout requires creating a new template with a defined section structure, NOT enabling free placement.

(See `ARCHITECTURE_INVARIANTS.md` §8 for the product invariant statement.)

### Why strict templates

- Deterministic export (same template + same bindings = same pixel output)
- Operators come from Figma/Canva culture; templates are the familiar mental model
- Bindings (Phase 3) only make sense within a fixed slot structure

### Anti-patterns

- "Just let the operator drag blocks anywhere" — violates template lock
- "Auto-resize a Long template into a Story preset" — explicitly deferred per roadmap §6: "this is a redesign problem, not a resize problem. Force operator to choose compatible base template."

## 3. Block types catalog

13 block types across 5 categories (memory item).

### Categories
- **Text blocks:** headlines, body text, source, eyebrow
- **Data blocks:** ranked bar, key-value, line series, table
- **Visual blocks:** image, background fill
- **Structural blocks:** divider, spacer
- **Annotation blocks:** caption, footnote, callout

(Confirm exact 13 block names from in-repo `EDITOR_ARCHITECTURE.md` if MD discovers naming has drifted. This list is the count + category breakdown.)

### Adding a new block type

1. Add block type to schema (this file §5)
2. Implement render in `renderer/` directory
3. Implement `measureLayout` contribution (§7)
4. Add migration step if existing schemas need normalization
5. Add to `assertDocumentIntegrity` validator
6. Add tests: render snapshot + integrity assertion + migration round-trip
7. Update this file's catalog

## 4. Template families

11 templates across 7 families (memory item).

### Families
- **Long form** — vertical multi-section (deep dives, year-end recaps)
- **Story** — vertical short (Instagram/Facebook stories, vertical TikTok)
- **Square** — 1:1 (Instagram feed, generic share)
- **Wide** — 16:9 horizontal (X header card, Reddit OG image, LinkedIn)
- **Ranked** — ranked list emphasis
- **Comparison** — two-column or side-by-side
- **Snapshot** — single key metric foreground

(Exact template names per family confirmed from in-repo `EDITOR_ARCHITECTURE.md`. This file lists the 7 families and total of 11 templates.)

### Cross-family resize is forbidden

Per roadmap §6 deferred: auto-resize across preset families (e.g. Long → Story) is explicitly NOT a roadmap item. It is a redesign problem, not a resize problem. Operator must choose a compatible base template.

## 5. Canonical document schema

### Top-level fields

```typescript
interface PublicationDocument {
  schemaVersion: number;        // bumped on every breaking schema change
  templateId: string;           // references one of the 11 templates
  page: PageMeta;               // page-level config (background, palette, theme)
  sections: Section[];          // ordered list of sections
  blocks: Record<string, Block>; // blocks keyed by ID; sections reference IDs
  workflow: WorkflowState;      // draft / in_review / approved / exported / published
  meta: {
    history: HistoryEntry[];    // undo stack — see §8 history batching rule
    comments: Comment[];        // review comments (Stage 3)
    [k: string]: unknown;
  };
}
```

### Why blocks are keyed by ID

Sections reference block IDs, not block objects directly. This allows:
- Block reuse across sections (e.g. shared caption in headline + footer)
- Cleaner deletion (drop section reference; block GC handles cleanup separately)
- Migration safety (block schema can evolve without restructuring sections)

### Block instance fields (shape in `doc.blocks[id]`)

```typescript
interface Block {
  id: string;             // matches the registry key — invariant
  type: string;           // BREG[type] resolves to BlockRegistryEntry
  props: BlockProps;      // type-specific data (text, items[], series[], …)
  visible: boolean;       // false → omitted from render and intrinsic-height calc
  locked?: boolean;       // Phase 1.6, additive (no schemaVersion bump):
                          // true → blocks UPDATE_PROP / UPDATE_DATA / TOGGLE_VIS
                          // through the reducer permission gate. Independent of
                          // registry-level `status: "required_locked"`, which is
                          // template-immutable and additionally blocks deletion.
                          // Optional + undefined-coalesce-to-false to keep older
                          // serialized docs forward-compatible.
}
```

The `visible` and `locked` flags interact independently — a block can be
both locked and hidden. `REMOVE_BLOCK` ignores `block.locked` (Phase 1.6
Q2: lock blocks editing/movement, not deletion); `REMOVE_BLOCK` IS blocked
by registry-level `status: "required_locked" | "required_editable"`.

### `assertDocumentIntegrity` validator

Runs in dev mode after every dispatch. Asserts:
- Every block ID referenced in sections exists in `blocks` registry
- Every block in `blocks` registry is referenced by at least one section (no orphans)
- `templateId` is a known template
- `schemaVersion` is current or migration-ready

If any assertion fails → throws in dev (red error overlay), warns in prod (does not crash, but logs to telemetry).

## 6. applyMigrations pipeline

### Source: memory item

Migration pipeline (`applyMigrations` in editor) MUST abort on missing intermediate steps. Silent skip is forbidden.

### Pipeline shape

```typescript
const migrations: Record<number, (doc: any) => any> = {
  1: migrateV0toV1,
  2: migrateV1toV2,
  // ... ordered by source version ...
};

function applyMigrations(doc: any): PublicationDocument {
  const target = CURRENT_SCHEMA_VERSION;
  let current = doc.schemaVersion ?? 0;
  
  while (current < target) {
    const next = current + 1;
    const migrator = migrations[next];
    if (!migrator) {
      throw new Error(`Missing migration from v${current} to v${next}`);
    }
    doc = migrator(doc);
    current = next;
  }
  
  return doc;
}
```

### Why abort, not skip

Skipping intermediate migrations leads to silently broken documents that pass validation in current schema but have stale fields from older schemas. Crash early, surface the missing migration step.

### Migration test rule

Every new migration adds:
1. The migration function (`migrateVNtoVN+1`)
2. Round-trip test: load v(N) sample document → apply migrations → assert resulting document matches expected v(N+1) shape
3. Sample documents in `__tests__/__fixtures__/` for each schemaVersion

## 7. Render pipeline

### measureLayout prepass

`measureLayout` runs before render to compute intrinsic heights. This is what allows variable-height blocks (text wrapping, multi-line headlines) to coexist with fixed-height blocks (charts, dividers) in deterministic layouts.

**File:** `renderer/measure.ts`

**Output:** `RenderResult` type with `intrinsicHeight` field.

### RenderResult type

```typescript
interface RenderResult {
  intrinsicHeight: number;       // measured height for layout calc
  // ... other render output ...
}
```

### Click-to-select with hitArea (Stage 4)

Click-to-select uses explicit hitArea per block type — not just the rendered bbox. Some blocks (text) have hitArea matching bbox; others (chart with sparse rendering) have hitArea wider than visible content for ergonomics.

### PNG export uses logical CSS dimensions

**Memory item:** PNG export must use logical CSS dimensions, not DPR-scaled canvas.

Rationale: scaling at the canvas API layer breaks the deterministic-export invariant. Same template + same bindings on a different DPR display would produce different pixel output.

Use logical dimensions in CSS, then export at 2x or 3x via standard rendering pipeline. Don't manually scale canvas.

## 8. History and undo

### History batching window

**Memory item:** history batching uses 800ms window.

Edits within 800ms collapse to a single history entry. Outside the window, a new entry is created. Prevents history flooding from typing each character.

### History storage

History lives in `meta.history`. Bounded by max length (configurable; default keeps last 50 entries to bound document size).

### Autosave + history interaction

Autosave (Phase 1.5) writes to backend via PATCH. History stays client-side only (not persisted to backend). On reload, history is empty — undo across reloads is NOT supported.

## 9. Keyboard shortcuts

### shouldSkipGlobalShortcut utility

**Memory item:** `shouldSkipGlobalShortcut` utility handles IME guard + testability.

Global shortcuts (Cmd+S save, Cmd+Z undo, etc.) MUST run through this utility, which:
- Detects IME composition (Asian input methods) — skips global shortcut while composing
- Allows test-mode override (testability)

**Anti-pattern:** registering global keyboard listener directly without going through `shouldSkipGlobalShortcut`. Breaks IME-using operators silently.

### Operators are not developers

(Cross-ref `ARCHITECTURE_INVARIANTS.md` §8.) Avoid command palettes (Cmd+K) and developer-culture keybindings. Visual UI is preferred.

### Phase 1.6 — block context-menu shortcuts

Right-click on a block in Canvas opens the context menu (Lock / Hide /
Duplicate / Delete). The same four actions are bound to keyboard shortcuts
when a block is selected:

| Shortcut | Action | Notes |
|---|---|---|
| `⌘L` / `Ctrl+L` | Toggle `block.locked` | No-op when no selection. |
| `⌘H` / `Ctrl+H` | Toggle `block.visible` | No-op when block is locked. |
| `⌘D` / `Ctrl+D` | Duplicate selected block | `preventDefault()` mandatory — browser bookmark default. Clashes with `Ctrl+Shift+D` debug toggle are avoided by checking `!e.shiftKey`. |
| `Delete` / `Backspace` | Delete selected block | Empty (default-state) blocks delete without confirm; non-empty blocks open `DeleteConfirmModal`. Skipped automatically by `shouldSkipGlobalShortcut` when focus is in an input/textarea/contenteditable. |

All four flow through `shouldSkipGlobalShortcut` so IME composition is
respected. Right-click on a block selects the block first, then opens the
menu — selection and inspector stay coherent. Right-click on empty Canvas
falls through to the browser default.

## 10. Export pipeline

### PNG export (Stage 4)

- Logical CSS dimensions, not DPR-scaled canvas (memory item, see §7)
- Font-gated export: export blocked if any block requires a font that hasn't loaded
- Debug overlay (Stage 4): visible in dev mode showing measure outputs, hitAreas, layout boxes

### Multi-preset ZIP export (Phase 2.1)

Phase 2.1 plans client-side fflate ZIP with PNGs for each enabled preset. Out of scope for Stage 4. Cross-ref roadmap §5.2.

### Distribution package (Phase 2.2)

ZIP includes `distribution.json` + `publish_kit.txt` + per-preset PNGs + UTM-tagged URLs. Cross-ref roadmap §5.2.

## 11. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from aggregated memory items + reference to in-repo EDITOR_ARCHITECTURE.md |
| 2026-04-27 | Phase 1.6 (`claude/add-context-menus-kf2rk`) | §5, §9, §11 | Right-click block context menu (Lock/Hide/Duplicate/Delete). Schema additive: `Block.locked?: boolean` (no schemaVersion bump). New reducer actions `TOGGLE_LOCK`, `DUPLICATE_BLOCK`, `REMOVE_BLOCK`. Cmd/Ctrl+L/H/D + Delete shortcuts gated on `shouldSkipGlobalShortcut`. DEBT-044 logged for multi-select v2. |
| 2026-04-27 | Phase 2.1 PR#1 (`claude/render-helper-infographic-qi4GI`) | §7, §10 | Added `export/renderToBlob.ts` pure async helper for sequential per-preset rendering (Q-2.1-1). Added `long_infographic` preset (1200×4000 cap sentinel) to `SIZES` with variable-height measure path. `measureLayout` accepts `size.h === Infinity` to compute intrinsic height; `computeLongInfographicHeight` sums per-section consumed heights + width-scaled page padding. Cap exceeded throws `RenderCapExceededError` (caught by PR#3 orchestrator → `qa_status: "skipped"`). i18n key `validation.long_infographic.height_cap_exceeded` added EN+RU. PR#1 mode A — single PR, both phases. Existing `exportPNG` callback in `index.tsx:1211-1250` left untouched (replaced by PR#3 ZIP flow). |
| 2026-04-27 | Phase 2.1 PR#2 (`claude/schema-migration-presets-CC3Or`) | §5, §6, §11 | schemaVersion bump 2 → 3. Added `PageConfig.exportPresets: string[]` with `DEFAULT_EXPORT_PRESETS` (common-4: `instagram_1080`, `twitter_landscape`, `reddit_standard`, `linkedin_landscape`) per recon Q-2.1-8 / approval A2. Renamed preset IDs (`instagram_port` → `instagram_portrait`, `story` → `instagram_story`, `twitter` → `twitter_landscape`, `reddit` → `reddit_standard`, `linkedin` → `linkedin_landscape`); back-compat aliases in `SIZE_FROM_BACKEND` (one-way; `SIZE_TO_BACKEND` only contains new IDs since the v2→v3 migration ensures every loaded doc is on new IDs before any write). New atomic `migrateV2toV3` step does both rename + new field together (recon §5 Risk 3). Inspector "Export presets" section in LeftPanel theme tab — 7 checkboxes; preset matching `page.size` is force-enabled; non-current presets togglable via new `UPDATE_PAGE_EXPORT_PRESETS` reducer action. i18n keys `editor.inspector.export_presets.{label,help,current_required}` EN+RU. `renderDocumentToBlob` `presetId` parameter tightened from `string` to `keyof typeof SIZES` (Q-2.1-12 / approval A5). Migration tests cover 4 scenarios (no-field default, legacy-id rename, already-renamed idempotent, abort discipline). EXPORTABLE_PRESET_IDS still excludes `long_infographic`; PR#3 expands once ZIP flow handles `RenderCapExceededError`. |
| 2026-04-27 | Phase 2.1 PR#3 (`claude/add-zip-export-manifest-17STq`) | §10, §11 | Multi-preset ZIP export shipped. New module `editor/export/zipExport.ts` orchestrates per-preset render loop (sequential, snapshot via `structuredClone` at click time per Q-2.1-6); new helpers `manifest.ts` builds `schemaVersion=1` manifest with `qa_status` per preset (Q-2.1-7), `zipFilename.ts` produces deterministic `summa-<templateId>-export-YYYYMMDD-HHmmss.zip` (Q-2.1-3). Added `fflate ^0.8.2` runtime dep (Q-2.1-4). TopBar Export button replaced with "Export all valid"; per-preset `N/total` progress inline via new `ZipExportProgress` component (Q-2.1-5). `RenderCapExceededError` now carries `i18nKey` field (PR#1 fix1 TODO resolved); orchestrator catches it → `qa_status: "skipped"` in manifest, other 6 presets continue (Q-2.1-10 / approval A4). `EXPORTABLE_PRESET_IDS` expanded to 7 entries (now includes `long_infographic` — legacy size picker safe now that ZIP flow handles cap-exceeded). i18n keys EN+RU under `editor.export_zip.*` (button.label/aria, progress.rendering/packing, toast.success/partial/error, skipped.long_infographic_cap_exceeded). End-of-export feedback rendered via local notification state (no centralized toast system in repo yet; richer toast deferred to follow-up). Hybrid testing per Q-2.1-11: 8 unit tests + 1 real-wire integration test that decodes ZIP via `fflate.unzipSync` and asserts entry filenames + manifest content. `jest.setup.ts` polyfills `structuredClone` (jsdom global gap) and `Blob.prototype.arrayBuffer` (jsdom Blob omits). **fix1 (founder review):** manifest skipped entries now set `filename: null` (was `"<id>.png"` referencing a file not in the ZIP) and carry `skipped_reason` (i18n key) for machine-readable downstream consumption; integration test extended with a skipped-preset consistency case. `ManifestPresetEntry.filename` widened to `string \| null`; `skipped_reason?: string` added. |
| 2026-04-28 | Phase 2.1 PR#4 (`claude/per-preset-qa-0Ta0z`) | §11 | Per-preset QA evaluator. `validation/validate.ts` split into `validateDocument(doc)` (size-independent) + `validatePresetSize(doc, presetId)` (size-dependent only). Existing `validate(doc)` becomes a back-compat wrapper combining both for current `doc.page.size` (single production callsite at `index.tsx:330` QA panel — unchanged behavior). New pre-render gate in `export/zipExport.ts`: orchestrator calls `validatePresetSize(snapshot, presetId)` BEFORE `renderDocumentToBlob`; any error-level entry → preset skipped, manifest entry has `qa_status: "skipped"` + `filename: null` + `skipped_reason = first_error.key`. Warnings/info do NOT cause skip — they propagate to the new Inspector per-preset badge. Runtime `RenderCapExceededError` catch retained as defense-in-depth. Long-infographic cap check now exists in TWO places (validator + renderer) — agreed redundancy: validator gives early UI feedback, renderer guarantees no OOM if validator is wrong. ExportPresetsSection adds `PresetQaBadge` column (OK / OK·WARN / SKIP) per row; tooltip shows first issue's i18n key (full localization deferred to follow-up — current QA panel already shows the localized text). 3 new i18n keys EN+RU under `inspector.export_presets.qa_status.*`. Phase 2.1 functional scope CLOSES with this PR; final polish batch (5 P3 items) is a separate scope. |
