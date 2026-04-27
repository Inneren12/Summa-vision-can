# Phase 2.1 — Recon-Proper

**Branch:** claude/create-phase-2-1-recon-UI7I3
**HEAD:** d771484 Merge pull request #213 from Inneren12/claude/phase-2-1-pre-recon-finalize
**Date:** 2026-04-27
**Status:** APPROVAL_PENDING — recon complete; awaiting founder approval gate decisions on items A1-A5 in §7.

**Consumes:** docs/recon/phase-2-1-pre-recon.md (merged to main as of d771484)
**Produces:** architectural decisions, founder approval gate, PR decomposition for impl phase.

## 1. Executive summary

Phase 2.1 ships **multi-preset client-side ZIP export** for the editor. Operator clicks "Export all valid", browser sequentially renders each enabled preset to PNG, packs into a ZIP with a minimal `manifest.json`, triggers download. No backend changes in 2.1; Phase 2.2 will extend `manifest.json` into a full `distribution.json` and add backend ZIP-upload integration.

**Locked by founder before recon:**
- 7 presets all included (incl. `long_infographic` newly implemented in 2.1)
- "Export all valid" = combo (A) QA-pass + (C) listed in `document.exportPresets`
- ZIP = PNGs + minimal `manifest.json`
- Sequential per-preset rendering
- 4-PR decomposition (revised from roadmap "M, 2-3"; roadmap update deferred to post-recon-merge per Variant α)
- `long_infographic` hard cap 4000px, exceeding triggers QA error
- `exportPresets` field added to PageConfig via schemaVersion bump + migration

**Recon-proper resolves:**
- 13 open questions (8 fully resolved by recon; 5 require founder approval — see §7 in Turn 3)
- 3 drift rows (D1 preset IDs, D2 QA per-preset axis, D3 exportPresets field) — triage in Turn 2 §4
- 8 risks — mitigations in Turn 2 §5
- Final PR boundaries and dependencies — Turn 3 §6

## 2. Scope re-statement (verbatim from pre-recon §1)

This section duplicates pre-recon §1 verbatim so recon is self-contained for impl-phase consumption. Any divergence between this section and pre-recon §1 is a bug in recon — pre-recon is canonical.

### 2.1 Original founder Q1–Q5 (2026-04-27)

- 7 export presets all included: instagram_1080, instagram_portrait, instagram_story, twitter_landscape, reddit_standard, linkedin_landscape, long_infographic.
- "Export all valid" = combo (A) QA-pass + (C) listed in `document.exportPresets`. QA-failed presets skipped with warning, not blocking.
- ZIP contents: per-preset PNGs + minimal `manifest.json`. Phase 2.2 extends manifest into `distribution.json`.
- Rendering strategy: sequential per-preset (Variant A). No Web Workers / OffscreenCanvas in 2.1.
- PR decomposition (original): 2-3 PRs.

### 2.2 Updates after §2.C/D pre-recon findings (founder, 2026-04-27 same day)

- **`long_infographic` IMPLEMENTED in 2.1 scope** (Variant a). Max-height: hard cap 4000px (Variant ii). Exceeding triggers QA error blocking export.
- **`exportPresets` field ADDED to PageConfig** (Variant 2). schemaVersion bump + migration N→N+1. Toggle UI placement TBD per Q-2.1-9.
- **PR estimate revised: 4 PRs minimum** (PR#1 render+long_infographic, PR#2 schema+UI, PR#3 fflate+manifest, PR#4 per-preset QA).
- **Roadmap update deferred** to post-recon-merge (Variant α).

## 3. Open questions — resolutions

Recon-proper consumes pre-recon §3 Q-2.1-1 through Q-2.1-13 and answers each with a recommendation, rationale, and implementation hint. Five of these (Q-2.1-2, 8, 9, 10, 12) are also lifted into the founder approval gate in Turn 3 §7 — those decisions need explicit founder yes/no before impl PR#1 dispatches.

This turn writes Q-2.1-1 through Q-2.1-6. Turn 2 writes Q-2.1-7 through Q-2.1-13.

### Q-2.1-1 — Re-entrant render path

**Recommendation:** YES — `renderDoc` is already re-entrant; PR#1 wraps it in a pure-helper boundary without `renderDoc` modifications.

**Rationale:** Pre-recon §2.B confirms `renderDoc` is invoked twice per session today (preview at `index.tsx:368` and export at `index.tsx:1236`) on different `(w, h)` parameters within the same React render cycle, with no observable state contamination. The function takes all inputs as parameters (no closure reads, no module-scope mutable state), is impure only in that it writes to the passed `ctx`. The export-once-then-tear-down concerns live in the `exportPNG` closure (`index.tsx:1211-1250`), not in `renderDoc` itself. PR#1 extracts a pure helper wrapping this call surface; the helper passes (doc, pal, presetId) → fresh detached canvas + fresh ctx + `renderDoc` invocation → toBlob → Blob, with no shared state across invocations.

**Implementation hint:** PR#1 file structure: `frontend-public/src/components/editor/export/renderToBlob.ts` exporting `async function renderDocumentToBlob(doc: CanonicalDocument, pal: Palette, presetId: string): Promise<Blob>`. Reuses `SIZES[presetId]`, `BGS[doc.page.background]`, existing `renderDoc` import. Caller passes `pal` and `doc` snapshot; helper does not read from store.

### Q-2.1-2 — Per-preset QA evaluator placement

**Recommendation:** Split-rules approach — refactor `validate.ts` into two layers: size-independent rules run once per document, size-dependent rules run once per enabled preset. Single `validate(doc, sizeOverride?)` signature with a `sizeOverride` optional parameter.

**Rationale:** Pre-recon §2.D identifies size-dependent checks at lines 105/117/135/136/142 of `validate.ts` — these are the only rules that need re-running per preset. Size-independent rules (required blocks, contrast, max-chars from §10/§12) cost the same per call regardless of size, so document-level evaluation runs them once and per-preset evaluation skips them. Split-rules avoids the alternatives' costs: doc-clone (allocates copies of large doc trees per preset) and pure signature-change (forces all callers to think about per-preset axis even when document-level is enough). The single-signature with optional override keeps existing single-call sites untouched (`index.tsx:327` passes no override → size-independent + doc-default-size dependent rules, identical behavior).

**Implementation hint:** PR#4 introduces `validateDocument(doc): DocumentValidation` (size-independent) and `validatePresetSize(doc, sizeId): SizeValidation` (size-dependent only). Existing `validate(doc)` wraps both for back-compat. Per-preset evaluator at the ZIP export entry calls `validatePresetSize(doc, presetId)` for each enabled preset; combines with `validateDocument(doc)` once. **FOUNDER APPROVAL REQUIRED — see Turn 3 §7.**

### Q-2.1-3 — ZIP filename source

**Recommendation:** `summa-${doc.templateId}-export-${YYYYMMDD-HHmmss}.zip` (no slug). TemplateId is on doc state (no fetch needed); timestamp is local-tz formatted.

**Rationale:** Single-PNG already uses `summa-${doc.templateId}-${doc.page.size}.png` (pre-recon §2.A) — staying with the same `summa-${templateId}-` prefix keeps user mental model intact. ZIP doesn't need preset-id in filename (it's inside the ZIP). Slug fetching adds backend coupling (autosave-response cache) for one filename token — net cost outweighs benefit. Timestamp format YYYYMMDD-HHmmss avoids timezone/locale ambiguity in filesystem sorting.

**Implementation hint:** PR#3 helper `frontend-public/src/components/editor/export/zipFilename.ts` exporting `function buildZipFilename(doc: CanonicalDocument, now: Date = new Date()): string`. Pure function. Test asserts deterministic format and no special chars that break Windows/macOS file managers.

### Q-2.1-4 — fflate version pin

**Recommendation:** `^0.8.2` (caret on current stable major). Match repo convention for non-framework deps.

**Rationale:** Pre-recon §2.E confirms repo uses `^` for non-framework deps and exact pins only for `next` and `react`. fflate is a non-framework utility library with stable API since 0.7.x; `^0.8.2` accepts patch and minor updates within the 0.8 major, matching the repo's stance on `@hookform/resolvers` (`^5.2.2`), `next-intl` (`^4.9.1`), etc. Bundle impact ~8KB gzipped acknowledged in PR#3 description.

**Implementation hint:** PR#3 adds `"fflate": "^0.8.2"` to `frontend-public/package.json` runtime deps. Use `fflate/browser` ESM import for tree-shake, not the default UMD bundle. Bundle-size delta verified via existing `analyze` script (pre-recon §2.E).

### Q-2.1-5 — Progress UI granularity

**Recommendation:** Option (b) — per-preset progress bar with N/7 counter. No named preset label.

**Rationale:** Sequential render of 7 presets at 200-500ms per preset = 2-4 sec total. (a) overall spinner gives no signal that progress is happening (operator may think it froze). (c) named preset label adds i18n surface (7 preset name translations × 2 locales = 14 keys minimum) for a UX gain that doesn't justify the maintenance. (b) numeric counter "Rendering 4/7…" is unambiguous, locale-light (single key with ICU plural for the count), and bounds operator anxiety. The bar is a thin progress indicator, not a multi-step wizard.

**Implementation hint:** PR#3 component `frontend-public/src/components/editor/components/ZipExportProgress.tsx`. State: `{ current: number, total: number, status: "rendering"|"packing"|"done"|"error" }`. i18n key `editor.export_zip.progress.rendering` with ICU `{current, number}/{total, number}`. Renders inline in TopBar replacing the Export button label during the operation.

### Q-2.1-6 — Cancellation during render

**Recommendation:** Option (c) — allow edits + continue ZIP from doc-snapshot taken at start. Snapshot is `structuredClone(doc)` at the moment "Export all valid" is clicked.

**Rationale:** (a) blocking edits during 2-4 sec is operator-hostile (they may want to fix a small thing they noticed). (b) abort-on-mutation guarantees they restart from scratch — frustrating if they were 5 of 7 presets in. (c) snapshot-and-continue is consistent with the deterministic-export invariant (`ARCHITECTURE_INVARIANTS.md` §8 "Same input → same pixel output") — what they get in the ZIP corresponds exactly to the doc state at click time, and edits flow into a future ZIP. Implementation cost is one `structuredClone(doc)` call (~ms-level even for large docs).

**Implementation hint:** PR#3 entry handler clones doc once: `const snapshot = structuredClone(doc); const enabled = computeEnabledPresets(snapshot, qaResults);` — the entire render loop reads from `snapshot`, not from live state. Editor remains responsive to edits during the loop. Test: dispatch an edit mid-render; assert ZIP contains pre-edit content; assert post-render store reflects post-edit state.

### Q-2.1-7 — manifest.json schema for 2.1

**Recommendation:** Schema:

```json
{
  "schemaVersion": 1,
  "publication_id": null,
  "templateId": "<doc.templateId>",
  "generated_at": "<ISO-8601 UTC>",
  "presets": [
    {
      "id": "<presetId>",
      "filename": "<presetId>.png",
      "width": 1080,
      "height": 1080,
      "qa_status": "pass" | "warning" | "skipped"
    }
  ]
}
```

`publication_id` reserved as nullable for the v1 unattached-export case (operator exports a draft never published yet); Phase 2.2 fills it when integrating with the publish flow. `qa_status` enumerates the three outcomes per preset.

**Rationale:** schemaVersion at the top makes Phase 2.2 forward-compat trivial — bump to 2 when adding `distribution.json` fields (UTM tags, social captions, channel overrides). `presets` is an array (not a map) so order matches export order, matching `document.exportPresets` order, giving operators a predictable manifest. `qa_status` per preset is required by combo (A)+(C) — without it the manifest can't tell consumers which presets were skipped vs included.

**Implementation hint:** PR#3 type `frontend-public/src/components/editor/export/manifest.ts` exports `interface ZipManifest` matching the schema, plus `function buildManifest(doc, results, generatedAt: Date): ZipManifest`. Manifest is JSON-stringified at the end of the render loop, added to the ZIP as `manifest.json` (top-level entry, no subfolder).

### Q-2.1-8 — exportPresets default value semantics

**Recommendation:** Default to **`["instagram_1080", "twitter", "reddit", "linkedin"]`** (the "common 4") for both new documents and migration of existing documents. Operators opt-in to story / portrait / long_infographic per-document via the toggle UI (Q-2.1-9).

**Rationale:** All-7-enabled-by-default produces a 7-PNG ZIP every export; story (1080×1920) and long_infographic (4000px) are heavy and not always wanted. Common-4 covers the highest-signal channels (Instagram feed, X, Reddit, LinkedIn) per `OPERATOR_AUTOMATION_ROADMAP.md` distribution targets. Migration of existing documents to common-4 is safer than to all-7 — existing drafts that operators expected to export to a single Instagram size won't suddenly produce 7 PNGs without consent. Operators noticing missing presets in their first ZIP after migration is a recoverable surprise; operators getting unexpected story/long_infographic PNGs is a confusing one. **FOUNDER APPROVAL REQUIRED — see Turn 3 §7.**

**Implementation hint:** PR#2 migration N→N+1 sets `page.exportPresets = ["instagram_1080", "twitter", "reddit", "linkedin"]` for any document missing the field. New-document factory in editor uses the same default. Constant `DEFAULT_EXPORT_PRESETS` in `frontend-public/src/components/editor/config/sizes.ts` so migration and factory share one source of truth.

### Q-2.1-9 — Toggle UI placement for exportPresets

**Recommendation:** **Inspector** (Variant b) — under existing page-properties section, alongside `page.size`. Render as a checkbox list of 7 presets with the current preset (matching `page.size`) marked as required-on.

**Rationale:** `page.size` already lives in the Inspector page-properties pane (existing convention); `exportPresets` is logically the same axis (which sizes does this document target?). TopBar (Variant a) burns top-bar real estate for a setting changed once per document, not per session — wrong density. Modal (Variant c) is more discoverable but pushes PR#2 from M to L per pre-recon §5 Risk 6, and the modal-open UX implies the setting is rarely-touched, contradicting that the operator should review it before every ZIP. Inspector is the right answer if "review before export" is the workflow expectation, and the right answer if the operator forgot — Inspector is one click away from the canvas. The current preset (matching `page.size`) is force-enabled because exporting the design-time size with QA-pass is the minimum sensible ZIP — preventing operators from accidentally producing an empty ZIP. **FOUNDER APPROVAL REQUIRED — see Turn 3 §7.**

**Implementation hint:** PR#2 component `frontend-public/src/components/editor/components/PageInspector.tsx` (or wherever current `page.size` selector lives — recon does not pre-fix the path; agent verifies during impl). Add a new section "Export presets" with 7 checkboxes wired to `doc.page.exportPresets`. Current `page.size` checkbox is `disabled checked`. i18n keys under `editor.inspector.export_presets.*`.

### Q-2.1-10 — long_infographic 4000px cap blocking scope

**Recommendation:** **Option (b) — preset-specific block.** Only `long_infographic` is skipped from the ZIP when its measured height exceeds 4000px; the other 6 presets export normally with a warning shown on the manifest entry's `qa_status: "skipped"` and a UI notification "long_infographic skipped: exceeds 4000px max height. N other presets exported."

**Rationale:** Document-wide block (Variant a) penalizes the operator for a single oversized preset they may not even have selected for distribution. Auto-truncate (Variant c) silently corrupts the editorial intent — content below 4000px is invisible in the export but visible in the editor, breaking deterministic-export trust. Preset-specific block (Variant b) preserves the deterministic-export invariant (the included presets are pixel-correct), gives operators actionable feedback (single named preset is the problem), and works naturally with combo (A)+(C) — long_infographic already needs per-preset QA evaluation per Q-2.1-2 to validate cap. **FOUNDER APPROVAL REQUIRED — see Turn 3 §7.**

**Implementation hint:** PR#1 measure-phase: when computing `long_infographic` intrinsic height, if Σ section heights > 4000, emit `validation.long_infographic.height_cap_exceeded` error scoped to preset `long_infographic`. PR#4 per-preset QA evaluator reads this scoped error → marks `long_infographic` as `qa_status: "skipped"` in manifest and excludes from render loop. Other 6 presets unaffected. UI notification is a single toast at end of export "long_infographic skipped: <reason>. <N> presets exported successfully."

### Q-2.1-11 — Test depth on toBlob/ZIP boundary

**Recommendation:** **Hybrid (Variant c)** — unit-test per helper (renderDocumentToBlob, buildManifest, buildZipFilename, packZip) with mocked `toBlob` returning predictable bytes, PLUS one real-wire end-to-end test per PR (PR#1 and PR#3) that runs the actual flow and asserts on output bytes via `fflate.unzipSync` to verify ZIP entry filenames + manifest content.

**Rationale:** Pure unit tests with mocked toBlob (Variant b) keep iteration fast but miss the regression class that hurt Slice 3.8 (`TEST_INFRASTRUCTURE.md` §4.1) — pipeline state contamination. Real-wire-only (Variant a) is slow per assertion. The hybrid pattern adopts `TEST_INFRASTRUCTURE.md` §4.1 mandate for HTTP→state→UI boundaries to the analogous render→blob→file boundary. PR#1 estimate: ~12 unit tests + 1 integration. PR#3 estimate: ~8 unit tests + 1 integration that asserts ZIP unzips and contains expected `manifest.json` + N `<preset>.png` entries.

**Implementation hint:** Test files: PR#1 adds `frontend-public/tests/components/editor/export/renderToBlob.test.ts` (unit) and `frontend-public/tests/components/editor/export/renderToBlob.integration.test.tsx` (real-wire). PR#3 adds `frontend-public/tests/components/editor/export/zipExport.test.ts` (unit per helper) and `frontend-public/tests/components/editor/export/zipExport.integration.test.tsx` (real-wire end-to-end). Both integration tests use the canvas-mock pattern from `tests/components/editor/context-menu-integration.test.tsx:6,21` (jsdom workaround for HTMLCanvasElement.getContext returning null).

### Q-2.1-12 — Preset ID rename strategy

**Recommendation:** **Code-rename to match MD §6**, with backward-compat alias map in `utils/persistence.ts`. After 2.1 merge, MD §6 is the canonical source — code reflects MD, not the other way around.

**Rationale:** Pre-recon §4 D1 marks this as High severity. The MD is canonical reference for the architecture (designers, marketing, operators consult it); renaming the MD to match code embeds informal naming into the architectural surface. Code-rename keeps MD authoritative. Alias map (`SIZE_FROM_BACKEND`) handles existing serialized documents in DB — old documents stored with `twitter` resolve to `twitter_landscape` on load. Hard-rename without aliases corrupts existing documents on first edit. **FOUNDER APPROVAL REQUIRED — see Turn 3 §7.**

**Implementation hint:** PR#2 (the schema-touching PR) renames keys in `frontend-public/src/components/editor/config/sizes.ts`:
- `instagram_port` → `instagram_portrait`
- `story` → `instagram_story`
- `twitter` → `twitter_landscape`
- `reddit` → `reddit_standard`
- `linkedin` → `linkedin_landscape`

Adds aliases to `utils/persistence.ts` `SIZE_FROM_BACKEND` so old IDs resolve forward. Migration N→N+1 in same PR rewrites stored `page.size` and `page.exportPresets` values to new IDs at document load.

### Q-2.1-13 — Safe-area / per-platform rules location

**Recommendation:** **Out-of-scope for Phase 2.1**. Add a follow-up DEBT entry. Per-platform safe areas and max-series / min-font / preferred-mode rules from `DESIGN_SYSTEM_v3.2.md` БЛОК 11 are not blocking ZIP export; they're a content-quality concern that becomes more relevant when per-preset QA from Q-2.1-2 is actively scoring exports against platform-specific minimums.

**Rationale:** Including safe-area encoding in Phase 2.1 would require: (a) extending `SizePreset` shape with `safeAreas` field, (b) modifying renderer to honor safe-area boundaries, (c) per-platform QA checks evaluating min-font / max-series. That's a separate body of work — call it Phase 2.1.5 or fold into Phase 3 binding-status work where data-driven font sizes are computed. ZIP export ships without it; documents currently produced without explicit safe-areas will continue producing ZIPs with the same visual fidelity they have today.

**Implementation hint:** No PR action in 2.1. Turn 3 §6 PR decomposition does NOT include safe-area work. Recon-proper Turn 3 also adds DEBT entry "DEBT-NN — Encode per-platform safe-areas + min-font / max-series rules from DESIGN_SYSTEM_v3.2.md БЛОК 11" with status active, severity low (not blocking 2.1), category code-quality.

## 4. Drift triage

Pre-recon §4 surfaced 3 drift rows. Recon-proper resolves which are closed in Phase 2.1 vs which remain follow-up.

### D1 — Preset IDs (High severity)

**Resolved by:** Q-2.1-12 — code-rename to match MD §6 + back-compat aliases.
**PR:** PR#2 (schema migration PR includes the rename).
**Closure:** After PR#2 merges, `EDITOR_ARCHITECTURE.md` §6 IDs and code IDs match. Aliases preserved indefinitely for old serialized documents.

### D2 — QA per-preset axis (High severity)

**Resolved by:** Q-2.1-2 — split-rules approach (size-independent + size-dependent), Q-2.1-9 — exportPresets toggle making per-preset evaluation reachable from operator UI, Q-2.1-10 — preset-specific cap-blocking honors per-preset evaluation.
**PR:** PR#4 (per-preset QA evaluator + UI integration).
**Closure:** After PR#4 merges, combo (A)+(C) is fully implementable. `validate.ts` exports `validateDocument` and `validatePresetSize` separately. UI shows per-preset QA status in the export panel. After 2.1 merge, founder updates `EDITOR_ARCHITECTURE.md` §15 to clarify per-preset semantics — that's a docs-only PR, ~10 lines, not blocking.

### D3 — exportPresets field (Medium-High severity)

**Resolved by:** Q-2.1-8 — default value semantics, Q-2.1-9 — toggle UI placement, founder Variant 2 lock from §1.
**PR:** PR#2 (schema migration PR adds field + migration + UI).
**Closure:** After PR#2 merges, `PageConfig` has `exportPresets: string[]` field. All existing documents migrated to common-4 default. Schema docs updated in same PR.

### Drift not surfaced in pre-recon but found during recon

None as of Turn 2. If Turn 3 surfaces additional drift during PR-decomposition design (e.g. existing test patterns assuming document-level QA), add D4+ rows here in Turn 3.

## 5. Risk mitigations

Pre-recon §5 listed 8 risks. Recon-proper assigns each a concrete mitigation (test pattern, PR boundary, documentation discipline).

### Risk 1 — Render helper extraction from impure exportPNG closure

**Mitigation:** Q-2.1-1 confirms `renderDoc` itself is re-entrant. PR#1 helper signature is documented as `main-thread-only, rAF-bound, must NOT be called from Web Worker context` — explicit JSDoc on `renderDocumentToBlob`. Test: invoke helper 7 times back-to-back in a single tick; assert all 7 resolve with distinct Blob bytes (no shared state contamination).

### Risk 2 — long_infographic implementation expands PR#1 scope ~50%

**Mitigation:** PR#1 explicit scope split into two phases within the same PR:
1. Pure render helper for fixed-size presets (existing 6).
2. Variable-height extension for `long_infographic` with cap enforcement at measure phase.

If during impl phase 2 reveals deeper `measureLayout` rework than estimated, defer phase 2 to a separate PR#1.5 between PR#1 and PR#2. Recon flags this as a permitted late-stage split — impl agent notifies founder when invoking the split.

### Risk 3 — Schema migration discipline (PR#2)

**Mitigation:** PR#2 includes migration test fixture `frontend-public/tests/components/editor/migrations/v(N)-to-v(N+1).test.ts` with three round-trip scenarios:
1. Pre-migration document with no `exportPresets` → migrates to default common-4.
2. Pre-migration document with old preset IDs in `page.size` (e.g. `twitter`) → migrates to `twitter_landscape`.
3. Pre-migration document with `page.size` already on a renamed ID (forward-compat sanity) → unchanged.

`applyMigrations` abort-on-missing-intermediate from `EDITOR_BLOCK_ARCHITECTURE.md` §6 is verified by adding a deliberately-missing intermediate test that asserts the abort throws.

### Risk 4 — Font-gate single-check semantics

**Mitigation:** PR#1 helper's JSDoc states explicitly: "Caller must ensure `document.fonts.ready` resolved before invoking. Helper does NOT re-check fonts between invocations. For sequential per-preset rendering, check fonts ONCE at loop entry." Caller responsibility, not helper-internal state. PR#3 export trigger code adds a comment at the loop-entry font-check tying back to this contract.

### Risk 5 — Test coverage gap on toBlob/ZIP boundary

**Mitigation:** Q-2.1-11 hybrid testing pattern — every PR introducing a new helper adds unit + one real-wire integration test minimum. PR#1: renderDocumentToBlob unit + integration. PR#3: buildManifest, buildZipFilename, packZip units + ZIP integration that uses `fflate.unzipSync` to verify byte-level correctness.

### Risk 6 — UI placement for exportPresets toggle

**Mitigation:** Q-2.1-9 picks Inspector (Variant b) — in-budget for PR#2 M-size estimate. Modal option (c) explicitly rejected to keep PR#2 in M.

### Risk 7 — 4-PR estimate vs roadmap "M, 2-3 PRs"

**Mitigation:** Recon-proper §6 (Turn 3) explicitly states "supersedes roadmap row 2.1 estimate". Founder updates `OPERATOR_AUTOMATION_ROADMAP.md` row 2.1 in a docs-only PR after recon-proper merges. During the recon period (now until merge), `OPERATOR_PHASE_STATUS.md` row 2.1 stays at status `Pending` — when impl PRs land, founder updates to `In progress`. No silent drift between roadmap and actual scope.

### Risk 8 — Preset ID rename ripple (Q-2.1-12 / D1)

**Mitigation:** Q-2.1-12 picks code-rename WITH back-compat aliases. The aliases live in `SIZE_FROM_BACKEND` (`utils/persistence.ts:36-57` per pre-recon §2.C). PR#2 migration test (Risk 3 mitigation, scenario 2) explicitly covers old-ID → new-ID resolution. The forward-compat case (already-renamed) is also tested (scenario 3). Rename direction is one-way: code renamed → matches MD; aliases handle pre-rename DB state.

## 6. PR decomposition

Founder Variant 2 + Variant a from §1 expands roadmap "M, 2-3 PRs" to **4 PRs minimum** (revised estimate per pre-recon §5 Risk 7). This recon is the authoritative source for Phase 2.1 scope; `OPERATOR_AUTOMATION_ROADMAP.md` row 2.1 will be updated by founder post-recon-merge per Variant α.

### PR#1 — Pure render helper + long_infographic rendering

**Branch:** `claude/phase-2-1-pr-1-render-helper-<suffix>`
**Estimate:** M (~3-5 days impl + 1-2 fix rounds)
**Depends on:** none (pre-recon and recon merged)
**Blocks:** PR#3 (ZIP export needs this helper)

**Scope (in):**
- New module `frontend-public/src/components/editor/export/renderToBlob.ts` — pure async helper
- Variable-height extension for `long_infographic` preset (Q-2.1-1, Q-2.1-10, Risk 2)
- Cap enforcement at measure phase: `validation.long_infographic.height_cap_exceeded` error scoped to preset
- Unit tests for `renderDocumentToBlob` (mocked toBlob)
- One real-wire integration test (canvas-mock pattern from `tests/components/editor/context-menu-integration.test.tsx`)

**Scope (out — explicitly):**
- ZIP packing (PR#3)
- Per-preset QA evaluator (PR#4)
- `exportPresets` schema field (PR#2)
- Toggle UI (PR#2)
- Safe-area encoding (out-of-scope per Q-2.1-13)

**Files added:**
- `frontend-public/src/components/editor/export/renderToBlob.ts`
- `frontend-public/tests/components/editor/export/renderToBlob.test.ts`
- `frontend-public/tests/components/editor/export/renderToBlob.integration.test.tsx`

**Files modified:**
- `frontend-public/src/components/editor/config/sizes.ts` — add `long_infographic` entry with `h: 4000` cap sentinel
- `frontend-public/src/components/editor/renderer/measure.ts` — variable-height path for `long_infographic`
- `frontend-public/src/components/editor/validation/validate.ts` — cap-exceeded error
- `frontend-public/messages/en.json` + `ru.json` — `validation.long_infographic.height_cap_exceeded` key

**Late-stage split clause (Risk 2):** if measure-phase variable-height work reveals deeper rework than estimated, defer the long_infographic portion to a separate PR#1.5 between PR#1 and PR#2. Impl agent flags founder before splitting.

**Drift docs:** EDITOR_BLOCK_ARCHITECTURE.md §11 maintenance log entry: "Added export/renderToBlob.ts pure helper; long_infographic variable-height rendering with 4000px cap."

### PR#2 — Schema migration + exportPresets field + Inspector UI

**Branch:** `claude/phase-2-1-pr-2-schema-migration-<suffix>`
**Estimate:** M (~3-5 days impl + 1-2 fix rounds)
**Depends on:** PR#1 merged (long_infographic ID exists in SIZES; otherwise migration can't reference it)
**Blocks:** PR#3 (ZIP export needs `exportPresets` field), PR#4 (per-preset QA reads enabled list)

**Scope (in):**
- schemaVersion bump N → N+1
- Migration step in `applyMigrations`: add `exportPresets` field with common-4 default (Q-2.1-8); rename old preset IDs (Q-2.1-12)
- Aliases in `utils/persistence.ts` `SIZE_FROM_BACKEND`
- Type extension `PageConfig.exportPresets: string[]` in `types.ts`
- Inspector UI section "Export presets" — 7 checkboxes (Q-2.1-9)
- Migration tests with three scenarios (Risk 3 mitigation)
- i18n keys under `editor.inspector.export_presets.*`

**Scope (out):**
- ZIP packing (PR#3)
- Per-preset QA UI surfacing (PR#4)
- TopBar / modal placement (rejected per Q-2.1-9)

**Files added:**
- `frontend-public/tests/components/editor/migrations/v(N)-to-v(N+1).test.ts`

**Files modified:**
- `frontend-public/src/components/editor/types.ts` — `PageConfig.exportPresets`
- `frontend-public/src/components/editor/config/sizes.ts` — preset IDs renamed; `DEFAULT_EXPORT_PRESETS` constant
- `frontend-public/src/components/editor/utils/persistence.ts` — `SIZE_FROM_BACKEND` aliases
- `frontend-public/src/components/editor/migrations.ts` (or wherever `applyMigrations` lives)
- `frontend-public/src/components/editor/components/PageInspector.tsx` (or wherever current `page.size` selector lives — agent verifies during impl)
- `frontend-public/messages/en.json` + `ru.json`

**Drift docs:** EDITOR_ARCHITECTURE.md §6 entries match code post-merge (D1 closed). EDITOR_BLOCK_ARCHITECTURE.md §11 entry: "schemaVersion bump for exportPresets field; preset IDs renamed to match MD §6."

### PR#3 — fflate ZIP + manifest.json + Export button

**Branch:** `claude/phase-2-1-pr-3-zip-export-<suffix>`
**Estimate:** M (~2-4 days impl + 1-2 fix rounds)
**Depends on:** PR#1 merged (renderToBlob), PR#2 merged (exportPresets field)
**Blocks:** PR#4 (UI gating reads ZIP-export trigger state)

**Scope (in):**
- New runtime dep: `fflate ^0.8.2` (Q-2.1-4)
- New module `frontend-public/src/components/editor/export/zipExport.ts` — orchestrates render loop, manifest, ZIP packing
- `buildManifest`, `buildZipFilename`, `packZip` helpers (Q-2.1-3, Q-2.1-7)
- TopBar Export button replaced with "Export all valid" (Q-2.1-5)
- Progress UI component (Q-2.1-5 — per-preset N/7 counter)
- Cancellation behavior: snapshot via `structuredClone(doc)` at click, allow edits during render (Q-2.1-6)
- Unit tests + one real-wire integration with `fflate.unzipSync` byte-level verification (Q-2.1-11)
- i18n keys under `editor.export_zip.*`

**Scope (out):**
- Per-preset QA evaluator integration (PR#4 — uses placeholder always-pass for now or document-level check only)
- Backend upload of ZIP (Phase 2.2)
- `distribution.json` extension (Phase 2.2)
- Web Worker rendering (Phase 2.2 if at all)

**Files added:**
- `frontend-public/src/components/editor/export/zipExport.ts`
- `frontend-public/src/components/editor/export/manifest.ts`
- `frontend-public/src/components/editor/export/zipFilename.ts`
- `frontend-public/src/components/editor/components/ZipExportProgress.tsx`
- `frontend-public/tests/components/editor/export/zipExport.test.ts`
- `frontend-public/tests/components/editor/export/zipExport.integration.test.tsx`

**Files modified:**
- `frontend-public/package.json` — `"fflate": "^0.8.2"`
- `frontend-public/src/components/editor/components/TopBar.tsx` — Export button → "Export all valid"
- `frontend-public/src/components/editor/index.tsx` — replace `exportPNG` callback or sit alongside; reuse `deferRevoke` from `utils/download.ts`
- `frontend-public/messages/en.json` + `ru.json`

**Drift docs:** EDITOR_BLOCK_ARCHITECTURE.md §11 entry: "Multi-preset ZIP export shipped; fflate added; manifest.json schema v1."

### PR#4 — Per-preset QA evaluator + UI integration

**Branch:** `claude/phase-2-1-pr-4-per-preset-qa-<suffix>`
**Estimate:** S-M (~2-3 days impl + 1 fix round)
**Depends on:** PR#1 merged (cap error type exists), PR#2 merged (exportPresets field), PR#3 merged (ZIP pipeline emits per-preset slots in manifest)
**Blocks:** none — closes Phase 2.1

**Scope (in):**
- Refactor `validate.ts` into `validateDocument(doc)` + `validatePresetSize(doc, sizeId)` (Q-2.1-2)
- Existing `validate(doc)` becomes a back-compat wrapper that combines both
- ZIP export pipeline calls `validatePresetSize` per enabled preset; combo (A) skip-on-failure logic
- Inspector UI shows per-preset QA badge next to each enabled preset
- Toast at end of ZIP export "long_infographic skipped: ..." (Q-2.1-10) when applicable
- Unit tests for new selectors + integration test that exercises skip-on-fail flow

**Scope (out):**
- Cross-platform safe-area / max-series / min-font checks (DEBT-NN per Q-2.1-13)
- Document-level validation rule changes (out of scope — only refactor structure)

**Files modified:**
- `frontend-public/src/components/editor/validation/validate.ts` — split signature
- `frontend-public/src/components/editor/components/PageInspector.tsx` — per-preset badge
- `frontend-public/src/components/editor/export/zipExport.ts` (from PR#3) — combo (A) gate
- `frontend-public/messages/en.json` + `ru.json` — toast keys, badge labels

**Drift docs:** EDITOR_ARCHITECTURE.md §15 — founder updates post-merge to clarify per-preset semantics (D2 closed). Docs-only follow-up PR ~10 lines.

### Dependency graph

```
PR#1 ─────┬─→ PR#2 ─────┬─→ PR#3 ─────→ PR#4
          │              │
          │              └─ PR#3 also needs PR#1 (renderToBlob)
          │
          └─ PR#2 also needs PR#1 (long_infographic ID in SIZES)
```

Critical path: PR#1 → PR#2 → PR#3 → PR#4. Total estimate: 10-17 days impl + fix rounds, ~2-3 weeks elapsed.

### Roadmap update (post-recon-merge action)

Founder updates `OPERATOR_AUTOMATION_ROADMAP.md` row 2.1 from "M, 2-3 PRs" to "M, 4 PRs (PR#1-4 per recon)" in a docs-only PR after recon merges. Variant α deferral closes here.

## 7. Founder approval gate

The following architectural decisions are flagged for founder approval throughout §3. Founder reviews each, approves with explicit yes / no / change. Recon-proper does not dispatch impl prompts until all five are resolved.

### Approval item A1 — Per-preset QA evaluator (Q-2.1-2)

**Recommendation:** Split-rules approach — `validateDocument(doc)` (size-independent) + `validatePresetSize(doc, sizeId)` (size-dependent only). Existing `validate(doc)` wraps both for back-compat.

**Founder decision:** [ ] approve / [ ] reject / [ ] modify with: ____________

### Approval item A2 — Default exportPresets value (Q-2.1-8)

**Recommendation:** Default to `["instagram_1080", "twitter", "reddit", "linkedin"]` (common-4) for both new documents and migration of existing documents.

**Founder decision:** [ ] approve common-4 / [ ] approve all-7 / [ ] modify with: ____________

### Approval item A3 — Toggle UI placement (Q-2.1-9)

**Recommendation:** Inspector page-properties section (Variant b), alongside `page.size`. Current preset force-enabled.

**Founder decision:** [ ] approve Inspector / [ ] TopBar instead / [ ] Modal instead / [ ] modify with: ____________

### Approval item A4 — long_infographic cap blocking scope (Q-2.1-10)

**Recommendation:** Preset-specific block (Variant b) — only `long_infographic` skipped from ZIP when over cap; other 6 presets export normally with toast notification.

**Founder decision:** [ ] approve preset-specific / [ ] document-wide block / [ ] auto-truncate / [ ] modify with: ____________

### Approval item A5 — Preset ID rename strategy (Q-2.1-12)

**Recommendation:** Code-rename to match MD §6, with backward-compat aliases in `SIZE_FROM_BACKEND`. After 2.1 merge, MD is canonical.

**Founder decision:** [ ] approve code-rename / [ ] update MD instead / [ ] modify with: ____________

### Resolution protocol

When all five boxes have a non-empty decision, founder posts a single message:
> "Approval gate resolved: A1=approve, A2=approve, A3=approve, A4=approve, A5=approve" (or with specifics).

Recon-proper status flips from `APPROVAL_PENDING` to `APPROVED`. Impl prompts for PR#1 dispatch immediately after.

## 8. Test plan consolidated

Aggregates test counts and patterns across all 4 PRs. Real-wire integration tests follow `TEST_INFRASTRUCTURE.md` §4.1 pattern (mock at fetch / canvas boundary, not at consumer module).

| PR | Unit tests | Integration tests | Migration tests | Notes |
|---|---|---|---|---|
| PR#1 | ~12 (renderDocumentToBlob, measure variable-height, cap-exceeded) | 1 (real-wire renderToBlob) | — | Re-entrancy test (Risk 1) — invoke helper 7× single-tick, assert distinct blob bytes |
| PR#2 | ~8 (PageInspector toggle, exportPresets default constant) | — | 3 scenarios (Risk 3) | Migration scenarios: missing field → common-4; old IDs → renamed; already-renamed → unchanged |
| PR#3 | ~8 (buildManifest, buildZipFilename, packZip) | 1 (real-wire ZIP unzip + manifest verify) | — | Real-wire uses `fflate.unzipSync` to assert byte-level entries |
| PR#4 | ~6 (validateDocument, validatePresetSize, badge selector) | 1 (skip-on-fail flow with long_infographic over cap) | — | Skip-on-fail integration asserts 6 PNGs in ZIP, manifest skipped entry, toast text |
| **Total** | **~34** | **3** | **3** | Estimate, may flex ±20% |

### jsdom canvas workaround

All integration tests use the canvas-mock pattern established in `tests/components/editor/context-menu-integration.test.tsx:6,21`:

```typescript
// HTMLCanvasElement.getContext returns null in jsdom by default
// Mock it to return a stub ctx with measureText, fillText, etc.
HTMLCanvasElement.prototype.getContext = jest.fn(() => stubCtx);
```

Reuse the existing stub from `renderer-contract.test.ts:3-36` (`makeCtx()`) — extract to a shared test util in PR#1 if not already.

### Coverage gate

PR#1, PR#3 each must have one real-wire integration test minimum (Risk 5 mitigation). Reviewer rejects PR if absent. PR#2 doesn't need integration test (no canvas/blob boundary, just schema). PR#4's integration test exercises the skip-on-fail flow end-to-end since that's the critical user-visible behavior.

## 9. DEBT entry stub for Q-2.1-13

To be added to `DEBT.md` by founder when impl PR#1 lands (or earlier if convenient — recon does NOT modify DEBT.md, this is a stub for the founder commit). Following the existing DEBT.md format observed in repo.

````markdown
### DEBT-NN: Encode per-platform safe-areas + min-font / max-series rules

- **Source:** Phase 2.1 recon Q-2.1-13
- **Added:** <date when founder commits>
- **Severity:** low (not blocking 2.1, content-quality concern)
- **Category:** code-quality
- **Status:** active
- **Description:** `DESIGN_SYSTEM_v3.2.md` БЛОК 11 specifies safe areas (top 48 / bottom 80 / L-R 48; story top 120 / bottom 100) and per-platform max-series / min-font / preferred-mode rules. Currently NOT encoded anywhere in code.
- **Impact:** Per-preset QA from PR#4 evaluates document-level rules but cannot enforce platform-specific minimums (e.g. min font 13px for Twitter cards, 14px for Instagram feed, 12px for LinkedIn). Operator may export technically-valid PNGs that violate per-platform readability standards.
- **Resolution:**
  - Extend `SizePreset` shape in `config/sizes.ts` with `safeAreas: { top, bottom, left, right }` field
  - Modify renderer to honor safe-area boundaries (visual: warn-on-overflow if any block extends past safe area)
  - Add per-platform QA checks to `validatePresetSize` evaluating min-font / max-series
- **Target:** Phase 2.1.5 standalone OR fold into Phase 3 binding-status work where data-driven font sizes are computed.
````

NN is the next available DEBT number. Founder picks at commit time.

## Document history

| Date | Turn | Notes |
|---|---|---|
| 2026-04-27 | 1 | §1 executive summary, §2 scope restate, §3 Q-1..6 |
| 2026-04-27 | 2A | §3 Q-7..10 (after stream-timeout split from Turn 2) |
| 2026-04-27 | 2B | §3 Q-11..13, §4 drift triage, §5 risk mitigations |
| 2026-04-27 | 3A | §6 PR decomposition (preventively split from Turn 3 due to size) |
| 2026-04-27 | 3B | §7 founder approval gate, §8 test plan, §9 DEBT stub, document history. Status flipped to APPROVAL_PENDING. |
