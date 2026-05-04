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
