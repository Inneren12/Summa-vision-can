# Phase 3.1d — RECON (snapshot persistence + staleness comparison)

## 1) Locked decisions table

| ID | Decision | Source |
|---|---|---|
| **Q1** | **Snapshot storage:** separate table `publication_block_snapshot`. Inline option dead per §B2 #4 (validator strips unknown block.props keys via `sanitizeBlockProps`). | §F Q1 / §B2 #4 |
| **Q2** | **Snapshot key:** `UNIQUE(publication_id, block_id)`. Semantic context (cube_id, semantic_key, coord, period) stored on the row alongside the snapshot fingerprint. | §F Q2 |
| **Q3** | **Comparator model:** §J ComparatorResult adopted, with **7 reasons** (5 from §J + 2 new): `mapping_version_changed`, `source_hash_changed`, `value_changed`, `missing_state_changed`, `cache_row_stale`, **`compare_failed`**, **`snapshot_missing`**. | §F Q3 + Q3-followup |
| **Q3-severity** | Per-reason severity mapping: `compare_failed`='warning', `snapshot_missing`='info', drift reasons per §3.5 below. | Q3-followup |
| **Q4** | **v1 scope:** publish-time capture + explicit admin compare endpoint. NO automatic hydrate fanout, NO scheduler, NO public-side compare. | §F Q4 |
| **Q4-endpoint** | **`POST /api/v1/admin/publications/{id}/compare`** — action endpoint, runs fresh compute, returns ComparatorResult. NO GET endpoint in v1 (no result caching layer). | Q4-followup |
| **Q5** | **Behavior:** admin badge + explicit operator refresh flow. NO publish gate in v1. | §F Q5 |
| **Q6** | **Missing observation:** dedicated `missing_state_changed` reason, separate from `value_changed`. | §F Q6 |
| **Q7** | **Public stale:** backend-computed/admin-only by default in v1. Public flag is optional/future, NOT in 3.1d scope. | §F Q7 |
| **Q8** | **Backend service reuse:** direct `ResolveService` reuse via DI. NO HTTP self-call. | §F Q8 |
| **Clone** | **Clone has no snapshots until first publish.** Matches DEBT-026 `document_state=None` reset pattern. Operator sees `snapshot_missing` reason on cloned publication until they republish. | Q1+Q2-followup |

## 2) Storage contract (Q1, Q2, Clone)

### 2.1 Table schema for `publication_block_snapshot`

Required columns and constraints are locked exactly as ratified, plus two justified columns for ResolveService input fidelity (`dims_json`, `members_json`) per §4 decision (c).

- PK: `id`
- FK: `publication_id -> publications.id` with `ON DELETE CASCADE`
- Unique: `UNIQUE(publication_id, block_id)`
- Index: `ix_publication_block_snapshot_publication_id`
- Column order in migration: `id, publication_id, block_id, cube_id, semantic_key, coord, period, dims_json, members_json, mapping_version_at_publish, source_hash_at_publish, value_at_publish, missing_at_publish, is_stale_at_publish, captured_at, created_at, updated_at`

**Locked column types (P1-a, P1-d):**

| Column | Type | Constraints |
|---|---|---|
| `id` | `Integer` | PK autoincrement |
| `publication_id` | `Integer` | FK → `publications.id` ON DELETE CASCADE, NOT NULL |
| `block_id` | `String(128)` | NOT NULL — covers nanoid/uuid block id formats with headroom |
| `cube_id` | `String(50)` | NOT NULL — matches `semantic_value_cache.cube_id` |
| `semantic_key` | `String(200)` | NOT NULL — matches `semantic_mappings.semantic_key`. NOT 100. See DEBT-063. |
| `coord` | `String(40)` | NOT NULL — 10-slot canonical encoding |
| `period` | `String(20)` | nullable — null = "latest at capture time" |
| `dims_json` | `JSONB` | NOT NULL — list[int] with service invariants below |
| `members_json` | `JSONB` | NOT NULL — list[int] with service invariants below |
| `mapping_version_at_publish` | `Integer` | nullable |
| `source_hash_at_publish` | `String(64)` | NOT NULL |
| `value_at_publish` | `Text` | nullable — string per 3.1c canonical_str (no length cap для long Decimals) |
| `missing_at_publish` | `Boolean` | NOT NULL |
| `is_stale_at_publish` | `Boolean` | NOT NULL |
| `captured_at` | `DateTime(timezone=True)` | NOT NULL — publish action timestamp |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, server_default `now()` |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, onupdate `now()` |

**Service-level validation invariants (P1-d, enforced before upsert):**
- `len(dims_json) == len(members_json)` — empty arrays valid (block with no dim filters)
- All `dims_json` elements are integers in 1..10 range (matches 3.1c BLOCKERS-1 fix)
- All `members_json` elements are non-negative integers
- Order is preserved (positional pairing — dims_json[i] pairs with members_json[i])

Alembic naming convention: mirror existing phase pattern with next timestamped file under `backend/alembic/versions/` using slug format like `YYYYMMDD_HHMM_phase_3_1d_publication_block_snapshot.py`; upgrade creates table+constraints+index, downgrade drops index then table.

### 2.2 Clone semantics

Source read confirmed `clone_publication` exists and delegates clone row construction to repository `create_clone`. `create_clone` explicitly sets `document_state=None`, sets `status=DRAFT`, and does not set `published_at`, so `published_at` remains null on clone. Clone path does not write snapshot-like related tables today (only publication row + audit emission from endpoint layer).

Contract:
- cloned publication gets **no** `publication_block_snapshot` rows;
- first publish on clone performs first snapshot capture;
- comparator returns `stale_status="unknown"`, reason `snapshot_missing`, severity `info` until republish capture occurs.

**Verbatim verification (added per Part 3 P2 ask):** `clone_publication` confirmed via Appendix B grep G. Method body shows that clone delegates to `repo.create_clone(...)` (line 62 in clone.py) which:
- does NOT pass `published_at` argument → SQLAlchemy default (None) applies
- does NOT touch any related table (no snapshot, no audit — audit emission lives at endpoint layer)
- explicitly passes `fresh_review_json` with `workflow="draft"`, empty history, empty comments

Therefore §2.2 contract holds: cloned publication has `published_at=None`, no snapshot rows, fresh draft review. First publish on clone executes the standard publish-handler flow including snapshot capture per Part 1.

### 2.3 Backwards compatibility for pre-3.1d publications

Publications published before snapshot rollout have no snapshot rows. Comparator contract is `unknown + [snapshot_missing] + info`.

Operator path:
- badge copy: “Snapshot pre-dates 3.1d. Re-publish to capture.”
- compare endpoint is diagnostic/read-only and does not recapture.
- explicit refresh flow in Q5 maps to republish action (`POST /{publication_id}/publish`) in v1.

**Refresh flow lock (Q5, P1-e):** "Explicit refresh" in v1 maps to **republish via the existing `POST /{publication_id}/publish` endpoint**. NO dedicated "refresh snapshot without status transition" action in 3.1d. Operator workflow:
1. Operator sees stale badge in admin editor.
2. Operator triggers republish (existing UI action; body extended with `bound_blocks` per Part 1).
3. Publish handler captures fresh snapshots; subsequent compare returns FRESH.

A dedicated "recapture without state transition" action is DEFERRED — see DEBT-NN7 in §8.

## 3) API surface (Q4-endpoint, Q8)

### 3.1 Endpoint contract

- Path: `POST /api/v1/admin/publications/{id}/compare`
- Auth: existing API-key middleware
- Request body: none
- 200: `PublicationComparatorResponse`
- 404: `PUBLICATION_NOT_FOUND`
- 401: middleware
- No-compare-possible cases still return 200 with `overall_status=unknown` and typed reasons (`snapshot_missing`, `compare_failed`).

**Side-effect contract (locked, P1-b):** `POST /compare` is side-effect-free in v1 except for structured logs and metrics. The endpoint MUST NOT:
- Write to `publication_block_snapshot` (no recapture during compare)
- Mutate `publications.published_at` or any other field
- Trigger auto_prime on the value cache (resolve calls flow through 3.1c's normal cache-miss handling, which itself may auto-prime; compare adds no separate trigger)
- Emit AuditEvent rows (compare is diagnostic, not audit-worthy in v1)

Rationale: v1 has no result caching layer, so caching the compare result is not a side effect anyone needs. A future PR adding result caching MUST update this contract explicitly.

### 3.2 Service contract (direct `ResolveService` reuse)

`PublicationStalenessService` injected with direct `ResolveService` instance via DI. No internal HTTP calls.

`BoundBlockReference` contract for publish-time capture:
- `block_id: str`
- `cube_id: str`
- `semantic_key: str`
- `dims: list[int]`
- `members: list[int]`
- `period: str | None`

Invocation: called from existing publish handler after successful publish mutation, before response return.

Failure policy: best-effort capture; publish success is not rolled back on snapshot capture errors.

Bound block extraction verdict (HALT-cleared): existing publish handler currently accepts no body. Recon locks optional **wrapper-object** body extension on the publish endpoint:

```python
class PublicationPublishRequest(BaseModel):
    bound_blocks: list[BoundBlockReference] = Field(default_factory=list)
    # Reserved for future extension (capture_mode, idempotency_key, etc.)
    # All future fields must default to backward-compatible values.

@router.post("/{publication_id}/publish", ...)
async def publish_publication(
    publication_id: int,
    payload: PublicationPublishRequest | None = Body(default=None),
    repo: PublicationRepository = Depends(_get_repo),
    audit: AuditWriter = Depends(_get_audit),
    staleness: PublicationStalenessService = Depends(_get_staleness_service),
) -> PublicationResponse:
    ...
    bound_blocks = payload.bound_blocks if payload else []
```

**Backward compatibility contract (locked):**
- No body, null body, and `{}` body all parse as `payload=None` OR a request with empty `bound_blocks` list. All three paths produce zero snapshot rows; first compare returns `unknown + [snapshot_missing] + info`.
- A request with `{"bound_blocks": [...]}` parses correctly because the wrapper is a BaseModel (FastAPI auto-embeds object body fields without needing `embed=True`).
- Bare array body (`[...]`) is NOT accepted — there is no top-level array unwrapping.
- Future extension fields land on `PublicationPublishRequest`; existing `bound_blocks`-only clients keep working as long as new fields default.

### 3.3 Repository contract

`PublicationBlockSnapshotRepository` minimum methods:
- `upsert_for_block(...)`
- `get_for_publication(publication_id)`
- `delete_for_publication(publication_id)`

Upsert semantics locked: overwrite by `(publication_id, block_id)`, preserve `created_at`, bump `updated_at`, refresh all snapshot fields, set `captured_at` to publish action timestamp.

**`delete_for_publication` usage rule (locked, P1-c):**
- Used ONLY for hard-delete cleanup (FK CASCADE handles publication deletion automatically; this method exists for explicit testing scenarios + future cleanup workflows).
- NEVER called in normal publish flow. Normal publish capture is per-block upsert.
- Stale snapshot rows (block removed from publication's bindings) are LEFT AS ORPHANS in v1. Cleanup deferred — see DEBT-NN6 in §8.
- Tests that need to reset state between cases MAY call `delete_for_publication` directly.

**Upsert semantics (locked):** Same `(publication_id, block_id)` writes a fresh row; previous row is overwritten in place, `created_at` preserved, `updated_at` bumped, all `*_at_publish` fields refreshed, `captured_at` set to current publish action timestamp.

### 3.4 Response schema

Stale reasons:
- `mapping_version_changed`
- `source_hash_changed`
- `value_changed`
- `missing_state_changed`
- `cache_row_stale`
- `compare_failed`
- `snapshot_missing`

Statuses: `fresh`, `stale`, `unknown`

Severities: `info`, `warning`, `blocking`

**Locked Pydantic schema:**

```python
class StaleStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"

class StaleReason(str, Enum):
    MAPPING_VERSION_CHANGED = "mapping_version_changed"
    SOURCE_HASH_CHANGED = "source_hash_changed"
    VALUE_CHANGED = "value_changed"
    MISSING_STATE_CHANGED = "missing_state_changed"
    CACHE_ROW_STALE = "cache_row_stale"
    COMPARE_FAILED = "compare_failed"
    SNAPSHOT_MISSING = "snapshot_missing"

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"

class SnapshotFingerprint(BaseModel):
    mapping_version: int | None
    source_hash: str
    value: str | None
    missing: bool
    is_stale: bool
    captured_at: datetime

class ResolveFingerprint(BaseModel):
    mapping_version: int | None
    source_hash: str
    value: str | None
    missing: bool
    is_stale: bool
    resolved_at: datetime

class CompareKind(str, Enum):
    DRIFT_CHECK = "drift_check"
    SNAPSHOT_MISSING = "snapshot_missing"
    COMPARE_FAILED = "compare_failed"

class DriftCheckBasis(BaseModel):
    compare_kind: Literal[CompareKind.DRIFT_CHECK]
    matched_fields: list[str]
    drift_fields: list[str]

class SnapshotMissingBasis(BaseModel):
    compare_kind: Literal[CompareKind.SNAPSHOT_MISSING]
    cause: Literal["no_snapshot_row"]

class CompareFailedBasis(BaseModel):
    compare_kind: Literal[CompareKind.COMPARE_FAILED]
    resolve_error: Literal[
        "MAPPING_NOT_FOUND",
        "RESOLVE_CACHE_MISS",
        "RESOLVE_INVALID_FILTERS",
        "UNEXPECTED",
    ]
    details: dict  # {exception_type: str, message: str}

CompareBasis = Annotated[
    DriftCheckBasis | SnapshotMissingBasis | CompareFailedBasis,
    Field(discriminator="compare_kind"),
]

class BlockComparatorResult(BaseModel):
    block_id: str
    cube_id: str
    semantic_key: str
    stale_status: StaleStatus
    stale_reasons: list[StaleReason]
    severity: Severity
    compared_at: datetime
    snapshot: SnapshotFingerprint | None     # null when snapshot_missing
    current: ResolveFingerprint | None       # null when compare_failed pre-resolve
    compare_basis: CompareBasis              # discriminated union; FastAPI validates per variant

class PublicationComparatorResponse(BaseModel):
    publication_id: int
    overall_status: StaleStatus
    overall_severity: Severity
    compared_at: datetime
    block_results: list[BlockComparatorResult]
```

**`compare_basis` dict (BLOCKER-3 diagnostic surface):**

For each block result, `compare_basis` carries diagnostic detail in one of three forms:

```python
# 1. Compare ran successfully (stale_status = fresh OR stale):
compare_basis = {
    "compare_kind": "drift_check",
    "matched_fields": ["mapping_version", "source_hash"],   # fields that DIDN'T trigger reasons
    "drift_fields": ["value", "missing"],                   # fields that DID trigger reasons
}

# 2. No snapshot row exists (stale_status = unknown, reason = snapshot_missing):
compare_basis = {
    "compare_kind": "snapshot_missing",
    "cause": "no_snapshot_row",
    # No further detail — service can't distinguish pre-3.1d / clone /
    # omitted body / failed capture without expected-bindings persistence,
    # which is deferred per BLOCKER-2 Option C (DEBT-NN5).
}

# 3. Snapshot exists but resolve failed (stale_status = unknown, reason = compare_failed):
compare_basis = {
    "compare_kind": "compare_failed",
    "resolve_error": "MAPPING_NOT_FOUND" | "RESOLVE_CACHE_MISS" |
                     "RESOLVE_INVALID_FILTERS" | "UNEXPECTED",
    "details": {
        "exception_type": "<class name>",
        "message": "<sanitized>",
    },
}
```

**Aggregation rules (locked, BLOCKER-2 Option C):**
- `overall_status`: STALE if any block STALE; else UNKNOWN if any UNKNOWN; else FRESH.
- `overall_severity`: max(block severities); ordering: blocking > warning > info.
- **No-snapshot-rows case** (covers pre-3.1d publications, fresh clones, publish-without-bound_blocks, and all-blocks-capture-failed): comparator returns a single synthetic `BlockComparatorResult` with `block_id=""`, `cube_id=""`, `semantic_key=""`, `stale_status=UNKNOWN`, `stale_reasons=[SNAPSHOT_MISSING]`, `severity=INFO`, `snapshot=None`, `current=None`, `compare_basis=SnapshotMissingBasis(compare_kind="snapshot_missing", cause="no_snapshot_row")`. The aggregate then yields `overall_status=UNKNOWN`, `overall_severity=INFO`. Backend cannot distinguish the four sub-causes in v1; all collapse to the same synthetic entry. This unifies the contract: every published publication ALWAYS produces non-empty `block_results` with at least one entry carrying `stale_reasons`.

**This DROPS the prior zero-bindings-fresh rule.** Backend has no way to tell "intentionally zero bindings" from "missing captures" without persisted expected-bindings list. Frontend that needs a true zero-bindings signal must either:
(a) interpret empty `block_results` + status=UNKNOWN as "needs republish to capture," OR
(b) wait for future PR (DEBT-NN5) that persists expected-bindings list.

### 3.5 Severity mapping

| Reason | Severity |
|---|---|
| mapping_version_changed | info |
| source_hash_changed | info |
| value_changed | warning |
| missing_state_changed | warning |
| cache_row_stale | warning |
| compare_failed | warning |
| snapshot_missing | info |

## 4) Comparator algorithm (Q3, Q6, Q8)

Locked compare behavior:
1. Iterate snapshot rows for publication.
2. Re-resolve current value through direct `ResolveService` using snapshot identity.
3. On resolve exceptions (`MappingNotFound...`, cache miss, invalid filters, unexpected), emit `compare_failed`.
4. On success, evaluate drift reasons: mapping version, source hash, value, missing state, current is_stale.
5. Compute stale status + severity from reason set.
6. For expected bound blocks absent in snapshot table, emit `snapshot_missing` with `unknown/info`.

Value comparison for `value_changed` is byte-equal string compare (canonical-string contract).

Coord-vs-dims/members verdict: **Option (c) chosen** — store raw dims/members alongside coord to keep resolve call mechanical and avoid decode coupling.

## 5) Capture flow (Q4 publish-time)

### 5.1 Invocation point

Publish endpoint (`publish_publication`) sets published status/timestamp via repository, then staleness capture executes best-effort prior to returning response.

### 5.2 Bound block extraction

Decision: explicit list at publish time via optional request body extension.

If `bound_blocks` omitted, publish remains successful and no snapshots are written; later compare surfaces `snapshot_missing`.

Frontend integration: required companion change for functional rollout; without it, 3.1d behaves diagnostically as unknown/missing.

### 5.3 Capture algorithm

For each bound block, call `ResolveService.resolve_value(...)`, then upsert snapshot row with resolve fingerprint and `captured_at`. Resolve failures are logged and skipped per-block.

## 6) Test plan

### 6.1 Unit tests
All listed unit cases from the ratified plan are required, including reason detection, severity aggregation, compare_failed handling, and byte-equal value normalization.

### 6.2 Repository tests
Required: upsert overwrite semantics, list retrieval behavior, FK cascade, unique constraint enforcement.

### 6.3 Integration tests
Required endpoint tests: 404, fresh/stale paths, pre-3.1d missing snapshots, clone missing snapshots, capture-failure non-blocking publish, severity aggregation, auth enforcement.

### 6.4 Pipeline test

Required end-to-end: `test_publish_then_compare_full_pipeline`. Executes:
1. Seed `semantic_mappings` row + `semantic_value_cache` row in test DB (no external StatCan calls).
2. POST publish with `{"bound_blocks": [...]}` body via httpx + AsyncClient.
3. Assert publish 200, publication has captured snapshot rows.
4. POST compare via httpx; assert response shape, status=fresh.
5. Mutate cache row in DB (simulate value drift).
6. POST compare again; assert status=stale, reasons include `value_changed`.

**Scope clarification (P1-f):** "real DB-backed resolve path" means `ResolveService.resolve_value` is invoked through the live DI graph against seeded DB rows. NO mocking of `ResolveService`. NO external network — `auto_prime` is not exercised because seeded cache rows are present (cache-hit path). If the test triggers `auto_prime` (cache-miss path), the test is structurally wrong — re-seed.

This avoids flakiness from external StatCan dependencies while still proving the pipeline isn't dead-mapper-style broken.

## 7) Drift detection touch list

Required in impl PR:
- `docs/api.md`
- `docs/architecture/BACKEND_API_INVENTORY.md`
- `docs/architecture/ROADMAP_DEPENDENCIES.md`
- `docs/architecture/ARCHITECTURE_INVARIANTS.md`

Optional/follow-up after frontend integration:
- `docs/architecture/FRONTEND_AUTOSAVE_ARCHITECTURE.md`
- `docs/architecture/FLUTTER_ADMIN_MAP.md`
- `docs/architecture/_DRIFT_DETECTION_TEMPLATE.md`
- `docs/architecture/AGENT_WORKFLOW.md`
- `docs/architecture/TEST_INFRASTRUCTURE.md`
- `docs/architecture/DEPLOYMENT_OPERATIONS.md`

## 8) DEBT entries to file

**Canonical DEBT register path: `DEBT.md` at repo root** (NOT `docs/architecture/DEBT.md`). Pre-flight grep A confirmed: `docs/architecture/DEBT.md` does not exist; `DEBT.md` exists at repo root with the canonical 9-field schema (Source/Added/Severity/Category/Status/Description/Impact/Resolution/Target) per memory rule #21.

Next free DEBT-NN per pre-flight grep E: **DEBT-045** (impl-time agent fills in from grep output).

**7 entries to file in `DEBT.md`:**

**DEBT-NN1: 3.1d-deferred automatic hydrate fanout**
- Source: Phase 3.1d recon §F Q4
- Added: <YYYY-MM-DD>
- Severity: low | Category: architecture | Status: active
- Description: 3.1d v1 ships explicit-action compare only; no automatic compare on document hydrate.
- Impact: stale data may go undetected if operator doesn't compare before re-publishing.
- Resolution: add hydrate-time compare in admin editor.
- Target: Phase 3.2 frontend hardening or operator-feedback driven.

**DEBT-NN2: 3.1d-deferred scheduled background compare**
- Source: Phase 3.1d recon §F Q4
- Added: <YYYY-MM-DD>
- Severity: low | Category: architecture | Status: active
- Description: No periodic backend job comparing all published publications.
- Impact: large catalog can drift without operator notice.
- Resolution: APScheduler job mirroring 3.1aaa pattern, populating cached `staleness_status` on Publication.
- Target: Phase 3.2 or after >50 publications shipped.

**DEBT-NN3: 3.1d-deferred public stale display**
- Source: Phase 3.1d recon §F Q7
- Added: <YYYY-MM-DD>
- Severity: low | Category: architecture | Status: active
- Description: Public viewer doesn't show stale state. v1 lock per Q7.
- Impact: public viewers may render outdated values without indication.
- Resolution: extend `PublicationPublicResponse` with backend-computed flag (depends on DEBT-NN2).
- Target: Phase 3.2 frontend hardening, after DEBT-NN2 lands.

**DEBT-NN4: 3.1d-followup coord-vs-dim/member storage**
- Source: Phase 3.1d recon §4 option (c)
- Added: <YYYY-MM-DD>
- Severity: low | Category: architecture | Status: active
- Description: §4 option (c) stores raw dims/members alongside coord, doubling identity context storage.
- Impact: ~2 extra columns per snapshot row; minor storage overhead.
- Resolution: when ResolveService gains a coord-direct entrypoint, drop redundant columns.
- Target: opportunistic, low priority.

**DEBT-NN5: 3.1d-followup expected-bindings persistence**
- Source: Phase 3.1d recon BLOCKER-2 Option C (Part 1b)
- Added: <YYYY-MM-DD>
- Severity: medium | Category: architecture | Status: active
- Description: BLOCKER-2 Option C drop. Backend cannot distinguish "publication has 0 bindings" from "publication has bindings but capture failed/omitted." All collapse to synthetic `block_results` entry with `snapshot_missing + info`.
- Impact: operator sees ambiguous badge for genuinely-empty publications. Edge case.
- Resolution: persist expected-bindings list either in new `publication_bound_block_reference` table OR JSONB column on `publications`. Compare endpoint reads both expected list and actual snapshot table; difference yields true `snapshot_missing`.
- Target: when operator reports confusion OR when frontend ships zero-bindings publication type.

**DEBT-NN6: 3.1d-followup orphan snapshot cleanup**
- Source: Phase 3.1d recon §3.3 P1-c (Part 2)
- Added: <YYYY-MM-DD>
- Severity: low | Category: code-quality | Status: active
- Description: Block removed from publication's bindings leaves orphaned `publication_block_snapshot` row. v1 doesn't clean these up.
- Impact: minor storage growth, no behavioral effect (compare iterates only what's there).
- Resolution: cleanup pass on republish — compare current bound_blocks against existing snapshot rows, delete rows for removed blocks.
- Target: opportunistic, low priority.

**DEBT-NN7: 3.1d-followup dedicated refresh-snapshot action**
- Source: Phase 3.1d recon §2.3 P1-e (Part 2)
- Added: <YYYY-MM-DD>
- Severity: low | Category: architecture | Status: active
- Description: v1 conflates "refresh snapshot" with "republish" — operator can only refresh by triggering full republish action.
- Impact: operator must re-confirm publish workflow even if only data refresh is wanted; minor UX friction.
- Resolution: new `POST /{publication_id}/recapture-snapshots` endpoint that runs capture flow without state transition.
- Target: Phase 3.2 or operator-feedback-driven.

## 9) Risk inventory

1. Capture-time partial failure (medium, Q4) — mitigated via per-block missing diagnostics.
2. Publish/compare race (low, Q4-endpoint) — accepted transient inconsistency window.
3. Mapping deletion post-publish (medium, §4) — surfaced as `compare_failed`.
4. Coord encoding drift (low with option c) — mitigated by persisted dims/members.
5. Pre-3.1d operator confusion (medium, Q5) — explicit badge copy.
6. Frontend extension friction (high, §5.2) — frontend publish body extension required milestone.
7. Clone block-id stability uncertainty (medium-high, Q1+Q2) — clone resets `document_state=None`; no snapshot carryover avoids cross-publication key reuse coupling.

## 10) Migration order + implementation phasing

1. Alembic migration.
2. ORM model.
3. Snapshot repository.
4. Staleness service.
5. Staleness schemas.
6. Admin publications compare route.
7. Publish handler optional body + capture hook.
8. Tests (unit → repo → integration → pipeline).
9. Drift docs.
10. DEBT updates.

## 11) Pre-flight greps verification

Pre-flight checks completed; verbatim outputs are captured in Appendix B.

### Appendix B — Verbatim command outputs

```bash
grep -n "async def clone_publication\|def clone_publication" backend/src/services/publications/clone.py
26:async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
```

```bash
grep -n "def publish_publication\|/{id}/publish\|async def publish" backend/src/api/routers/admin_publications.py
510:async def publish_publication(
```

```bash
grep -n "publish.*body\|PublicationPublishRequest\|publish.*Body(" backend/src/api/routers/admin_publications.py backend/src/schemas/publication.py
```

```bash
grep -nE "^### DEBT-[0-9]+" docs/architecture/DEBT.md | tail -5
grep: docs/architecture/DEBT.md: No such file or directory
```

```bash
grep -nE "ForeignKey.*publications.id|on_delete.*CASCADE" backend/src/models/* | head -10
backend/src/models/publication.py:91:        ForeignKey("publications.id", ondelete="SET NULL"),
```

```bash
grep -n "Body(default=None)\|Body(\.\.\..*default" backend/src/api/routers/* | head -10
```

```bash
nl -ba backend/src/services/publications/clone.py | sed -n '1,220p'
     1	"""Clone use-case for Publication."""
     2	from __future__ import annotations
     3	
     4	import json
     5	
     6	from sqlalchemy.exc import IntegrityError
     7	from sqlalchemy.ext.asyncio import AsyncSession
     8	
     9	from src.models.publication import Publication, PublicationStatus
    10	from src.repositories.publication_repository import PublicationRepository
    11	from src.services.publications.exceptions import (
    12	    PublicationCloneNotAllowedError,
    13	    PublicationNotFoundError,
    14	)
    15	from src.services.publications.lineage import (
    16	    compute_config_hash,
    17	    derive_clone_lineage_key,
    18	    derive_size_from_visual_config,
    19	)
    20	
    21	_COPY_PREFIX = "Copy of "
    22	_HASH_SLICE = 16
    23	_MAX_CLONE_VERSION_RETRIES = 3
    24	
    25	
    26	async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
    27	    """Clone a published publication into a new draft."""
    28	    repo = PublicationRepository(session)
    29	
    30	    source = await repo.get_by_id(source_id)
    31	    if source is None:
    32	        raise PublicationNotFoundError()
    33	
    34	    if source.status != PublicationStatus.PUBLISHED:
    35	        status_val = source.status.value if hasattr(source.status, "value") else str(source.status)
    36	        raise PublicationCloneNotAllowedError(
    37	            publication_id=source_id,
    38	            current_status=status_val,
    39	        )
    40	
    41	    new_headline = source.headline if source.headline.startswith(_COPY_PREFIX) else f"{_COPY_PREFIX}{source.headline}"
    42	
    43	    size = derive_size_from_visual_config(source.visual_config)
    44	    new_config_hash = compute_config_hash(
    45	        chart_type=source.chart_type,
    46	        size=size,
    47	        title=new_headline,
    48	    )[:_HASH_SLICE]
    49	
    50	    fresh_review_json = json.dumps(
    51	        {"workflow": "draft", "history": [], "comments": []},
    52	    )
    53	
    54	    last_exc: IntegrityError | None = None
    55	    for attempt in range(_MAX_CLONE_VERSION_RETRIES):
    56	        if source.source_product_id is None:
    57	            new_version = 1
    58	        else:
    59	            latest = await repo.get_latest_version(source.source_product_id, new_config_hash)
    60	            new_version = (latest or 0) + 1
    61	        try:
    62	            clone = await repo.create_clone(
    63	                source=source,
    64	                new_headline=new_headline,
    65	                new_config_hash=new_config_hash,
    66	                new_version=new_version,
    67	                fresh_review_json=fresh_review_json,
    68	                lineage_key=derive_clone_lineage_key(source),
    69	            )
    70	            await session.commit()
    71	            return clone
    72	        except IntegrityError as exc:
    73	            await session.rollback()
    74	            last_exc = exc
    75	            if attempt == _MAX_CLONE_VERSION_RETRIES - 1:
    76	                raise
    77	            continue
    78	
    79	    assert last_exc is not None
    80	    raise last_exc
```

```bash
nl -ba backend/src/api/routers/admin_publications.py | sed -n '470,620p'
   470	    # value-change predicate so a PATCH that keeps ``workflow="published"``
   471	    # does not re-emit.
   472	    if new_workflow == "published" and new_workflow != previous_workflow:
   473	        await audit.log_event(
   474	            event_type=EventType.PUBLICATION_PUBLISHED,
   475	            entity_type="publication",
   476	            entity_id=str(publication.id),
   477	            metadata={
   478	                "from": previous_workflow,
   479	                "to": new_workflow,
   480	                "source": "patch_review",
   481	            },
   482	            actor="admin_api",
   483	        )
   484	
   485	    logger.info(
   486	        "publication_updated",
   487	        publication_id=publication.id,
   488	        fields=list(payload.keys()),
   489	        previous_workflow=previous_workflow,
   490	        new_workflow=new_workflow,
   491	    )
   492	    response.headers["ETag"] = compute_etag(publication)
   493	    return _serialize(publication)
   494	
   495	
   496	# ---------------------------------------------------------------------------
   497	# POST /api/v1/admin/publications/{publication_id}/publish
   498	# ---------------------------------------------------------------------------
   499	
   500	
   501	@router.post(
   502	    "/{publication_id}/publish",
   503	    response_model=PublicationResponse,
   504	    status_code=status.HTTP_200_OK,
   505	    summary="Publish a draft publication",
   506	    responses={
   507	        404: {"description": "Publication not found."},
   508	    },
   509	)
   510	async def publish_publication(
   511	    publication_id: int,
   512	    repo: PublicationRepository = Depends(_get_repo),
   513	    audit: AuditWriter = Depends(_get_audit),
   514	) -> PublicationResponse:
   515	    """Set status to PUBLISHED, stamp ``published_at``, and audit.
   516	
   517	    If the row already carries a ``review`` payload the endpoint also
   518	    mirrors ``review.workflow = "published"`` and appends a history
   519	    entry authored as ``"system"`` so the frontend can render the
   520	    transition in its timeline. Rows without a ``review`` payload are
   521	    published by status alone (no review sync is attempted).
   522	    """
   523	    publication = await repo.publish(publication_id)
   524	    if publication is None:
   525	        raise PublicationNotFoundError()
   526	
   527	    # Mirror into review.workflow when a review payload exists. We
   528	    # cannot know the ``fromWorkflow`` safely from the backend (no
   529	    # atomic snapshot), so leave it ``None`` — the frontend shape
   530	    # allows a null ``fromWorkflow`` for system-emitted entries.
   531	    publication = await _sync_workflow_from_status(
   532	        repo, publication, target_workflow="published",
   533	        summary="Published via admin endpoint",
   534	    )
   535	
   536	    await audit.log_event(
   537	        event_type=EventType.PUBLICATION_PUBLISHED,
   538	        entity_type="publication",
   539	        entity_id=str(publication.id),
   540	        metadata={"headline": publication.headline},
   541	        actor="admin_api",
   542	    )
   543	    logger.info("publication_published", publication_id=publication.id)
   544	    return _serialize(publication)
   545	
   546	
   547	# ---------------------------------------------------------------------------
   548	# POST /api/v1/admin/publications/{publication_id}/unpublish
   549	# ---------------------------------------------------------------------------
   550	
   551	
   552	@router.post(
   553	    "/{publication_id}/unpublish",
   554	    response_model=PublicationResponse,
   555	    status_code=status.HTTP_200_OK,
   556	    summary="Unpublish a publication (revert to DRAFT)",
   557	    responses={
   558	        404: {"description": "Publication not found."},
   559	    },
   560	)
   561	async def unpublish_publication(
   562	    publication_id: int,
   563	    repo: PublicationRepository = Depends(_get_repo),
   564	    audit: AuditWriter = Depends(_get_audit),
   565	) -> PublicationResponse:
   566	    """Revert the publication to DRAFT status and record an audit event.
   567	
   568	    The audit trail must be symmetric with :func:`publish_publication` —
   569	    there is currently no dedicated ``PUBLICATION_UNPUBLISHED`` member in
   570	    :class:`EventType`, so we reuse :attr:`EventType.PUBLICATION_PUBLISHED`
   571	    and distinguish the reversal via ``metadata.action = "unpublish"``
   572	    (with ``new_status`` for dashboard filtering).
   573	    """
   574	    publication = await repo.unpublish(publication_id)
   575	    if publication is None:
   576	        raise PublicationNotFoundError()
   577	
   578	    publication = await _sync_workflow_from_status(
   579	        repo, publication, target_workflow="draft",
   580	        summary="Unpublished via admin endpoint; returned to draft",
   581	    )
   582	
   583	    await audit.log_event(
   584	        event_type=EventType.PUBLICATION_PUBLISHED,
   585	        entity_type="publication",
   586	        entity_id=str(publication.id),
   587	        metadata={
   588	            "action": "unpublish",
   589	            "new_status": "DRAFT",
   590	            "headline": publication.headline,
   591	        },
   592	        actor="admin_api",
   593	    )
   594	    logger.info("publication_unpublished", publication_id=publication.id)
   595	    return _serialize(publication)
   596	
   597	
   598	@router.post(
   599	    "/{publication_id}/clone",
   600	    response_model=PublicationResponse,
   601	    status_code=status.HTTP_201_CREATED,
   602	    summary="Clone a published publication into a new draft",
   603	    responses={
   604	        404: {"description": "Publication not found."},
   605	        409: {"description": "Publication is not published and cannot be cloned."},
   606	    },
   607	)
   608	async def clone_publication_endpoint(
   609	    publication_id: int,
   610	    response: Response,
   611	    session: AsyncSession = Depends(get_db),
   612	) -> PublicationResponse:
   613	    """Clone a published publication into a new draft.
   614	
   615	    Sets ``ETag`` response header on the clone so the editor can use it as
   616	    the seed ``If-Match`` for the first PATCH (Phase 1.3 fork-path).
   617	    """
   618	    try:
   619	        clone = await clone_publication(session=session, source_id=publication_id)
   620	    except (PublicationNotFoundError, PublicationCloneNotAllowedError) as exc:
```

```bash
# Part 3 additions — DEBT path + create_clone evidence

ls -la DEBT.md docs/architecture/DEBT.md 2>&1
ls: cannot access 'docs/architecture/DEBT.md': No such file or directory
-rw-r--r-- 1 root root 57932 May  3 17:31 DEBT.md

grep -nE "^### DEBT-[0-9]+|^## DEBT-[0-9]+|^- \*\*DEBT-[0-9]+|^DEBT-[0-9]+:" DEBT.md | tail -10
571:### DEBT-060: ResolvedValue.units lacks a canonical mapping source
626:### DEBT-026: Lossy round-trip between CanonicalDocument and AdminPublicationResponse
640:### DEBT-021: Temp upload Parquet files not cleaned up
693:### DEBT-035: Parallel config_hash computation in pipeline + lineage helper
705:### DEBT-036: Verify crop zone dimensions against current platform layouts
717:### DEBT-040: Phase 2.5b — three deferred Exception Inbox row types
729:### DEBT-041: PATCH publications has no idempotency-key short-circuit
741:### DEBT-042: PATCH publications tolerates missing If-Match for v1 deploy compat
753:### DEBT-043: PATCH publications has narrow TOCTOU window between ETag check and UPDATE
766:### DEBT-044: Phase 1.6 — multi-block selection + bulk context-menu actions

grep -nE "Source:|Added:|Severity:|Category:|Status:|Description:|Impact:|Resolution:|Target:" DEBT.md | head -20
38:- **Source:** Phase 3 Slice 3.7 recon (`docs/phase-3-slice-7-recon.md` §4 Decision 4)
39:- **Added:** 2026-04-24
40:- **Severity:** low
41:- **Category:** code-quality
42:- **Status:** accepted
43:- **Description:** Two parallel generation notifier stacks exist:
47:- **Impact:** Minor code duplication in 3.8 impl (2 switch statements, 5-7 lines each). No runtime issue, no user-facing bug.
48:- **Resolution:** Refactor to a single shared `GenerationPhase` enum used by both notifier stacks. Update all consumers. Delete the duplicate.
49:- **Target:** Opportunistic — during a future graphics refactor or when the chart config flow is re-architected for backend Phase 2 integration.
59:- **Source:** Phase 3 Slice 3.11 Consolidation recon
60:- **Added:** 2026-04-24
61:- **Severity:** low
62:- **Category:** code-quality
63:- **Status:** resolved
64:- **Description:** Four existing locale-switch smoke tests (queue, editor,
73:- **Impact:** Minor maintenance overhead; tests remain green; no runtime
76:- **Resolution:** Refactor all locale-switch smokes to share a common
80:- **Target:** Opportunistic during future test infrastructure work or
88:- **Source:** Phase 3 Slice 3.3+3.4 recon (`docs/phase-3-slice-3-recon.md` §6)
89:- **Added:** 2026-04-23

grep -n "def create_clone" backend/src/repositories/publication_repository.py
193:    async def create_clone(

sed -n '193,245p' backend/src/repositories/publication_repository.py
    async def create_clone(
        self,
        *,
        source: Publication,
        new_headline: str,
        new_config_hash: str,
        new_version: int,
        fresh_review_json: str,
        lineage_key: str,
    ) -> Publication:
        """Create a draft clone of a published publication.

        Args:
            source: The published publication to clone from.
            new_headline: Headline for the new clone.
            new_config_hash: Config hash for the new clone version.
            new_version: Version number for the new clone.
            fresh_review_json: JSON-serialised fresh review subtree.
            lineage_key: UUID v7 lineage identifier; caller computes via
                ``derive_clone_lineage_key(source)`` to inherit the
                source's lineage_key (clones share with source).
        """
        existing_slugs = await self._get_existing_slugs()
        clone_slug = derive_clone_slug(new_headline, existing_slugs=existing_slugs)
        clone = Publication(
            headline=new_headline,
            chart_type=source.chart_type,
            slug=clone_slug,
            eyebrow=source.eyebrow,
            description=source.description,
            source_text=source.source_text,
            footnote=source.footnote,
            visual_config=source.visual_config,
            # document_state intentionally NOT copied — see Phase 1.1 Fix Round 1.
            # Frontend hydrates from document_state first (DEBT-026), and the
            # source's embedded review.workflow="published" would cause autosave
            # to re-publish the clone. Setting None forces frontend hydration
            # fallback to backend columns (status=DRAFT, fresh review).
            document_state=None,
            review=fresh_review_json,
            source_product_id=source.source_product_id,
            config_hash=new_config_hash,
            version=new_version,
            status=PublicationStatus.DRAFT,
            cloned_from_publication_id=source.id,
            lineage_key=lineage_key,
        )
        self._session.add(clone)
        await self._session.flush()
        await self._session.refresh(clone)
        return clone
```
