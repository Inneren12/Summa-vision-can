# Phase 1.3 Pre-Recon Part C1 — ETag Derivation

**Type:** DESIGN PROPOSAL (1 of 2 splits of original Part C)
**Scope:** Section A only — ETag derivation function and integration points.
**Date:** 2026-04-27
**Inputs consumed:**
- `docs/recon/phase-1-3-A-backend-inventory.md` (Part A, complete)
- `docs/recon/phase-1-3-B-frontend-inventory.md` (Part B, referenced for handler-location cross-checks only)

**Other splits:** C2 (R16 + 412 envelope + frontend handling + backcompat) — not in this doc.

---

## Section A — ETag derivation

### A.1 Source columns (verbatim from Part A §1.2)

The Publication model is at `backend/src/models/publication.py` (Part A §1.2 line 77). The version-relevant columns the ETag derivation will consume:

| Column        | Type / nullability                                | Notes (from A.1.2)                                            |
| ------------- | ------------------------------------------------- | ------------------------------------------------------------- |
| `id`          | `int`, PK, `autoincrement=True`, NOT NULL         | Always present after row insert.                              |
| `updated_at`  | `DateTime(timezone=True)`, **nullable**           | `onupdate=func.now()`. NULL until first UPDATE.               |
| `config_hash` | `String(64)`, **nullable**                        | Populated for clone-lineage rows; NULL for plain DRAFTs.      |
| `created_at`  | `DateTime(timezone=True)`, NOT NULL               | `default=lambda: datetime.now(timezone.utc)`. Always present. |
| `version`     | `int`, NOT NULL, default 1                        | Product-lineage version, **NOT** row-revision counter (A.1.2 gloss). Excluded from ETag — would not change on autosave. |

**Key facts driving the design:**
- `updated_at` is nullable. A publication immediately after `create()` has `updated_at = None`. Only the ORM `onupdate` trigger populates it on subsequent UPDATEs (A.1.3 confirms: `update_fields` uses ORM `setattr`+`flush`, which does fire `onupdate`).
- `config_hash` is nullable for non-clone DRAFT rows.
- `id` and `created_at` are guaranteed non-null and immutable post-insert.

R19 satisfied: derivation reuses `updated_at` + `config_hash`. **No new column required.**

### A.2 Derivation function (proposed)

```python
# backend/src/services/publications/etag.py
import hashlib
from src.models.publication import Publication


def compute_etag(pub: Publication) -> str:
    """Derive a weak ETag for a Publication row.

    Pure function — no I/O, no clock reads, no DB. ARCH-PURA-001 compliant.

    Inputs: id (PK), updated_at (or created_at fallback), config_hash.
    Output: RFC 7232 weak validator, e.g. W/"a1b2c3d4e5f60718".
    """
    timestamp = (pub.updated_at or pub.created_at).isoformat()
    config = pub.config_hash or ""
    raw = f"{pub.id}|{timestamp}|{config}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f'W/"{digest}"'
```

**Counter to the spec's pseudo-code:**

The spec proposed `f"{pub.id}|{pub.updated_at.isoformat()}|{pub.config_hash}"`. This raises `AttributeError` when `updated_at is None` (fresh DRAFT, never updated) and emits the literal string `"None"` when `config_hash is None`. Two corrections applied:

1. **Fallback `updated_at or created_at`.** `created_at` is non-nullable (A.1.2:104-109) and is set at insert time. For a fresh row whose `updated_at` is still NULL, the ETag derives from `created_at`. After the first UPDATE fires `onupdate=func.now()`, the ETag flips. This matches the semantic ("ETag changes whenever the row materially changes").
2. **`config_hash or ""`.** Treats NULL as empty-string, deterministic across reads. (Substituting the literal `"None"` would also be deterministic but couples the hash to Python's `str(None)` representation.)

**Why 16 hex chars (= 64 bits):** sufficient collision resistance for a single-row optimistic-concurrency check. The check is `client_etag == server_etag` for a *known row id*; the birthday-collision search space is per-row, not global. Full SHA-256 (64 hex) would just bloat the header for no defensive value.

### A.3 Format choice — weak ETag

**Decision: weak (`W/"…"`).** Justification:

- Autosave bodies are not byte-identical between operators (JSON key ordering, whitespace, optional-field elision, Pydantic alias serialization). Two semantically-equivalent saves can produce different byte strings.
- RFC 7232 §2.3: weak validators are appropriate when "two representations of the same resource are equivalent but not byte-for-byte identical." This is exactly our case.
- Strong ETags would require octet-equality, which our serialization layer does not guarantee.

CDN/proxy implications: weak ETags are not eligible for `If-None-Match` revalidation on byte-range requests, but PATCH does not use ranges. No downside for our use case.

### A.4 Where computed

**Decision: pure function in `services/publications/etag.py`, called from handlers — NOT from the repository.**

Rationale (ARCH-PURA-001):
- The repository methods do I/O (DB reads). Adding ETag computation to them would be benign, but coupling it inside repo methods makes the function harder to unit-test in isolation.
- `compute_etag(pub)` is pure and takes only the entity. The handler:
  ```python
  publication = await repo.get_by_id(publication_id)
  if publication is None:
      raise PublicationNotFoundError()
  etag = compute_etag(publication)  # pure
  ```
- No tuple-return refactor of `PublicationRepository` needed (the spec offered two alternatives — tuple return or a separate `compute_etag_for(pub_id)` repo method; **both are rejected** in favor of a pure function called from the handler).
- A separate `compute_etag_for(pub_id)` repo method would do a redundant DB read after the existing `get_by_id`. Avoided.

**File location: `backend/src/services/publications/etag.py`.**

Counter to the spec's `backend/app/domain/publication/etag.py`:
- Part A §1.1 already flagged that the repo uses `backend/src/`, not `backend/app/`.
- There is no `domain/` directory in `backend/src/` (verified: `backend/src/` contains `api/`, `core/`, `models/`, `repositories/`, `schemas/`, `services/`, `templates/` — no `domain/`).
- `backend/src/services/publications/` already houses publication-scoped helpers (`lineage.py`, `exceptions.py`, `clone.py`). New file `etag.py` mirrors that convention.

### A.5 Where the ETag header is set on responses

**GET single publication exists.** Handler at `backend/src/api/routers/admin_publications.py:315-332`:

```python
@router.get(
    "/{publication_id}",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a single publication",
    responses={404: {"description": "Publication not found."}},
)
async def get_publication(
    publication_id: int,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    publication = await repo.get_by_id(publication_id)
    if publication is None:
        raise PublicationNotFoundError()
    return _serialize(publication)
```

**Refactor to set the ETag header** (FastAPI pattern — inject `response: Response`):

```python
async def get_publication(
    publication_id: int,
    response: Response,                                    # NEW
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    publication = await repo.get_by_id(publication_id)
    if publication is None:
        raise PublicationNotFoundError()
    response.headers["ETag"] = compute_etag(publication)   # NEW
    return _serialize(publication)
```

This preserves `response_model=PublicationResponse` and the body shape; only the header is added. No status-code change.

**PATCH response should also set the ETag** (after a successful update, the response body is the new state — including the new ETag lets the client store it without re-GET):

PATCH handler is at `backend/src/api/routers/admin_publications.py:340-355` (Part A §1.1). Same pattern: inject `response: Response`, set `response.headers["ETag"] = compute_etag(updated_publication)` before returning.

**Other GET endpoints to consider (not in scope for v1):**
- `list_publications` at `:280` — collection endpoint. Per-row ETags don't apply to a list. Out of scope.
- (Any public-side read endpoint, if it exists.) Not in 1.3 scope; admin-only autosave path is the v1 target.

### A.6 Where the If-Match header is read on PATCH

**Inject as a FastAPI `Header(...)` parameter** (no new `Depends`-style helper required — `Header` is FastAPI built-in):

```python
from fastapi import Header

@router.patch(
    "/{publication_id}",
    response_model=PublicationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Publication not found."},
        412: {"description": "ETag does not match — publication has changed."},
        422: {"description": "Validation failure."},
    },
)
async def update_publication(
    publication_id: int,
    body: PublicationUpdate,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),    # NEW
    repo: PublicationRepository = Depends(_get_repo),
    audit: AuditWriter = Depends(_get_audit),
) -> PublicationResponse:
    ...
```

**Comparison location: inside the same DB transaction as the update.**

The TOCTOU concern: if we (a) read the row, (b) compute its ETag, (c) compare to `If-Match`, (d) commit-and-release the session, then later open a new tx to UPDATE — a concurrent writer could land between (c) and (d). To avoid this:

- Use the existing per-request session pattern. Per Part A §1.6 (`_make_app` fixture lines 81-113), the request session is opened by `_override_repo`, yielded, and committed at the end. Production wiring uses the same single-session-per-request pattern via `_get_repo`.
- The handler issues `repo.get_by_id(publication_id)` → compares ETag → calls `repo.update_fields(...)` → returns. All three operations execute on the same `AsyncSession`, in the same transaction, before the dependency's `await session.commit()` runs.
- Two concurrent PATCHes on the same row will serialize at the database level when the second one tries to UPDATE (PostgreSQL row-level lock acquired implicitly by UPDATE). The second one's prior ETag-read is still self-consistent because UPDATE will fail or succeed against the row state at update time — but our `update_fields` uses ORM `setattr+flush` (A.1.3), which writes `updated_at = func.now()` via the `onupdate` trigger on flush. The second writer's flush will produce a new `updated_at`, so its ETag is now stale relative to the first writer's commit.
- **Stronger guarantee available if needed:** add `.with_for_update()` to the `get_by_id` SELECT used by PATCH. That converts the read into a row lock. For v1, the implicit UPDATE-side serialization is sufficient; flag `with_for_update()` as a hardening option in C2/Part D if telemetry shows lost-update races.

**Result of comparison:**
- `if_match is None` → behaviour deferred to C2 §E (backcompat fork).
- `if_match == compute_etag(publication)` → proceed with update.
- `if_match != compute_etag(publication)` → raise `PublicationPreconditionFailedError` (envelope shape spec'd in C2 §C). 412 returned.

### A.7 Pure-function placement (ARCH-PURA-001)

**File proposal:** `backend/src/services/publications/etag.py`

Justification:
- No `domain/` directory exists in `backend/src/` (verified at top of §A.4).
- `services/publications/` is the established home for publication-scoped pure-ish helpers: `lineage.py` (publication-lineage version arithmetic), `clone.py` (clone-payload construction), `exceptions.py` (error class hierarchy).
- `etag.py` slots naturally next to `lineage.py` (both compute deterministic values from a Publication's identity columns).
- Imports stay one-way: `services/publications/etag.py` imports `models.Publication`. No back-edges, no cycles.

**Module surface:**
```python
# backend/src/services/publications/etag.py
def compute_etag(pub: Publication) -> str: ...
```

That is the entire surface. No classes, no DI, no constructor — therefore ARCH-DPEN-001 is trivially satisfied (no class to inject into).

### A.8 Open questions / counter-proposals raised

1. **`updated_at` NULL fallback to `created_at`** — counter-proposal to the spec's pseudo-code. Spec did not handle nullability. Recommended: accept the fallback; alternative is to backfill `updated_at = created_at` on insert via a server-side default, but that's an unrelated migration.
2. **`config_hash` NULL substitution to `""`** — counter-proposal. Spec used raw `pub.config_hash`. Recommended: accept `or ""`.
3. **Pure function in `services/publications/etag.py`, not in repo or in a non-existent `domain/`** — counter-proposal to both the spec's pseudo-code (which placed it in repo read methods) and the spec's path (which presumed `backend/app/domain/publication/etag.py`).

No founder Q raised — `config_hash` exists per A.1.2, so the reduced-coverage fallback path is not needed.

---

## Summary Report

```
GIT REMOTE: http://local_proxy@127.0.0.1:34577/git/Inneren12/Summa-vision-can
DOC PATH: docs/recon/phase-1-3-C1-etag.md

INPUTS CONSUMED:
  Part A: docs/recon/phase-1-3-A-backend-inventory.md
  Part B: docs/recon/phase-1-3-B-frontend-inventory.md (handler-location cross-check only)

§A ETag derivation:
  Source columns confirmed from A.1.2: id (PK, NOT NULL), updated_at (nullable, onupdate=func.now()), config_hash (String(64), nullable), created_at (NOT NULL — fallback for NULL updated_at)
  config_hash exists: yes
  Format: weak (W/"<16-hex sha256>")
  Where computed: pure function in services/publications/etag.py, called from handlers (NOT in repo; rejects spec's tuple-return alternative)
  GET handler exists per A.1.1: yes — backend/src/api/routers/admin_publications.py:315 (single); :280 (list, out of scope)
  PATCH handler location: backend/src/api/routers/admin_publications.py:340 (per A §1.1)
  Pure-function file proposal: backend/src/services/publications/etag.py
  Founder Q raised: none (config_hash present; NULL handled via "or \"\"" substitution; updated_at NULL handled via fallback to created_at)

VERDICT: READY-FOR-C2
```

---

**End of Part C1.**
