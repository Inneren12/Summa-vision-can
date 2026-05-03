# Phase 3.1c Recon — Semantic resolve endpoints (backend only)

## §A — Frontend consumer analysis

### A1 — Roadmap consumer audit (verbatim + derivations)
Verbatim source command:
```bash
sed -n '180,225p' docs/OPERATOR_AUTOMATION_ROADMAP.md
```

Verbatim excerpt:
```text
| 3.1 | Semantic Layer backend (Dimension → Category → Metric) | M | 3-4 | — |
| 3.2 | Hybrid binding frontend (Zustand snapshot state) | L | 4-5 | 3.1 |
| 3.3 | Binding status UI (subtle color dots, no heavy iconography) | S | 1 | 3.2 |
| 3.4 | Template Suggestion (silent prefill from `subject_code`) | S | 1 | 3.1 |
| 3.5 | Publish-time stale binding warn-and-confirm dialog | S | 1 | 3.2 |

Definition of done for Phase 3:
- Operator selects a cube, sees semantic picker ("Current rate", "YoY change", "Top 10 by X"), no Polars schema exposed
- Bound block stores `snapshotValue`, `resolvedAt`, source hash — rendering uses snapshot, never live read
- Status dots next to bound blocks: empty / gray (current) / yellow (stale) / red (broken schema)
- "Check for updates" action compares snapshot to live source, creates new R19 version on re-resolve
...

Explicit non-goals in Phase 3:
- No live-resolving bindings (violates R19 determinism)
- No bindings saved as standalone reusable slices — bindings stay coupled to their publication
- No confidence scores or AI-driven template suggestion — deterministic lookup only
```

Derivations from verbatim text:
- Picker flow implies per-binding resolution UX must exist (one semantic key at a time) and must not expose raw schema internals.
- Snapshot flow requires response fields that can be persisted into block snapshot state: `snapshotValue`, `resolvedAt`, `sourceHash`.
- Check-for-updates flow implies doc-level re-resolution over multiple bindings in one action; this strongly pressures either bulk endpoint or client fan-out.
- Non-goal “No live-resolving bindings” confirms cache-first deterministic snapshots, not runtime render-time fetch.

### A2 — Existing frontend code grep (verbatim)
Command 1:
```bash
rg -n "semantic|semanticKey|binding|resolve|snapshotValue|resolvedAt|sourceHash" frontend-public/src frontend/lib/features
```

Verbatim output:
```text
frontend/lib/features/data_preview/presentation/data_preview_screen.dart:152:          // - resolved == null  → no diff tracking (storage path has no
... [trimmed in-doc for readability; original run captured in terminal]
frontend-public/src/components/editor/types.ts:105:  resolved: boolean;
frontend-public/src/components/editor/types.ts:106:  resolvedAt: string | null;
frontend-public/src/components/editor/types.ts:107:  resolvedBy: string | null;
...
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:21:      '/api/v1/admin/semantic-mappings',
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:37:    final response = await _dio.get('/api/v1/admin/semantic-mappings/$id');
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:57:      '/api/v1/admin/semantic-mappings/upsert',
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:86:    final response = await _dio.delete('/api/v1/admin/semantic-mappings/$id');
```

Command 2:
```bash
rg -n "/admin/semantic|admin/semantic" frontend-public/src frontend/lib
```

Verbatim output:
```text
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:21:      '/api/v1/admin/semantic-mappings',
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:37:    final response = await _dio.get('/api/v1/admin/semantic-mappings/$id');
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:57:      '/api/v1/admin/semantic-mappings/upsert',
frontend/lib/features/semantic_mappings/repository/semantic_mappings_repository.dart:86:    final response = await _dio.delete('/api/v1/admin/semantic-mappings/$id');
```

Analysis:
- `frontend/lib/features/semantic_mappings/*` hits are expected 3.1b CRUD only.
- `frontend-public/src/components/editor/*` “resolved/resolvedAt” hits are comment-resolution fields, not semantic binding fields.
- No `snapshotValue` or `sourceHash` field appears in editor model path.
- No resolve endpoint client exists in either app currently.

Conclusion: resolve consumers are future Phase 3.2 editor binding state and doc-level update checker; no current client coupling constrains endpoint design.

### A3 — Editor block model audit (verbatim schema excerpts)
Commands:
```bash
sed -n '85,160p' docs/architecture/EDITOR_BLOCK_ARCHITECTURE.md
cat frontend-public/src/components/editor/types.ts
```

Verbatim architecture excerpt:
```typescript
interface PublicationDocument {
  schemaVersion: number;
  templateId: string;
  page: PageMeta;
  sections: Section[];
  blocks: Record<string, Block>;
  workflow: WorkflowState;
  meta: {
    history: HistoryEntry[];
    comments: Comment[];
    [k: string]: unknown;
  };
}
...
interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;
}
```

Verbatim editor types excerpt:
```typescript
export interface Block {
  id: string;
  type: string;
  props: BlockProps;
  visible: boolean;
  locked?: boolean;
}
...
export interface CanonicalDocument {
  schemaVersion: number;
  templateId: string;
  page: PageConfig;
  sections: Section[];
  blocks: Record<string, Block>;
  meta: DocMeta;
  review: Review;
}
```

Finding: today’s document/block schema has no semantic `binding`, `snapshotValue`, or `sourceHash` fields. Phase 3.2 must introduce additive binding payloads, and 3.1c resolve contract should already provide fields needed for those additions.

### A4 — Multi-block document pattern
Roadmap includes check-for-updates at publication scope, implying N-binding resolution pass in one user action. Empirical planning assumption: 7 bound blocks per doc is realistic for infographics with KPI + chart + supporting blocks.

### A5 — Check-for-updates mechanics
No separate cube-hash endpoint needed if resolve/bulk resolve returns deterministic `source_hash`; client compares stored snapshot hash vs newly resolved hash.

### A6 — Endpoint shape tradeoff matrix + recommendation
| Aspect | α (single only) | β (bulk only) | γ (both) |
|---|---|---|---|
| Per-binding picker UX | ✅ direct fit | ❌ awkward bulk-of-1 | ✅ |
| Doc snapshot ops (multi-block) | ❌ many round trips | ✅ one request | ✅ |
| API surface | smallest | small | largest |
| Test count | 6-8 | 8-10 | 12-16 |
| Caching semantics | simple per-item ETag | bulk ETag harder | mixed |
| Phase 3.2 client complexity | higher fan-out logic | higher single-as-bulk logic | lowest |

Recommendation: **γ (both)**, justified by A1 dual-flow roadmap quotes (picker and check-for-updates), A2 no existing client lock-in, and A4 multi-binding document flow.

### A7 — `sourceHash` derivation decision
Cache-shape evidence: cached row carries `cube_id`, `product_id`, `dimensions`, `frequency_code`, titles, `fetched_at`; no `etag`/version column.

Option analysis:
```python
# (i) time-anchored
sha256(f"{cube_id}|{semantic_key}|{cache_fetched_at.isoformat()}")

# (ii) content-addressed
sha256(f"{cube_id}|{semantic_key}|{value}|{units}|{period}")

# (iii) cache-version coupling
# unavailable: no cache etag/version column in cube_metadata_cache
```

Final: pick **(ii)** and **exclude fetched_at** to avoid false stale after cache refresh when value tuple unchanged.

## §B — Service layer design

### B1
Create new `SemanticResolveService` to keep 3.1b CRUD/validation service bounded.

### B2
Methods:
- `resolve(cube_id, semantic_key) -> ResolvedSemantic`
- `resolve_many(items) -> list[ResolvedSemanticResultItem]`

### B3 — `ResolvedSemantic.value` type decision (locked)
Evidence commands:
```bash
sed -n '40,80p' backend/src/services/statcan/metadata_cache.py
sed -n '55,90p' backend/src/models/cube_metadata_cache.py
rg -n "dimensions.*\=.*\{" backend/tests/services/statcan/ backend/src/services/semantic/seed/
```

Observed:
- Cache stores **dimension metadata catalog** (`dimensions` with names/members), not numeric measure datapoints.
- Fixture examples use `dimensions={"dimensions": []}`.

Decision: **`value: str`** (canonical string), because 3.1c cache payload does not currently expose typed numeric datapoints; any derived resolved value must be serialized deterministically for cross-client portability.

### B4 — Resolution algorithm (code-cited)
From validator (`backend/src/services/semantic_mappings/validation.py`):
- Name-based normalized matching (`_normalize_name`) across `dimension_filters` against cached `dimensions[].name_en` and `members[].name_en`.
- Output gives resolved `(dimension_position_id, member_id)` pairs.

Algorithm:
1. Load mapping by `(cube_id, semantic_key)` and ensure active.
2. Load cache row via `get_cached(cube_id)`.
3. Validate mapping filters against cache metadata using existing pure validator.
4. If validator errors: fail with semantic mismatch error.
5. **Critical:** cache row currently holds only dimension/member catalog; no scalar metric datapoint payload exists in shown schema. Therefore value extraction cannot be completed from current cache model alone.
6. To preserve founder lock (cache-first, no live resolve calls), 3.1c requires either:
   - extending cached payload to include resolvable datapoints, or
   - an upstream precomputed semantic value store keyed by mapping.

This is surfaced as phase-blocking founder question Q-3.1c-7.

### B5 inactive mapping
Return 404 (treat inactive as non-resolvable).

### B6 stale cache
Allow resolve with `cache_is_stale=true` flag; do not hard-fail.

## §C — Endpoint specs
- `GET /api/v1/admin/semantic/resolve?cube_id&semantic_key`
- `POST /api/v1/admin/semantic/resolve` with `{items:[...]}`
- Auth: admin `X-API-KEY` only.
- Envelope for bulk partial:
```json
{
  "items": [
    {"ok": true, "data": {...}},
    {"ok": false, "error": {"code": "SEMANTIC_CACHE_MISS", "message": "..."}}
  ]
}
```

## §D — Repository impact
Read-only usage of existing semantic mappings repository and cube metadata cache repository; no schema migration for 3.1c endpoint layer itself.

## §E — Tests
Unit + API tests for single/bulk, inactive, cache miss, mismatch, stale flag, deterministic hash, partial bulk envelope, cap enforcement.

## §F — Founder questions (tightened)
1. Q-3.1c-1 endpoint shape: approve γ based on A6 matrix?
2. Q-3.1c-2 sourceHash formula: approve content-addressed hash excluding fetched_at?
3. Q-3.1c-3 inactive behavior: 404 vs alternative?
4. Q-3.1c-4 stale cache behavior: allow with stale flag?
5. Q-3.1c-5 bulk partial envelope: per-item `{ok,data|error}` in 200?
6. Q-3.1c-7 **phase blocker**: cache catalog lacks datapoints; which cache-first path should be approved (extend cache payload vs precomputed store)?

(Q-3.1c-6 removed; value type decided as `str` in B3.)

## §G — Glossary
- ResolvedSemantic
- sourceHash
- snapshotValue
- stale binding
- cache-first resolve

## §H — DEBT entries (9-field canonical)
### DEBT-058: Formal response caching strategy for semantic resolve endpoints
- **Source:** Phase 3.1c recon §C
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** Resolve endpoints deterministic but no explicit cache headers.
- **Impact:** redundant DB reads and weaker client-side caching.
- **Resolution:** add `ETag` from `source_hash` + `Cache-Control` and 304 handling.
- **Target:** post-Phase 3.2 integration.

### DEBT-059: Bulk partial-error envelope standardization
- **Source:** Phase 3.1c recon §C/§F
- **Added:** 2026-05-03
- **Severity:** medium
- **Category:** api
- **Status:** accepted
- **Description:** Need cross-admin consistency for per-item success/failure format.
- **Impact:** divergent client handling patterns and brittle parsing.
- **Resolution:** formalize shared envelope contract and error schema.
- **Target:** with 3.1c implementation PR.

( DEBT-060 dropped because value type now decided in §B3. )

## §I — Impl blockers (concrete)
- Q-impl-1: inspect `BACKEND_API_INVENTORY.md` table format via targeted grep before insertion.
- Q-impl-2: inspect locale catalogs (`messages/en.json`, `messages/ru.json`) insertion points for new error keys.
- Q-impl-3: inspect fixture pattern in semantic endpoint tests (`test_semantic_mappings_endpoints.py`) to mirror shared fixture style.
- Q-impl-4: validate cache-datapoint strategy against real cached WDS payloads once founder picks Q-3.1c-7 direction.
