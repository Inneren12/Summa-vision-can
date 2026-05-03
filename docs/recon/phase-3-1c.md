# Phase 3.1c Recon — Semantic resolve endpoints (backend only)

## §A — Frontend consumer analysis

### A1 — Roadmap consumer audit
Verbatim Phase 3 evidence (roadmap):
- "3.1 Semantic Layer backend (Dimension → Category → Metric)".
- "3.2 Hybrid binding frontend (Zustand snapshot state)".
- "3.4 Template Suggestion (silent prefill from `subject_code`)".
- "3.5 Publish-time stale binding warn-and-confirm dialog".
- "Bound block stores `snapshotValue`, `resolvedAt`, source hash — rendering uses snapshot, never live read".
- "Check for updates action compares snapshot to live source, creates new R19 version on re-resolve".  
Source: `docs/OPERATOR_AUTOMATION_ROADMAP.md` lines 191-202.

Implication: resolve must support both per-binding UX and doc-level refresh/snapshot operations.

### A2 — Existing frontend code grep
Verbatim grep command run:
```bash
rg -n "semantic|semanticKey|binding|resolve|snapshotValue|resolvedAt|sourceHash|/admin/semantic" frontend-public/src frontend/lib/features
```
Findings:
- No public-editor semantic binding integration yet (no `snapshotValue`/`sourceHash` binding fields in editor model usage).
- Flutter admin app has `semantic-mappings` CRUD repository only (`frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart`), no resolve endpoint client yet.
- Most `resolved*` matches in `frontend-public` are for comment thread resolution, unrelated to semantic data binding.

Conclusion: Phase 3.2 binding frontend has not started; endpoint choice must be roadmap-driven + architecture-aligned.

### A3 — Editor block model audit
`EDITOR_BLOCK_ARCHITECTURE.md` defines `CanonicalDocument` with `blocks: Record<string, Block>` and does not define a semantic `binding` field yet. The architecture emphasizes determinism and mentions bindings conceptually, not as current schema fields. (`docs/architecture/EDITOR_BLOCK_ARCHITECTURE.md`, around lines 93-143 and deterministic notes).

`frontend-public/src/components/editor/types.ts` has document/schema/history/comment types, but no explicit semantic-binding payload model yet.

### A4 — Hypothetical multi-block document resolve pattern
For a doc with 7 bound blocks:
- 7 sequential single resolves: simplest but expensive and fragile over network latency.
- 1 bulk resolve: one request, preserves ordering, better for snapshot-atce workflows.
- Mixed UX: per-block resolve while editing + bulk resolve for "check updates".

Given roadmap §3.5 "check for updates" and status dots, doc-level refresh is core.

### A5 — "Check for updates" mechanic
Recommend using resolve endpoint(s) directly, not a separate "cube hash only" endpoint in 3.1c. Reason: stale check needs per-binding value+hash comparison eventually, and extra endpoint increases surface before evidence.

### A6 — Endpoint shape proposal
Recommend **Option γ (both)**:
- `GET /api/v1/admin/semantic/resolve?cube_id=X&semantic_key=Y`
- `POST /api/v1/admin/semantic/resolve` (bulk array)

Why:
- A1+A4+A5 show two distinct consumer patterns (single picker resolution vs batch check/update).
- Minimizes frontend round-trips for snapshot/check flows while preserving simple per-item ergonomics.

Tradeoff: larger API surface; acceptable due clear dual usage.

### A7 — `sourceHash` derivation
Recommend (ii) content-addressed hash of resolved tuple:
`sha256(cube_id|semantic_key|resolved_value|units|period|cache_fetched_at_iso)`.

Rationale:
- R19 determinism requires hash change only when effective resolved snapshot changes.
- Better stale-check ergonomics than pure timestamp hash.
- Works even without explicit cache `etag` column.

## §B — Service layer design

### B1 — New service or extend existing?
Recommend **new `SemanticResolveService`**.
- Keeps CRUD validation/upsert concerns in `SemanticMappingService`.
- Aligns with ARCH-DPEN-001 constructor DI.
- Avoids router/repo coupling anti-pattern.

### B2 — Method signatures
```python
async def resolve(*, cube_id: str, semantic_key: str) -> ResolvedSemantic
async def resolve_many(*, items: list[ResolveRef]) -> list[ResolvedSemantic]
```
Idempotent read-only. `resolve_many` preserves input order; non-atomic by default is acceptable if per-item envelopes supported, else fail-fast policy needs founder confirmation.

### B3 — `ResolvedSemantic` shape
Cache DTO fields available today: `cube_id`, `product_id`, `dimensions: dict`, `frequency_code`, titles, `fetched_at`. No `etag` field exists. Sources: `backend/src/services/statcan/metadata_cache.py` lines 44-55; `backend/src/models/cube_metadata_cache.py` lines 61-70.

Proposed:
```python
@dataclass(frozen=True)
class ResolvedSemantic:
    cube_id: str
    semantic_key: str
    value: str | int | float | Decimal
    units: str | None
    period: str | None
    resolved_at: datetime
    source_hash: str
    cache_fetched_at: datetime
    cache_is_stale: bool
```
Value exact type remains founder decision (see §F).

### B4 — Resolution algorithm
1) `SemanticMappingRepository.get_by_key(cube_id, semantic_key)`; 404 if missing.
2) If mapping inactive, default recommendation: 404 (`MAPPING_NOT_FOUND`) to keep inactive hidden.
3) Fetch cache by cube_id (`StatCanMetadataCacheService.get_cached`/repo lookup path). Cache miss => 404 `CUBE_NOT_IN_CACHE` (no auto-prime in resolve).
4) Apply mapping `config.dimension_filters` against cached `dimensions` using existing semantic validation-style matching strategy.
5) Derive resolved value tuple + `sourceHash`.
6) Return `ResolvedSemantic`.

### B5 — Inactive mappings
Recommendation: **404** (treat as not resolvable). 410 adds little value for admin-only API and leaks lifecycle semantics to consumers.

### B6 — Stale cache behavior
Recommend: resolve succeeds with `cache_is_stale=true` and optionally warning metadata.
- Blocking on stale would degrade operator flow and conflicts with roadmap "warn-and-confirm" mechanics.

## §C — Endpoint specs

### C1-C6 summary
- **Single**: `GET /api/v1/admin/semantic/resolve?cube_id&semantic_key`
  - 200 resolved payload
  - 401 auth
  - 404 mapping missing/inactive or cache miss
  - 422 bad params
- **Bulk**: `POST /api/v1/admin/semantic/resolve` body `{items:[{cube_id,semantic_key}]}`
  - 200 list result
  - 401/422/404 (policy for partials in §F)

Error envelope: DEBT-030 hybrid envelope reused.
New codes likely: `SEMANTIC_RESOLVE_NOT_FOUND`, `SEMANTIC_CACHE_MISS`, `SEMANTIC_DIMENSION_FILTER_MISMATCH`, `SEMANTIC_BULK_LIMIT_EXCEEDED`.

Auth: path-based AuthMiddleware reuse from 3.1b admin routes (`admin_semantic_mappings.py` prefix and middleware conventions).

If-Match: not applicable (read-only).

R15 cap: recommend bulk max=100 (default conservative; founder confirm 50 vs 100).

Caching headers: private short TTL + ETag on payload hash optional; defer strict policy to DEBT if not shipping in 3.1c.

## §D — Repository changes
- D1: `get_by_key` already exists and is reusable.
- D2: cube metadata cache service/repo already supports `get_by_cube_id` retrieval paths.
- D3: no new tables; read-only over existing `semantic_mappings` + `cube_metadata_cache`.

## §E — Test plan

### E1 Unit (10)
1) single happy path
2) mapping missing
3) mapping inactive
4) cache miss
5) stale cache success flag
6) dimension filter mismatch
7) sourceHash deterministic same input
8) sourceHash changes on value change
9) bulk happy path (ordered)
10) bulk over-cap

### E2 API (8)
1) GET 200
2) GET 401
3) GET 404 mapping
4) GET 404 cache
5) GET 422 params
6) POST bulk 200
7) POST bulk 422 invalid body
8) POST bulk 422 cap exceeded

### E3 Integration pattern
Mirror 3.1b endpoint fixture pattern (`test_semantic_mappings_endpoints.py` with Postgres testcontainer + alembic upgrade path).

### E4
No concurrency tests needed (read-only).

### E5
Backward compatibility: existing 3.1b CRUD tests unchanged.

## §F — Founder questions (Q-3.1c-N)

### Q-3.1c-1 — Endpoint shape
- Section: A6
- Question: γ (single+bulk) now vs α now + β later?
- Why: API surface vs immediate doc-refresh performance.
- Options: α minimal / β bulk-only / γ dual.
- Recon recommendation: γ.

### Q-3.1c-2 — sourceHash contract
- Section: A7
- Question: timestamp-based vs content-based hash?
- Why: stale detection semantics and R19 snapshot diffs.
- Recommendation: content-based tuple hash.

### Q-3.1c-3 — inactive mapping behavior
- Section: B5
- Question: 404 vs 410 vs resolve-with-flag?
- Recommendation: 404.

### Q-3.1c-4 — stale cache behavior
- Section: B6
- Question: fail resolve vs allow resolve with stale flag?
- Recommendation: allow + flag.

### Q-3.1c-5 — bulk partial failures
- Section: C1/E2
- Question: all-or-nothing 404 on any miss vs per-item statuses?
- Recommendation: per-item statuses in 200 response for operator ergonomics.

### Q-3.1c-6 — value type
- Section: B3
- Question: JSON number/string normalization rules?
- Recommendation: canonical string in API + optional numeric parse field.

## §G — Glossary additions
- **ResolvedSemantic**: resolved snapshot payload for one semantic key.
- **sourceHash**: deterministic hash of resolved tuple for stale detection.
- **stale binding**: snapshot hash differs from current resolve hash.
- **bulk resolve**: resolve many semantic refs in one request.

## §H — DEBT entries planned
Max DEBT observed: DEBT-057, so next IDs start at DEBT-058.

- **DEBT-058**: Add formal response caching strategy (`ETag`/`Cache-Control`) for semantic resolve endpoints.
- **DEBT-059**: Standardize bulk-partial-error envelope contract across admin endpoints.
- **DEBT-060**: Define canonical value typing for semantic resolve (`string` vs numeric union) and cross-client parsing contract.

(Use canonical 9-field schema in impl PR update to `DEBT.md`.)

## §I — Impl-phase blockers (Q-impl-N)
- Q-impl-1: exact algorithm to extract final resolved metric value from `dimensions` payload needs targeted fixture-driven inspection.
- Q-impl-2: current backend error-code registry files for semantic admin/public clients need exact insertion points during impl.
- Q-impl-3: precise `BACKEND_API_INVENTORY.md` table insertion location/style should be followed in impl commit.
