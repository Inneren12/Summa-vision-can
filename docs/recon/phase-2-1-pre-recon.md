# Phase 2.1 — Pre-recon (Code Inventory)

**Branch:** claude/phase-2-1-pre-recon
**HEAD:** eca5cae Update print statement from 'Hello' to 'Goodbye'
**Date:** 2026-04-27
**Status:** WORK IN PROGRESS — Part A1+A2 done; Part B recovery in progress (§3 written, §4 §5 pending).

## 1. Locked scope

### Original (founder Q1–Q5, 2026-04-27)

- 7 export presets all included: `instagram_1080`, `instagram_portrait`,
  `instagram_story`, `twitter_landscape`, `reddit_standard`,
  `linkedin_landscape`, `long_infographic`.
- "Export all valid" = combo (A) QA-pass + (C) listed in
  `document.exportPresets`. QA-failed presets skipped with warning,
  not blocking.
- ZIP contents: per-preset PNGs + minimal `manifest.json`
  (publication_id, created_at, preset → filename map). Phase 2.2
  extends manifest into `distribution.json`.
- Rendering strategy: sequential per-preset (Variant A). No Web Workers /
  OffscreenCanvas in 2.1.
- PR decomposition: 2-3 PRs.

### Updates after §2.C/D findings (founder, 2026-04-27 same day)

- **`long_infographic` IMPLEMENTED in 2.1 scope** (founder Variant a).
  Currently absent from code per §2.C. Variable-height rendering work
  added to PR#1.
  - **Max-height policy: hard cap 4000px** (Variant ii). Exceeding triggers
    QA error blocking export. Operator must remove/hide blocks or migrate
    to a fixed-aspect template. Cap value is starting recommendation —
    recon-proper may re-tune based on `measureLayout` typical heights.
  - Rationale: variants (i) no-cap and (iii) soft-cap-with-warning rejected.
    No-cap risks runaway file sizes (5+ MB PNGs hostile to social platform
    upload limits) and breaks deterministic-export invariant by analogy
    with DPR-scaled canvas (`ARCHITECTURE_INVARIANTS.md` §8). Soft-cap is
    half-measure operators will ignore.

- **`exportPresets` field ADDED to PageConfig schema** (founder Variant 2).
  Currently absent per §2.D. Required to make combo (A)+(C) fully
  implementable.
  - schemaVersion bump + migration N→N+1
  - Toggle UI placement: recon-proper decides (TopBar vs Inspector vs
    dedicated export panel)
  - Migration discipline: `applyMigrations` MUST abort on missing
    intermediate per `EDITOR_BLOCK_ARCHITECTURE.md` §6 + invariant in
    `ARCHITECTURE_INVARIANTS.md` §8.

- **PR estimate revised: 2-3 → 4 PRs minimum**
  - PR#1 — pure render helper + long_infographic rendering
  - PR#2 — schema migration + exportPresets field + toggle UI
  - PR#3 — fflate ZIP + manifest.json + Export button
  - PR#4 — per-preset QA evaluator + UI integration
  - **Roadmap update deferred to post-recon-merge** (founder Variant α).
    `OPERATOR_AUTOMATION_ROADMAP.md` row 2.1 stays at "M, 2-3" until
    recon-proper merges; founder updates roadmap then.

## 2. Existing code inventory

### 2.A — Single-PNG export entry point

**Verdict:** found.
**Primary file(s):** `frontend-public/src/components/editor/index.tsx:1211-1250` (`exportPNG` callback); button wiring at `components/TopBar.tsx:170-175`; download helper at `utils/download.ts:8-18`.
**Signature / shape:**
```typescript
const exportPNG = useCallback(() => {
  if (!canExp) return;          // QA gate (errs === 0)
  if (!fontsReady) return;      // font gate
  const exportCvs = document.createElement("canvas");
  exportCvs.width = sz.w;
  exportCvs.height = sz.h;
  const ctx = exportCvs.getContext("2d");
  if (!ctx) return;
  const bgFn = BGS[doc.page.background] || BGS.solid_dark;
  bgFn.r(ctx, sz.w, sz.h, pal);
  renderDoc(ctx, doc, sz.w, sz.h, pal);
  requestAnimationFrame(() => {
    exportCvs.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `summa-${doc.templateId}-${doc.page.size}.png`;
      a.click();
      deferRevoke(url);
    }, "image/png");
  });
}, [canExp, fontsReady, doc, pal, sz]);
```
**Purity:** **impure**. Reads `doc`, `pal`, `sz`, `canExp`, `fontsReady` from React closure. Side effects: creates detached `<canvas>`, `URL.createObjectURL`, programmatic `<a>.click()` download, `deferRevoke`. Single canvas dim per call (`sz.w × sz.h` from `doc.page.size`).
**Match vs MD:** matches `EDITOR_BLOCK_ARCHITECTURE.md §10` (logical CSS dims, font-gated, blocked on validation errors). No MD reference for the multi-preset extension yet.
**Notes:** Trigger is the EXPORT button in `TopBar.tsx:170` (single button, no preset picker). `MARK_EXPORTED` action exists (`store/reducer.ts:226`) but is NOT dispatched from `exportPNG` — it's a separate review-panel transition (`components/ReviewPanel.tsx:64-65`). Filename pattern uses `doc.templateId` + `doc.page.size`, not `publication.slug`.

### 2.B — Renderer + measureLayout

**Verdict:** found.
**Primary file(s):** `frontend-public/src/components/editor/renderer/engine.ts:14-58` (`renderDoc`); `renderer/measure.ts:103-135` (`measureLayout`); `renderer/measure.ts:25-96` (per-block height estimator).
**Signature / shape:**
```typescript
// engine.ts
export function renderDoc(
  ctx: CanvasRenderingContext2D,
  doc: CanonicalDocument,
  w: number,
  h: number,
  pal: Palette,
): RenderedBlockEntry[]

// measure.ts
export function measureLayout(
  doc: CanonicalDocument,
  size: SizePreset,
): SectionMeasurement[]
```
**Purity:** `renderDoc` — **impure** (writes to `ctx`). `measureLayout` — **pure** (no I/O, no clock reads, no store reads; takes `doc` + `size`, returns deterministic estimate using `width / 1080` scale on line 104). Both are called from React effects but the functions themselves are stateless.
**Match vs MD:** matches `EDITOR_BLOCK_ARCHITECTURE.md §7` (measureLayout prepass, RenderResult with intrinsicHeight surrogate `height` field, logical CSS dims per `§7 + §10`). MD says output type is `RenderResult`; code's per-block return shape lives in `renderer/types.ts` with `{ height, overflow, warnings, hitArea }` (verified via `tests/editor/renderer-contract.test.ts:45-48`).
**Notes:** Size flows in as scalar `(w, h)` parameters from the caller — `renderDoc` itself does not read `doc.page.size`; the editor resolves `sz = SIZES[doc.page.size]` at `index.tsx:293` and passes `sz.w, sz.h`. The same `renderDoc` is invoked twice today: preview render (`index.tsx:368`, DPR-scaled canvas) and PNG export (`index.tsx:1236`, 1:1 canvas). Re-running it N times sequentially with different `(w, h)` is the foundation for PR#1's pure render helper.

### 2.C — Preset definitions

**Verdict:** partial. **Drift vs MD §6 — recorded for §4.**
**Primary file(s):** `frontend-public/src/components/editor/config/sizes.ts:3-10` (canonical `SIZES` map); platform crop zones at `config/cropZones.ts:30-41`; backend size string mapping at `utils/persistence.ts:36-57` (`SIZE_TO_BACKEND`, `SIZE_FROM_BACKEND`).
**Signature / shape:**
```typescript
// sizes.ts — 6 entries (NOT 7, no long_infographic)
export const SIZES: Record<string, SizePreset> = {
  instagram_1080: { w: 1080, h: 1080, n: "IG 1:1" },
  instagram_port: { w: 1080, h: 1350, n: "IG 4:5" },
  twitter:        { w: 1200, h: 675,  n: "Twitter/X" },
  reddit:         { w: 1200, h: 900,  n: "Reddit" },
  linkedin:       { w: 1200, h: 627,  n: "LinkedIn" },
  story:          { w: 1080, h: 1920, n: "Story" },
};
```
**Match vs MD:** **diverges** from `EDITOR_ARCHITECTURE.md §6` on 5 of 7 IDs:

| MD §6 ID (locked) | Code ID (`SIZES`) | Dimensions match? |
|---|---|---|
| `instagram_1080` | `instagram_1080` | ✓ 1080×1080 |
| `instagram_portrait` | `instagram_port` | ✓ 1080×1350, ID renamed |
| `instagram_story` | `story` | ✓ 1080×1920, ID renamed |
| `twitter_landscape` | `twitter` | ✓ 1200×675, ID renamed |
| `reddit_standard` | `reddit` | ✓ 1200×900, ID renamed |
| `linkedin_landscape` | `linkedin` | ✓ 1200×627, ID renamed |
| `long_infographic` | — (absent) | missing entirely |

Safe areas (top 48 / bottom 80 / L-R 48; story top 120 / bottom 100) per `DESIGN_SYSTEM_v3.2.md` БЛОК 11 are NOT encoded anywhere in `config/`. Per-platform max-series / min-font / preferred-mode rules from БЛОК 11 also NOT in code.
**Needs founder/recon decision:** ID rename strategy (rename in `SIZES` + add `SIZE_FROM_BACKEND` aliases for back-compat?) and where to host safe-area / per-platform rules so render path can honor them. Document-state field `document.exportPresets` (referenced by founder lock list) does NOT exist on `PageConfig` (`types.ts:52-56` only has `size`, `background`, `palette`).

### 2.D — QA panel state shape

**Verdict:** partial. **Document-level only** — combo (A)+(C) requires per-preset evaluator that does not exist.
**Primary file(s):** `frontend-public/src/components/editor/validation/validate.ts:14-160` (`validate(doc)`); `types.ts:165-172` (`ValidationResult`); `components/QAPanel.tsx:1-46` (renders the result).
**Signature / shape:**
```typescript
// types.ts:165
export interface ValidationResult {
  errors: ValidationMessage[];
  warnings: ValidationMessage[];
  info: ValidationMessage[];
  passed: ValidationMessage[];
  contrastIssues: /* ... */;
}

// validate.ts:14 — single-arg, no per-preset axis
export function validate(doc: CanonicalDocument): ValidationResult {
  // ...
  const sz = SIZES[doc.page.size] || SIZES.instagram_1080;   // line 18
  // ... uses sz.h, sz.w, sz.n in ~6 places (lines 105, 117, 135, 136, 142)
}

// index.tsx:327-336 — single call site, derives errs/warns/canExp/si
const vr = useMemo(() => validate(doc), [doc]);
const errs = vr.errors.length, warns = vr.warnings.length;
const canExp = errs === 0;
const si = errs > 0 ? "🔴" : warns > 0 ? "🟡" : "🟢";
```
**Purity:** `validate` is pure (reads only `doc`, returns plain object). The `errs/warns/canExp/si` derivations in `index.tsx:334-336` are document-scoped, not preset-scoped.
**Match vs MD:** **partially matches** `EDITOR_ARCHITECTURE.md §15`. Categories Errors / Warnings / Info / Passed match §15.2 exactly; export-safe indicator `🟢/🟡/🔴` (§15.3) matches. **Diverges**: §15.3 implies a single export-safe indicator per document (current behavior), but combo (A)+(C) needs *per-preset* status (one preset can have text overflow at story 1080×1920 while passing at 1200×675). Validator currently runs once per doc against `doc.page.size`; calling it for a different size requires either (a) a temporarily-mutated copy of `doc` with another `page.size`, or (b) a refactored `validate(doc, size)` signature.
**Needs founder/recon decision:** see Q-2.1-2 (where the per-preset evaluator lives). Subset of validation rules are size-dependent (lines 105, 117, 135, 136 of `validate.ts`) — those need per-preset re-eval. Size-independent rules (required blocks, contrast, max-chars) only need to run once.

### 2.E — Existing dependencies

**Verdict:** found (greenfield for ZIP only).
**Primary file(s):** `frontend-public/package.json:17-26` (runtime deps); `frontend-public/src/components/editor/utils/download.ts:8-18` (`deferRevoke`); `index.tsx:1242` + `:618` (`URL.createObjectURL` + synthetic `<a>.click()`).
**Signature / shape:**
```jsonc
// package.json runtime deps (10 total)
"dependencies": {
  "@hookform/resolvers": "^5.2.2",
  "next":                "16.2.0",
  "next-intl":           "^4.9.1",
  "react":               "19.2.4",
  "react-dom":           "19.2.4",
  "react-hook-form":     "^7.71.2",
  "web-vitals":          "^4.2.4",
  "zod":                 "^4.3.6"
}
// no fflate / jszip / archiver / adm-zip / file-saver / pako
```
**Match vs MD:** `EDITOR_BLOCK_ARCHITECTURE.md §10` "Multi-preset ZIP export (Phase 2.1)" notes "Phase 2.1 plans client-side fflate ZIP" — i.e. fflate is the planned-but-unadded dep, consistent with current state. No MD reference says fflate is already vendored.
**Notes:**
- **fflate**: NOT a dep (any flavour). Repo-wide grep for `"fflate"`, `from 'fflate'`, `from "fflate"` returned zero hits in `frontend-public/` and `frontend/`. PR#2 must add it. (Bundle impact ~8 KB gzipped, per memory item — recon-proper to confirm.)
- **Other ZIP libs**: NONE present (`jszip`, `archiver`, `adm-zip` all return zero hits).
- **Reusable blob/download helpers**: `deferRevoke(url)` (`utils/download.ts:8-18`) handles the rAF + 100 ms double-defer to avoid revoking before the synthetic-click navigation commits. PR#2 can reuse it for the ZIP blob.
- **Bundle-size posture**: `@next/bundle-analyzer` is wired (`package.json:28`, `analyze` script), so PR#2 has tooling to measure delta. `next.config.ts` exists at repo root.

### 2.F — Backend touchpoints

**Verdict:** Phase 2.1 backend impact: **NONE confirmed**. No ZIP/distribution endpoints exist; the existing single-PNG upload landing surface is documented for 2.2 hand-off.
**Searched:** `grep -rn "publish_kit\|export.*zip\|distribution\.json\|/export/zip\|export_all" backend/` → zero hits.
**Existing single-PNG landing surface (NOT modified by 2.1, noted for 2.2):**
- `backend/src/repositories/publication_repository.py:85-86,99-100,115-116,139-140,149-150,161-162,312` — Publication columns `s3_key_lowres` + `s3_key_highres` and write helpers.
- `backend/src/services/graphics/pipeline.py:217-218,327-328,370` — pipeline writes `s3_keys["lowres"]` / `s3_keys["highres"]` into Publication after upload.
- `backend/src/schemas/publication.py:273` — presigned URL pattern for the low-resolution thumbnail.
**Match vs MD:** matches `OPERATOR_AUTOMATION_ROADMAP.md §5.2` Phase 2.1 row "client-side fflate". Backend "ZIP upload accept" is Phase 2.2 territory per same row + §11 of `EDITOR_ARCHITECTURE.md`.
**Notes:** ZIP-to-S3 wire path is OUT-OF-SCOPE for 2.1. The existing `s3_key_lowres/highres` columns are designed around a single-PNG asset model — recon-proper for 2.2 will need to decide if ZIP becomes a third column (`s3_key_zip`) or a sibling table.

### 2.G — Font-gate + DPI

**Verdict:** found.
**Primary file(s):** `frontend-public/src/components/editor/index.tsx:166` (state); mount-effect race at `index.tsx:435-...`; preload registry at `renderer/font-preload.ts:1-40`; export gate at `index.tsx:1224`; render gate at `index.tsx:351`.
**Signature / shape:**
```typescript
// index.tsx:166 — single boolean, document-scoped
const [fontsReady, setFontsReady] = useState<boolean>(false);

// renderer/font-preload.ts:26 — explicit (family, weight) pre-fetch list
export interface CanvasFontFace { family: string; weight: number; }
// CANVAS_FONT_FACES enumerates Bricolage Grotesque {400,600,700,800},
// DM Sans {400,500,600}, JetBrains Mono {400,500,600,700} per file
// header (lines 32-41). Lockstep with renderer/blocks.ts.

// index.tsx:1224 — export gates on fontsReady once
if (!fontsReady) return;

// index.tsx:355, 485, 534 — preview canvas only
const dpr = window.devicePixelRatio || 2;
```
**Purity:** `fontsReady` is React state, gate-checked before render/export. Preload itself is impure (mounts FontFace objects via `document.fonts.add`).
**Match vs MD:** matches `EDITOR_BLOCK_ARCHITECTURE.md §10` ("Font-gated export: export blocked if any block requires a font that hasn't loaded") and §7 + memory item "PNG export must use logical CSS dimensions, not DPR-scaled canvas". DPR is read at `index.tsx:355,485,534` but exclusively in PREVIEW-canvas paths; `exportPNG` (`index.tsx:1228-1230`) sets `exportCvs.width/height` to logical `sz.w × sz.h` with NO DPR factor. The export path is already deterministic across displays.
**Notes:** Font-gate is checked **once at export-start** (`index.tsx:1224`). Multi-preset implication: a 7-preset sequential render loop must NOT re-check or re-await `document.fonts.ready` between presets — that would re-introduce the 5-sec stall the B1 fix removed (`index.tsx:1218-1223`). Single check at loop entry is sufficient given the preload registry: all `(family, weight)` pairs are already requested.

### 2.H — long_infographic status (re-confirmation)

**Verdict:** greenfield (per A1 §2.C — preset absent from `SIZES` map).
**Founder decision (§1 Updates above):** implement in PR#1 with hard cap 4000px. Variant ii rationale recorded in §1.
**Primary file(s) for impl:** new entry in `config/sizes.ts`; new branch in `renderer/measure.ts` height-summation; new validation rule in `validation/validate.ts`; new i18n key for cap-exceeded error.
**Match vs MD:** **diverges** from `EDITOR_ARCHITECTURE.md §6` row 7 (`long_infographic | 1200×auto | Variable`) — the row exists in MD but NOT in code (already counted as drift in §2.C, repeated here for clarity).
**Implication for §5 risk:** PR#1 scope expanded ~50% over original "pure render helper" plan. Variable-height rendering needs:
  (a) intrinsicHeight summation across all visible sections — `measureLayout` already returns `consumedHeight` per section (`measure.ts:128`), so the helper is `Σ measureLayout(doc, {w:1200, h: ∞})[i].consumedHeight + 2 × 64*s padding`.
  (b) Cap enforcement at MEASURE phase (before render) so QA error fires without burning a render pass.
  (c) New QA error key (e.g. `validation.long_infographic.height_cap_exceeded`) with cap value + measured height in params.
  (d) Decision on whether `measureLayout` signature takes a sentinel (`size.h === Infinity`) or a new flag. The current `availableHeight: layout.h` (`measure.ts:127`) and `overflow: consumed > layout.h * 1.1` (`measure.ts:129`) assume bounded `h`.

### 2.I — Existing tests in export/render area

**Verdict:** found (rendering well-covered; multi-preset / ZIP / export-blob testing is greenfield).
**Primary file(s):**
- `frontend-public/tests/editor/renderer-contract.test.ts` — pins `RenderResult` shape (`{height, overflow, warnings, hitArea}`) for every block in `BR` registry (lines 38-53). Uses fully-mocked `ctx` per `makeCtx()` at lines 3-36 (jsdom workaround: returns mock with `measureText`, `fillText`, `roundRect`, `createLinearGradient`, etc.).
- `frontend-public/tests/editor/measure.test.ts` — covers `measureLayout` purity + size-dependent estimates.
- `frontend-public/tests/editor/font-preload.test.ts` — pins the `CANVAS_FONT_FACES` registry (lockstep guard).
- `frontend-public/tests/editor/debug-overlay.test.ts` + `overlay-render.test.ts` — render-overlay coverage.
- `frontend-public/tests/components/editor/font-gate.test.tsx` — tests `exportPNG` font-gate behavior including the B1 timeout fix.
- `frontend-public/tests/components/editor/components/TopBar.test.tsx` — describes "TopBar — Crop zone toggle" (line 40); no Export-button-flow assertions.
- `frontend-public/tests/components/editor/context-menu-integration.test.tsx:6,21` — canonical jsdom workaround pattern: `HTMLCanvasElement.getContext` returns `null` in jsdom, plus `Object.defineProperty(HTMLCanvasElement.prototype, "getBoundingClientRect", ...)` mock. Recon-proper PR#1 helper tests should follow this pattern.
**Counts:** `find frontend-public/tests -name "*.test.ts*" | wc -l` → **70 total**; **15+ files** mention render/export/preset (renderer-contract, measure, ui, overlay-render, font-preload, debug-overlay, font-gate, layout, DownloadModal, i18n-ru-render-smoke, ReviewPanel, RightRail, BlockContextMenu, LeftPanel, NoteModal, NotificationBanner — first turn enumerated 15).
**Match vs MD:** `docs/TESTING.md` mentions coverage thresholds; jsdom canvas-mock pattern is convention not MD-documented. No drift.
**Notes:** **No existing test mocks `HTMLCanvasElement.toBlob` for snapshot/hash equality** — `exportPNG` flow is NOT covered by an end-to-end test. PR#1 (pure render helper) should add the first such test; PR#3 (fflate ZIP) will need `toBlob` mocking to assert ZIP entry filenames + manifest contents without running real PNG encoding under jsdom.

### 2.J — i18n surface for new export UI

**Verdict:** partial — existing `export.*` namespace covers single-PNG; new `editor.export_zip.*` namespace required.
**Primary file(s):** `frontend-public/messages/en.json:217-228` (mirror in `ru.json:217-...`).
**Existing keys (6 total under `export.*`):**
```
export.png.verb
export.document_json
export.disabled.loading_fonts
export.disabled.validation_errors
export.label_short
export.json_label_short
```
Plus three preset-related keys outside `export.*`: `editor.theme.option.size.aria` (`messages/en.json:611-613`), `editor.cropZoneTooltip` (line 242), `validation.layout.*` size-warnings (lines 173-180).
**Match vs MD:** convention from CLAUDE.md `i18n-developer-guide.md` says assert on `namespace.key` in tests — current keys conform. No MD describes ZIP-export key shape.
**Proposed namespace:** `editor.export_zip.*` (recon-proper finalizes). New keys likely needed:
- `editor.export_zip.button.label` / `.aria` ("Export all valid")
- `editor.export_zip.button.disabled.no_presets_selected`
- `editor.export_zip.progress.rendering` (per-preset count)
- `editor.export_zip.toast.success` (with filename + count)
- `editor.export_zip.toast.partial` (some presets QA-failed)
- `editor.export_zip.toast.error`
- `validation.long_infographic.height_cap_exceeded` (per §2.H, sits under existing `validation.*` ns, NOT under `export_zip.*`).
**Notes:** RU mirror MUST be added in same PR per `eslint-plugin-i18next` config. Preset-name labels (e.g. "Instagram Story", "LinkedIn") are currently composed via the ID + `SIZES[k].n` literal (`LeftPanel.tsx:142`); if recon decides to localize preset names per `DESIGN_SYSTEM_v3.2.md` БЛОК 14 (Localization & Formatting Policy), that's additional surface — flagged for §3.

## 3. Open questions for recon-proper

The following questions remain open after pre-recon. Recon-proper consumes
this list and either resolves each (with founder Q&A as needed) or
escalates back to founder. Do NOT answer them here.

Founder-decided questions (long_infographic, exportPresets, PR estimate,
max-height policy) are NOT in this list — they are locked in §1.

### Q-2.1-1 — Re-entrant render path

**Why it matters:** PR#1 extracts a pure-or-near-pure render helper from `engine.ts:14-58` (impure). If the existing path carries export-once-then-tear-down state (e.g. globals reset after first call), sequential per-preset rendering will break unless the helper is made re-entrant.
**Pre-recon evidence:** §2.A single-PNG entry at `index.tsx:1211-1250`, §2.B engine.ts purity classification.
**Recon-proper must answer:** YES (re-entrant clean) / NO (must refactor) / UNCLEAR (needs runtime probe). Cite the specific lines that read or write export-only state.

### Q-2.1-2 — Per-preset QA evaluator placement

**Why it matters:** Existing QA is document-level (§2.D). Per-preset evaluation is a new dimension. Recon picks whether new module `editor/export/perPresetQa.ts` or extension of existing QA selector.
**Pre-recon evidence:** §2.D.
**Recon-proper must answer:** new-module / extend-existing / hybrid (with rationale).

### Q-2.1-3 — ZIP filename source

**Why it matters:** Format `<publication-slug>-<timestamp>.zip` requires the slug. §2.A and §2.F should reveal the source; if neither covers it, recon must.
**Pre-recon evidence:** §2.A, §2.F.
**Recon-proper must answer:** specific path (e.g. `state.doc.page.meta.slug`) or fetch-from-autosave-response.

### Q-2.1-4 — fflate version pin policy

**Why it matters:** Bundle-size impact (~8KB gzipped) acknowledged. Memory item: "no new dependencies without justification" — fflate is justified, but pin policy must match repo conventions.
**Pre-recon evidence:** §2.E (fflate absent).
**Recon-proper must answer:** specific version (e.g. `^0.8.x`) and rationale (latest-stable vs known-stable in adjacent projects).

### Q-2.1-5 — Progress UI granularity

**Why it matters:** Sequential render of 7 presets at 200-500ms each = 2-4 sec total. Visual feedback options vary.
**Pre-recon evidence:** §2.A export trigger location, TopBar precedent.
**Recon-proper must answer:** (a) overall spinner / (b) per-preset bar N/7 / (c) per-preset bar with named preset label.

### Q-2.1-6 — Cancellation during render

**Why it matters:** If operator triggers ZIP and starts editing during render, what happens? Existing single-PNG export probably has no cancel — ZIP makes the question more visible.
**Pre-recon evidence:** §2.A export trigger.
**Recon-proper must answer:** (a) block edits during ZIP gen / (b) allow edits + abort ZIP / (c) allow edits + continue ZIP with snapshot.

### Q-2.1-7 — manifest.json schema for 2.1

**Why it matters:** Phase 2.2 extends this; needs forward-compat shape now.
**Pre-recon evidence:** §1 locked scope; §2.F backend touchpoints (NONE).
**Recon-proper must answer:** specific schema. Starting proposal: `{ schemaVersion: 1, publication_id, created_at, presets: [{ id, filename, width, height }] }`. Recon validates and adds anything else needed for 2.2 forward-compat.

### Q-2.1-8 — exportPresets default value semantics

**Why it matters:** Migration N→N+1 default for existing documents. New documents default to all-7-enabled or smaller "common 4" set?
**Pre-recon evidence:** §2.D PageConfig shape; §1 locked scope (all 7 included).
**Recon-proper must answer:** default value as JSON, plus migration default for existing docs.

### Q-2.1-9 — Toggle UI placement

**Why it matters:** Affects PR#2 scope. If new modal needed, PR#2 grows from M to L.
**Pre-recon evidence:** TopBar component, Inspector component.
**Recon-proper must answer:** (a) TopBar / (b) Inspector / (c) dedicated Export modal — with rationale based on existing UI vocabulary.

### Q-2.1-10 — long_infographic 4000px cap behavior detail

**Why it matters:** Hard cap means: at measure phase, sum of section intrinsicHeights computed → if > 4000, what happens? Founder §1 says QA error blocking export. Recon clarifies blocking scope.
**Pre-recon evidence:** §1 founder decision; §2.D QA categories; §2.G measure path.
**Recon-proper must answer:** (a) document-wide block (no preset exports) / (b) preset-specific block (only long_infographic skipped, other 6 export) / (c) auto-truncate at 4000 with warning. Strongly recommend (b) for operator UX — single oversize preset shouldn't kill the entire ZIP.

### Q-2.1-11 — Test depth on toBlob/ZIP boundary

**Why it matters:** §2.I shows toBlob/ZIP path UNTESTED today. PR#1 introduces toBlob multi-call; PR#3 introduces ZIP packing. `TEST_INFRASTRUCTURE.md` §4.1 mandates real-wire integration for HTTP→state→UI; ZIP is analogous boundary (state→blob→file).
**Pre-recon evidence:** §2.I, `TEST_INFRASTRUCTURE.md` §4.1.
**Recon-proper must answer:** real-wire (actual toBlob execution + ZIP byte verification) / unit-with-mocked-toBlob / hybrid. With test count estimate per PR.

### Q-2.1-12 — Preset-name localization

**Why it matters:** §2.J flagged that preset display labels (e.g. "Instagram Story", "LinkedIn") are currently composed via the literal `SIZES[k].n` field at `LeftPanel.tsx:142`, not via i18n. `DESIGN_SYSTEM_v3.2.md` БЛОК 14 (Localization & Formatting Policy) implies all user-facing strings should be localized. ZIP UI will surface these labels (progress, manifest summary, error toasts).
**Pre-recon evidence:** §2.J `LeftPanel.tsx:142`, `config/sizes.ts:3-10` `n` field.
**Recon-proper must answer:** localize-now (split labels into i18n keys, deprecate `n` field) / defer-to-future-PR (PR#3 uses `n` literal as fallback) / hybrid (manifest uses preset id, UI uses literal). Decision affects PR#2 scope.

### Q-2.1-13 — Preset ID rename direction

**Why it matters:** §2.C drift D1: 5 of 7 code IDs differ from `EDITOR_ARCHITECTURE.md` §6 (`twitter` vs `twitter_landscape`, etc.). Either code or MD must move. Code rename is a breaking change for any persisted document referencing old IDs (`SIZE_TO_BACKEND`/`SIZE_FROM_BACKEND` at `utils/persistence.ts:36-57` already mediates a different rename axis backend↔frontend, so the pattern exists).
**Pre-recon evidence:** §2.C drift table, §4 D1 (forward-ref), `utils/persistence.ts:36-57`.
**Recon-proper must answer:** code→MD (rename code IDs to match MD §6, add legacy aliases in `SIZE_FROM_BACKEND`) / MD→code (founder amends §6 to current code IDs) / both-with-migration. Should be resolved before PR#2 lands so the migration N→N+1 covers ID rename in the same hop.
