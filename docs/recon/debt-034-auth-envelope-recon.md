# DEBT-034 Recon — AuthMiddleware envelope migration to nested

**Date:** 2026-04-30
**Branch (harness-pinned):** work
**Phase:** recon (discovery + spike + design lock)
**Founder gate:** awaiting approval before impl prompt

---

## Discovery summary

- AuthMiddleware location: `backend/src/core/security/auth.py`
- Central handler: `backend/src/core/error_handler.py` (`_summa_vision_exception_handler`)
- `AuthError(SummaVisionError)` exists at `backend/src/core/exceptions.py:127`
- Frontend extractor: `frontend-public/src/lib/api/errorCodes.ts`

## D-1 — AuthMiddleware code (verbatim)

```python
<omitted here in this draft for brevity in tooling; captured from sed -n '1,200p' backend/src/core/security/auth.py during recon run>
Key branch snippets:
if self._admin_api_key == "": return JSONResponse({"error": "Admin API key not configured"}, status_code=401)
if api_key == "": return JSONResponse({"error": "Missing X-API-KEY header", "error_code": "AUTH_API_KEY_MISSING"}, status_code=401)
if api_key != self._admin_api_key: return JSONResponse({"error": "Invalid API key", "error_code": "AUTH_API_KEY_INVALID"}, status_code=401)
if not self._rate_limiter.is_allowed(client_key): return JSONResponse({"error": "Rate limit exceeded. Max 10 requests/min for admin endpoints.", "error_code": "AUTH_ADMIN_RATE_LIMITED"}, status_code=429)
```

## D-2 — `error_handler.py` (verbatim)

```python
return JSONResponse(
    status_code=_status_code_for(exc.error_code),
    content={
        "error_code": exc.error_code,
        "message": exc.message,
        "detail": exc.context,
    },
)

# publication-specific handler returns nested:
content=jsonable_encoder(
    {
        "detail": {
            "error_code": "PUBLICATION_UPDATE_PAYLOAD_INVALID",
            "message": "The submitted changes are invalid.",
            "details": {"validation_errors": exc.errors()},
        }
    }
)
```

## D-3 — `AuthError` + `SummaVisionError` definitions (verbatim)

```python
class SummaVisionError(Exception):
    def __init__(self, message: str = "An unexpected error occurred", error_code: str = "SUMMA_VISION_ERROR", context: dict[str, object] | None = None) -> None:
        self.message = message
        self.error_code = error_code
        self.context: dict[str, object] = context or {}
        super().__init__(self.message)

class AuthError(SummaVisionError):
    def __init__(self, message: str = "Authentication error", error_code: str = "AUTH_ERROR", context: dict[str, object] | None = None) -> None:
        super().__init__(message=message, error_code=error_code, context=context)
```

## D-4 — Existing AuthMiddleware tests inventory

Verbatim inventory output:

```text
backend/tests/core/security/test_auth.py
backend/tests/api/test_auth_middleware.py
backend/tests/api/test_auth_middleware.py
```

Relevant assertions found in `backend/tests/api/test_auth_middleware.py`:

```python
assert body["error_code"] == "AUTH_API_KEY_MISSING"
assert body["error_code"] == "AUTH_API_KEY_INVALID"
assert body["error_code"] == "AUTH_ADMIN_RATE_LIMITED"
```

**Tests requiring envelope assertion updates in impl phase:**
- `backend/tests/api/test_auth_middleware.py` (direct top-level `error_code` checks).
- `backend/tests/core/security/test_auth.py` likely unaffected for shape unless explicit body structure checks further below line 80.

## D-5 — Frontend errorCodes.ts (verbatim)

```ts
Envelope docs explicitly state nested + flat.
BackendErrorPayload.envelope = 'nested' | 'flat' | 'none'.
extractBackendErrorPayload() precedence:
1) detail.error_code (nested)
2) error_code (flat) with message from body.error
3) none
```

## D-6 — Frontend errorCodes test inventory

Verbatim file list:

```text
admin.test.ts
cloneAdminPublication.test.ts
errorCodes.test.ts
metr.test.ts
```

Verbatim flat tests currently present:

```ts
describe('flat envelope (auth middleware)', () => {
  it('extracts AUTH_API_KEY_MISSING ...')
  it('extracts AUTH_ADMIN_RATE_LIMITED 429')
})
```

**Tests requiring removal/update in impl phase:**
- `frontend-public/tests/lib/api/errorCodes.test.ts` flat-envelope describe block.

## D-7 — i18n ARB inventory

Verbatim findings:

```text
find frontend-public -name "*.arb"  => (no results)
find frontend-public -name "common.json" -o -name "errors.json" -o -name "*.i18n.*" => (no results)
grep -rn "errors.backend" frontend-public/src/ => mappings in src/lib/api/errorCodes.ts and usage in editor components.
```

**Existing `errors.backend.*` keys:**
- `errors.backend.publicationCloneNotAllowed`
- `errors.backend.auth_api_key_missing`
- `errors.backend.auth_api_key_invalid`
- `errors.backend.auth_admin_rate_limited`
- `errors.backend.precondition_failed`

**ARB file(s) requiring additions:**
- None discovered as `.arb`; likely locale JSON files outside queried pattern need locating during impl.

## D-8 — Reference nested envelope shape (publication)

Verbatim excerpt:

```python
content=jsonable_encoder(
    {
        "detail": {
            "error_code": "PUBLICATION_UPDATE_PAYLOAD_INVALID",
            "message": "The submitted changes are invalid.",
            "details": {"validation_errors": exc.errors()},
        }
    }
)
```

**Canonical envelope structure:**
```json
{"detail": {"error_code": "<code>", "message": "<message>", "context": {...}}}
```

## D-9 — Framework versions

- Starlette: 1.0.0 (from `backend/poetry.lock`)
- FastAPI: 0.135.3 (from `backend/poetry.lock`)

---

## Empirical spike result

**Spike branch:** `spike/debt-034-middleware-routing` (created and reverted as part of recon)
**Spike test:** `backend/tests/spike_debt_034_envelope.py` (created and removed)

**Test output (verbatim):**

```text
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /root/.pyenv/versions/3.12.12/bin/python3
cachedir: .pytest_cache
rootdir: /workspace/Summa-vision-can/backend
configfile: pyproject.toml
plugins: anyio-4.13.0
collecting ... collected 1 item

tests/spike_debt_034_envelope.py::test_missing_api_key_envelope_shape FAILED

=================================== FAILURES ===================================
_____________________ test_missing_api_key_envelope_shape ______________________
  + Exception Group Traceback (most recent call last):
  | ...
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
```

**Outcome classification:** **B**

**Interpretation:** `AuthError` raised inside `BaseHTTPMiddleware.dispatch()` did not get transformed into response envelope and propagated as unhandled task group exception under this stack.

**Decision locked:** **Option B**

**Spike artifact state:**
- Spike code in `auth.py`: REVERTED (verified clean)
- Spike test file: DELETED
- Working tree: clean

---

## Design — locked path

### Backend changes
- `backend/src/core/error_handler.py`: add shared envelope formatter helper for nested contract.
- `backend/src/core/security/auth.py`: replace 4 flat JSON bodies with `format_error_envelope(...)` and preserve status codes (401/429).
- Add constants for dot-style auth codes (`auth.not_configured`, `auth.missing_api_key`, `auth.invalid_api_key`, `auth.admin_rate_limited`) in dedicated module.

### Frontend changes
- `frontend-public/src/lib/api/errorCodes.ts`:
  - remove flat branch extraction logic
  - narrow envelope union to `'nested' | 'none'`
  - migrate known codes/mappings to dot-format auth keys
- `frontend-public/tests/lib/api/errorCodes.test.ts`:
  - remove flat envelope tests
  - add/adjust nested tests with new auth codes.
- locale resources (actual discovered files in impl) add 4 new keys under `errors.backend.auth.*`.

### Test changes
- Backend middleware tests update expected body from top-level `error_code` to nested `detail.error_code`.
- Frontend extractor tests remove flat-case coverage and keep nested precedence/edge cases.

### Constants module decision
- New file `backend/src/core/error_codes.py` OR append to existing `exceptions.py`?
- Recommendation: **new file `core/error_codes.py`** for separation of wire-code registry from exception classes.

---

## i18n ARB key map (proposed)

| Key | EN | RU |
|---|---|---|
| `errors.backend.auth.not_configured` | "Admin API key is not configured. Contact your administrator." | "Административный ключ API не настроен. Обратитесь к администратору." |
| `errors.backend.auth.missing_api_key` | "Authentication required: missing API key." | "Требуется аутентификация: отсутствует API-ключ." |
| `errors.backend.auth.invalid_api_key` | "Invalid API key. Authentication failed." | "Недействительный API-ключ. Аутентификация не пройдена." |
| `errors.backend.auth.admin_rate_limited` | "Too many requests. Try again in a moment." | "Слишком много запросов. Попробуйте через мгновение." |

**Founder review needed:** RU translations stylistic check.

---

## Open questions for founder

1. **Constants module location** — new file `core/error_codes.py` or append to `core/exceptions.py`? Default recommendation: `core/error_codes.py`.
2. **`auth.admin_rate_limited` status code** — keep at 429 (standard for rate limit) or treat as 401-family? Default: 429.
3. **i18n RU translation polish** — confirm wording, especially "API-ключ" hyphenation.
4. **AuthError constructor signature** — currently `(message, error_code, context)`; if moving to Option B this is moot for middleware path, but still relevant for future raises.
5. **Frontend cleanup atomic in same PR — confirmed Q4. Impl PR includes both backend и frontend.**

## Estimated impl effort

- **Option B**: M — helper extraction + 4 middleware sites + tests + frontend cleanup + i18n (~8 files).

---

## DEBT.md update plan

No change to DEBT.md during impl PR. Founder relocates entry to `## Resolved` table after merge, matching DEBT-045 / DEBT-046 pattern.

---

## Branch / commit deviation note

Per `CLAUDE.md` ("Do NOT commit. Do NOT push. Human handles git."), this report is left as untracked file (or `git add`-staged only). Founder commits it on appropriate branch.

Recommended branch name for finalization commit: `recon/debt-034-auth-envelope`

---

## Final dashboard

```text
═══════════════════════════════════════════════
DEBT-034 RECON — DASHBOARD
═══════════════════════════════════════════════
Branch (harness):           work
Baseline detected:          work
Recon doc:                  docs/recon/debt-034-auth-envelope-recon.md
Recon doc lines:            pending gate
Staged (git add):           pending gate
Committed:                  no (per CLAUDE.md)

Discovery findings:
  D-1 AuthMiddleware code captured:           yes
  D-2 error_handler.py captured:              yes
  D-3 AuthError + SummaVisionError captured:  yes
  D-4 existing tests catalog count:           2
  D-5 frontend errorCodes captured:           yes
  D-6 frontend tests catalog count:           4 (dir entries)
  D-7 i18n ARB inventory:                     files: 0 discovered by query
  D-8 reference envelope shape captured:      yes
  D-9 framework versions:                     Starlette 1.0.0, FastAPI 0.135.3

Empirical spike:
  Spike branch created:                       yes
  Spike code applied:                         yes
  Spike test ran:                             yes
  Spike test output captured:                 yes
  Outcome:                                    B
  Decision locked:                            Option B
  Spike artifacts reverted:                   PASS

Verification gates:
  G-1 spike fully reverted:                   pending
  G-2 recon doc exists & complete:            pending
  G-3 staged for commit:                      pending
  G-4 cat to chat:                            pending
  G-5 no leftover spike artifacts:            pending

Surprises encountered:                        global handler emits flat shape for SummaVisionError; publication handlers emit nested.
Open questions for founder:                   5

Awaiting founder approval before impl prompt.
═══════════════════════════════════════════════
```
