# Test Infrastructure — Patterns and Conventions

**Status:** Living document — update on every PR that introduces a new test pattern or hits a new failure mode
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Source:** Memory items aggregated from Phase 1.1, 1.4, 1.5, DEBT-030, Slice 3.8

**Maintenance rule:** any PR that hits a new test-flake mode, fixture pattern, or test-runner gotcha MUST update this file in the same commit. The point is that the next agent doesn't re-discover the same lesson on a different PR.

## How to use this file

- Pre-recon prompts MUST point to this file when planning tests for a new endpoint, screen, or notifier.
- Impl prompts MUST cite the specific section a test pattern is drawn from (e.g. "fixture follows §2.3 pattern").
- Agents reading this MD are NOT allowed to deviate from documented patterns silently. If a test would violate a pattern here, the impl prompt must call this out and either pre-approve or update the MD in the same PR.

This file is split by stack:
- §2 — Backend (Python / FastAPI / SQLAlchemy / Testcontainers)
- §3 — Flutter (Dart / flutter_test / Riverpod / Hive)
- §4 — Frontend Next.js (React / Jest / fetch mocking)
- §5 — Cross-cutting principles (diagnostic-first, real-wire integration, etc.)

## 2. Backend testing

### 2.1 Custom RequestValidationError handler must use jsonable_encoder

**Source:** DEBT-030 PR1 hotfix.

FastAPI custom `RequestValidationError` handler MUST wrap `exc.errors()` in `jsonable_encoder()` before `JSONResponse(...)`. Pydantic v2's `.errors()` can include `ctx.error` as a raw `ValueError` exception object (non-JSON-serializable), causing TypeError → expected 422 becomes unhandled 500.

The default FastAPI handler uses `jsonable_encoder`; custom handlers MUST do same.

```python
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

return JSONResponse(
    status_code=422,
    content=jsonable_encoder({
        "detail": {
            "error_code": "...",
            "message": "...",
            "details": {"validation_errors": exc.errors()},
        }
    }),
)
```

This applies to ALL custom JSON-returning exception handlers, not only validation. Examples: 412 PreconditionFailed handler in Phase 1.3, future 409 Conflict, etc.

### 2.2 jsonable_encoder behavior on non-serializable Python objects

**Source:** DEBT-030 PR1 round 1 hotfix.

`jsonable_encoder` is NOT `str()` coercion. For arbitrary Python objects, FastAPI's `jsonable_encoder` uses vars()-based dict conversion. `ValueError(msg)` becomes `{}` (no instance attrs). Pydantic v2 wraps this in `ctx.error` of validation errors.

**Test contract:** assert JSON-roundtrip + presence of useful info (loc, msg, type) — NOT `ctx.error is str`. The real message lives in `err.msg` root field, not in `ctx.error`.

### 2.3 Endpoint integration test fixture must override ALL deps

**Source:** Phase 1.1 PR165.

Endpoint integration test fixture must override every `Depends(...)` the endpoint uses, not just service-level deps.

PR165 example: clone endpoint depends on `get_db` (raw session); test app only overrode `_get_repo`/`_get_audit`, so endpoint hit prod DB pool in test event loop → asyncpg "attached-to-different-loop" errors + 404s.

Fix: `app.dependency_overrides[get_db] = _override_db` with session_factory.

When endpoint uses `Depends(get_db)` directly, fixture MUST override `get_db`, not just service deps.

### 2.4 Test fixture creating own FastAPI app must mirror main.py wiring

**Source:** DEBT-030 PR1.

Test `_make_app()` missed `register_exception_handlers()` call, so custom RequestValidationError handler never registered for tests → test got default `{detail:[...]}` envelope, expected `{detail:{error_code,...}}`, TypeError on dict access.

For any new handler/middleware in `main.py`, audit all test fixtures building app independently — same wiring required or test diverges from prod.

Checklist for test fixtures:
- `register_exception_handlers()` called
- All middleware in `main.py` order replicated
- Same dependency overrides for `get_db` and any other infrastructure deps

### 2.5 Sandbox tests may fail due to missing pytest plugins

**Source:** DEBT-030 PR1.

When all tests error with the same root cause (e.g. missing `pytest-asyncio`), suspect environment before code.

Validate via:
```bash
python -c "from X import Y"  # import smoke
pytest --collect-only         # collection without run
```

If both succeed, code is structurally sound — push to CI for real validation. CI is source of test truth.

### 2.6 Integration test environment

- **PostgreSQL via Testcontainers**, not SQLite
- Migrations: use `subprocess.run(['alembic', 'upgrade', 'head'])` — NOT programmatic Alembic API. Programmatic API conflicts with `pytest-asyncio`.
- Teardown: `alembic downgrade base` (drops PostgreSQL enum types) — NOT `Base.metadata.drop_all` (leaves enum types behind, breaks rerun).
- Enum migrations require `postgresql.ENUM(..., create_type=False)` with `checkfirst=True` everywhere they appear.

### 2.7 Async mocking

- Use `AsyncMock` for all async test mocks. `MagicMock` for async returns silently produces unawaited-coroutine warnings that don't fail tests but break behavior.

---

**End of Part 1. Sections 3-6 added by Part 2.**
