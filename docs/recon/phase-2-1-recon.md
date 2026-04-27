# Phase 2.1 — Recon-Proper

**Branch:** claude/create-phase-2-1-recon-UI7I3
**HEAD:** d771484 Merge pull request #213 from Inneren12/claude/phase-2-1-pre-recon-finalize
**Date:** 2026-04-27
**Status:** WORK IN PROGRESS — Turn 1 of 3 (§1, §2, §3 partial Q-1..6).

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
