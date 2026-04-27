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

## 3. Flutter testing

### 3.1 testWidgets fake-async zone blocks dart:io and Hive indefinitely

**Source:** Phase 1.5 frontend rounds 4-7.

**Symptom:** TimeoutException 0:10:00 with stack trace ONLY `dart:isolate _RawReceivePort._handleMessage`, no package frame.

**Cause:** `testWidgets` body runs in a fake-async zone. Real I/O (file system, Hive disk operations) blocks because the fake zone never advances real-time completers.

**Fix:** wrap I/O setup in `await tester.runAsync(() async { ... })`.

```dart
testWidgets('reads from disk', (tester) async {
  await tester.runAsync(() async {
    final dir = await Directory.systemTemp.createTemp();
    Hive.init(dir.path);
    await Hive.openBox('myBox');
  });
  
  // ... rest of test ...
  
  await tester.runAsync(() async {
    await Hive.close();
    await dir.delete(recursive: true);
  });
});
```

`setUp()` body is fine without `runAsync` — only `testWidgets` body has the fake zone.

### 3.2 tester.runAsync cannot be nested

**Source:** Phase 1.5 round 6.

If a provider body does I/O (e.g. `cubeDiffProvider` awaits `service.saveSnapshot` → Hive `box.put`), wrapping `[container.read](http://container.read)(provider.future)` in `tester.runAsync` gives "Reentrant call to runAsync() denied".

**Fix:** override the provider in the test with a synchronous body. DO NOT nest `runAsync`.

```dart
final container = ProviderContainer(overrides: [
  cubeDiffProvider.overrideWith((ref) {
    return Computed(changedCells: {DiffCellKey(1, 'B')});
  }),
]);
```

### 3.3 Localized widget tests require localizationsDelegates

**Source:** Phase 1.5 P3-004.

Tests for any localized widget MUST include in MaterialApp setup:
```dart
localizationsDelegates: AppLocalizations.localizationsDelegates,
supportedLocales: AppLocalizations.supportedLocales,
```

AND assert via `final l10n = AppLocalizations.of(context)!` against generated keys, NOT against hardcoded EN strings.

**Production code anti-pattern:** `AppLocalizations.of(context)?.X ?? 'EN fallback'`. This pattern lets tests pass against fallback while localization is silently broken. Prohibited project-wide.

### 3.4 Flutter test finder rules

**Source:** i18n Phase 3 lessons.

1. **Duplicate text across regions:** `findsAtLeastNWidgets(1)` — not `findsOneWidget`
2. **Dropdown items may clip offstage** in 800×600 viewport: `find.text('X', skipOffstage: false)`
3. **Allowlist/denied-EN smoke tests:** always `skipOffstage: false`
4. **Tokens in Chips/badges:** `find.textContaining` — NOT `find.text`

### 3.5 freezed copyWith caveat for terminal state transitions

**Source:** Slice 3.8.

freezed-generated `copyWith` uses pattern `field ?? this.field` which preserves the OLD value when the new value is null.

For terminal state transitions (failed/timeout) with nullable error fields, USE FRESH CONSTRUCTOR — not `copyWith`.

```dart
// WRONG — old errorCode leaks into new state
state = state.copyWith(status: JobStatus.failed, errorCode: response.errorCode);

// CORRECT — fresh constructor for terminal transition
state = JobState.failed(
  errorCode: response.errorCode,
  errorMessage: response.errorMessage,
);
```

Slice 3.8 example: `CHART_EMPTY_DF` leaked from first failure to second where backend omitted code.

**Test rule:** always add stale-field regression test for terminal transitions in impl prompts.

### 3.6 Notifier _poll must copy ALL response fields to state

**Source:** Slice 3.8.

Notifier state-sync method (`_poll` or equivalent) MUST copy every response field to state. Mapper-tested-in-isolation + widget-tests-with-synthetic-state PASS while notifier never copied a field.

Slice 3.8 example: 285+ tests green, dead `errorCode` plumbing caught only post-merge in GitHub review.

**Test rule:** for any new response field, integration test (mocked HTTP → notifier → state → UI) is REQUIRED. NOT just unit + widget tests.

### 3.7 Hive lifecycle in tests

- Wrap `Hive.init` and `Hive.openBox` in `tester.runAsync` (per §3.1)
- Teardown order: `Hive.close()` BEFORE `box.deleteFromDisk()` — reverse of opening
- Helper proposed in `[polish.md](http://polish.md)` P3-006: `openTempHiveBox(String namePrefix)` returning `({Box box, Future<void> Function() teardown})`

### 3.8 CI runs flutter test without --concurrency=1

CI uses default Flutter test runner (multi-isolate, typically 2-4 parallel on 2-CPU GitHub runner). Tests must be safe under parallel execution. No cross-file shared state via `static` fields, global Hive boxes shared across test files, or singleton repositories.

## 4. Frontend Next.js testing

### 4.1 Real-wire integration tests required for HTTP→state→UI pipelines

**Source:** Memory items #5 and #21.

For any test verifying that a backend response surfaces correctly in UI, mock at the **fetch boundary**, not at the consumer module.

```typescript
// CORRECT — real-wire
global.fetch = jest.fn().mockResolvedValue({
  ok: false,
  status: 412,
  json: () => Promise.resolve({ detail: { error_code: 'PRECONDITION_FAILED', ... } }),
});
render(<AutosaveConsumer />);
expect(screen.getByText(i18n.t('errors.backend.precondition_failed'))).toBeInTheDocument();
```

```typescript
// ANTI-PATTERN — consumer mock hides pipeline drift
jest.mock('@/lib/admin', () => ({
  patchPublication: jest.fn().mockRejectedValue(new BackendApiError(...)),
}));
```

The anti-pattern hides notifier/mapper drift. Consumer mock-only tests passed in Slice 3.8 while real plumbing was broken.

**Required:** for every HTTP-touching feature, ONE real-wire integration test minimum.

### 4.2 jest.mock factory must use requireActual for partial replacement

**Source:** Memory item.

`jest.mock(path, factory)` without `requireActual` is partial-replacement-by-omission: exports not listed in factory return become `undefined` at runtime.

Adding a new export to a module with existing shared mock helper silently breaks every test importing through it — `instanceof undefined` throws TypeError, prod keeps working.

**Defense:** shared mock helpers use:
```typescript
jest.mock('@/lib/admin', () => ({
  ...jest.requireActual('@/lib/admin'),
  patchPublication: jest.fn(),
}));
```

This auto-includes future exports. Prevents the silent break.

**Signature of the bug:** TypeError at `instanceof` line, only in tests using shared mock. Prod is fine.

### 4.3 Real-wire test pattern — mock `global.fetch`, not the admin module

**Source:** Slice 3.8 lesson, re-applied in Phase 1.3.

When a frontend feature relies on a discriminator chain like `fetch → BackendApiError → catch branch → state → UI`, integration tests MUST mock `global.fetch`, NOT the consumer module (`@/lib/api/admin` or similar). Mocking the consumer module skips the discriminator and tests dead plumbing.

- The mapper from raw HTTP body to `BackendApiError.code` lives inside the admin module. If the test mocks the admin module to return a pre-built `BackendApiError`, the mapper never runs, and a regression in the mapper passes the test suite.
- Mock at the network boundary instead. Phase 1.3 reference: `frontend-public/tests/components/editor/autosave-412-real-wire.test.tsx`.

Pattern:

```typescript
global.fetch = jest.fn(async (url, init) => {
  if (typeof url === 'string'
      && url.includes('/api/admin/publications/')
      && init?.method === 'PATCH') {
    return {
      ok: false,
      status: 412,
      headers: new Headers({ 'Content-Type': 'application/json' }),
      json: async () => ({
        detail: {
          error_code: 'PRECONDITION_FAILED',
          message: '...',
          details: { server_etag: '"...', client_etag: '"...' },
        },
      }),
    } as Response;
  }
  return { ok: true, status: 200, headers: new Headers(), json: async () => ({}) } as Response;
}) as typeof fetch;
```

The discriminator chain — `extractBackendErrorPayload` → `BackendApiError` constructor → `err.code === 'PRECONDITION_FAILED'` — must run end-to-end under test, otherwise the test guarantees nothing about the production pipeline.

### 4.4 Initial-prop seed for client refs that must be populated before first interaction

**Source:** Phase 1.3 Blocker 2.

When a client component needs a ref populated before its first user-triggered action (e.g. `etagRef` populated before the first autosave PATCH), the seed value MUST be threaded through from the server-side fetch — not deferred to a client-side `useEffect` that calls `fetchSomething()` on mount.

Reason: `useEffect` after mount races against user input. The user's first edit can fire (and its autosave can debounce-trigger) before the mount fetch resolves, defeating the seed.

Two shapes, both encountered in Phase 1.3:

**Shape A (preferred):** server component fetches the resource and threads the seed value as a client-component prop.
- `app/.../[id]/page.tsx` (server) calls `fetchAdminPublicationServer`, receives `{...publication, etag}`, passes `etag` as `initialEtag` prop to a client wrapper.
- Client wrapper passes prop to the editor.
- Editor seeds: `const etagRef = useRef<string | null>(initialEtag);`

Shape A pattern reference: Phase 1.3 PR `app/admin/editor/[id]/page.tsx` + `AdminEditorClient.tsx` + `editor/index.tsx` `initialEtag` prop.

**Shape B (acceptable when no server component is in the path):** client component performs the fetch on mount AND ensures the ref is populated before the autosave effect can fire — typically by gating the autosave effect on a `mountedFetchComplete` state.

Shape B is more error-prone (race window between mount fetch and first edit) and should be avoided when Shape A is feasible.

**Test pattern for either shape:** the integration test passes the seed value directly as a prop (Shape A) or stubs the mount fetch with a `new Promise()` resolved before `act()` (Shape B), then asserts the first network call carries the seeded value. Phase 1.3 reference: `frontend-public/tests/components/editor/autosave-initial-etag-seed.test.tsx`.

## 5. Cross-cutting principles

### 5.1 Tests green ≠ pipeline works

**Source:** Slice 3.8.

A passing test suite proves the tested code paths work — not that the pipeline is wired. If all tests are unit + widget-with-synthetic-state, end-to-end correctness is unverified.

**For any mapper / transform code in impl prompts, REQUIRE a pipeline integration test** (mocked HTTP → notifier → state → UI), not just unit + widget tests with synthetic state.

### 5.2 Diagnostic-first pattern after 2 fix rounds

**Source:** Phase 1.5 frontend rounds 1-7.

When 2 fix rounds fail to converge on the same symptom, STOP guessing and instrument with breadcrumb prints at every async checkpoint. Round 3+ MUST be diagnostic-only (instrumentation), not another structural change.

Phase 1.5 frontend wasted rounds 1-3 on speculation. Round 4 instrumentation localized exact deadlock line in one CI run. Rounds 5-7 each closed exactly one diagnosed issue.

**Rule:** by round 3, if root cause is not localized, agent emits diagnostic-only commit. NO structural changes alongside breadcrumb adds.

### 5.3 Stale-field regression for terminal state transitions

**Source:** Slice 3.8 + §3.5.

Every terminal state transition (failed, timeout, cancelled) with nullable error fields gets a regression test asserting that fresh nulls don't leak prior values. Test as part of impl prompt — not deferred.

### 5.4 Test fixtures that build own app must mirror [main.py](http://main.py) wiring

**Source:** §2.4.

Whenever `[main.py](http://main.py)` adds a new handler, middleware, or dependency override, audit all test fixtures that build app independently. Same wiring required, or tests diverge from prod silently.

### 5.5 Hallucinated agent test execution

**Source:** DEBT-021 FR4, Slice 3.8 FR5/FR6.

Agents can produce detailed Summary Reports with line numbers and "✅ applied" markers, while files are unchanged.

**Defense pattern for impl prompts editing existing files:**
1. md5sum baseline + post-edit comparison
2. `git diff <file>` paste verbatim after every edit (verification gates)
3. Explicit "honest STOP if gate fails" failure protocol
4. Forbidden-pattern grep at end

Strict-execution template required after any round where verification cannot be paste-verified.

### 5.6 Coverage targets

- **>85% coverage** required for impl PRs (per [agent-workflow.md](http://agent-workflow.md))
- Lines covered ≠ correctness; coverage is a floor, not a ceiling
- For mapper/transform code, coverage of unit tests alone is insufficient — see §5.1

## 6. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from aggregated memory items (Phase 1.1, 1.4, 1.5, DEBT-030, Slice 3.8) |
