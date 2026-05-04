# Architecture Invariants

**Status:** Living document — invariants are added when an architectural decision is made; modified only after explicit founder review
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Sources:** ARCH_RULES.md, DEBT.md, memory items aggregated from Phase 1.1, 1.4, 1.5, DEBT-030, Slice 3.8

**Maintenance rule:** an invariant in this file is a **contract**. Changing it requires:
1. Founder explicit approval in chat
2. Update DEBT.md with the change rationale
3. Update this file in the same commit as the code change
4. Audit downstream consumers (every PR / module that depends on the changed invariant)

If an impl prompt would violate an invariant, the prompt MUST flag it and either pre-approve the violation in §J of recon, or update this MD as part of the same PR.

## How to use this file

- §2 — Architectural rules (ARCH-* and R*)
- §3 — Error envelope contract (DEBT-030)
- §4 — Versioning rules (R19)
- §5 — Idempotency state (R16)
- §6 — Token / auth boundaries (R17)
- §7 — Etag derivation contract (placeholder until Phase 1.3 lands; updated in 1.3 impl PR)
- §8 — Other invariants

When recon-proper or impl prompts touch any of these, cite the section number for traceability.

## 2. Architectural rules (ARCH-* and R*)

### ARCH-PURA-001 — Pure functions

Hashing, data transformation, and any function with no side effects MUST be implemented as pure functions: deterministic given inputs, no DB calls, no clock reads, no global state.

**Applied in:**
- ETag derivation (Phase 1.3) — pure function over publication fields
- `config_hash` computation — pure over visual_config JSON
- Any new aggregation function — must be pure

**Common violations to watch for:**
- Hash function calling `datetime.utcnow()` instead of accepting timestamp argument
- Function pulling data from a global `Settings` object instead of receiving it as argument

### ARCH-DPEN-001 — Constructor dependency injection

No global state. Dependencies passed via constructor, not imported at module level.

**Applied in:** repositories, service classes, any class with collaborators.

**Common violations to watch for:**
- `from app.core.db import async_session` at module top, used inside class methods → use constructor `__init__(self, session_factory)` instead
- Job handlers creating httpx clients inline (DEBT-017 — known violation, tracked for refactor)

### ARCH-CACHED-ONLY-RESOLVE-001 — Compare path uses cached-only resolve

The Phase 3.1d staleness compare endpoint (`POST /api/v1/admin/publications/{id}/compare`)
MUST invoke `ResolveService.resolve_value` with `allow_auto_prime=False`. This
guarantees the compare operation is strictly side-effect-free at the storage
layer: a cache miss surfaces as `compare_failed(resolve_error="RESOLVE_CACHE_MISS")`
instead of triggering the auto-prime + re-query workflow that the interactive
resolve endpoint uses.

The capture path (publish-time, `PublicationStalenessService.capture_for_publication`)
uses default `allow_auto_prime=True` per recon §5.3 — capture intentionally
seeds the cache so subsequent compares have a reference point to drift against.

**Enforced by:**
- `PublicationStalenessService._compare_one_snapshot` (passes `allow_auto_prime=False`)
- `ResolveService.resolve_value` short-circuit (raises `ResolveCacheMissError` before step 5 when `allow_auto_prime=False`)
- `backend/tests/api/test_publication_compare.py::test_compare_returns_fresh_when_snapshot_matches_current_cache` (asserts `fake.calls[0]["allow_auto_prime"] is False`)
- `backend/tests/api/test_publication_compare.py::test_compare_returns_compare_failed_when_cache_row_missing`
- `backend/tests/api/test_publish_then_compare_pipeline.py::test_publish_then_compare_full_pipeline` (real ResolveService composition; asserts cache-hit path produces `fresh` then `value_changed` after upstream drift)

### R6 — Short-lived DB sessions

Request-scoped DB sessions live only for the duration of a single request. Background tasks MUST NOT hold a session across long-running operations.

**Anti-pattern:** opening a session in request handler, passing the session to a background task that runs longer than the request → session timeout / connection leak.

**Correct pattern:** background task opens its own short-lived session for each unit of work.

**Memory item:** request-scoped DB sessions must not be used in background tasks (recurring agent failure).

### R15 — Hard caps on result sizes

No unbounded queries. Every list endpoint MUST have a default `limit` (e.g. 100) and a maximum cap (e.g. 1000). Pagination via cursor or offset.

### R16 — Idempotent retry

(See §5 below for current state and DEBT-tracked gaps.)

### R17 — Token flow security

Tokens (auth, ETag, idempotency keys) MUST be tied to the resource they protect, not to the requesting session.

**Applied in:**
- ETag is tied to publication ID, not session — same publication has same ETag for any user
- Magic link tokens tied to publication, with user binding via separate session

### R19 — Publication versioning

(See §4 below.)

### No pandas in Polars-path files

Files in `backend/app/services/data_processing/` (and other Polars-path modules) MUST NOT import `pandas`. Polars is the canonical dataframe engine.

**Memory item:** "no pandas in Polars-path files."

### AsyncMock for all async test mocks

`MagicMock` for async returns silently produces unawaited-coroutine warnings. Use `AsyncMock` always.

## 3. Error envelope contract (DEBT-030)

**Source:** DEBT-030 PR1+hotfix+PR2 merged 2026-04-26.

### Canonical shape

```json
{
  "detail": {
    "error_code": "<UPPERCASE_SNAKE>",
    "message": "<human-readable>",
    "details": { "<key>": "<value>", ... }
  }
}
```

### When this envelope applies

- Custom exception handlers returning structured errors (PATCH publications validation, future PreconditionFailed, future Conflict)
- Auth-side endpoints currently use a flat envelope; unification tracked in DEBT-034 (future work)

### error_code naming

- ALL CAPS UPPERCASE_SNAKE
- Domain-specific names preferred over HTTP-status names where the HTTP status is generic (e.g. `STALE_VERSION` over `PRECONDITION_FAILED` if the former is more specific to the domain)
- Decided in Phase 1.3: `PRECONDITION_FAILED` chosen for ETag mismatch — matches HTTP semantic exactly

### Frontend coupling

- `BackendApiError` class in `frontend-public/src/lib/admin.ts` carries `errorCode`, `details`, `message`
- `KNOWN_BACKEND_ERROR_CODES` array in same file — adding a new code requires update here AND i18n entries
- Detection: code-first (response body's `detail.error_code` read first; HTTP status as backstop)
- i18n namespacing (Option C hybrid): domain keys `publication.*`, cross-cutting backend errors `errors.backend.<code_lowercase>`

### Critical handler implementation rule

**Every custom JSON-returning exception handler MUST wrap response body via `fastapi.encoders.jsonable_encoder`** before `JSONResponse(...)`.

```python
from fastapi.encoders import jsonable_encoder

return JSONResponse(
    status_code=<status>,
    content=jsonable_encoder({
        "detail": {
            "error_code": "...",
            "message": "...",
            "details": {...},
        }
    }),
)
```

Without `jsonable_encoder`, Pydantic v2 internals can produce non-JSON-serializable objects (e.g. `ValueError` in `ctx.error`) → handler returns 500 instead of intended status. Reference: DEBT-030 PR1 hotfix.

### What is NOT covered (out of scope)

- Auth-side endpoints with flat envelope (DEBT-034)
- POST create publications endpoint validation (still returns generic FastAPI default)
- `PublicationInternalSerializationError` class exists but not yet raised anywhere — contract reserved for future

---

## 4. Publication versioning (R19)

### Lineage key

`(source_product_id, config_hash)` is the lineage key. Two publications with the same `source_product_id` and same `config_hash` share lineage; different `config_hash` means a new version of the same lineage.

### Stored fields on Publication

- `id` — primary key, unique per row
- `source_product_id` — references the cube/dataset the publication is derived from
- `config_hash` — deterministic hash of `visual_config` JSON
- `updated_at` — touched on every write, including autosave

### Determinism requirement

Same input (same data, same config) → same pixel output on export. Any binding or resolution mechanism MUST preserve this.

**Implication:** bindings stored in `visual_config` MUST capture `snapshotValue` + `resolvedAt` + source hash. Rendering uses snapshot, never live read. Live-resolving bindings violate R19 (Phase 3 explicit non-goal).

### Clone behavior (Phase 1.1)

When a publication is cloned:
- New publication gets fresh `id`
- `source_product_id` preserved (lineage continuity for the source dataset)
- `config_hash` recomputed (the clone may diverge)
- `document_state` set to None on clone — frontend hydrates from column fallback (DEBT-026 lesson). NOT copied verbatim from source.

**Memory item:** Backend Publication clone must NOT copy `document_state` verbatim. Frontend hydrates from `document_state` first; cloned doc keeps source `review.workflow=published`; autosave PATCH then re-publishes the clone. Clone must set `document_state=None` OR run mutate function with `workflow=draft, history=[], comments=[]`.

### Memory item — backend `StatCanClient` constructor argument names

Open question from earlier audit: scheduler's `StatCanClient` constructor argument names (`client`, `guard`, `bucket`) may not match actual `__init__` signature — passes mocked tests but could fail at runtime. Tracked for verification.

## 5. Idempotency state (R16)

### What R16 says

Operations that are conceptually idempotent should be safe to retry without side effects. Specifically: a duplicate request with the same body should not produce a duplicate side effect.

### Current state — partial

**HTTP-level idempotency-key infrastructure does NOT exist** in this codebase as of 2026-04-26.

What DOES exist:
- Background job retry semantics (jobs that fail are retryable; the same input doesn't double-process if the job is dedup-keyed)
- APScheduler with SQLAlchemyJobStore (jobs survive restarts, retried per backoff policy)

What does NOT exist:
- HTTP-level `Idempotency-Key` header handling on PATCH/POST endpoints
- Request-level cache that short-circuits a duplicate request returning the cached response
- Idempotency-key TTL infrastructure

### Implication for ETag (Phase 1.3)

Without idempotency-key short-circuit, a legitimate retry of an already-successful PATCH (network drop on response) will return 412 because the server's ETag has advanced past client's `If-Match`.

Phase 1.3 v1 design accepts this trade-off:
- ETag check applies unconditionally on every PATCH
- Client treats 412 as "reload and retry" UX (correct for both genuine concurrent edit AND rare retry)
- One extra round trip per network drop is cheaper than building idempotency-cache infrastructure

### DEBT for future hardening

Tracked: when HTTP idempotency-key infrastructure is added project-wide, integrate cache-hit short-circuit before ETag check. Cache hit MUST short-circuit BEFORE ETag check, returning cached 200; ETag check applies only on cache miss.

(See `[DEBT.md](http://DEBT.md)` for current entry number assigned in Phase 1.3 impl PR.)

## 6. Token / auth boundaries (R17)

### Tokens MUST be tied to resource, not session

Examples:
- **ETag** is computed over publication fields (id, updated_at, config_hash) — same publication has same ETag for any user. Cross-user requests don't leak via session-bound ETag.
- **Magic link tokens** for download access are tied to publication ID + lead email, with separate session binding. Token alone doesn't authenticate, but identifies the resource.
- **Idempotency keys** (when added) MUST be scoped per resource + endpoint, not per session.

### Don't leak tokens in URLs to third parties

- ETag goes in HTTP header, not URL parameter
- Magic link tokens go in URL but use one-time-use semantics + short TTL
- UTM tags (Phase 2.3) are non-sensitive lineage IDs, not auth tokens — different category

### Anti-pattern: session-bound ETag

If ETag derivation includes user ID or session ID, two users editing the same publication get different ETags → false 412 mismatches → broken UX. Phase 1.3 explicitly avoids this.

## 7. ETag derivation contract

**Status:** Active as of Phase 1.3.

### Pure function signature

```python
# backend/src/services/publications/etag.py
def compute_etag(pub: Publication) -> str: ...
```

Pure module. No I/O, no clock reads, no DB access. ARCH-PURA-001 + ARCH-DPEN-001 trivially satisfied (no class, no DI).

### Source columns

- `pub.id` (PK, NOT NULL)
- `pub.updated_at` (`DateTime`, nullable; `onupdate=func.now()`) OR `pub.created_at` (NOT NULL fallback for fresh DRAFT rows)
- `pub.config_hash` (`String(64)`, nullable; substituted with `""` when NULL for determinism)

### Format

Strong ETag (no `W/` prefix). The validator serves as an optimistic-concurrency token for `If-Match`, not as a body hash. It is derived from the persisted publication state version (`id` + last-write timestamp + `config_hash`); identical persisted state always produces an identical token, which is the contract `If-Match` requires. RFC 7232 §2.3 strong-validator semantics about byte-identical response bodies do not strictly apply — our concern is row-state equivalence, not byte equivalence of the response. Format: `"<16-hex-sha256>"`.

### Where computed

In handlers, NOT in repository (per ARCH-PURA-001). The pure function takes a `Publication` entity; no DB read embedded in the function call. Today three endpoints compute ETag:
- `GET /api/v1/admin/publications/{id}` — sets the response header.
- `PATCH /api/v1/admin/publications/{id}` — checks `If-Match` against `compute_etag(previous)`, then sets the response header to `compute_etag(updated)`.
- `POST /api/v1/admin/publications/{id}/clone` — sets the response header on the freshly created clone so the editor can seed its first PATCH's `If-Match`.

### Where read on PATCH

`if_match: str | None = Header(default=None, alias="If-Match")` parameter on the FastAPI handler. Comparison happens inside the same per-request `AsyncSession` transaction as the SELECT and UPDATE.

### Stability requirements

- MUST NOT change between identical reads of the same row (deterministic).
- MUST change after any write that touches `updated_at` (the `onupdate=func.now()` trigger guarantees this on every UPDATE through `update_fields`).
- MUST NOT include user ID, session ID, or any per-request data — same publication has same ETag for any user (per §6 anti-pattern).

### Separator

`|` (ASCII 0x7C). Collision-safe in this domain: id is integer-stringified, timestamp is ISO-8601, config_hash is 64-char hex — none can contain `|`. Changing the separator invalidates every cached `If-Match` token; requires DEBT entry per the rule below.

### Hash + truncation

SHA-256 over the UTF-8-encoded composite string `f"{id}|{timestamp}|{config_hash_or_empty}"`, truncated to the first 16 hex characters, wrapped in double quotes.

### v1 tolerate-absent posture

PATCH currently tolerates a missing `If-Match` (warn-log + proceed). Tracked in DEBT-042 for hardening to 428 Precondition Required after the rollout window stabilises.

### Contract immutability

Changing the derivation invalidates every client's cached `If-Match` token. Any change to the inputs, separator, hash algorithm, or truncation length requires explicit founder approval and a DEBT entry.

## 8. Other invariants

### LLM not in critical pipeline

LLM-based components are NOT in the critical content-generation pipeline. Replaced with `KeywordScorer`, `HeadlineTemplateEngine`, `ArtPromptSelector` (deterministic). LLM retained only as optional "AI Enhance" post-launch button.

**Implication:** no cost-tracking infrastructure for LLM, no caching with `prompt_hash + data_hash`, no budget alerts. One-off LLM calls (Phase 2.4 draft social text) are explicit exceptions, not the default.

### Template lock

The editor is template-driven. Free-form canvas is NOT a substitute. 13 block types, 11 templates across 7 families. New blocks/templates added via the strict-template architecture, not by introducing a free-form mode.

### Deterministic export

Same input (data + config) → same pixel output. Any binding or resolution mechanism that breaks this requires explicit founder review and DEBT entry. PNG export uses logical CSS dimensions, not DPR-scaled canvas (memory item).

### Operator-not-developer assumption

Designers come from Figma/Canva culture; data workers come from Excel culture. Neither knows SQL, Polars schemas, or CLI. Command palettes and keyboard-driven interfaces are a misfit.

**Implication:** no Cmd+K palette in admin UI; visual + form-based interfaces preferred. Roadmap §6 explicitly defers command palette as developer-culture pattern.

### applyMigrations pipeline must abort on missing intermediate

Document migration pipeline (`applyMigrations` in editor) MUST abort if an intermediate migration step is missing. Silent skip is forbidden. Memory item from editor architecture.

## 9. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from ARCH_[RULES.md](http://RULES.md), [DEBT.md](http://DEBT.md), memory items |
| 2026-04-27 | Phase 1.3 impl | §7 | Filled placeholder with the live ETag derivation contract (pure `compute_etag` over `id` / `updated_at` OR `created_at` / `config_hash`, weak ETag, `|` separator, SHA-256 truncated to 16 hex). Cross-refs DEBT-041/042/043. |
| 2026-04-27 | Phase 1.3 fix  | §7 | Corrected ETag format to **strong** (dropped `W/` prefix). Rationale: the validator is derived from row metadata, not the response body, so the byte-identical-output criterion *is* satisfied — strong ETags are the correct semantic fit for `If-Match` lost-update protection. Updated `compute_etag`, all tests, and §7 Format/Hash subsections accordingly. |
