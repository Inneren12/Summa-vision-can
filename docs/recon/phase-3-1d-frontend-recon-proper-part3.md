# Phase 3.1d Frontend Recon-Proper Part 3 — Flows + Slices + DEBT (§G–§K)

**Type:** reconnaissance (read-only + design)  
**Branch:** `claude/phase-3-1d-frontend-recon-proper-part3`  
**Date:** 2026-05-04

## §G — Walker + republish-as-refresh confirm modal flow

### §G.1 Walker definition
Recommend a pure helper at `frontend-public/src/lib/publication/walker.ts`:

```ts
const SINGLE_BINDING_BLOCK_TYPES = new Set(['hero_stat', 'delta_badge']);

type WalkerWarning = {
  block_id: string;
  reason:
    | 'unsupported_block_type'
    | 'unsupported_kind'
    | 'invalid_filters'
    | 'invalid_binding_shape';
};

interface WalkerResult {
  refs: BoundBlockReference[];
  warnings: WalkerWarning[];
}

function walkBoundBlocks(doc: CanonicalDocument): WalkerResult {
  const refs: BoundBlockReference[] = [];
  const warnings: WalkerWarning[] = [];

  for (const [blockId, block] of Object.entries(doc.blocks)) {
    if (!block.binding) continue;

    // v1 only supports single-value bindings
    if (block.binding.kind !== 'single') {
      warnings.push({ block_id: blockId, reason: 'unsupported_kind' });
      continue;
    }

    // v1 only supports a fixed allowlist of block types
    if (!SINGLE_BINDING_BLOCK_TYPES.has(block.type)) {
      warnings.push({ block_id: blockId, reason: 'unsupported_block_type' });
      continue;
    }

    const ref = bindingToBoundBlockRef(block, block.binding);
    if (!ref) {
      warnings.push({ block_id: blockId, reason: 'invalid_filters' });
      continue;
    }
    refs.push(ref);
  }

  return { refs, warnings };
}

function bindingToBoundBlockRef(
  block: Block,
  binding: SingleValueBinding,
): BoundBlockReference | null {
  // Sort filter pairs by numeric dim_id for deterministic snapshot identity.
  // Object.entries() iteration order is implementation-defined for mixed keys;
  // explicit numeric sort ensures stable dims[]/members[] ordering across
  // platforms, JS engines, and document round-trips.
  const pairs = Object.entries(binding.filters ?? {})
    .map(([dimId, memberId]) => [Number(dimId), Number(memberId)] as const)
    .sort(([a], [b]) => a - b);

  if (pairs.length === 0) return null;
  if (pairs.some(([d, m]) => !Number.isInteger(d) || !Number.isInteger(m))) {
    return null;
  }

  return {
    block_id: block.id,
    cube_id: binding.cube_id,
    semantic_key: binding.semantic_key,
    dims: pairs.map(([d]) => d),
    members: pairs.map(([, m]) => m),
    period: binding.period,
  };
}
```

Notes:
- v1 handles `kind === 'single'` only.
- `time_series` / `multi_metric` / `tabular` walker expansion is explicitly deferred to Phase 3.1e.
- Unit tests target `walkBoundBlocks` and `bindingToBoundBlockRef` independently from UI.

### §G.2 Republish trigger surfaces
- Editor TopBar is the v1 trigger surface; no visible publish button exists in current TopBar, so Slice 4 will add one near clone/export controls.
- Publication list currently has no per-card publish action in current frontend-public recon scope.
- v1 scope: editor TopBar only.

### §G.3 Confirm modal design (Q3=(c))
**Trigger:** user clicks Publish → walker runs → modal opens for both N>0 and N=0.

**Title:** `Republish publication`

**Body scenarios (all mandatory):**
1. **N>0 refs:** “Publishing will create new snapshots of {N} bound blocks at current data state.”
2. **N=0 refs:** “No data-bound blocks. This will publish editorial content only.”
3. **stale/missing prior compare:** warning callout with stale/missing count and refresh implication.
4. **compare not run:** notice + tertiary action “Compare first”.

**Content structure:**
- Summary lines: bound count, collapsed block-id list, last compare aggregate severity.
- Collapsible details: per block -> label/type + `cube_id` + `semantic_key` + last preview value (if available).
- Secondary warning area for skipped malformed bindings.

**Actions:**
- Primary: `Confirm and publish`
- Secondary: `Cancel`
- Optional tertiary: `Compare first`

**Reuse:** base modal primitives exist (`DeleteConfirmModal`, `NoteModal`, `PreconditionFailedModal`), so implement as dedicated `PublishConfirmModal` using the same visual shell.

### §G.4 Publish flow state machine
```ts
type PublishState =
  | { kind: 'idle' }
  | { kind: 'walking' }
  | {
      kind: 'modal_open';
      refs: BoundBlockReference[];
      skipped: WalkerWarning[];
      lastCompare?: CompareResponse;
    }
  | { kind: 'publishing'; refs: BoundBlockReference[]; startedAt: number }
  | { kind: 'success'; document: AdminPublicationResponse; etag: string }
  | { kind: 'conflict'; serverEtag: string }
  | { kind: 'error'; error: BackendApiError | Error };
```
Transitions:
- `idle -> walking -> modal_open`
- `modal_open -> idle` on cancel
- `modal_open -> publishing` on confirm
- `publishing -> success` on 200
- `publishing -> conflict` on 412
- `publishing -> error` on non-412 failure

### §G.5 ETag conflict handling
Reuse Phase 1.3 conflict model via `PreconditionFailedModal` pattern:
- **Reload**: refetch publication, replace local state, rerun walker, reopen publish modal.
- **Save-as-new-draft**: `cloneAdminPublication` then save current payload into clone and redirect.

If exact modal cannot be shared without prop mismatch, factor a shared `ConflictModal` in Slice 4 (filed as DEBT entry in §K).

### §G.6 Walker failure handling
- Invalid binding mapping (e.g., non-numeric filter ids) is skipped, not fatal.
- Modal shows skipped count + collapsible list.
- Publish proceeds with valid refs.

### §G.7 Verification
- Single-kind walker only, others skipped.
- Modal covers 4 founder scenarios.
- 7-state publish machine defined.
- 412 flow aligned with Phase 1.3 pattern.
- Multi-value design explicitly deferred.

## §H — Pre-3.1d “Refresh required” CTA flow

### §H.1 Detection logic
Decision: **Option A** (compare-response based) for v1, with revised detection logic.

**Backend reality check (verified Part 2):** Compare endpoint `POST /admin/publications/{id}/compare` operates on existing `publication_block_snapshot` rows. Pre-3.1d publications have ZERO snapshot rows, so backend compare returns `block_results: []` (empty array), NOT a list of `snapshot_missing` per expected binding. Backend does not currently know which blocks the document has bindings for — the compare endpoint accepts no `bound_blocks` body.

**Detection rule (v1):**
1. Compute set of bindable block IDs from `document.blocks` (filter by `block.binding` present + `block.binding.kind === 'single'` + block type in v1 allowlist).
2. After running compare, classify publication as `pre31d_refresh_required` if BOTH:
   - Local bindable set is non-empty (publication has at least one valid v1 binding), AND
   - Compare response satisfies one of:
     - `block_results.length === 0` (zero snapshot rows on backend), OR
     - Every local bindable block ID is either absent from `block_results` entirely, or present with `stale_reasons` containing `snapshot_missing`.
3. If any local bindable block has a `block_results` entry with `stale_reasons` NOT including `snapshot_missing`, use normal compare aggregate logic from §E.4.

**Rationale:** No backend extension required. Frontend computes bindable set from local document; matches against compare response, treating both "absent from response" and "explicit snapshot_missing" as equivalent missing-snapshot signals. The empty `block_results` case (zero rows on backend) is the most common pre-3.1d signal.

**Test surface explicit:**
- `block_results: []` + local bindable set non-empty → `pre31d_refresh_required`
- `block_results: []` + local bindable set empty → `unknown` (editorial-only publication, no refresh needed)
- `block_results` with all local IDs absent → `pre31d_refresh_required`
- `block_results` with mix of `snapshot_missing` and present → use partial-coverage logic (see §H.4)
- Standard fresh/stale results → normal compare aggregate

**Future improvement (NOT v1):** Backend extension to accept `bound_blocks` body on compare endpoint, returning explicit `snapshot_missing` per expected binding. Tracked as separate future improvement; not required for v1.

### §H.2 CTA presentation
When `pre31d_refresh_required`:
- Replace compare badge region in TopBar with warning banner.
- Banner strings:
  - Label: “Refresh required”
  - Body: publication predates snapshot tracking
  - CTA: “Republish to refresh”
- CTA click routes through §G flow (walker → confirm modal → publish).
- After successful publish, next compare should move to regular fresh/stale/missing/partial buckets.

### §H.3 Visibility scope
Show in:
1. Editor TopBar compare slot.
2. Publication list card (compact needs-refresh tag).

Do not show in:
1. Post-3.1d publications without compare run.
2. Publications already containing snapshot coverage.

### §H.4 Partial coverage edge case
If only a subset is `snapshot_missing`:
- show regular compare badge aggregate = `missing` (frontend bucket),
- do **not** show refresh-required banner.

Exact banner rule: banner only when 100% of bindable blocks are `snapshot_missing`.

### §H.5 Verification
- Option A selected with rationale.
- Banner + CTA behavior specified.
- Surface scope and exclusions explicit.
- Partial coverage differentiated from full pre-3.1d state.

## §I — i18n key plan + glossary additions

### §I.1 Glossary additions plan
After full glossary review, propose additions only for terms missing as standalone glossary rows:
- stale
- fresh
- drift
- snapshot
- republish
- unknown
- point-level
- aggregate severity
- binding
- unbound

If term already exists in adjacent form (`stale data`, `data binding`, etc.), add a normalized row only if standalone usage is needed for labels/badges.

### §I.2 Namespace structure
Add two namespaces under `publication.*`:
- `publication.compare.*`
- `publication.binding.*`

Error mapping pattern (hybrid, consistent with DEBT-030 direction):
- UI key: `publication.binding.resolve.mapping_not_found`
- backend code registry maps `MAPPING_NOT_FOUND` -> UI key.

### §I.3 `publication.compare.*` key map
- `publication.compare.button.compare` — Compare / Сравнить
- `publication.compare.button.comparing` — Comparing… / Сравнение…
- `publication.compare.button.retry` — Retry failed blocks / Повторить
- `publication.compare.badge.fresh` — Fresh / Актуально
- `publication.compare.badge.stale` — Stale / Устарело
- `publication.compare.badge.missing` — Missing / Нет снимка
- `publication.compare.badge.unknown` — Unknown / Не проверено
- `publication.compare.badge.partial` — Partial / Частично проверено
- `publication.compare.badge.not_compared` — Not compared / Не проверялось
- `publication.compare.timestamp.compared_relative` — Compared {time} ago / Проверено {time} назад
- `publication.compare.partial.toast` — Some blocks could not be compared / Не удалось проверить часть блоков
- `publication.compare.refresh_required.label` — Refresh required / Требуется обновление
- `publication.compare.refresh_required.body` — This publication was created before snapshot tracking was enabled. Republish to enable comparison. / Эта публикация создана до включения отслеживания снимков. Переопубликуйте для активации сравнения.
- `publication.compare.refresh_required.cta` — Republish to refresh / Переопубликовать

### §I.4 `publication.binding.*` key map
- `publication.binding.section_title` — Data binding / Привязка данных
- `publication.binding.empty.body` — This block is not bound to live data. Static content from props. / Этот блок не привязан к живым данным. Используется статичное содержимое.
- `publication.binding.empty.cta` — Add binding / Привязать данные
- `publication.binding.action.edit` — Edit binding / Изменить привязку
- `publication.binding.action.remove` — Remove binding / Удалить привязку
- `publication.binding.action.remove_confirm` — Remove binding from this block? / Удалить привязку из блока?
- `publication.binding.field.cube` — Cube / Куб
- `publication.binding.field.metric` — Metric / Метрика
- `publication.binding.field.filters` — Filters / Фильтры
- `publication.binding.field.period` — Period / Период
- `publication.binding.field.format` — Format / Формат
- `publication.binding.preview.heading` — Preview / Превью
- `publication.binding.preview.resolved_value` — Resolved value / Полученное значение
- `publication.binding.preview.formatted_value` — Formatted value / Форматированное значение
- `publication.binding.preview.resolved_at` — Resolution time / Время получения
- `publication.binding.preview.source` — Source: {cube} / {metric} / {period} / Источник: {cube} / {metric} / {period}
- `publication.binding.preview.loading` — Loading… / Загрузка…
- `publication.binding.preview.retry` — Retry / Повторить
- `publication.binding.deferred_3_1e` — Multi-value bindings available in Phase 3.1e. / Привязка нескольких значений будет в Phase 3.1e.
- `publication.binding.resolve.mapping_not_found` — Mapping not found for selected filters / Соответствие не найдено для выбранных фильтров
- `publication.binding.resolve.invalid_filters` — Invalid filter set / Неверный набор фильтров
- `publication.binding.resolve.cache_miss` — Cache miss (no row after prime) / Промах кэша
- `publication.binding.resolve.internal_error` — Server error during resolve. Retry. / Ошибка сервера при разрешении. Повторите.
- formatter extras:
  - `publication.binding.format.passthrough`
  - `publication.binding.format.delta_bps`
  - `publication.binding.format.percent_1`
  - `publication.binding.format.currency_compact`

### §I.5 Existing-key reuse check
Current messages structure has no `publication.compare.*` or `publication.binding.*` namespace; only generic publication error keys exist. Therefore all keys above are additive.

### §I.6 String freeze
String freeze baseline starts at Part 3 approval for:
- `publication.compare.*`
- `publication.binding.*`
Any new user-visible copy in these namespaces requires glossary + recon delta before implementation PR merge.

### §I.7 Verification
- Missing-term verification done before proposal.
- EN/RU key pairs supplied for both namespaces.
- Hybrid error-code mapping retained.
- No collision with existing `publication.*` keys.

## §J — Slice plan

### §J.1 Graph
1a -> 1b -> 2 -> 3a -> 3b -> 4 -> 5 -> 6; 3.1e multi-value follows.

### §J.2 Per-slice specs
#### Slice 1a — TS types + API client
- Files: `src/lib/api/admin.ts`, NEW `src/lib/types/compare.ts`, `src/lib/api/errorCodes.ts`
- Tests: API request/response shape; error code extraction.
- Dependencies: none.
- Acceptance: compare + publish admin calls compile and parse known errors.
- Risk: low.

#### Slice 1b — Compare badge UI + manual trigger
- Files: TopBar + NEW CompareBadge + NEW useCompareState.
- Tests: severity render (5 buckets), state transitions, retry for partial.
- Dependencies: 1a.
- Acceptance: manual compare updates badge bucket.
- Risk: low-medium.

#### Slice 2 — Block schema extension
- Files: `types.ts`, `registry/guards.ts`.
- Tests: valid binding passes; invalid dropped; no-binding blocks unaffected.
- Dependencies: 1a.
- Acceptance: binding survives round-trip; invalid sanitized.
- Risk: medium.

#### Slice 3a — Binding editor (cube + semantic key)
- Files: Inspector + NEW BindingEditor + picker subcomponents + `admin.ts` clients.
- Tests: visibility matrix by block type; picker chain behavior.
- Dependencies: 2.
- Acceptance: hero_stat/delta_badge can choose cube + semantic key.
- Risk: medium-high.

#### Slice 3b — Binding editor (filters/period/format + preview)
- Files: BindingEditor extension + NEW subpickers + NEW ResolvePreview + `previewBindingResolve` in admin client.
- Tests: preview state machine; resolver error code rendering.
- Dependencies: 3a.
- Acceptance: full single-value binding resolves preview.
- Risk: medium-high.

#### Slice 4 — Walker + publish confirm modal
- Files: NEW walker module, NEW PublishConfirmModal, TopBar wiring, NEW usePublishFlow.
- Tests: walker unit + modal behavior + 412 branch.
- Dependencies: 1a,2,3a,3b.
- Acceptance: publish flow performs republish-as-refresh with confirmation.
- Risk: high.

#### Slice 5 — Pre-3.1d Refresh required CTA
- Files: TopBar conditional + compare state hook + publication list tag surface.
- Tests: full-missing banner; partial-missing falls back to standard badge.
- Dependencies: 1b,4.
- Acceptance: legacy publications prompt republish-to-refresh.
- Risk: low-medium.

#### Slice 6 — Integration/e2e
- Files: NEW e2e spec(s) in existing test framework location.
- Tests: happy path, 412 path, pre-3.1d refresh path.
- Dependencies: all prior slices.
- Acceptance: CI green on three scenarios.
- Risk: medium.

### §J.3 Merge order + parallelism
**Implementation may parallelize low-coupling pieces** (e.g. Slice 1a TypeScript types can be drafted alongside Slice 2 schema validation; i18n keys can be added in parallel with badge visual component prototyping). **Merge order remains strict** — slices merge in dependency order to avoid integration drift.

For Phase 3.1e onward, multi-value slices can parallelize per-block-type once Phase 3.1e backend storage shape lands.

### §J.4 Out of scope
- Multi-value binding kinds (`time_series`, `multi_metric`, `tabular`) interactive editing.
- Point drilldown compare UI.
- Auto-poll compare.
- Symbolic “latest” period.
- Backend endpoint invention for cube/semantic-key discovery if absent.

### §J.5 Verification
All slices include files/tests/dependencies/acceptance/risk; graph is acyclic; out-of-scope explicit.

## §K — DEBT entries (draft only, do not file in DEBT.md in this prompt)

Next available ID verified as **DEBT-071**.

### DEBT-071: Phase 3.1e backend dependency — multi-value snapshot extension
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part1.md` §B1
- **Added:** 2026-05-04
- **Severity:** high
- **Category:** architecture
- **Status:** active
- **Description:** Phase 3.1d backend captures single-value snapshot rows only. Multi-value blocks (`comparison_kpi`, `bar_horizontal`, `line_editorial`, `table_enriched`, `small_multiple`) need JSONB `points` expansion to represent per-point snapshots.
- **Impact:** 5/7 bindable block types remain non-functional for live binding in v1.
- **Resolution:** Phase 3.1e extends snapshot model/capture/compare paths to point arrays and aggregate severity rules.
- **Target:** Phase 3.1e milestone

### DEBT-072: Multi-value resolver iteration strategy
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part1.md` §B2.6
- **Added:** 2026-05-04
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** Existing resolve contract is singular (`GET /admin/resolve/{cube_id}/{semantic_key}`). Multi-value binding needs either client fan-out or backend batch resolve.
- **Impact:** 3.1e performance and API contract remain unresolved.
- **Resolution:** Decide contract in 3.1e recon; prefer batch endpoint for latency/caching predictability.
- **Target:** Phase 3.1e milestone

### DEBT-073: Cube list / semantic key list frontend admin client gap
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part2.md` §F.3
- **Added:** 2026-05-04
- **Severity:** medium
- **Category:** code-quality
- **Status:** active
- **Description:** Binding editor requires list endpoints/clients for cube and semantic_key discovery. Frontend `admin.ts` currently has no such client functions.
- **Impact:** Slice 3a blocked until client additions (and backend availability confirmation).
- **Resolution:** Verify backend list endpoints; add admin client methods in Slice 3a. If backend missing, add backend endpoints before UI.
- **Target:** Phase 3.1d Slice 3a

### DEBT-074: Compare badge icon strategy
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part2.md` §E.2
- **Added:** 2026-05-04
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** Compare badge requires 5 severity visuals; current editor code does not establish a dedicated icon stack for this surface.
- **Impact:** UI consistency/polish risk in Slice 1b.
- **Resolution:** Slice 1b chooses minimal local SVG set or introduces `lucide-react` if dependency review approves.
- **Target:** Phase 3.1d Slice 1b

### DEBT-075: Per-block tint wrapper integration (deferred post-v1)
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part2.md` §E.5
- **Added:** 2026-05-04
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** Per-block visual tint based on compare result is deferred to post-v1 per Q7 aggregate-only constraint. When implemented, requires a wrapper layer around block render output rather than changing each renderer function.
- **Impact:** No v1 impact. Future implementation needs wrapper to avoid high diff-risk across all 13 block renderers.
- **Resolution:** Post-v1 milestone (Phase 3.1e or UX polish): add `BlockRenderWrapper` accepting compare result, inject subtle tint via CSS variable + opacity, no border change to avoid layout shift.
- **Target:** Phase 3.1e or UX polish milestone (NOT Phase 3.1d Slice 1b)

### DEBT-076: Conflict modal factoring for publish reuse
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part3.md` §G.5
- **Added:** 2026-05-04
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** 412 conflict UX exists for autosave (`PreconditionFailedModal` + editor-level handlers). Publish flow needs same pattern and may duplicate control logic.
- **Impact:** Duplicate 412 handling paths if not factored.
- **Resolution:** Slice 4 either reuses existing modal with shared controller logic or factors shared conflict orchestration hook/component.
- **Target:** Phase 3.1d Slice 4

### DEBT-077: String freeze enforcement for compare/binding namespaces
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part3.md` §I.6
- **Added:** 2026-05-04
- **Severity:** low
- **Category:** ops
- **Status:** active
- **Description:** Slices may introduce ad-hoc strings outside approved `publication.compare.*` and `publication.binding.*` baseline.
- **Impact:** i18n drift and glossary inconsistency during rollout.
- **Resolution:** Add string-freeze checklist item to each Phase 3.1d slice PR.
- **Target:** Phase 3.1d slices 1a–6

### DEBT-078: API key handling for resolve preview
- **Source:** `docs/recon/phase-3-1d-frontend-recon-proper-part2.md` §F and Part 3 security decision
- **Added:** 2026-05-04
- **Severity:** medium
- **Category:** security
- **Status:** active
- **Description:** Browser-direct resolve preview calls would require exposing admin API credentials if implemented with `NEXT_PUBLIC_*` key.
- **Impact:** Elevated credential exposure risk and weaker production posture.
- **Resolution:** Implement preview via server-side Next.js Route Handler proxy; keep admin secret server-only.
- **Target:** Phase 3.1d Slice 3b

### §K.4 Founder merge-gate approvals
Founder must explicitly approve all eight draft DEBT entries (071–078), including any severity/target adjustments.
