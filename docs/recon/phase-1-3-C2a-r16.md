# Phase 1.3 — Part C2a — R16 Idempotency Tension Decision

**Type:** DESIGN
**Scope:** Section B only — R16 idempotency tension decision.
**Date:** 2026-04-27
**Branch:** `claude/design-r16-idempotency-Uo4AN`

**Precondition (already established in earlier diagnostic):**
HTTP-level `Idempotency-Key` infrastructure does **not** exist in this codebase.

---

## Section B — R16 Tension Decision

### Decision: v1 has no idempotency-key short-circuit

- The ETag (`If-Match`) precondition check applies to **every** `PATCH /publications/{id}` request, unconditionally.
- There is **no** server-side cache of `(Idempotency-Key → response)` consulted before the ETag check.
- The PATCH handler is therefore stateless with respect to retries: each request is evaluated against the current persisted ETag, full stop.

### Risk

- A legitimate retry following a network drop on the *response* path (request reached the server, mutation succeeded, response lost in transit) will hit a server whose ETag has already advanced past the client's `If-Match` value.
- That retry receives `412 Precondition Failed`, even though the client's intent was a benign retry of an already-successful operation — not a concurrent edit.

### Mitigation

- The client treats every `412` uniformly as **"reload the resource (refetch ETag + body) and retry"**.
- This UX is correct in *both* scenarios:
  1. **Genuine concurrent edit** — another writer advanced the ETag; the user must reconcile.
  2. **Rare lost-response retry** — the user's own prior write advanced the ETag; reload yields the already-applied state and the retry becomes a no-op (or a trivial re-apply on top of the user's own change).
- Cost: at most one extra round trip per network drop on the response leg.
- Benefit: avoids building, testing, and operating a distributed idempotency-key cache (TTL, eviction, key collision policy, replay-window semantics, cache-hit vs ETag-check ordering) for v1.
- Trade-off accepted: one extra round trip on a rare failure mode is materially cheaper than the infrastructure cost of project-wide idempotency-key support before that infrastructure exists.

### DEBT to log

**DEBT-037 (proposed):** *"PATCH publications has no idempotency-key short-circuit; legitimate retries may 412"*

- **Severity:** Low
- **Category:** api-correctness-edge-case
- **Symptom:** A retried `PATCH /publications/{id}` after a lost response returns `412` instead of replaying the prior successful response.
- **Resolution path:** When HTTP `Idempotency-Key` infrastructure lands project-wide (cache + middleware), integrate a cache-hit short-circuit that runs **before** the ETag precondition check inside the PATCH handler. On cache hit, replay the stored response verbatim; on cache miss, fall through to the existing ETag check.
- **Out of scope for v1:** No change to handler ordering or wire contract until that infrastructure exists.

### Old founder Q7 dropped

The earlier founder question Q7 — *"hard-require ETag without short-circuit OR defer 1.3 entirely"* — is **resolved** by the decision above:
- ETag is hard-required in v1.
- Short-circuit is deferred to a future phase, tracked as DEBT-037.
- Phase 1.3 itself is **not** deferred.

**Q7 is dropped. Q1–Q6 remain open.**
