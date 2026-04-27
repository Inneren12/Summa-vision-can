# Phase 1.3 — Part C2b — 412 Error Envelope

**Type:** DESIGN (2 of 4 micro-splits of original Part C2)
**Scope:** Section C only — 412 response envelope and handler implementation note.
**Date:** 2026-04-27
**Branch:** `claude/design-412-error-envelope-S9iX8`

**Cited references:**
- Part A §1.4 — existing handler pattern (`backend/src/core/error_handler.py:87`).
- Part A §1.5 — existing `PublicationApiError` envelope (`backend/src/services/publications/exceptions.py:16`).
- Part B §1.2 — i18n hybrid (DEBT-030 Option C) confirmed at `frontend-public/src/lib/api/errorCodes.ts:108`.

---

## Section C — 412 Error Envelope

### C.1 Response shape

```json
{
  "detail": {
    "error_code": "PRECONDITION_FAILED",
    "message": "The publication has been modified since you loaded it.",
    "details": {
      "server_etag": "W/\"def...\"",
      "client_etag": "W/\"abc...\""
    }
  }
}
```

This shape mirrors exactly the existing 422 envelope produced by
`_publication_validation_exception_handler` (Part A §1.4 — `error_handler.py:87-109`) and the
`PublicationApiError` `detail_payload` constructor (Part A §1.5 —
`services/publications/exceptions.py:16`):
`{"detail": {"error_code", "message", "details"}}`. No new top-level shape is introduced.

### C.2 Field decisions

#### `error_code: "PRECONDITION_FAILED"`

**Proposal:** `PRECONDITION_FAILED`.

**Counter-options (founder Q2):**

| Candidate              | Why considered                                | Why rejected                                                         |
|------------------------|-----------------------------------------------|----------------------------------------------------------------------|
| `STALE_VERSION`        | Reads naturally in UX copy.                   | Editorializes — implies a versioning model the wire contract does not expose. Conflates "stale" (a UX framing) with "precondition failed" (the protocol fact). |
| `VERSION_MISMATCH`     | Symmetric with client/server ETag pairing.    | Same editorialization issue; also drifts from HTTP terminology and forces consumers to re-map back to 412. |
| `IF_MATCH_FAILED`      | Most literal — names the failed header.       | Leaks header-level detail into the application code; hostile to future precondition mechanisms (e.g., `If-Unmodified-Since`) that would also produce 412. |
| **`PRECONDITION_FAILED`** | **Matches HTTP 412 semantic exactly.**     | **Picked.** Aligns the error_code with the status code's RFC-defined name; no editorialization; stable across precondition mechanisms. UX copy is carried by the `message` field and i18n key, not the code. |

**Justification:** the `error_code` is a stable machine-readable contract; localized phrasing belongs in `message` + i18n. `PRECONDITION_FAILED` is the only option that carries no editorial framing.

#### `details.server_etag`

The current persisted ETag of the publication, as the server would have returned on a fresh GET
of the resource at the moment of conflict.

**Rationale:** lets the client offer a "reload and reapply" affordance without an extra GET round
trip. The client already knows the resource id; with the server ETag in hand it can decide
whether to refetch the body (always, in v1) or to skip refetch and surface a merge UI in a
future revision.

#### `details.client_etag`

The `If-Match` value the client supplied on the failing PATCH.

**Rationale:** server-side telemetry only — observe stale-ETag patterns (e.g., a single client
repeatedly racing the same generation suggests a UI bug; many clients all stuck on one prior
generation suggests a stuck cache or CDN). Not consumed by the client; included in the envelope
because logging it from the request is cheaper and more reliable than parsing it back out of
access logs after the fact.

### C.3 Handler implementation note (CRITICAL — DEBT-030 PR1 hotfix memory)

The 412 handler **MUST** wrap the response body via `jsonable_encoder(...)`:

```python
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi import status

return JSONResponse(
    status_code=status.HTTP_412_PRECONDITION_FAILED,
    content=jsonable_encoder(
        {
            "detail": {
                "error_code": "PRECONDITION_FAILED",
                "message": message,
                "details": {
                    "server_etag": server_etag,
                    "client_etag": client_etag,
                },
            }
        }
    ),
)
```

**Why this is mandatory:** without `jsonable_encoder`, Pydantic v2 internals can produce
non-JSON-serializable objects inside `details` (e.g., when ETag values originate from Pydantic
models or `datetime`-derived weak validators). `JSONResponse` then fails serialization and
FastAPI surfaces a generic `500 Internal Server Error` *instead of* the intended `412`. The
client's "reload and retry" UX never fires; the user sees a generic crash banner.

This is the same trap DEBT-030 PR1 fixed for the 422 handler. The 412 handler must mirror it
exactly. See Part A §1.4: `_publication_validation_exception_handler` already imports
`jsonable_encoder` (line 23) and uses it on both branches (lines 95 and 108). The 412 handler
must be registered through the same `register_exception_handlers(app)` entry point
(`backend/src/core/error_handler.py:112`, called from `backend/src/main.py:151`) — no new
registration site.

### C.4 i18n key

**Key:** `errors.backend.precondition_failed`

**Justification:** Part B §1.2 confirmed the DEBT-030 hybrid (Option C) at
`frontend-public/src/lib/api/errorCodes.ts:108` — publication-specific UX messages live under
`publication.*`; cross-cutting / protocol-level codes live under `errors.backend.*`. A 412
precondition failure is a **protocol-level** concurrency signal, not a publication-domain UX
event (the same code would apply to any future ETag-guarded resource), so it belongs under
`errors.backend.*`.

**Casing:** `snake_case` (`precondition_failed`), matching the three existing
`errors.backend.*` snake_case leaves observed in Part B §1.4
(`auth_api_key_missing`, `auth_api_key_invalid`, `auth_admin_rate_limited`). The
camelCase outlier `publicationCloneNotAllowed` is a noted inconsistency in Part B and is **not**
the precedent to follow for new protocol-level codes.

### C.5 EN draft

```
"This publication has changed since you loaded it. Reload and reapply your changes, or save as a new draft."
```

Two-clause structure: (1) plain-language statement of *what happened*, no jargon; (2) two
concrete next actions ranked by likelihood — reload-and-reapply for the common concurrent-edit
case, save-as-new-draft as the escape hatch when the user does not want to discard their
in-flight changes.

### C.6 RU translation

**DEFERRED — founder Q5.** Authoring Russian copy without founder review risks
register/tone mismatch with the existing `ru.json` corpus (Part B §1.4 reports all 8 existing
leaf paths populated). The placeholder MUST be added to `ru.json` in the same PR that adds the
EN string, but the Russian *value* is left for founder Q5 to resolve before merge.

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-C2b-envelope.md
error_code: PRECONDITION_FAILED
i18n key: errors.backend.precondition_failed
jsonable_encoder note: included
RU translation: deferred to Q5
VERDICT: COMPLETE
```
