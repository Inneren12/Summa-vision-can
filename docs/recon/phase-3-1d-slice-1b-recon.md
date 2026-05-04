# Phase 3.1d Slice 1b Recon — Reviewer-Fix Locked

## Pre-flight verification
- Branch: `claude/phase-3-1d-slice-1b-recon`.
- Baseline file: `docs/recon/phase-3-1d-slice-1b-recon.md`.
- Baseline md5 + line count captured before edits.

### Slice 1a polish fix locale state — verify at impl time
Slice 1a polish fix (PR `claude/phase-3-1d-slice-1a-polish-fix`) added `publication.binding.resolve.{mapping_not_found,invalid_filters,cache_miss}` keys to en.json and ru.json. Recon does not assume their presence; impl prompt pre-flight will verify via:

```bash
node -e "const d=JSON.parse(require('fs').readFileSync('frontend-public/messages/en.json')); console.log('binding.resolve keys:', d.publication?.binding?.resolve ? Object.keys(d.publication.binding.resolve) : 'absent');"
```

If keys present: Slice 1b adds `publication.compare.*` siblings; binding.resolve untouched.
If absent: coordinate with Slice 1a polish merge, or add both key groups atomically based on observed state.

## §A — TopBar surface inventory
### A.1 TopBar anatomy
- TopBar has left and right action clusters in a compact flex row.
- Right cluster currently includes clone and export controls with small inter-button gaps.
- Slice 1b compare surface remains TopBar-only.

### §A.1.1 Locked TopBar layout (left-to-right)
`[CLONE button] [COMPARE button] [COMPARE badge] [EXPORT ZIP button]`

Specifications:
- Compare button and compare badge are visually paired.
- Compare button states:
  - Idle: enabled; label `publication.compare.button.compare`.
  - Loading: disabled; label `publication.compare.button.comparing`.
  - Success: enabled; label resets to compare.
- Compare badge states:
  - Idle: `publication.compare.badge.not_compared` with unknown styling.
  - Loading: badge hidden (or temporary checking placeholder in impl decision).
  - Success: glyph + label + relative time.
  - Partial success (`state.badge === 'partial'`): glyph + label + adjacent retry button (`publication.compare.button.retry`).
  - Error: badge hidden; error toast shown.
- Retry CTA placement: adjacent to badge (not inside badge, not toast).

### A.2 Badge primitive path
- Keep `CompareBadge` as a dedicated component (parallel to workflow `StatusBadge`).
- No shared generic badge extraction in Slice 1b.

### A.3 Button primitive path
- Reuse existing TopBar plain-button styling conventions.

### A.4 Existing icon usage (locked for Slice 1b)
TopBar currently uses text/glyph indicators (no lucide-react, no inline SVG icon library). Slice 1b matches existing TopBar style: text/glyph badges via Unicode characters with `aria-hidden` decoration and `sr-only` label for screen readers. **No new icon dependency added in Slice 1b** — DEBT-074 closes with decision "text glyphs sufficient for v1; revisit if design system adopts a library globally."

### A.5 Relative-time utility
- Relative-time formatting is implemented minimally in-slice (no extra dependency required).

## §B — Publication list page badge — DEFERRED, NOT in Slice 1b

**Decision:** Slice 1b does NOT render any compare-related badge on the publication list page (`frontend-public/src/app/admin/page.tsx`).

Reasoning:
- List page is a server component fetching publications via `fetchAdminPublicationListServer`.
- Compare state is editor-session-local (`useCompareState` reducer state in editor shell).
- Static list placeholders would imply authoritative freshness state that does not exist.
- Backend does not expose persisted compare summary on publication metadata.

**Deferred to:** post-3.1d feature with backend support for persisted compare summary.

**Files NOT touched in Slice 1b:**
- `frontend-public/src/app/admin/page.tsx`
- Any list-page card component
- Any list-page hook

This overrides earlier mention of list page compare badge surface. Pre-3.1d refresh-required list tag remains deferred to Slice 5.

## §C — State machine design (simplified)
### C.1 State union
```ts
type CompareState =
  | { kind: 'idle' }
  | { kind: 'loading'; startedAt: number }
  | { kind: 'success'; result: CompareResponse; comparedAt: string; badge: CompareBadgeSeverity }
  | { kind: 'error'; error: BackendApiError | Error };
```

`partial` is NOT a lifecycle state. It is a severity bucket inside successful lifecycle completion (`kind: 'success'`) when payload contains `compare_failed` reasons.

Simplifications:
- 4 actions instead of 5
- fewer reducer branches
- same retry path across all success severities
- smaller test matrix

### C.2 Actions
```ts
type CompareAction =
  | { type: 'compare:start' }
  | { type: 'compare:success'; result: CompareResponse }
  | { type: 'compare:error'; error: BackendApiError | Error }
  | { type: 'compare:reset' };
```

### C.3 Reducer core
```ts
case 'compare:success': {
  const badge = aggregateCompareSeverity(action.result);
  return {
    kind: 'success',
    result: action.result,
    comparedAt: action.result.compared_at,
    badge,
  };
}
```

### C.4 Aggregate helpers (v1 scope)
Pure functions in `lib/utils/compareSeverity.ts`:

```ts
function aggregateCompareSeverity(result: CompareResponse): CompareBadgeSeverity {
  // unchanged aggregate precedence rules
  ...
}

function countReason(result: CompareResponse, reason: StaleReason): number {
  return result.block_results.filter(b => b.stale_reasons.includes(reason)).length;
}

interface CompareSummary {
  total: number;
  stale: number;
  missing: number;
  failed: number;
}

function summarizeCompare(result: CompareResponse): CompareSummary {
  return {
    total: result.block_results.length,
    stale: countReason(result, 'value_changed') + countReason(result, 'source_hash_changed'),
    missing: countReason(result, 'snapshot_missing'),
    failed: countReason(result, 'compare_failed'),
  };
}
```

`failedBlockIds()` is deferred until per-block UI exists (Q7 aggregate-only, DEBT-075 post-v1).

### C.5 Hook signature
```ts
function useCompareState(publicationId: string): {
  state: CompareState;
  compare: () => void;
  reset: () => void;
};
```

### C.6 Hook dispatches single success action
```ts
try {
  const result = await comparePublication(publicationId, { signal });
  dispatch({ type: 'compare:success', result });
} catch (error) {
  if (error.name === 'AbortError') return;
  dispatch({ type: 'compare:error', error });
}
```

Reducer computes badge including partial bucket. UI reads `state.badge`:
```tsx
const showRetry = state.kind === 'success' && state.badge === 'partial';
```

## §D — Severity visual mapping
### §D.1 Icon/glyph mapping (text-based, no dependency)
Slice 1b uses Unicode text glyphs to match existing TopBar style. No npm package added.

| Severity | Glyph | Codepoint | Rationale |
|---|---|---|---|
| `fresh` | ✓ | U+2713 | Check mark, positive |
| `stale` | ⚠ | U+26A0 | Warning sign |
| `missing` | × | U+00D7 | Distinct from stale; not present |
| `unknown` | ? | U+003F | Interrogative state |
| `partial` | ◐ | U+25D0 | Completed with failures |

Rendering pattern in `CompareBadge`:
```tsx
<span className="badge-glyph" aria-hidden="true">⚠</span>
<span className="sr-only">{label}</span>
<span className="badge-label" aria-hidden="true">{label}</span>
```

Color tokens from §D.2 stay unchanged; glyph+color provides differentiation.

### D.2 Color tokens
Use existing design-system tokens unchanged for `fresh|stale|missing|unknown|partial`.

## §E — Locale key plan
- Keep 14 keys under `publication.compare.*` (EN/RU verbatim as previously locked).
- Refresh-required keys still added now for later Slice 5 consumer.

### §E.4 — Existing key collision check (nested JSON path walking)
Locale files are nested JSON; dotted-key grep is invalid for collision detection.

```bash
node -e "const d=JSON.parse(require('fs').readFileSync('frontend-public/messages/en.json')); console.log('publication.compare keys:', d.publication?.compare ? Object.keys(d.publication.compare) : 'absent');"
node -e "const d=JSON.parse(require('fs').readFileSync('frontend-public/messages/ru.json')); console.log('publication.compare keys:', d.publication?.compare ? Object.keys(d.publication.compare) : 'absent');"
```

If object exists: merge keys without overwriting existing values.
If absent: add `publication.compare` under `publication`.

## §F — Test plan (reduced scope)
### F.1 compareSeverity utility tests — 7 cases
- empty blocks → unknown
- stale only
- fresh only
- snapshot_missing precedence
- compare_failed precedence
- countReason with compare_failed count
- summarizeCompare mixed reasons

### F.2 reducer tests — 5–6 cases
- idle→loading
- loading→success
- loading→error
- success→loading (re-compare)
- error→loading (retry)
- reset→idle

### F.3 hook tests — 5–6 cases
- initial idle
- success path
- error path
- abort cleanup on unmount
- re-compare aborts prior request

### F.4 CompareBadge tests — 5 cases
- one case for each severity variant.

### F.5 TopBar integration tests — 3–4 cases
- compare button renders
- click triggers compare
- loading disables button
- success shows badge

### §F.6 — Integration test deferred to later slice
Slice 1b does NOT include a multi-component pipeline integration test. TopBar integration coverage in §F.5 is the correct layer for this slice.

End-to-end pipeline test (deferred to Slice 4/Slice 6) should cover broader compose chain (publish/snapshot/compare/refresh-required CTA) once those surfaces are wired.

**Total tests forecast: ~26–30 tests across 5 files**.
- compareSeverity: 7
- compareReducer: 5–6
- useCompareState: 5–6
- CompareBadge: 5
- TopBar integration: 3–4

## §G — File inventory
### G.1 New files: 9
# Phase 3.1d Slice 1b Recon — Compare Badge UI + Manual Trigger + State Machine

## Pre-flight verification
- Branch at recon start: `work`.
- Recon-proper docs present: parts 1/2/3 found.
- Recon-proper line counts: part1=578, part2=369, part3=498.
- Slice 1a artifacts present:
  - `frontend-public/src/lib/types/compare.ts` exists.
  - `frontend-public/src/lib/api/admin.ts` exists with `comparePublication`.
  - `frontend-public/messages/en.json` and `ru.json` include `publication.binding.resolve.*`.
- `frontend-public/package.json` currently has no `lucide` dependency.

### Recon-proper read confirmation (GATE-A evidence)
#### Part 1
- First 5 lines:
  1. `# Phase 3.1d Frontend Recon-Proper Part 1 — Schema + Scope (§A–§C)`
  2. ``
  3. `**Type:** Reconnaissance (read-only + design)`
  4. `**Branch:** \`claude/phase-3-1d-frontend-recon-proper-part1\``
  5. `**Date:** 2026-05-04`
- Last 5 lines:
  1. `- aggregate severity`
  2. `- binding`
  3. `- unbound`
  4. ``
  5. `(Flag-only in this part; no key map authored here.)`

#### Part 2
- First 5 lines:
  1. `# Phase 3.1d Frontend Recon-Proper Part 2 — UI Surface (§D–§F)`
  2. ``
  3. `## §D — Compare API client + TypeScript types`
  4. ``
  5. `### §D.1 Existing \`admin.ts\` structure recap`
- Last 5 lines:
  1. `- GATE-D: reusable components searched (\`StatusBadge\`, inspector chips, QA badge pattern).`
  2. `- GATE-E: design token mismatch flagged; used verified v3.2 tokens only.`
  3. `- GATE-F: consistent mapping between compare types, UI severity bucket, binding editor payloads.`
  4. `- GATE-G: no TODO/FIXME markers.`
  5. `- GATE-H: all gates pass with explicit flagging where backend/frontend endpoints are not yet exposed in client.`

#### Part 3
- First 5 lines:
  1. `# Phase 3.1d Frontend Recon-Proper Part 3 — Flows + Slices + DEBT (§G–§K)`
  2. ``
  3. `**Type:** reconnaissance (read-only + design)`
  4. `**Branch:** \`claude/phase-3-1d-frontend-recon-proper-part3\``
  5. `**Date:** 2026-05-04`
- Last 5 lines:
  1. `- **Resolution:** Implement preview via server-side Next.js Route Handler proxy; keep admin secret server-only.`
  2. `- **Target:** Phase 3.1d Slice 3b`
  3. ``
  4. `### §K.4 Founder merge-gate approvals`
  5. `Founder must explicitly approve all eight draft DEBT entries (071–078), including any severity/target adjustments.`

## §A — TopBar surface inventory
### A.1 TopBar anatomy
- File: `frontend-public/src/components/editor/components/TopBar.tsx`.
- Signature: large prop object (`TopBarProps`) with doc/editor state, save/export callbacks, debug/crop toggles, and clone controls.
- Hooks/translations used: `useTranslations` namespaces `qa`, `debug`, `export`, `import`, `editor`, `editor.mode`, `undo`, `redo`, `save`, `draft`, `editor.actions`, `editor.export_zip.button`.
- Layout is two main flex containers:
  - Outer wrapper: `display:flex; alignItems:center; justifyContent:space-between`.
  - Left cluster: brand/template tag + `StatusBadge` + mode tabs + undo/redo + save status indicator.
  - Right cluster: QA compact string, version text, debug button (conditional), crop-zone button (conditional), hidden file input, import button, export JSON button, mark-saved button, clone button, export ZIP button.
- Right-side current order (verbatim): `si` → `v{doc.meta.version}` → `DBG?` → `cropZone?` → `IMPORT` → `JSON` → `SAVE` → `CLONE` → `EXPORT ZIP`.
- Compare insertion point for Slice 1b (locked): between clone and export ZIP.
- Spacing conventions: compact topbar controls with inline styles, primary action buttons mostly `3px 6px`/`3px 7px`, cluster gap `5px`, left-side gaps `6px/8px`.

### A.2 Existing badge/chip primitives
- `StatusBadge` (`.../StatusBadge.tsx`): accepts `workflow` + `size`, hardcodes workflow enum → label/style maps. Strongly workflow-coupled; not a generic severity badge.
- Inspector chip-like styles are present as ad-hoc spans in inspector locales/markup, not as reusable component primitive in editor components scan.
- Recommendation: **Option A** (new `CompareBadge.tsx`) to avoid overloading workflow semantics and keep compare severity mapping isolated.

### A.3 Existing button primitive
- TopBar uses plain native `<button>` elements with inline styles; no shared button component is used here.
- Slice 1b compare button should follow this established TopBar inline style pattern (no new button primitive).

### A.4 Existing icon usage
- TopBar currently has no lucide imports and no inline `<svg>` icons.
- Existing icon-like glyph usage is text arrows (`↩`, `↪`) and text labels.
- `frontend-public/package.json` has no `lucide-react` entry; dependency addition remains needed in impl.

### A.5 Relative-time utility
- Grep found no `date-fns`, `dayjs`, `moment`, or `formatDistance` utility in frontend source.
- Conclusion: relative time helper is absent and should be introduced minimally in Slice 1b implementation.
- `next-intl` interpolation pattern `{time}` is already used extensively in locale messages, so `publication.compare.timestamp.compared_relative` with `{time}` is compatible.

## §B — Publication list page badge
### B.1 List page anatomy
- File: `frontend-public/src/app/admin/page.tsx`.
- Pattern: async server component fetching list server-side via `fetchAdminPublicationListServer({ limit: 100 })`.
- Card layout per publication:
  - top meta row: left `status`, right optional virality score (`V:{toFixed(1)}`)
  - title `headline`
  - optional eyebrow text.
- Small compare badge slot: top meta row right side after/before virality score (compact badge).

### B.2 Data flow + decision
- Data is fetched server-side at page render; no client hook for compare state on this page.
- Locked scope says list page does not trigger compare.
- Recommendation: **Option C** for Slice 1b — always show static “Not compared” (`unknown` bucket visual) on list page.
- Rationale: avoids fake authority without backend persistence; editor session remains authoritative compare surface.

### B.3 Refresh-required list tag
- For Slice 1b: defer “Refresh required” list tag to Slice 5 as planned.
- This recon keeps list badge static “Not compared” only.

## §C — State machine design
- State union (locked): `idle | loading | success | partial | error`.
- Action union (locked): `compare:start | compare:success | compare:partial | compare:error | compare:reset`.
- Hook computes `success` vs `partial`; reducer stores and transitions.
- Valid transitions:
  - `idle -> loading`
  - `loading -> success|partial|error`
  - `success|partial|error -> loading` (manual retry/re-compare)
  - any -> `idle` via `reset`.
- Abort/race handling stays in hook with `AbortController`; reducer remains pure.
- Aggregate severity helper location recommendation: **Option C** `frontend-public/src/lib/utils/compareSeverity.ts`.
- Include `failedBlockIds(result)` helper in same module.

## §D — Severity → visual mapping
### D.1 lucide icon mapping
- Proposed mapping (locked):
  - fresh → `CheckCircle2`
  - stale → `AlertTriangle`
  - missing → `XCircle`
  - unknown → `HelpCircle` (fallback `CircleHelp` if export naming mismatch)
  - partial → `Clock`
- Verification status:
  - `lucide` site confirms active v1 and icon catalog endpoint.
  - `npm view lucide-react version` returns `1.14.0` (current latest as of 2026-05-04).
  - Exact per-icon export name should be re-checked in impl against installed typings; fallback names listed above.

### D.2 Color tokens
Verified from `docs/DESIGN_SYSTEM_v3.2.md` token block:
- `--data-positive`, `--data-warning`, `--destructive`, `--text-secondary`, `--accent-muted`, `--bg-surface-active`, `--bg-surface` are present.
- Mapping remains as locked in prompt.

### D.3 CompareBadge props
Use locked API:
```ts
interface CompareBadgeProps {
  severity: CompareBadgeSeverity;
  comparedAt?: string;
  variant?: 'topbar' | 'list';
  onClick?: () => void;
}
```

## §E — Locale key plan
- Locale structure is nested JSON objects (`publication -> binding -> resolve`), not flat dotted keys.
- New compare keys should be nested under `publication.compare.*` in both `en.json` and `ru.json`.
- Collision check:
  - `grep -n "publication\.compare\." frontend-public/messages/en.json` => no matches.
  - `grep -n "publication\.compare\." frontend-public/messages/ru.json` => no matches.
- Include all locked 14 keys with verbatim EN/RU text from prompt, including RU P2-B fix:
  - `publication.compare.refresh_required.cta = "Переопубликовать для обновления"`.
- Refresh-required keys are added in Slice 1b for i18n batching, consumed later in Slice 5.

## §F — Test plan
- Coverage shape matches locked recon: unit + reducer + hook + component + topbar integration + pipeline integration.
- Forecast count:
  - compareSeverity: 8+
  - compareReducer: 8+
  - useCompareState: 8+
  - CompareBadge: 6+
  - TopBar compare integration: 6+
  - compareFlow integration: 3+
  - Total forecast: ~39–45 tests.
- This passes realism gate target (~40).

## §G — File inventory (Slice 1b implementation target)
### New files (10)
1. `frontend-public/src/components/editor/components/CompareBadge.tsx`
2. `frontend-public/src/components/editor/components/CompareButton.tsx`
3. `frontend-public/src/components/editor/hooks/useCompareState.ts`
4. `frontend-public/src/components/editor/hooks/compareReducer.ts`
5. `frontend-public/src/lib/utils/compareSeverity.ts`
6. `frontend-public/src/components/editor/components/__tests__/CompareBadge.test.tsx`
7. `frontend-public/src/components/editor/hooks/__tests__/compareReducer.test.ts`
8. `frontend-public/src/components/editor/hooks/__tests__/useCompareState.test.tsx`
9. `frontend-public/src/lib/utils/__tests__/compareSeverity.test.ts`

### G.2 Modified files
- `frontend-public/src/components/editor/components/TopBar.tsx`
- `frontend-public/messages/en.json`
- `frontend-public/messages/ru.json`
- existing TopBar test file (if present)

### G.3 Files NOT touched
- `frontend-public/src/app/admin/page.tsx`
- `frontend-public/src/lib/api/admin.ts`
- `frontend-public/src/lib/types/compare.ts`
- backend files

## §H — Founder confirmations
### §H.1 Confirm list page deferral
List page badge is deferred until backend exposes persisted compare summary. Confirm no v1 placeholder on list page.

### §H.2 Confirm TopBar layout
Layout locked in §A.1.1: `[CLONE] [COMPARE button] [COMPARE badge] [EXPORT ZIP]`. Confirm no override required.

### §H.3 Confirm retry CTA placement
Retry button stays adjacent to compare badge in partial-success view.

## §I — Gates status
- Scope discipline restored: TopBar-only, no new deps, reduced tests.
- DEBT-074 decision captured as text glyphs sufficient for v1.
- No lifecycle `partial` state; partial now modeled as `state.badge === 'partial'` in success state.
10. `frontend-public/src/components/editor/__tests__/compareFlow.integration.test.tsx`

### Modified files (5–6)
- `frontend-public/src/components/editor/components/TopBar.tsx`
- `frontend-public/src/app/admin/page.tsx`
- `frontend-public/messages/en.json`
- `frontend-public/messages/ru.json`
- `frontend-public/package.json`
- optional existing TopBar test file

### Not touched
- `frontend-public/src/lib/api/admin.ts`
- `frontend-public/src/lib/types/compare.ts`
- `frontend-public/src/lib/api/errorCodes.ts`
- editor canonical types/guards
- backend files

## §H — Founder review items
1. Confirm list-page Option C (always Not compared) for Slice 1b.
2. Confirm TopBar layout Option A: `[clone] [Compare] [Badge] [Export ZIP]`.
3. Confirm retry CTA placement adjacent to badge.
4. Confirm lucide-react version pin style (`^1.14.0` recommended baseline at recon date).
5. Confirm bundle size tradeoff acceptance (~few KB gzipped for 5 icons, tree-shaken).

## §I — Gate outcomes
- GATE-A Recon read confirmed: **PASS**.
- GATE-B TopBar inventory verified from file with line-backed observations: **PASS**.
- GATE-C lucide availability/version verification: **PASS with impl-time export-name check note**.
- GATE-D locale collision check: **PASS** (0 existing compare keys).
- GATE-E test count realism: **PASS** (~39–45).
- GATE-F cross-reference consistency with recon-proper Parts 2/3 and locked decisions: **PASS**.
- GATE-G forbidden markers in this doc: **PASS** (none in spec sections).
- GATE-H honest-stop trigger: **PASS** (no structural mismatch blocking recon).
- GATE-I scope discipline: **PASS** (no implementation/per-block/backend drift).
