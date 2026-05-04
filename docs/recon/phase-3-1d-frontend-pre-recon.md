# Phase 3.1d Frontend Integration — Pre-Recon

**Status:** discovery (read-only)  
**Branch:** claude/phase-3-1d-frontend-pre-recon  
**Date:** 2026-05-04  
**Purpose:** map current frontend surface for publication actions; surface founder-approval questions before recon-proper commits to architecture.

---

## §A — Publication CRUD/publish action location today

### Findings
- Flutter source exists (`frontend/test/helpers/pump_localized_router.dart`), but grep and feature-tree discovery found no dedicated publications CRUD feature directory.
- Flutter has **no** concrete call-site to `POST /api/v1/admin/publications/{id}/publish` in `frontend/lib/`.
- Next.js admin surface contains admin publication proxy/client modules and the admin editor route under `/admin/editor/[id]`.
- Publication edit/save (`PATCH /admin/publications/{id}`) is wired in Next.js editor (`updateAdminPublication` callsite at `frontend-public/src/components/editor/index.tsx:655`). Explicit publish action wiring (`POST /publish`) was NOT confirmed in this pre-recon — `publishAdminPublication` is absent from `admin.ts` exports and no publish-button handler was located. Recon-proper must locate or add the publish action helper.

### Verbatim discovery evidence

#### A.1 Flutter existence check
```bash
frontend/test/helpers/pump_localized_router.dart
```

#### A.2 Flutter grep: publications/publish paths
```bash
frontend/lib/features/editor/domain/editor_notifier.dart:58:/// future save/publish/unpublish backend actions. This notifier currently
frontend/lib/l10n/app_en.arb:123:    "description": "Error message when GET /admin/publications/{id} fails. {error} placeholder receives the backend error detail verbatim (may remain in source language).",
frontend/lib/l10n/app_en.arb:183:    "description": "Generic wrapper for editor backend action errors (PATCH /publications/{id}, publish, unpublish). Placeholder {error} receives backend detail or exception message as-is. RESERVED — not currently rendered; editor endpoints still lack structured error_codes (DEBT-030). Will be activated when backend admin_publications endpoints emit stable error_code values and the backend_errors.dart mapper is extended accordingly.",
frontend/lib/l10n/generated/app_localizations.dart:269:  /// Error message when GET /admin/publications/{id} fails. {error} placeholder receives the backend error detail verbatim (may remain in source language).
frontend/lib/l10n/generated/app_localizations.dart:341:  /// Generic wrapper for editor backend action errors (PATCH /publications/{id}, publish, unpublish). Placeholder {error} receives backend detail or exception message as-is. RESERVED — not currently rendered; editor endpoints still lack structured error_codes (DEBT-030). Will be activated when backend admin_publications endpoints emit stable error_code values and the backend_errors.dart mapper is extended accordingly.
frontend/lib/core/network/mock_interceptor.dart:260:                  '{"publication_id":1,"cdn_url_lowres":"https://placehold.co/1080x1080/141414/00E5FF?text=Mock+Chart","s3_key_highres":"publications/1/v1/abcd_highres.png","version":1}',
frontend/lib/core/network/mock_interceptor.dart:542:              '{"publication_id":42,"cdn_url_lowres":"https://cdn.example.com/pub/42/v1/lowres.png","s3_key_highres":"publications/42/v1/highres.png","version":1}',
frontend/lib/core/network/mock_interceptor.dart:564:              '{"publication_id":43,"cdn_url_lowres":"https://cdn.example.com/pub/43/v1/lowres.png","s3_key_highres":"publications/43/v1/highres.png","version":1}',
```

#### A.3 Flutter grep: Publication/repository terms
```bash
frontend/lib/features/jobs/presentation/widgets/job_detail_sheet.dart:195:                label: const Text('View Publication'),
frontend/lib/features/graphics/presentation/chart_config_screen.dart:674:                label: Text(l10n.chartConfigPublicationChip(result.publicationId)),
frontend/lib/features/queue/domain/content_brief.dart:6:/// Domain model matching the backend [PublicationResponse] schema.
...
frontend/lib/l10n/app_en.arb:299:  "chartConfigPublicationChip": "Publication #{id}",
```

#### A.4 Flutter feature directories
```bash
frontend/lib/features/
frontend/lib/features/exceptions
frontend/lib/features/jobs
frontend/lib/features/data_preview
frontend/lib/features/semantic_mappings
frontend/lib/features/graphics
frontend/lib/features/editor
frontend/lib/features/queue
frontend/lib/features/cubes
```

#### A.5 Next.js existence + publish/publication grep
```bash
frontend-public/src/lib/api/admin-server.ts:35:    `${apiUrl}/api/v1/admin/publications/${encodeURIComponent(id)}`,
frontend-public/src/lib/api/admin-server.ts:64:    `${apiUrl}/api/v1/admin/publications${qs ? `?${qs}` : ''}`,
frontend-public/src/lib/api/admin.ts:2:// `/api/admin/publications/*` — the proxy injects the server-only
frontend-public/src/lib/api/admin.ts:13:const PROXY_BASE = '/api/admin/publications';
frontend-public/src/app/api/admin/publications/[...path]/route.ts:3:const BACKEND_ADMIN_PREFIX = '/api/v1/admin/publications';
```

#### A.6 Next.js targeted symbols
```bash
frontend-public/src/lib/api/admin.ts:150:export async function updateAdminPublication(
frontend-public/src/components/editor/index.tsx:31:  updateAdminPublication,
frontend-public/src/components/editor/index.tsx:655:    updateAdminPublication(publicationId, payload, { ifMatch: etagRef.current })
frontend-public/src/components/editor/index.tsx:947:      await updateAdminPublication(clone.id, payload, { ifMatch: clone.etag });
```

#### A.7 Next.js route directories
```bash
frontend-public/src/app/api/admin
frontend-public/src/app/api/admin/publications
frontend-public/src/app/api/admin/publications/[...path]
frontend-public/src/app/admin
frontend-public/src/app/admin/editor
frontend-public/src/app/admin/editor/[id]
```

### Required answers (§A)
- Does Flutter today have ANY publication-related screen? **No dedicated publications CRUD/edit screen found** (only references in job detail/chart config text/UI labels).
- Does Flutter today call POST /publish? **No callsite found in `frontend/lib/` grep outputs.**
- Where in Next.js is publish action wired? **NOT CONFIRMED. Edit/save wired via `updateAdminPublication`; clone wired via `cloneAdminPublication`; publish-specific wiring (helper or button handler) was not found in this pre-recon's grep coverage. Recon-proper must locate the publish action surface or confirm it does not yet exist in this frontend.**
- Where in Next.js is publication detail/edit UI? **Route: `frontend-public/src/app/admin/editor/[id]/page.tsx`; page component `AdminEditorPage` hydrating `AdminEditorClient`.**
- Is there a `frontend/lib/features/publications/` directory at all? **No.**

## §B — Flutter publication UI inventory

### Verbatim checks
```bash
# grep -rln "PublicationScreen|PublicationsList|publication_list_screen|publication_detail" frontend/lib/
# (no output)

# grep -rn "publicationsListProvider|publicationDetailProvider|publicationRepositoryProvider" frontend/lib/
# (no output)

# find frontend/lib/ -name "publication.dart" -o -name "publication.freezed.dart"
# (no output)
```

### Required answers (§B)
- Publication screens in Flutter today: **none found**.
- Publication providers in Flutter today: **none found**.
- `Publication` freezed model in Flutter: **none found**.
- Conclusion: Flutter publication CRUD/editor is **greenfield**. Adjacent publication references exist (`features/queue/domain/content_brief.dart` matches `PublicationResponse` schema; `jobs/widgets/job_detail_sheet.dart` has "View Publication" button; `graphics/chart_config_screen.dart` has Publication chip; `core/network/mock_interceptor.dart` carries publication payloads). No dedicated admin publication workflow/provider was found.

## §C — Next.js publication editor surface

### Concrete path + components
- Publication editor page route: `frontend-public/src/app/admin/editor/[id]/page.tsx` (component `AdminEditorPage`).
- Editor client component: `AdminEditorClient` -> `InfographicEditor` path under `frontend-public/src/components/editor/index.tsx`.

### Verbatim export inventory (`frontend-public/src/lib/api/admin.ts`)
```bash
91:export async function fetchAdminPublication(
112:export async function fetchAdminPublicationList(
150:export async function updateAdminPublication(
200:export async function cloneAdminPublication(
```

### Publish function check
- `publishAdminPublication(...)` export currently **not present** in `admin.ts` export inventory.
- Existing write operation is `updateAdminPublication(...)` (`PATCH`), not publish-specific action.

### Required answers (§C)
- Path to publication detail/edit page: `frontend-public/src/app/admin/editor/[id]/page.tsx`.
- Component name for publish button: **publish button handler symbol not found by provided grep terms; editor shell identified as `InfographicEditor`.**
- Existing `admin.ts` publication operations: `fetchAdminPublication`, `fetchAdminPublicationList`, `updateAdminPublication`, `cloneAdminPublication`.
- Is there `publishAdminPublication(id, body?)` already? **No.**

## §D — Binding state in editor document model

### Discovery grep blocks
```bash
# grep -rn "block_id|cube_id|semantic_key|bindings|bound" frontend-public/src/ | head -30
frontend-public/src/lib/api/errorCodes.ts:160: * The cast is unsafe in principle but bounded in practice: the key
frontend-public/src/components/editor/index.tsx:372:    // overflow); canvas rendering clips draws to section bounds but raw
... (no concrete binding model hit in first 30 lines for requested tokens)
```

```bash
# find frontend-public/src -type f -name "*.ts" | xargs grep -l "BlockType|VisualConfig|DocumentBlock|EditorBlock" | head -5
frontend-public/src/lib/api/admin.ts
frontend-public/src/lib/types/publication.ts
frontend-public/src/components/editor/registry/guards.ts
frontend-public/src/components/editor/utils/persistence.ts
frontend-public/src/components/editor/utils/block-label.ts
```

```bash
# grep -rn "resolveValue|admin/resolve|resolveAdmin" frontend-public/src/ | head -10
# (no output)
```

```bash
# grep -rn "kpi_value|hero_stat|stat_card|chart|series|data_binding" frontend-public/src/ | head -20
# (no output from this grep slice)
```

### Findings
- From requested grep queries alone, explicit `bound_blocks` collection utility was **not found**.
- No evidence in returned grep blocks of a current client-side walker that emits `{block_id, cube_id, semantic_key, dims, members, period}`.
- Current editor persistence flow is centered on `buildUpdatePayload(snapshotDoc)` -> `updateAdminPublication(...)` path in `frontend-public/src/components/editor/index.tsx`.

### Required answers (§D)
- How bindings are stored in document state: **not located with provided grep probes (needs deeper recon-proper follow-up scan of editor types/schema).**
- Which block types have bindings: **not established from this pre-recon grep slice.**
- Existing code that walks doc collecting bound blocks: **no evidence found.**
- Can `bound_blocks` payload be built without backend changes? **See §D2 for the inventory result.**

## §D2 — Canonical document / block schema inventory

Real schema discovery — files actually viewed, not just grepped.

### Files viewed
- `frontend-public/src/lib/types/publication.ts` — admin/public API shapes plus `VisualConfig` and `AdminPublicationResponse` (includes `document_state?: string | null`).
- `frontend-public/src/components/editor/registry/guards.ts` — schema migration/validation entry points (`validateImportStrict`, `sanitizeBlockProps`) and block sanitization behavior.
- `frontend-public/src/components/editor/utils/persistence.ts` — `buildUpdatePayload(doc)` serialization path and `hydrateDoc` parse/validate flow.
- `frontend-public/src/components/editor/index.tsx` — save pipeline (`const payload = buildUpdatePayload(snapshotDoc)`) proving full canonical doc is persisted through PATCH.
- `frontend-public/src/components/editor/types.ts` — canonical editor schema (`CanonicalDocument`, `Block`, `BlockProps`) where block IDs and props are defined.

### CanonicalDocument / VisualConfig type
```ts
export interface CanonicalDocument {
  schemaVersion: number;
  templateId: string;
  page: PageConfig;
  sections: Section[];
  blocks: Record<string, Block>;
  meta: DocMeta;
  review: Review;
}

export interface VisualConfig {
  layout: string;
  palette: string;
  background: string;
  size: string;
  custom_primary?: string | null;
  branding: BrandingConfig;
}
```

### Block type / BlockProps shape
```ts
export interface BlockProps {
  [key: string]: any;
}

export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;
}
```

### Block id field
- Field name: `Block.id: string` with document-level container `blocks: Record<string, Block>`.
- Stable across edits: **yes (within normal edit flow)** — `sections[].blockIds` references block IDs, and no sanitizer rewrites IDs in persistence/guards; IDs are validated/checked for consistency instead of regenerated in `validateImportStrict` path.

### Binding fields per block — does the doc model carry cube_id / semantic_key / dims / members / period?
- **Partial / unconstrained:** there are no strongly-typed canonical fields named `cube_id`, `semantic_key`, `dims`, `members`, or `period` in `Block`/`CanonicalDocument` types.
- `Block.props` is an open dictionary (`[key: string]: any`), so binding metadata *can* be stored there by convention, but current pre-recon evidence does not show a typed canonical binding contract.

### `buildUpdatePayload(snapshotDoc)` output shape
```ts
export function buildUpdatePayload(
  doc: CanonicalDocument,
): UpdateAdminPublicationPayload
```
- Output includes `document_state: JSON.stringify(doc)` plus derived columns (`chart_type`, `visual_config`, `review`, optional headline/eyebrow/source_text/footnote/description).

### Unknown-prop survival through persistence
- **Yes, with constraints.** `document_state` persists full canonical doc JSON, so unknown keys inside `Block.props` survive round-trip storage.
- Guard layer calls `sanitizeBlockProps` during import validation, so unknown keys may be normalized/filtered depending on block registry constraints. Implication: bound-block metadata can survive only if sanitizer rules permit those keys for relevant block types.

### Verdict on `bound_blocks` extraction
- **(b) Feasible only after schema extension** — current model lacks strongly-typed canonical binding fields (`cube_id/semantic_key/dims/members/period`) even though `Block.props` is flexible. Recon-proper should add an explicit binding schema contract (or documented per-block prop keys + sanitizer allowances) before locking Q5 implementation.

## §E — i18n status for new strings

### Flutter i18n
```bash
app_en.arb
app_ru.arb
backend_errors.dart
generated
```

- Flutter uses ARB + generated localizations (`app_en.arb`, `app_ru.arb`, generated classes), consistent with AppLocalizations pattern.

### Next.js i18n
```bash
frontend-public/messages/ru.json
frontend-public/messages/en.json
```

```bash
frontend-public/src/app/admin/layout.tsx:1:import { getTranslations } from 'next-intl/server';
frontend-public/src/components/editor/index.tsx:4:import { useTranslations } from 'next-intl';
```

- Next.js uses **next-intl** (`useTranslations`, `getTranslations`) with message JSON files.

### Glossary check (terms actually viewed in `docs/i18n-glossary.md`)

| Term (EN) | Term (RU) | In glossary? | Citation |
|-----------|-----------|--------------|----------|
| stale | — | no | — |
| fresh | — | no | — |
| drift | — | no | — |
| snapshot | — | no | — |
| refresh | Обновить / обновление данных | yes | Section 4 (`Refresh`), Section 3 (`data refresh`) |
| republish | — | no | — |
| compare | сравнение | yes | Section 2 (`comparison`) |
| unknown | — | no | — |

If 4+ terms missing: recon-proper must add glossary entries before next-intl key freeze.

### Required answers (§E)
- Flutter library: **AppLocalizations with ARB-generated messages**.
- Next.js library: **next-intl**.
- Existing `staleness.*` namespace: **not observed in sampled outputs**.
- Suggested namespace prefix for new keys: **`publication.compare.*`** (keeps editor/publication scope explicit in next-intl and mirrors likely Flutter feature grouping).
- Glossary approved terminology section for stale/fresh/drift: **glossary file exists; recon-proper should confirm final preferred terms from that source before string freeze.**

## §F — Founder approval questions (10 questions)

> Pre-recon surfaces options and recommendation only; founder decides.

**Q1 — Frontend split.**
- Options: (a) Flutter only, (b) Next.js only, (c) Both.
- Pre-recon recommendation: **(b) Next.js first** because publication editor and admin publication API surface already live there; Flutter appears greenfield for publication CRUD.

**Q2 — Compare trigger.**
- Options: (a) Manual, (b) On hydrate, (c) Polling, (d) Manual+hydrate.
- Pre-recon recommendation: **(a) manual for v1** to keep control and avoid background fanout risk already deferred in debt notes.

**Q3 — Republish-as-refresh UX.**
- Options: (a) single refresh via publish, (b) split refresh vs republish endpoint, (c) refresh confirm modal.
- Pre-recon recommendation: **(a) for milestone v1** with explicit operator-facing language. The action MUST be labeled "Republish to refresh snapshot" (not silently "Refresh") — it triggers full publish semantics, not a pure snapshot refresh. Dedicated refresh endpoint remains DEBT-070; until that ships, refresh = republish.

**Q4 — Severity rendering.**
- Options: (a) color badge, (b) icon+label, (c) placement variants.
- Pre-recon recommendation: **(b) icon+label with color assist**, better accessibility and clarity for unknown/error states.

**Q5 — `bound_blocks` source of truth at publish.**
- Options: (a) walk live doc, (b) maintain snapshot list while editing, (c) send empty until opt-in.
- Pre-recon recommendation: **BLOCKED — pending §D2 verdict.** Preliminary preference is (a) live doc walk *if* §D2 confirms binding metadata is canonical and stable in document state. Fallback (c) until binding model is added if §D2 returns verdict (b) or (c). Founder cannot lock Q5 until §D2 returns a concrete verdict.

**Q6 — Pre-3.1d publications (snapshot_missing).**
- Options: (a) unknown tooltip, (b) refresh-required CTA, (c) hide badge.
- Pre-recon recommendation: **(b)** to drive one-time remediation and reduce silent unknown backlog.

**Q7 — Per-block detail view.**
- Options: (a) aggregate only, (b) drill-down list, (c) inline block annotations.
- Pre-recon recommendation: **(a) in first slice**, defer (b)/(c) to later slices.

**Q8 — Compare error handling (`compare_failed`).**
- Options: (a) warning inline, (b) hide transient failures, (c) distinct partial-check state.
- Pre-recon recommendation: **(c)** explicit partial-check state + retry is operationally safest.

**Q9 — Phase scope split.**
- Options: (a) single PR, (b) sliced rollout, (c) compare-only read without capture wiring.
- Pre-recon recommendation: **(b) slices** to derisk editor integration and keep reviewable increments.

**Q10 — Acceptance criteria for milestone close.**
- Options: (a) badge only, (b) refresh only, (c) both + per-block detail, (d) plus integration test.
- Pre-recon recommendation: **(d-lite)** require (a)+(b) in Next.js plus one end-to-end UI/integration proof; per-block detail can be follow-up.

## §G — Recommended scope split

Given §A-§E findings:
1. **Slice 1a (Next.js, API layer):** add `compareAdminPublication(id)` and `publishAdminPublication(id, body?)` to `admin.ts` + corresponding TypeScript types for `PublicationComparatorResponse`, `BlockComparatorResult`, `CompareBasis`, `BoundBlockReference`, `PublicationPublishRequest`. Pure API client work, no UI changes.
2. **Slice 1b (Next.js, UI):** manual compare trigger button + top-level status badge (`fresh/stale/unknown`) on admin editor/publication context. Consumes Slice 1a types.
3. **Slice 2a (Next.js, schema):** binding collector — walker that traverses canonical document and emits `bound_blocks[]` array. Conditional on §D2 verdict (a). If §D2 returns (b)/(c), this slice is replaced by a backend/schema track.
4. **Slice 2b (Next.js, UI):** republish-as-refresh button wiring `bound_blocks` payload from Slice 2a collector. Confirmation modal per Q3 recommendation.
5. **Slice 3 (optional, Next.js):** per-block drift detail UX (drill-down list and/or inline annotations).
6. **Flutter track:** separate later milestone unless founder explicitly wants dual-frontend parity now. Greenfield scope per §B.

Rationale: publication edit/publish workflow is currently centered in Next.js; Flutter lacks publication CRUD primitives.

## §H — Open risks for recon-proper

1. **Binding model discoverability risk:** requested grep probes did not conclusively locate block binding schema path; recon-proper must map canonical doc fields before coding.
2. **Publish action symbol drift:** no explicit `publishAdminPublication` currently exported in `admin.ts`; publish path may be elsewhere or unimplemented in this frontend surface.
3. **Terminology consistency risk:** compare/staleness phrasing should be checked against `docs/i18n-glossary.md` before final copy freeze.
4. **Cross-frontend expectation risk:** founder request “start with Flutter” conflicts with current publication editor ownership in Next.js.

---

## Summary Report (findings only — operational metadata in PR description)

PHASE 3.1d FRONTEND PRE-RECON

Pre-reading completed:
  recon doc (Phase 3.1d backend):                         YES
  schemas/staleness.py:                                   YES
  admin_publications.py:                                  YES
  FLUTTER_ADMIN_MAP.md:                                   YES
  FRONTEND_AUTOSAVE_ARCHITECTURE.md:                      YES
  EDITOR_ARCHITECTURE.md:                                 YES
  DEBT-064..070 entries:                                  YES
  i18n-glossary.md:                                       YES (after fix)

Discovery sections completed:
  §A Publication CRUD/publish location:                   COMPLETE — Next.js owns editor; explicit publish action NOT confirmed
  §B Flutter publication UI:                              COMPLETE — greenfield + adjacent references documented
  §C Next.js publication editor:                          COMPLETE — /app/admin/editor/[id], admin API exports inventoried
  §D Binding state in document:                           COMPLETE — see §D2 for verdict
  §D2 Canonical document/block schema inventory:          COMPLETE — verdict (b) recorded
  §E i18n status:                                         COMPLETE — Flutter ARB/AppLocalizations; Next.js next-intl; glossary terms checked
  §F 10 founder questions:                                DRAFTED — Q5 marked BLOCKED pending §D2
  §G Scope split recommendation:                          DRAFTED — 6 slices including 1a/1b API+UI split
  §H Open risks:                                          4 items

Key findings (executive summary):
  1. Publication editor/admin publication API surface is currently in Next.js. Flutter has only adjacent references; publication CRUD is greenfield there.
  2. Explicit publish action wiring (`publishAdminPublication`) NOT found in this frontend; only edit/save (`updateAdminPublication`) and clone are wired.
  3. `bound_blocks` extraction feasibility: see §D2 verdict.

Critical surface for founder review:
  - Q1 frontend split: Next.js-first recommended
  - Q5 bound_blocks source of truth: BLOCKED pending §D2 verdict
  - Q9 scope split: sliced rollout (6 slices)
  - §G recommendation: Next.js slices 1a/1b first; 2a/2b conditional on §D2

Honest-STOP triggers:
  - IMPLEMENTATION HALT: bound_blocks schema/path must be confirmed by §D2 before Slice 2a/2b begin.
  - Pre-recon itself may proceed to founder review for non-§D2-blocked questions.

Ready for founder review of §F questions (excluding Q5): YES
