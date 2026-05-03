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

## §B Bound block contract
- Prompt-requested frontend paths (`frontend/src/types`, `frontend/src/schemas`) do not exist in this repository; those greps fail with no-such-directory.
- Repository has Flutter admin (`frontend/lib/...`) and separate web editor app under `frontend-public/src/components/editor`.
- In `frontend-public`, canonical block model is generic:
  - `Block { id, type, props: Record<string, any>, visible, locked? }`
  - No explicit `BoundBlock` type found.
- Semantic binding fields (`cube_id`, `semantic_key`) in frontend block schemas/types/components: **NOT FOUND in codebase** from requested search surface.
- Backend parsing of bound fields from `document_state`: comments indicate backend treats `document_state` as opaque text and does not inspect payload.
- Render value field for bound blocks: explicit bound-value renderer contract is **NOT FOUND in codebase** from searched surfaces.
- Terminology drift: this codebase uses “CanonicalDocument”, “blocks”, “props”, and “document_state”; no explicit “BoundBlock” type in observed files.

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

## §F Founder questions (≥5)
1. **Snapshot storage location ambiguity: where should publish-time resolve snapshots persist?**
   - Option A: Inline inside `document_state` JSON.
     - Benefit: single payload hydrate path already source-of-truth per DEBT-026.
     - Cost: schema evolution risk for opaque blob; larger payload churn on autosave/publish.
   - Option B: Separate `publication_block_snapshot` persistence surface.
     - Benefit: targeted querying/partial updates, cleaner schema evolution.
     - Cost: added join/read complexity and migration overhead.
   - Option C: Reuse/extend `semantic_value_cache` linkage.
     - Benefit: leverages existing stale/runtime metadata surface.
     - Cost: runtime cache semantics differ from publication immutability; coupling risk.
   - **Recommendation (preliminary): Option A or B, avoid C.** Rationale: current code comments strongly separate opaque publication persistence from runtime cache semantics (3.1aaa/3.1c).

2. **Snapshot key shape ambiguity: what uniquely keys each snapshot record?**
   - Option A: `(publication_id, block_id)`
     - Benefit: aligns with document-centric hydrate/update lifecycle.
     - Cost: requires stable block ids across clone/republish semantics decisions.
   - Option B: `(cube_id, semantic_key, coord, period)`
     - Benefit: tracks semantic cell identity independent of document internals.
     - Cost: multiple blocks could intentionally duplicate binding; block-specific UX provenance weaker.
   - Option C: `(publication_id, block_id, mapping_version_at_publish)`
     - Benefit: explicit versioned lineage when mappings evolve.
     - Cost: extra cardinality and republish behavior complexity.
   - **Recommendation (preliminary): Option A plus preserved semantic context payload.** Rationale: existing persistence and hydrate are publication-document-centric.

3. **Staleness comparator ambiguity: which mismatch defines stale?**
   - Option A: `source_hash` mismatch only.
     - Benefit: cheap and provenance-focused.
     - Cost: may mark stale on benign upstream refresh with same value.
   - Option B: value-state comparison (`value`/`missing`) only.
     - Benefit: user-visible drift centric.
     - Cost: misses structural mapping/source changes with unchanged output.
   - Option C: composite (source_hash OR value/missing OR mapping_version).
     - Benefit: broad drift detection envelope.
     - Cost: noisier stale rate; policy tuning needed.
   - Option D: strict all-three mismatch required.
     - Benefit: low false positive rate.
     - Cost: likely under-detects meaningful drift.
   - **Recommendation (preliminary): Option C.** Rationale: 3.1c intentionally exposes all these fields; comment precedent in semantic mapping mentions mapping-version drift.

4. **Execution timing ambiguity: when should comparison run?**
   - Option A: publish-time capture only (no re-check).
     - Benefit: minimal runtime cost.
     - Cost: no ongoing stale signal.
   - Option B: hydration-time re-resolve compare.
     - Benefit: on-demand freshness signal at operator/public touchpoints.
     - Cost: N resolve calls per page load risk.
   - Option C: periodic background scans only.
     - Benefit: centralized load shaping.
     - Cost: stale status lag and scheduler complexity.
   - Option D: combo (hydrate-time + periodic precompute).
     - Benefit: balances UX responsiveness with cached status.
     - Cost: highest system complexity.
   - **Recommendation (preliminary): Option D if scale requires; Option B for simplest first lock.** Rationale: existing scheduler precedent in 3.1aa/3.1aaa suggests periodic jobs are acceptable patterns.

5. **Behavior on stale ambiguity: what should user/system do when stale detected?**
   - Option A: admin-only badge.
     - Benefit: low public-risk, minimal product blast radius.
     - Cost: public consumers unaware of drift.
   - Option B: admin + public badge.
     - Benefit: transparency.
     - Cost: public UX/legal/comms implications.
   - Option C: block publish/re-publish until refresh.
     - Benefit: strong quality gate.
     - Cost: workflow friction.
   - Option D: auto-refresh resolved value silently.
     - Benefit: minimal operator overhead.
     - Cost: mutates published semantics without explicit acknowledgment.
   - **Recommendation (preliminary): Option A initially.** Rationale: least disruptive with current admin-centric resolve surface (`/api/v1/admin/resolve/...`).

6. **Missing-observation ambiguity: how compare `value=null, missing=true` states?**
   - Option A: treat unchanged missing-state as fresh regardless of source hash.
     - Benefit: avoids noisy stale on suppressed data.
     - Cost: hides provenance churn.
   - Option B: treat source_hash mismatch as stale even if missing-state unchanged.
     - Benefit: strict provenance integrity.
     - Cost: potentially high stale noise.
   - Option C: classify as separate “indeterminate” status.
     - Benefit: nuanced operator signal.
     - Cost: added UI/state complexity.
   - **Recommendation (preliminary): Option B or C depending on tolerance.** Rationale: 3.1c explicitly includes `source_hash` + missing contract, suggesting both matter.

7. **Public stale visibility ambiguity: what should public renderer do with stale blocks?**
   - Option A: show last published value + stale badge.
   - Option B: show last published value silently (admin-only stale visibility).
   - Option C: block render/degrade block output.
   - Option D: dynamically re-resolve for public render.
   - **Recommendation (preliminary): Option B initially.** Rationale: no direct public resolve caller currently identified; admin resolve route is explicit.

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
[verbatim file content captured in command transcript during execution]

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
