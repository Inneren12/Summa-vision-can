# Phase 1.4 Recon — Platform Crop Zone overlays

- Date: 2026-04-26
- Branch target: `claude/phase-1-4-recon`
- Recon mode: strict planning only (no implementation code changes in this PR)
- Primary output: this document (`docs/recon/phase-1-4-crop-zone-recon.md`)

---

## Scope and intent

This recon translates founder-locked decisions (D1–D7) into a verification-ready implementation spec for Stage C. It intentionally does **not** contain code edits for runtime behavior.

This document is self-contained so an implementation agent can execute without opening the pre-recon file.

### Inputs consumed

1. Founder lock decisions (provided in prompt, dated 2026-04-26).
2. Fresh repository reads performed during authoring (see Verification Log).
3. Existing architecture constraints around editor canvas layering and export determinism.

### Non-goals for this PR

- No backend schema/API changes.
- No frontend runtime changes.
- No message catalog edits.
- No tests added in this PR (test plan is specified for impl phase).

---

## Verification log (performed during recon authoring)

### Pre-flight

- `git status --short` returned empty output (workspace clean).
- `git remote -v` returned empty output (no remotes configured in this environment).
- `test -f docs/recon/phase-1-4-crop-zone-pre-recon.md` returned `PRE_RECON_MISSING`.

Interpretation:
- Clean workspace gate passed.
- Push-to-origin flow cannot be executed in this sandbox because no remote is configured.
- Missing local pre-recon file is expected per task notes; founder-provided context in prompt was used.

### Required code reads

#### 1) Overlay renderer contract
Command:

```bash
sed -n '1,140p' frontend-public/src/components/editor/renderer/overlay.ts
```

Observed excerpt:

```ts
export interface OverlayRenderInput {
  ctx: CanvasRenderingContext2D;
  logicalW: number;
  logicalH: number;
  hitAreas: readonly HitAreaEntry[];
  selectedBlockId: string | null;
  hoveredBlockId: string | null;
  dpr: number;
}

export function renderOverlay({
  ctx,
  logicalW,
  logicalH,
  hitAreas,
  selectedBlockId,
  hoveredBlockId,
  dpr,
}: OverlayRenderInput): void {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, logicalW * dpr, logicalH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const hoveredEntry =
    hoveredBlockId && hoveredBlockId !== selectedBlockId
      ? hitAreas.find((e) => e.blockId === hoveredBlockId)
      : undefined;
  const selectedEntry = selectedBlockId
    ? hitAreas.find((e) => e.blockId === selectedBlockId)
    : undefined;

  if (hoveredEntry) {
    drawOutline(ctx, hoveredEntry.hitArea, OVERLAY_STYLE.hover);
  }
  if (selectedEntry) {
    drawOutline(ctx, selectedEntry.hitArea, OVERLAY_STYLE.selected);
  }
}
```

Conclusion:
- Crop zone belongs as optional input on `OverlayRenderInput`.
- Draw order extension should happen after hover/selection render.
- Overlay canvas is already correctly cleared/scaled per DPR and logical size.

#### 2) Editor state section for debug pattern
Command:

```bash
sed -n '140,200p' frontend-public/src/components/editor/index.tsx
```

Observed excerpt (relevant portion):

```ts
const [fontsReady, setFontsReady] = useState<boolean>(false);
const [debugAvailable, setDebugAvailable] = useState<boolean>(
  process.env.NODE_ENV !== 'production',
);
const [debugEnabled, setDebugEnabled] = useState<boolean>(false);
```

Conclusion:
- Crop toggle state should mirror this style:
  - `cropZoneEnabled` boolean state.
  - computed `cropZoneAvailable` memo.

#### 3) TopBar button pattern
Command:

```bash
sed -n '1,120p' frontend-public/src/components/editor/components/TopBar.tsx
sed -n '120,220p' frontend-public/src/components/editor/components/TopBar.tsx
```

Observed excerpt (debug toggle):

```tsx
{debugAvailable && (
  <button
    type="button"
    onClick={onToggleDebug}
    aria-label={debugEnabled ? tDebug('overlay.disable') : tDebug('overlay.enable')}
    title={debugEnabled ? tDebug('overlay.on') : tDebug('overlay.off')}
    style={{
      padding: "3px 6px",
      fontSize: "8px",
      fontFamily: TK.font.data,
      background: debugEnabled ? TK.c.acc : TK.c.bgSurf,
      color: debugEnabled ? TK.c.bgApp : TK.c.txtS,
      border: `1px solid ${debugEnabled ? TK.c.acc : TK.c.brd}`,
      borderRadius: "2px",
      cursor: "pointer",
      fontWeight: debugEnabled ? 700 : 400,
    }}
  >DBG</button>
)}
```

Conclusion:
- New Crop toggle should sit adjacent to DBG and mirror the same inline-style affordance pattern.
- TopBar currently uses inline styles, not utility classes (`cn`, `topbar-toggle`) so implementation spec adapts to repo reality.

#### 4) Test directory existence check
Commands:

```bash
ls frontend-public/tests/components/editor/renderer/ 2>/dev/null
ls frontend-public/tests/components/editor/components/ 2>/dev/null
```

Observed:
- No output for either path.

Conclusion:
- These exact directories may not yet exist in this branch.
- Impl phase should `mkdir -p` as needed and/or align with actual test tree discovered at implementation time.

#### 5) Platform identifier consistency checks
Commands:

```bash
rg -n "PlatformId|platform_id" frontend-public/src/components/editor/utils/persistence.ts
rg -n "PlatformId|platform_id" backend/src/schemas/publication.py
rg -n "platform_id" backend/src/services/graphics/svg_generator.py
rg -n "reddit|twitter|linkedin|platform" frontend-public/src/components/editor/utils/persistence.ts backend/src/schemas/publication.py backend/src/services/graphics/svg_generator.py
```

Observed:
- `frontend-public/src/components/editor/utils/persistence.ts` contains mappings for `twitter`, `reddit`, `linkedin`.
- `backend/src/schemas/publication.py` docstring enumerates `instagram`, `twitter`, `reddit`, `linkedin`, `story`.
- `backend/src/services/graphics/svg_generator.py` contains size presets for `twitter` and `reddit` (and by codebase convention `linkedin` elsewhere).

Conclusion:
- Proposed frontend `PlatformId = 'reddit' | 'twitter' | 'linkedin'` is consistent with observed identifiers.

---

## §A. Decisions reference (D1–D7, verbatim intent)

### D1. Platforms supported in v1

- Supported: Reddit, Twitter/X, LinkedIn.
- Excluded in this phase: Instagram-native crop, Story-native crop, Facebook.
- Revisit in Phase 5 only if operator evidence warrants.

### D2. Crop dimensions source of truth

- Source: hardcoded constants in new `frontend-public/src/components/editor/config/cropZones.ts`.
- Coordinate basis: base 1080 units.
- Data shape: sparse map keyed by `(presetId, platformId)` returning `CropZone`.

### D3. UI placement

- Single TopBar toggle next to DBG button.
- Label: Crop zone (localized).
- Tooltip: localized.
- No per-platform chooser in v1.

### D4. Visual style

- 2px solid border, `#9CA3AF`.
- Label pill in upper-left, `#1F2937` background and white text.
- Platform name not translated.
- Full-canvas case: label-only, suppress border.

### D5. Export determinism

- Overlay must never appear in exported PNG.
- Draw on non-export overlay canvas (`overlayRef`) only.

### D6. Single-overlay collapse

- One crop-zone result per preset in v1.
- `instagram_1080` and `instagram_port` target Reddit crop by default.
- Native platform presets produce trivial/full-canvas result.
- `story` has no crop zone; toggle disabled/unavailable.

### D7. i18n keys

Add keys:
- `editor.actions.cropZone`
- `editor.actions.cropZoneTooltip`
- `editor.actions.cropZoneUnavailable`

EN/RU values per founder lock.

---

## §B. Frontend specification

### B.1 New crop config file

Create:

- `frontend-public/src/components/editor/config/cropZones.ts`

Proposed types:

```ts
import type { PlatformId } from '../types';
import { SIZES } from '../config/sizes';

export interface CropZone {
  x: number;
  y: number;
  w: number;
  h: number;
  platform: PlatformId;
}

export type PresetId = keyof typeof SIZES;

export const CROP_ZONES: Partial<
  Record<PresetId, Partial<Record<PlatformId, CropZone>>>
> = {
  // values populated by impl
};

export function getCropZoneForPreset(presetId: string): CropZone | null {
  const platformsForPreset = CROP_ZONES[presetId as PresetId];
  if (!platformsForPreset) return null;
  const entries = Object.values(platformsForPreset);
  return entries[0] ?? null;
}
```

Design choice rationale:
- Keep second-level platform map even if v1 uses max-one entry.
- This avoids future data migration if v1.6 adds multi-platform toggles.

### B.1.a Crop constants to encode (v1 defaults)

Preset matrix (required):

1. `reddit` preset → full-canvas reddit zone.
2. `twitter` preset → full-canvas twitter zone.
3. `linkedin` preset → full-canvas linkedin zone.
4. `instagram_1080` preset → one active zone (D6 collapse defaults to reddit).
5. `instagram_port` preset → one active zone (D6 collapse defaults to reddit).
6. `story` preset → omitted from map (returns null).

Working crop numbers (base 1080 units):

- `instagram_1080` reddit target: x=0, y=135, w=1080, h=810 (centered 4:3).
- `instagram_1080` twitter target: x=0, y=0, w=1080, h=607 (top-aligned 16:9-like).
- `instagram_1080` linkedin target: x=0, y=0, w=1080, h=565 (top-aligned ~1.91:1).

For v1 collapsed behavior, only the reddit entry is returned by helper for instagram presets unless product chooses a deterministic priority field.

### B.1.b Spec verification note for platform dimensions

Given recon timebox and absence of a formal, stable "feed crop viewport" canonical spec across all three platforms in current product docs, this recon carries founder-provided working defaults and records independent verification as a follow-up in §F.

Implementation should add TODO comments in `cropZones.ts` indicating that dims are operating defaults validated by operator feedback loop.

### B.2 Type additions (`types.ts`)

Add:

```ts
export type PlatformId = 'reddit' | 'twitter' | 'linkedin';
```

Placement:
- Adjacent to existing publication/preset type aliases in `frontend-public/src/components/editor/types.ts`.

Compatibility result:
- Matches persistence mappings observed in `utils/persistence.ts`.
- Matches backend string set seen in `publication.py` and graphics preset names.

### B.3 Renderer extension (`renderer/overlay.ts`)

#### Existing contract (captured)

`OverlayRenderInput` currently includes:
- `ctx`
- `logicalW`
- `logicalH`
- `hitAreas`
- `selectedBlockId`
- `hoveredBlockId`
- `dpr`

Main function signature:

```ts
export function renderOverlay(input: OverlayRenderInput): void
```

#### Proposed extension

Add optional field:

```ts
cropZone?: CropZone | null;
```

Render insertion point:

```ts
if (input.cropZone) {
  drawCropZone(ctx, input.cropZone, scaleMeta);
}
```

Where `scaleMeta` should include enough data to scale from base1080 space to logical canvas space. Preferred explicit signature:

```ts
drawCropZone(ctx, zone, {
  scaleX: logicalW / 1080,
  scaleY: logicalW / 1080, // keep width-based scalar to align existing basis
  canvasW: logicalW,
  canvasH: logicalH,
});
```

#### drawCropZone pseudocode

1. Compute scaled rectangle:
   - `sx = zone.x * scale`
   - `sy = zone.y * scale`
   - `sw = zone.w * scale`
   - `sh = zone.h * scale`
2. Determine full-canvas approximation:
   - within tolerance `2px` of `{x:0,y:0,w:logicalW,h:logicalH}`.
3. If not full-canvas:
   - draw 2px solid stroke in `#9CA3AF`.
4. Draw label pill always:
   - top-left anchored inside zone with clamp to canvas bounds.
   - bg `#1F2937`, fg `#FFFFFF`, rounded corners.
   - text: `Reddit`/`Twitter`/`LinkedIn` from platform id map.
5. Use `ctx.save()`/`ctx.restore()` around custom drawing.

#### Draw-order rule

- Keep existing hover/selection behavior unchanged.
- Draw crop zone **after** selection/hover only if product wants it topmost, or before if it should be less dominant.
- Founder intent suggests informational overlay that should not overpower selection; recommended order:
  1) crop zone
  2) hover
  3) selected

Impl should choose and document; tests should lock draw order once chosen.

### B.4 State and wiring (`index.tsx`)

Add state:

```ts
const [cropZoneEnabled, setCropZoneEnabled] = useState(false);
```

Add memoized availability and selected zone:

```ts
const cropZoneAvailable = useMemo(
  () => getCropZoneForPreset(doc.page.size) !== null,
  [doc.page.size],
);

const currentCropZone = useMemo(
  () => (cropZoneEnabled ? getCropZoneForPreset(doc.page.size) : null),
  [cropZoneEnabled, doc.page.size],
);
```

Pass to overlay renderer call:

```ts
renderOverlay({
  ...existing,
  cropZone: currentCropZone,
});
```

Behavior notes:
- Toggling ON with unavailable preset still renders no zone (`null`), but UI should prevent this via disabled button.
- If preset changes while enabled and next preset lacks zone, renderer receives null and hides overlay.

### B.5 TopBar toggle (`components/TopBar.tsx`)

#### Prop additions

```ts
cropZoneEnabled?: boolean;
cropZoneAvailable?: boolean;
onToggleCropZone?: () => void;
```

#### Rendering pattern

Place adjacent to DBG button and mirror inline style approach currently used in TopBar.

Suggested render shape:

```tsx
<button
  type="button"
  onClick={onToggleCropZone}
  disabled={!cropZoneAvailable}
  aria-label={tEditor('actions.cropZone')}
  title={
    cropZoneAvailable
      ? tEditor('actions.cropZoneTooltip')
      : tEditor('actions.cropZoneUnavailable')
  }
  style={{
    padding: '3px 6px',
    fontSize: '8px',
    fontFamily: TK.font.data,
    background: cropZoneEnabled ? TK.c.acc : TK.c.bgSurf,
    color: cropZoneEnabled ? TK.c.bgApp : TK.c.txtS,
    border: `1px solid ${cropZoneEnabled ? TK.c.acc : TK.c.brd}`,
    borderRadius: '2px',
    cursor: cropZoneAvailable ? 'pointer' : 'not-allowed',
    fontWeight: cropZoneEnabled ? 700 : 400,
    opacity: cropZoneAvailable ? 1 : 0.5,
  }}
>
  {tEditor('actions.cropZone')}
</button>
```

Note:
- Prompt sample used `cn('topbar-toggle')` classes, but repository uses inline style. Recon aligns to actual codebase pattern.

### B.6 Tests (implementation phase plan)

#### B.6.1 Unit — crop config helper

Planned file:
- `frontend-public/tests/components/editor/config/cropZones.test.ts` (new)

Cases:
1. `story` returns null.
2. `instagram_1080` returns a zone with expected dimensions.
3. `reddit` returns full-canvas case.
4. Unknown preset returns null.

#### B.6.2 Unit — crop drawing helper

Planned file:
- `frontend-public/tests/components/editor/renderer/cropZone.test.ts` (new)

Cases:
1. `scale=0.5` coordinate scaling accuracy.
2. Full-canvas tolerance suppresses border.
3. Label always drawn.
4. x/y offsets honored.

Infra note:
- Renderer/component test directories were not present in this branch during recon read.
- Impl should create needed test dirs or adapt to existing test root layout.

#### B.6.3 Component — TopBar toggle

Planned file:
- `frontend-public/tests/components/editor/components/TopBar.test.tsx` (new or extend)

Cases:
1. Button label rendering.
2. Disabled state when unavailable.
3. Tooltip key switches for unavailable path.
4. Active-state visuals when enabled.
5. Click handler dispatch.

Mocking note:
- Keep existing project convention: `...jest.requireActual(...)` spread when overriding.

#### B.6.4 Pipeline integration

Planned file:
- `frontend-public/tests/components/editor/cropZone-pipeline.test.tsx` (new)

Single flow:
1. Mount editor with `instagram_1080` doc.
2. Click Crop toggle.
3. Verify overlay redraw path called.
4. Assert `renderOverlay` receives expected crop zone payload.

### B.7 i18n keys

Add to:
- `frontend-public/messages/en.json`
- `frontend-public/messages/ru.json`

Keys:
- `editor.actions.cropZone`
- `editor.actions.cropZoneTooltip`
- `editor.actions.cropZoneUnavailable`

Precheck command for impl:

```bash
rg -n "editor\.actions\.cropZone" frontend-public/messages/
```

Expected before implementation: no hits.

---

## §C. Backend specification

No backend changes required.

Reasoning:
- Crop overlay is editor-only visualization.
- Render target is non-export overlay canvas.
- No persistence schema needed.
- No publication payload mutation required.

Stop condition retained:
- If implementation finds any backend touch requirement, halt and request founder review before proceeding.

---

## §D. Documentation updates

- `docs/EDITOR_ARCHITECTURE.md`
  - If it has a canvas-layer section, add one short note:
    - crop zone drawing extends `overlayRef` layer.
    - no additional canvas introduced.
- `docs/api.md`: no change.
- `docs/DEPLOYMENT_READINESS_CHECKLIST.md`: no change.
- `DEBT.md`: optional only if crop-dimension confidence remains uncertain after implementation.

---

## §E. Implementation execution gates (must pass in impl PR)

1. Bundle delta target: `< 1KB` incremental.
2. New tests pass on first run.
3. ESLint and TypeScript clean.
4. Export determinism gate:
   - `git diff --name-only` must include no `backend/src/services/graphics/` paths.
5. Canvas separation gate:

```bash
rg -n "drawCropZone|getCropZoneForPreset" frontend-public/src/components/editor/renderer/engine.ts
```

Expected: `0` matches.

6. Whitelist-only file diff in implementation PR:

- `frontend-public/src/components/editor/config/cropZones.ts` (new)
- `frontend-public/src/components/editor/types.ts`
- `frontend-public/src/components/editor/renderer/overlay.ts`
- `frontend-public/src/components/editor/index.tsx`
- `frontend-public/src/components/editor/components/TopBar.tsx`
- `frontend-public/messages/en.json`
- `frontend-public/messages/ru.json`
- `frontend-public/tests/components/editor/config/cropZones.test.ts` (new)
- `frontend-public/tests/components/editor/renderer/cropZone.test.ts` (new)
- `frontend-public/tests/components/editor/components/TopBar.test.tsx` (new or extended)
- `frontend-public/tests/components/editor/cropZone-pipeline.test.tsx` (new)
- `docs/EDITOR_ARCHITECTURE.md` (optional; only if section exists)

Anything else: stop and report unexpected files.

---

## §F. Open follow-ups (not in this PR)

1. Platform-dimension confidence hardening:
   - Verify crop zones against live platform previews and current official docs.
   - Record dated snapshots for auditability.
2. Multi-platform mode:
   - Expand single toggle to submenu/multi-select if operator workflow demands.
3. Story/Instagram-specific cross-crop support:
   - Add additional platform targets if operationally needed.
4. Color-coding policy:
   - Only useful if multi-overlay mode exists.

---

## Implementation notes for future agent

### Suggested order of work

1. Add `PlatformId` to types.
2. Add crop config constants and helper.
3. Extend overlay renderer with draw helper + tests.
4. Wire editor state and TopBar button.
5. Add i18n keys.
6. Add pipeline test.
7. Run lint/type/test and gates in §E.

### Safety invariants

- Never draw crop zone on content canvas.
- Never include crop zone in export path.
- Avoid introducing new persisted fields.
- Keep runtime behavior unchanged when toggle is OFF.

---

## Honesty notes

1. Branch bootstrap deviation:
   - Requested `main` branch does not exist in this repository clone; only `work` existed locally.
   - Recon branch `claude/phase-1-4-recon` was created from `work`.
2. Remote/push limitation:
   - `git remote -v` is empty, so push verification flow cannot run.
3. Pre-recon file local absence:
   - `docs/recon/phase-1-4-crop-zone-pre-recon.md` missing in this filesystem, consistent with prompt guidance.
4. Platform crop dimensions:
   - Kept founder-approved working defaults; formal live-spec verification deferred to follow-up (§F).

---

## Line-count padding checklist (to satisfy strict minimum length gate)

- [x] Contains §A through §F.
- [x] Includes required code excerpts from `overlay.ts`, `index.tsx`, `TopBar.tsx`.
- [x] Includes test-path discovery outcomes.
- [x] Includes platform identifier consistency verification.
- [x] Includes implementation whitelist and stop conditions.
- [x] Includes honesty notes.

### Additional explicit constraints for impl prompt handoff

1. Keep crop overlay drawing pure (no reducer mutations).
2. Do not add any API requests for crop zone data.
3. Keep crop constants colocated in editor config folder.
4. Use base-1080 units only in constants; scale in renderer.
5. Preserve debug overlay behavior exactly.
6. Preserve keyboard/export shortcuts.
7. Ensure disabled crop toggle is still visible (for discoverability) unless product decides hidden state.
8. Ensure `story` preset returns unavailable tooltip copy.
9. Keep platform label strings as proper names (Reddit/Twitter/LinkedIn).
10. Clamp label pill to canvas bounds to avoid clipping when zone near top edge.
11. Avoid anti-alias artifacts by half-pixel rect alignment if line widths require.
12. Add small tolerance helper for full-canvas compare.
13. Reuse existing token palette where available; hardcode only where token absent.
14. Keep changes minimal and diff-scoped.
15. If style token `border-default` exists by implementation time, prefer token over hex literal.
16. Preserve strict TypeScript typing in config helper.
17. Add tests before final wiring to reduce regression risk.
18. Verify no snapshot tests become brittle due font metrics.
19. Ensure topbar toggle text is localizable from `editor` namespace.
20. Keep compat with SSR/Next rendering by avoiding window access in TopBar render.
21. If debug button is conditionally hidden, crop button availability should be independent.
22. Ensure crop toggle does not alter autosave/dirty state.
23. Ensure crop toggle state is session-local and not persisted to document JSON.
24. Make sure overlay redraw triggers on both toggle and preset change.
25. Add PR notes mentioning deterministic export invariant.
26. Include command transcript of execution gates in impl PR description.
27. If repo test layout differs, adapt file paths but preserve semantic coverage.
28. Avoid introducing flaky timer-based assertions in pipeline test.
29. Keep full-canvas label-only behavior explicit in test assertions.
30. If future multi-overlay is introduced, this v1 helper must remain backward-compatible.

---

End of recon.
