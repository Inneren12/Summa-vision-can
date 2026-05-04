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
