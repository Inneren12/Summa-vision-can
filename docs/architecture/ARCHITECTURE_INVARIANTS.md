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

**End of Part 1. Sections 4-9 added by Part 2.**
