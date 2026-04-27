# Phase 1.3 Pre-Recon Part D1 — Test Plan (Section F)

**Type:** RECON FINALIZATION (1 of 4 micro-splits of original Part D)
**Scope:** Section F only — test plan with stable test IDs.
**Other splits:** D2 (migration/rollout), D3 (DEBT additions), D4 (polish + founder questions).
**Date:** 2026-04-27
**Branch:** `claude/test-plan-stable-ids-qRUkg`
**Git remote:** `http://local_proxy@127.0.0.1:35025/git/Inneren12/Summa-vision-can`

**Prereqs read:**
- Part A — `docs/recon/phase-1-3-A-backend-inventory.md` (handler at `backend/src/api/routers/admin_publications.py:340`; canonical PATCH fixture at `backend/tests/api/test_admin_publications.py:81 _make_app`).
- Part B — `docs/recon/phase-1-3-B-frontend-inventory.md` (`BackendApiError` at `frontend-public/src/lib/api/admin.ts:34`; autosave consumer at `frontend-public/src/components/editor/index.tsx:568 performSave`).

This document is **READ-ONLY** for production code — no migrations, no new modules, no DEBT additions, no founder questions. Those are explicitly deferred to Parts D2–D4.

---

## F. Test plan

Each test below carries a stable ID of the form `T-1.3-{B|F}-{UNIT|INT}-NN`
so impl prompts, PR descriptions, and review comments can cross-reference
specific tests without ambiguity.

### F.1 Backend unit (pure functions)

Targets `compute_etag(pub: Publication) -> str` from
`backend/src/services/publications/etag.py` (Part C1 §A — lines 38–43, 79–98).
These tests are pure (no DB, no FastAPI app, no fixtures beyond a constructed
`Publication` instance).

| Test ID                        | Assertion                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **T-1.3-B-UNIT-01**            | **`compute_etag` purity** — given an identical `Publication` instance, `compute_etag(pub)` returns the same string across two consecutive calls. Establishes the function is a pure projection of the input columns and has no hidden state (no clock, no random salt, no row counter mutation).                                                     |
| **T-1.3-B-UNIT-02**            | **`compute_etag` change-on-write** — three sub-assertions on the same fixture publication: (a) mutating `pub.updated_at` to a new timestamp **changes** the ETag; (b) mutating `pub.config_hash` to a new value **changes** the ETag; (c) mutating an unrelated column (e.g., `pub.headline` or `pub.eyebrow`) **does not change** the ETag. Locks the input set documented in Part C1 §A so future column additions don't accidentally invalidate every cached ETag. |

**File location proposal:**
`backend/tests/services/publications/test_etag.py`

> Rationale: the prompt suggested `backend/tests/unit/test_etag.py`, but
> `backend/tests/unit/` does not exist in this repo. The convention for
> pure-function tests on `services/publications/*.py` is
> `backend/tests/services/publications/test_<module>.py` — see the existing
> `test_lineage.py` and `test_clone.py` siblings. New test file slots in
> alongside them; aligns with Part C1 §A's file proposal at
> `backend/src/services/publications/etag.py`.

### F.2 Backend integration (router-level, real PostgreSQL)

Targets the PATCH handler at `backend/src/api/routers/admin_publications.py:340`
once 412 / `If-Match` support is wired. Per the prompt, these use real
PostgreSQL via Testcontainers — i.e. NOT the in-memory SQLite already in use
at `backend/tests/api/test_admin_publications.py` (`_make_app`, lines 61–113).
The fixture mirrors that file's existing publications fixture but swaps the
engine for a Testcontainers Postgres container.

| Test ID                        | Assertion                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **T-1.3-B-INT-01**             | **PATCH with matching `If-Match` returns 200** — `GET /api/v1/admin/publications/{id}` (or any read that emits the `ETag` header per Part C1 §A.6 line 133), capture the response `ETag`, then `PATCH /api/v1/admin/publications/{id}` with `If-Match: <captured>` and a valid `PublicationUpdate` body. Assert: `status == 200`, response `ETag` header is present and **differs** from the captured one (since `updated_at` advances per Part A §1.3 ORM `onupdate=func.now()`), body matches `PublicationResponse`. |
| **T-1.3-B-INT-02**             | **PATCH with mismatched `If-Match` returns 412 with envelope** — `PATCH` with `If-Match: "deadbeefdeadbeef"` (a syntactically valid ETag that doesn't match the row). Assert: `status == 412`; `body == {"detail": {"error_code": "PRECONDITION_FAILED", "message": <str>, "details": {"server_etag": <str>, "client_etag": "deadbeefdeadbeef"}}}` — exact key shape per Part C2b. JSON-roundtrip the response to verify no `TypeError` from un-encoded `datetime`/`UUID`/etc. objects (regression guard for the DEBT-030 PR1 hotfix; the new 412 handler MUST also use `jsonable_encoder` per Part A §1.4 lines 95 + 108). |
| **T-1.3-B-INT-03**             | **PATCH without `If-Match` (backcompat)** — `PATCH` with no `If-Match` header at all and a valid `PublicationUpdate` body. Assert: `status == 200`, body matches `PublicationResponse`, **and** a structured warn-log entry is emitted indicating "PATCH without If-Match" (caplog assertion on the logger configured for the handler). **Conditional on founder Q3 = "tolerate"** — Part C2d §E.2 line 41 confirms Q3's answer is "tolerate". If a future revision flips Q3 to "require", this test inverts: assert `status == 428 Precondition Required` per the DEBT-038 v2 plan (Part C2d §E.3 lines 78–80). |

#### F.2.x Critical fixture requirements (carry-forward from DEBT-030 PR1)

These are not separate tests; they are non-negotiable preconditions the
fixture used by every F.2 test must satisfy. Failure to honor any of these
is a known trap — DEBT-030 PR1 lost a half-day to exactly this set.

1. **`register_exception_handlers(app)` MUST be called** on the FastAPI
   instance the test client wraps. Without it the 412 handler does not fire
   and the test sees raw `HTTPException` JSON (`{"detail": "..."}`) instead
   of the structured `{"detail": {"error_code": "PRECONDITION_FAILED", ...}}`
   envelope. Reference: Part A §1.6 lines 488 + 502 — `_make_app` calls it,
   `_make_admin_and_public_app` does **not**, which is the canonical trap.
   Source location to call: `from src.core.error_handler import register_exception_handlers`
   (`backend/src/core/error_handler.py:112`).

2. **Every `Depends(...)` in the PATCH handler MUST be overridden.** Per
   Part A §1.1 lines 41–42, the verbatim dep list on
   `update_publication` is exactly two items:
   - `repo: PublicationRepository = Depends(_get_repo)`
   - `audit: AuditWriter = Depends(_get_audit)`

   so the fixture must set:
   ```python
   app.dependency_overrides[_get_repo]  = _override_repo
   app.dependency_overrides[_get_audit] = _override_audit
   ```
   verbatim (mirrors `backend/tests/api/test_admin_publications.py:109-110`).
   If Part C2 introduces a new dep (e.g., a request-scoped `If-Match`
   resolver), this list grows accordingly — re-cite Part A §1.1 at impl
   time and add the matching override.

3. **Use `subprocess.run(['alembic', 'upgrade', 'head'])` against the
   Testcontainers Postgres URL** to bring up the schema, NOT the programmatic
   Alembic API (`alembic.command.upgrade(cfg, 'head')`). The programmatic
   path leaks Alembic's `Config` object across tests and has been observed
   to silently skip migrations in pytest-xdist worker processes; the
   subprocess form is the documented safe path. Drop the schema with a
   container teardown, not with `Base.metadata.drop_all`.

4. **Fixture mirrors `_make_app`, NOT `_make_admin_and_public_app`.** Even
   though some 412 follow-up tests may want public-side overrides too, the
   PATCH-412 fixture must be derived from the admin-only `_make_app`
   (Part A §1.6 Fixture A) because that is the only one in the repo today
   that calls `register_exception_handlers`. If a combined fixture is
   needed later, it must add `register_exception_handlers(app)` explicitly.

### F.3 Frontend unit (`BackendApiError` propagation)

Targets the error branch in `updateAdminPublication` at
`frontend-public/src/lib/api/admin.ts:137-164` (Part B §1.1) once
`PRECONDITION_FAILED` is added to `KNOWN_BACKEND_ERROR_CODES`
(`frontend-public/src/lib/api/errorCodes.ts:17`, Part B §1.1).

| Test ID                        | Assertion                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **T-1.3-F-UNIT-01**            | **`BackendApiError` propagation on 412** — mock `fetch` to return `{ status: 412, json: async () => ({"detail": {"error_code": "PRECONDITION_FAILED", "message": "...", "details": {"server_etag": "abcd1234abcd1234", "client_etag": "deadbeefdeadbeef"}}}) }`. Call `updateAdminPublication('1', {...})`. Assert: rejects with a `BackendApiError`; `error.status === 412`; `error.code === 'PRECONDITION_FAILED'`; `error.details?.server_etag === 'abcd1234abcd1234'`; `error.details?.client_etag === 'deadbeefdeadbeef'`. (Property name on the JS class is `code`, not `errorCode` — Part B §1.1 lines 49–66; the prompt's "`error.errorCode`" wording is the spec's terminology and maps to `error.code` in the actual class.) |

### F.4 Frontend integration (real-wire — autosave consumer surfaces 412)

Per memory items #5 and #21, frontend integration tests for autosave error
flows must be **real-wire**: mock the network boundary (`fetch`), NOT the
consumer module under test (`updateAdminPublication`). This catches
regressions in the wiring between the API client, the `.catch` branch in
`performSave`, and the surfaced UX — exactly the layer DEBT-030 PR1 missed.

| Test ID                        | Assertion                                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **T-1.3-F-INT-01**             | **autosave consumer surfaces 412 modal** — render the autosave consumer (`frontend-public/src/components/editor/index.tsx`, the `performSave` chokepoint at lines 568–627 per Part B §1.3). Mock `global.fetch` (NOT `@/lib/api/admin`) to return the same 412 envelope as T-1.3-F-UNIT-01. Trigger a save (mark the doc dirty, advance timers past the autosave debounce). Assert: (a) the new `StaleVersionModal` (proposed location `frontend-public/src/components/editor/components/StaleVersionModal.tsx`, Part B §1.3) appears in the DOM; (b) it renders both a "Reload" button and a "Save as draft" button; (c) the displayed body text resolves from the i18n key `errors.backend.precondition_failed` (assert against the EN translation string from `frontend-public/messages/en.json`); (d) `saveStatus !== 'error'` with `canAutoRetry: true` — i.e. the 412 path **bypasses** the `NotificationBanner` auto-retry branch, exactly as Part B §1.3's "terminal — bypasses auto-retry" gloss requires. |

> Note on the i18n key: Part B §1.4 documents the existing hybrid (Option C)
> namespace. Both `publication.precondition_failed.*` and
> `errors.backend.precondition_failed` would be defensible; the prompt
> specifies `errors.backend.precondition_failed`, so this test asserts that
> exact key. If D4 / impl revisits the namespace decision, this test ID is
> the single point of update.

---

## F.5 Test ID register (cross-reference)

| ID                  | Layer                         | File (proposed)                                                                                       |
| ------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| T-1.3-B-UNIT-01     | backend unit (pure)           | `backend/tests/services/publications/test_etag.py`                                                    |
| T-1.3-B-UNIT-02     | backend unit (pure)           | `backend/tests/services/publications/test_etag.py`                                                    |
| T-1.3-B-INT-01      | backend integration (PG)      | `backend/tests/integration/test_publications_patch_etag.py` (new file; integration dir is greenfield) |
| T-1.3-B-INT-02      | backend integration (PG)      | `backend/tests/integration/test_publications_patch_etag.py`                                           |
| T-1.3-B-INT-03      | backend integration (PG)      | `backend/tests/integration/test_publications_patch_etag.py` (skip-marker if Q3 flips to "require")    |
| T-1.3-F-UNIT-01     | frontend unit                 | `frontend-public/src/lib/api/__tests__/admin.test.ts` (or sibling next to `admin.ts`)                 |
| T-1.3-F-INT-01      | frontend real-wire integration| `frontend-public/src/components/editor/__tests__/autosave-precondition.test.tsx`                      |

Total: **7** stable IDs. Impl prompts in D2/D3/D4 should reference these
IDs verbatim rather than re-describing the assertions.

---

## 3. Summary Report

```
DOC PATH: docs/recon/phase-1-3-D1-tests.md
Backend unit tests: 2
Backend integration tests: 3 (1 conditional on Q3)
Frontend unit tests: 1
Frontend real-wire integration: 1
Total IDs: 7
Critical fixture requirements documented: yes
VERDICT: COMPLETE
```

---

**End of Part D1.**
