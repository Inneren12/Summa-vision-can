# Phase 3.1d — Pre-Recon (snapshot persistence + staleness)

**Status:** Inventory only. No locked decisions.  
**Date:** 2026-05-03  
**Source:** GPT-5.3-Codex on `claude/phase-3-1d-pre-recon`

## Summary
Publication persistence is centered on the `publications` table with `document_state` as an opaque JSON string stored in a `Text` column; backend does not parse this payload, frontend-public owns strict shape validation during hydrate. Admin publication responses include `document_state`; public publication responses currently do not include it, and no `document_state` references were found in `public_*` backend routers. The 3.1c resolve stack is present with `ResolvedValueResponse` fields required for staleness comparisons (`mapping_version`, `source_hash`, `is_stale`, `value`, `missing`), but no direct frontend callers were found in this repo slice. Top ambiguities for recon lock: snapshot storage location, staleness comparator semantics, and execution timing (hydrate vs periodic vs combo).

## §A Publication entity surface
- `Publication` ORM is in `backend/src/models/publication.py`; columns include scalar editorial fields plus JSON-as-text fields (`visual_config`, `review`, `document_state`) and lifecycle fields (`status`, `published_at`, etc.).
- `document_state` is `Mapped[str | None] = mapped_column(Text, nullable=True)` (not JSONB). Backend comments explicitly state it is opaque and not inspected.
- Schema layer (`backend/src/schemas/publication.py`) keeps `document_state` typed as `Optional[str]` across create/update/response models. Comments explicitly say frontend serializes and validates; backend stores verbatim.
- Hydration/read paths:
  - Admin: `_serialize()` in `admin_publications.py` maps `document_state=publication.document_state` into `PublicationResponse`.
  - Public: `rg -n "document_state" backend/src/api/routers/public_*.py` returned **NOT FOUND in codebase**.
- Write paths:
  - Admin PATCH/Create schemas accept `document_state` in `PublicationUpdate`/`PublicationCreate`.
  - Router-level write orchestration exists in `admin_publications.py`; inventory confirms schema/serialization participation but pre-recon did not enumerate each repository callsite mutation line-by-line for every endpoint action.
- Snapshot-like field on `Publication`: **NOT FOUND in codebase** (no dedicated publish-time snapshot column).
- `review` field shape:
  - Model: `review` stored as JSON string in `Text` column.
  - Schema: `ReviewPayload` has top-level keys `workflow`, `history`, `comments`.

## §B (revised) Bound block contract
- Primary frontend search surface corrected to `frontend-public/src/` (reviewer blocker fix). The requested binding symbols (`cube_id`, `semantic_key`, `BoundBlock`, `dataBinding`) return no explicit bound-block type or mapping-prop shape in this editor code.
- Observed editor data model remains generic: blocks are `Record<string, Block>` and `Block.props` is untyped bag (`{ [key: string]: any }`) in `frontend-public/src/components/editor/types.ts`.
- Fallback repository search shows `cube_id` / `semantic_key` usage in Flutter semantic-mappings admin code (`frontend/lib/features/semantic_mappings/...`), not in frontend-public editor block payloads.
- Binding shape definition verdict: **no explicit binding type found**; if bindings exist for 3.1d target blocks, fields likely live directly on block props and are not currently discoverable by naming grep.
- Mapping reference field names on bound blocks (`cube_id`, `semantic_key`, dim/member, period): **NOT FOUND in codebase (frontend-public editor path)**.
- Renderer value field for bound blocks: **NOT FOUND in codebase** (no bound-value render path discovered by grep).
- Backend awareness verdict: backend treats `document_state` as opaque text; no backend parser found that extracts per-block binding fields.
- Typed vs untyped: block props are untyped JSON bag (`BlockProps` index signature), not a typed union per block kind at type-definition level.

## §B2 CanonicalDocument / block shape inventory
1. **CanonicalDocument type definition (authoritative round-trip type):** `frontend-public/src/components/editor/types.ts` defines `CanonicalDocument` with root fields `schemaVersion`, `templateId`, `page`, `sections`, `blocks`, `meta`, `review`. Backend has no equivalent deep schema; backend stores opaque JSON string in `document_state`.
2. **Block shape:** `Block` has `id`, `type`, `props`, `visible`, optional `locked`.
3. **block.props shape:** `BlockProps` is `[{key:string]: any}` (typed-bag / index-signature), not discriminated union.
4. **Validator unknown-field behavior (decision-flipper):** validation pipeline is custom TS (`validateImportStrict` + `migrateDoc` + shape/reference/registry checks), not Zod. In hydrate path, `validateImportStrict` returns migrated doc and does not sanitize unknown top-level keys itself; however `hydrateImportedDoc`/`sanitizeBlockProps` explicitly says unknown block-prop keys are dropped in strict normalization path. **Verdict:** Inline snapshot in block.props **WILL NOT** reliably survive all round-trip/editor normalization paths — Option A1 is non-viable as drafted without validator-path changes.
5. **schemaVersion/migration path:** `schemaVersion` exists at root; migration is explicit sequential map (`MIGRATIONS`, `applyMigrations`, `migrateDoc`) to `CURRENT_SCHEMA_VERSION`.
6. **Block id stability (decision-flipper):** editor hydration normalizes block ids to object keys (`id: key`) and warns on realignment. Duplication flow exists in reducer/actions, and clone publication backend clones full row document_state behavior (with workflow reset) via clone service path. **Verdict:**
   - Block ids preserved through publish action: **YES/PARTIAL** (publish status transition does not imply block-id regeneration path found).
   - Block ids preserved on clone publication row: **PARTIAL/UNKNOWN** (clone service behavior depends on whether cloned `document_state` is reused/reset by repository clone implementation; explicit `mutate_document_state_for_clone` symbol not found in backend search surface).
7. **Allowed-extra-props behavior on hydration:** strict import validator + normalizer path can drop unknown keys during sanitization. Unknown extra props are not guaranteed to survive hydration into running state.
8. **Document-level extension points:** top-level `meta` and `review` exist; no explicit `bindings`/`snapshots`/`extensions` root field currently defined in `CanonicalDocument`.

## §C 3.1c ResolvedValueResponse consumers
`ResolvedValueResponse` verbatim schema source is in `backend/src/schemas/resolve.py` (see Appendix command transcript with full file output).

- Resolve endpoint contract:
  - Route prefix: `/api/v1/admin/resolve`
  - Handler: `GET /{cube_id}/{semantic_key}`
  - Query params: repeated `dim`, repeated `member`, optional `period`
  - Auth: router docstring states AuthMiddleware X-API-KEY enforcement.
- Existing callers:
  - Backend: handler/service wiring found in `admin_resolve.py` and `services/resolve/service.py`.
  - Frontend/public caller references in searched paths: **NOT FOUND in codebase** (no direct resolve endpoint consumer found in grep excerpt).
- Field role inventory for recon:
  - Likely comparison material: `value`, `missing`, `source_hash`, `mapping_version`, `is_stale`
  - Likely metadata: `resolved_at`, `cache_status`, `units`
  - Identity context: `cube_id`, `semantic_key`, `coord`, `period`
  - (Classification is inference; no locked decision.)

## §D Existing snapshot/cache precedent
- Snapshot/frozen/as_of/version-at patterns in backend models:
  - `published_at` exists on `Publication`.
  - No dedicated generic snapshot model/table found by requested grep.
- Stale patterns:
  - `semantic_value_cache.is_stale` exists in model and resolve response.
  - `cube_metadata_cache` docs mention stale rows tolerated by validator flow.
- `semantic_mapping.py` includes explicit comment about 3.1d-style staleness check concept (`snapshot.mapping_version != current.version → stale`) as inline design note/comment, not an implemented publication snapshot entity.
- “value at time X + currentness marker” combo precedent:
  - Closest is runtime cache rows (`fetched_at` + `is_stale`) in semantic value cache.
  - Publication-level persisted snapshot+freshness dual state: **NOT FOUND in codebase**.

## §E Frontend hydration + render path
- Hydration is explicit in `frontend-public/src/components/editor/utils/persistence.ts`:
  - `hydrateDoc` prefers `document_state` (parse JSON + `validateImportStrict`).
  - Falls back to legacy scalar-field hydrate when `document_state` is null.
- DEBT-026 references are present across docs/tests and persistence comments; hydration-order behavior aligns with “document_state first” flow.
- Staleness UI hooks in frontend search scope:
  - `is_stale`/`isStale` occurrences found primarily in non-editor contexts (e.g., jobs/exceptions tests in Flutter app); no publication-block stale badge implementation identified in searched frontend-public editor paths.
- Admin/public entrypoints for publication hydration:
  - Admin editor hydration function confirmed (`hydrateDoc`) in frontend-public utility.
  - Public viewer consumption of resolved semantic block values: **NOT FOUND in codebase** in searched surfaces.
- Fresh-fetch vs stored-read default for publication editor hydrate:
  - Stored-read default (`document_state` from publication response) with legacy fallback; no automatic resolve call in hydrate utility.

## §F Founder questions (v2)
Q1. **Snapshot storage location ambiguity (expanded option matrix).**
- A1 Inline in `block.props.resolveSnapshot`.
  - Benefit: local per-block co-location with render payload.
  - Cost: viability depends on §B2 #4 unknown-field/normalization behavior.
  - Viability tag: depends on §B2 #4.
- A2 Inline in document-level `bindings` / `snapshots` map keyed by block id.
  - Benefit: single-document persistence path, less per-block prop pollution.
  - Cost: requires top-level extension-point decision (§B2 #8).
  - Viability tag: depends on §B2 #8.
- B1 Separate table (`publication_block_snapshot`) with doc holding only linkage.
  - Benefit: schema-evolvable, queryable, decoupled from editor doc churn.
  - Cost: sync surface between row set and document_state.
  - Viability tag: generally viable independent of §B2.
- B2 Separate table for current stale status only; frozen value remains doc-side.
  - Benefit: limits table footprint while preserving published snapshot locality.
  - Cost: split-source complexity.
  - Viability tag: generally viable independent of §B2.
- C Extend `semantic_value_cache` with publish snapshot fields.
  - Benefit: reuse existing cache infra.
  - Cost: cache lifecycle != publication lifecycle; high coupling risk.
- D Hybrid: publication-level summary status in `review` (or metadata field), block snapshots inline/separate.
  - Benefit: cheap aggregate UX signal.
  - Cost: mixes workflow/review with data-freshness concerns.
  - Viability tag: depends on §B2 #4 + §A review-shape constraints.
- **Preliminary bias:** A2 or B1. **Final recommendation deferred to recon-proper pending §B2 verdict on unknown-field survival (#4) and extension-point feasibility (#8).**

Q2. **Snapshot key shape ambiguity (expanded + dependency tags).**
- `(publication_id, block_id)` — depends on §B2 #6 block-id stability.
- `(publication_id, block_id, mapping_version_at_publish)` — same dependency plus mapping-version semantics.
- `(cube_id, semantic_key, coord, period)` — block-id independent but weaker publication-context tie.
- Composite `(publication_id, block_id, cube_id, semantic_key, coord, period)` — strongest traceability, highest complexity.
- **Preliminary bias:** depends on §B2 #6. If block_id stable through clone/publish, lean `(publication_id, block_id)`; otherwise lean semantic composite without block_id reliance. **Final recommendation deferred to recon-proper pending §B2 #6 certainty.**

Q3. **Comparator model ratification (replaces single-boolean stale rule).**
- Ambiguity: should staleness be modeled as reasoned multi-axis output vs one boolean?
- Options:
  - Adopt §J ComparatorResult as-is.
  - Adopt §J with reduced reason set.
  - Keep boolean `is_stale` only (least expressive).
- **Preliminary bias:** adopt §J reasoned model; recon to lock per-reason severity mapping.

Q4. **Timing matrix ratification (replaces single-timing question).**
- Ambiguity: which context/event combinations ship in 3.1d v1?
- Options:
  - Admin hydrate + publish hook only.
  - Add scheduled backend compare in v1.
  - Include public-side display path in v1.
- **Preliminary bias:** baseline in §K (publish hook + admin hydrate compare). Final scope lock deferred to recon-proper.

Q5. **Behavior on staleness once detected (depends on §K-enabled contexts).**
- Options: admin badge only; admin+public badge; publish gate; explicit operator refresh flow.
- **Preliminary bias:** admin badge first, with policy gates deferred.

Q6. **Missing observation semantics (`value=null, missing=true`)**
- Options: unchanged missing-state=fresh; source-hash-delta still stale; dedicated indeterminate reason.
- **Preliminary bias:** keep dedicated reason path in comparator so policy can map separately.

Q7. **Public stale visibility (defer pending §I public data surface).**
- If §I says public payload lacks compare basis, default collapses to “no client-side public compare; backend-computed flag only”.
- If §I says payload includes compare basis, options become badge / last-known-fresh fallback / render block.
- **Preliminary bias:** defer until §I verdict finalized.

Q8. **Backend service reuse vs HTTP self-call for resolve.**
- Option A: backend self-calls `/api/v1/admin/resolve/...` over HTTP.
  - Cost: auth plumbing, serialization overhead, observability split, rate-limit/deadlock risk.
- Option B: reuse `ResolveService` directly via DI/internal call path.
  - Benefit: single business-logic path, no self-auth, lower overhead.
- **Preliminary bias:** Option B (direct ResolveService reuse). Final recommendation can be ratified in recon-proper.

## §G Risk inventory
1. **JSON schema evolution risk (Severity: High; ties Q1/Q2).**
   - Failure mode: embedding snapshots in opaque `document_state` creates migration/versioning friction and brittle backward compatibility for old rows.
2. **Hydration performance risk (Severity: High; ties Q3/Q4).**
   - Failure mode: per-bound-block re-resolve on load causes N+1 latency spikes/timeouts on large documents.
3. **Cache coherence/race risk (Severity: Medium; ties Q3/Q4/Q6).**
   - Failure mode: scheduler refresh flips cache provenance during hydration compare, causing transient false stale/fresh outcomes.
4. **Auth surface expansion risk (Severity: Medium; ties Q5/Q7).**
   - Failure mode: introducing new snapshot/staleness endpoints accidentally broadens data exposure beyond existing admin resolve protections.
5. **UI state complexity risk (Severity: Medium; ties Q5/Q7).**
   - Failure mode: inconsistent stale semantics between admin editor and public viewer create operator confusion and support burden.
6. **Back-compat no-snapshot risk (Severity: High; ties Q1/Q4).**
   - Failure mode: pre-3.1d publications without snapshot cannot be deterministically classified, causing hydration ambiguity or errors.

## §H Drift detection touch list
Canonical architecture docs likely impacted after 3.1d ships (touch-list only):
1. `docs/architecture/BACKEND_API_INVENTORY.md`
2. `docs/architecture/FRONTEND_AUTOSAVE_ARCHITECTURE.md`
3. `docs/architecture/ARCHITECTURE_INVARIANTS.md`
4. `docs/architecture/ROADMAP_DEPENDENCIES.md`
5. `docs/architecture/_DRIFT_DETECTION_TEMPLATE.md`
6. `docs/architecture/AGENT_WORKFLOW.md`
7. `docs/architecture/FLUTTER_ADMIN_MAP.md`
8. `docs/architecture/TEST_INFRASTRUCTURE.md`
9. `docs/architecture/DEPLOYMENT_OPERATIONS.md`

## §I Public read surface depth
1. Public schema surface uses `PublicationPublicResponse` and public graphics wrapper in `public_graphics.py`; fields are scalar publication metadata + preview URL, with explicit omission of editor internals (`visual_config`, object keys).
2. Public viewer/render source appears pre-rendered/public-asset oriented (gallery list + preview URL), not canonical-document-in-browser render from `document_state`.
3. Scalar public fields include: `id`, `headline`, `slug`, `chart_type`, `eyebrow`, `description`, `source_text`, `footnote`, `virality_score`, `preview_url`, `status`, `cdn_url`, `created_at`, `updated_at`, `published_at`.
4. Stale-display feasibility verdict: **Public viewer CANNOT compare values for staleness client-side** because public response does not expose `document_state` + binding snapshot basis; public stale UX would require backend-computed flag.

## §J Comparator model
```
ComparatorResult:
  stale_status: Literal["fresh", "stale", "unknown"]
  stale_reasons: list[Literal[
    "mapping_version_changed",
    "source_hash_changed",
    "value_changed",
    "missing_state_changed",
    "cache_row_stale"
  ]]
  severity: Literal["info", "warning", "blocking"]
  compared_at: datetime
  compare_basis: dict
```
Open mapping questions for recon: reason→severity policy, multi-reason aggregation rule, and whether refresh is explicit operator action vs transparent.

## §K Execution timing matrix
| Context | Auth surface | Capture event | Comparison event | Notes |
|---|---|---|---|---|
| Admin editor | X-API-KEY (3.1c resolve available) | publish action | hydrate on reopen | Can compare on demand if resolver called. |
| Public viewer | Public/no auth | publish captures snapshot | hydrate/render | Needs backend-computed status; no direct resolve call. |
| Backend publish hook | Internal service | publish action | n/a | Captures snapshot synchronously at publish. |
| Backend scheduled job | Internal service | n/a | scheduled | Reuse ResolveService directly (Q8 bias). |

Narrative: v1 baseline likely publish-hook capture + admin-hydrate compare; scheduled backend compare and public stale display are likely deferred. Race surface exists when scheduled refresh overlaps admin hydrate compare (cross-ref §G cache-coherence risk).

## Appendix A — Grep transcript
```bash
$ rg -n "class Publication\b" backend/src/models/
backend/src/models/publication.py:27:class Publication(Base):

$ rg -n "document_state" backend/src/models/publication.py
154:    document_state: Mapped[str | None] = mapped_column(Text, nullable=True)

$ rg -n "document_state" backend/src/schemas/publication.py
156:    document_state: Optional[str] = None
191:    # Unlike ``review`` (parsed for workflow-sync logic), ``document_state``
196:    document_state: Optional[str] = None
243:    # Passed straight through from the ``publications.document_state``
246:    document_state: Optional[str] = None

$ rg -n "document_state" backend/src/api/routers/admin_publications.py | head -20
238:        document_state=publication.document_state,

$ rg -n "document_state" backend/src/api/routers/public_*.py | head -10
<NO MATCH>

$ rg -nF "review" backend/src/models/publication.py
5:API to serve a preview thumbnail while the full-resolution asset is
35:        s3_key_lowres: S3 object key for the low-resolution preview.
57:        review: JSON-serialised review subtree mirroring the frontend
58:            ``CanonicalDocument.review`` ( ``workflow``, ``history``,
138:    # comments (mirrors the frontend CanonicalDocument.review subtree).
144:    review: Mapped[str | None] = mapped_column(Text, nullable=True)

$ rg -n "bound\b|binding\b|BoundBlock\b" frontend/src/types/ frontend/src/schemas/ | head -20
rg: frontend/src/types/: No such file or directory (os error 2)
rg: frontend/src/schemas/: No such file or directory (os error 2)

$ rg -n "cube_id|semantic_key" frontend/src/types/ frontend/src/schemas/ frontend/src/components/ | head -20
rg: frontend/src/types/: No such file or directory (os error 2)
rg: frontend/src/schemas/: No such file or directory (os error 2)
rg: frontend/src/components/: No such file or directory (os error 2)

$ rg -n "BoundBlock|bound_block|binding_kind" backend/src/ | head -20
<NO MATCH>

$ cat backend/src/schemas/resolve.py
"""Phase 3.1c — :class:`ResolvedValueResponse` DTO (schema).

Verbatim from the impl-addendum §"REPLACEMENT — Phase 6 schema content".
11 fields. ``value`` is nullable (FIX-2 missing-observation contract);
``missing`` is a required raw-passthrough boolean from the cache row.

NO ``populate_by_name`` (alias-driven serialization is intentionally
absent — fields use their snake_case names on the wire).
NO ``prime_warning`` field (recon F-fix-2 removed this — errors surface
via structured logs and ``RESOLVE_CACHE_MISS.details`` only).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedValueResponse(BaseModel):
    cube_id: str = Field(description="Cube identifier.")
    semantic_key: str = Field(description="Semantic mapping key.")
    coord: str = Field(
        description=(
            "Service-derived StatCan coordinate string echoed from cache row."
        )
    )
    period: str = Field(description="Resolved period token (ref_period).")
    value: str | None = Field(
        default=None,
        description=(
            "Canonical stringified numeric value. None when the observation "
            "is suppressed/missing upstream (paired with missing=True)."
        ),
    )
    missing: bool = Field(
        description=(
            "Raw passthrough from cache row. True when the upstream "
            "observation is absent/suppressed; in that case value is None."
        ),
    )
    resolved_at: datetime = Field(
        description="Alias of cache row fetched_at timestamp."
    )
    source_hash: str = Field(description="Opaque cache provenance hash.")
    is_stale: bool = Field(description="Persisted stale marker from cache row.")
    units: str | None = Field(
        default=None,
        description="Unit from mapping.config.unit if string, else null.",
    )
    cache_status: Literal["hit", "primed"] = Field(description="Resolve status.")
    mapping_version: int | None = Field(
        default=None, description="Optional semantic mapping version."
    )


__all__ = ["ResolvedValueResponse"]

$ rg -n "resolve_value|/admin/resolve/" backend/src/ frontend/src/ | head -20
backend/src/services/resolve/__init__.py:5:(``GET /api/v1/admin/resolve/{cube_id}/{semantic_key}``).
backend/src/services/resolve/service.py:132:    async def resolve_value(
backend/src/api/routers/admin_resolve.py:5:    GET /api/v1/admin/resolve/{cube_id}/{semantic_key}
backend/src/api/routers/admin_resolve.py:113:async def resolve_value_handler(
backend/src/api/routers/admin_resolve.py:131:        return await service.resolve_value(

$ rg -n "snapshot|frozen|at_publish|as_of|published_at" backend/src/models/ | head -20
backend/src/models/publication.py:64:        published_at: UTC timestamp recorded when the publication
backend/src/models/publication.py:164:    published_at: Mapped[datetime | None] = mapped_column(

$ rg -n "is_stale|stale\b" backend/src/models/ backend/src/schemas/ | head -20
backend/src/models/semantic_mapping.py:112:    Used by snapshot staleness check in 3.1d:
backend/src/models/semantic_mapping.py:113:    snapshot.mapping_version != current.version → stale.
backend/src/models/semantic_value_cache.py:83:            "ix_semantic_value_cache_is_stale",
backend/src/models/semantic_value_cache.py:84:            "is_stale",
backend/src/models/semantic_value_cache.py:85:            postgresql_where=sa.text("is_stale = true"),
backend/src/models/semantic_value_cache.py:135:    is_stale: Mapped[bool] = mapped_column(
backend/src/schemas/resolve.py:46:    is_stale: bool = Field(description="Persisted stale marker from cache row.")

$ rg -n "version_at\b|locked_version\b" backend/src/ | head -10
<NO MATCH>

$ rg -n "hydrate|hydration|loadPublication|fetchPublication" frontend/src/ | head -15
rg: frontend/src/: No such file or directory (os error 2)

$ rg -n "DEBT-026|document_state hydrate" frontend/src/ docs/ | head -10
rg: frontend/src/: No such file or directory (os error 2)
docs/recon/phase-2-2-pre-recon.md:226:- Equivalents for `eyebrow`, `description`, `source_text` from DEBT-026 work — **not found in types.ts**. types.ts contains no string-literal references to these field names. Whatever DEBT-026 introduced lives in the registry / per-block prop catalogs, not in the canonical type surface. Chunk 2 should resolve their exact shape.
docs/recon/phase-2-2-pre-recon.md:479:| headline / source / etc | YES (B3 — block props on `headline_editorial`, `source_footer`, `eyebrow_tag`; runtime-typed via `BlockProps { [key: string]: any }`) | YES (DEBT-026 — `eyebrow`, `description`, `source_text`, `footnote` columns + matching `PublicationResponse` fields, plus opaque `document_state` JSON for full lossless round-trip) | None — caption builders can read straight from the in-memory `CanonicalDocument` snapshot at export time. |
docs/recon/phase-1-3-D3-debt.md:35:### DEBT-026: Lossy round-trip between CanonicalDocument and AdminPublicationResponse
docs/architecture/ARCHITECTURE_INVARIANTS.md:181:- `document_state` set to None on clone — frontend hydrates from column fallback (DEBT-026 lesson). NOT copied verbatim from source.
docs/SPRINT_STATUS.md:277:Follow-up close resolves DEBT-026: opaque `document_state` column on
docs/ARCHITECTURE.md:207:### Document persistence model (DEBT-026 closure)
docs/ARCHITECTURE.md:298:- `document_state` is RESET to `None`. The frontend hydrates from `document_state` first (DEBT-026); copying the source's published workflow JSON would cause autosave to re-publish the clone. Frontend hydration falls back to backend columns when `document_state` is null.
docs/modules/editor.md:646:### Persistence seam (DEBT-026 closed)

$ rg -n "isStale|is_stale|stale" frontend/src/ | head -10
rg: frontend/src/: No such file or directory (os error 2)
```


$ rg -n "cube_id|cubeId|semantic_key|semanticKey" frontend-public/src/ | head -30
(no matches)

$ rg -n "binding|bound|BoundBlock|boundBlock|dataBinding" frontend-public/src/ | head -30
frontend-public/src/components/editor/renderer/types.ts:38: * geometry to the visible section bounds.
frontend-public/src/components/editor/renderer/measure.ts:105: * `availableHeight` is the unbounded sentinel and `overflow` is always
frontend-public/src/components/editor/renderer/measure.ts:114:  const unbounded = size.h === Infinity;
frontend-public/src/components/editor/renderer/measure.ts:138:      overflow: unbounded ? false : consumed > layout.h * 1.1,
frontend-public/src/components/editor/export/renderToBlob.ts:20: * - rAF-bound: render pass + toBlob run inside `requestAnimationFrame` so that

$ rg -n "BlockProps|BlockRegistry|BREG|registry" frontend-public/src/components/editor/ | head -20
frontend-public/src/components/editor/types.ts:28:export interface BlockProps {
frontend-public/src/components/editor/types.ts:35:  props: BlockProps;

$ rg -n "source_hash|sourceHash|mapping_version|mappingVersion|is_stale|isStale|resolve" frontend-public/src/ | head -20
frontend-public/src/components/editor/types.ts:105:  resolved: boolean;
frontend-public/src/components/editor/types.ts:106:  resolvedAt: string | null;

$ rg -n "cube_id|cubeId|semantic_key|semanticKey" --type-not py --type-not md | head -30
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:14:    String? cubeId,

$ rg -n "BoundBlock|boundBlock" | head -20
docs/recon/phase-3-1d-pre-recon.md:30:  - No explicit `BoundBlock` type found.

$ rg -n "document_state\[.*block|json\.loads.*document_state|parse.*document_state" backend/src/ | head -15
backend/src/schemas/publication.py:191:    # Unlike ``review`` (parsed for workflow-sync logic), ``document_state``

$ rg -n "kind:.*kpi|kind:.*chart|type:.*kpi|type:.*chart|BlockKind" frontend-public/src/ | head -20
frontend-public/src/components/editor/registry/templates.ts:77:  ranked_bar_simple:{fam:"Ranked Bars",vr:"Simple Ranking",variantKey:"simple_ranking",desc:"Horizontal bars by value",descKey:"horizontal_bars_by_value",defaultPal:"housing",defaultBg:"gradient_midnight",defaultSize:"reddit_standard",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["bar_horizontal"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Housing Price-to-Income Ratio
Across Major Canadian Cities"},eyebrow_tag:{text:"RANKED: · HOUSING AFFORDABILITY · Q4 2025"},source_footer:{text:"Source: CMHC, Q4 2025"}}},

$ rg -n "validateImportStrict|validateImport|validateDocument" frontend-public/src/ backend/src/
backend/src/models/publication.py:151:    # inspects the payload — the frontend's ``validateImportStrict``
frontend-public/src/components/editor/validation/validate.ts:27:export function validateDocument(doc: CanonicalDocument): ValidationResult {

$ rg -n "\.strict\(\)|\.passthrough\(\)|\.strip\(\)" frontend-public/src/components/editor/ frontend-public/src/schemas/
rg: frontend-public/src/schemas/: No such file or directory (os error 2)
(no matches in frontend-public/src/components/editor/)

$ rg -n "block.*id|generateId|nanoid|uuid" frontend-public/src/components/editor/ | head -20
frontend-public/src/components/editor/renderer/measure.ts:129:      blockMeasures.push({ blockId: bid, type: block.type, estimatedHeight: estimated });

$ rg -n "clone|duplicate" frontend-public/src/components/editor/ | head -15
frontend-public/src/components/editor/validation/block-data.ts:12: * Keeping the rules here, rather than duplicated between registry/blocks.ts

$ rg -n "_serialize|clone_publication|mutate_document_state_for_clone" backend/src/ | head -10
backend/src/services/publications/clone.py:26:async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:

$ rg -n "PublicationPublic|PublicPublication|published" backend/src/api/ backend/src/schemas/ | head -25
backend/src/schemas/kpi.py:19:    published_count: int

$ rg -n "document_state|visual_config|blocks|render" backend/src/api/routers/public_*.py | head -20
backend/src/api/routers/public_graphics.py:76:# ``s3_key_highres`` and ``visual_config`` to prevent leaking internal

$ rg -n "publication_repo|public_publication" backend/src/api/ | head -15
(no matches)

$ rg -n "fetchPublication|loadPublication|publicViewer" frontend-public/src/ | head -20
(no matches)

$ grep -nE "\[verbatim.*captured\]|\[output captured\]|\[transcript.*\]|\[content captured\]|\[full output\]|\[see transcript\]|<output omitted>|<see (above|below)>" docs/recon/phase-3-1d-pre-recon.md
(no matches)
