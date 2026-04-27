# Deployment & Operations — Infrastructure Reference

**Status:** Living document — update on every infra/deploy/CI change
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Sources:** Memory items, ROADMAP_v8_FINAL.md, DEPLOYMENT_READINESS_CHECKLIST.md (in-repo)
**Related:** `DEPLOYMENT_READINESS_CHECKLIST.md` (go-live checklist), `BACKEND_API_INVENTORY.md` (endpoints), `TEST_INFRASTRUCTURE.md` §2.6 (integration test environment)

**Maintenance rule:** any PR that changes Docker config, PostgreSQL version, scheduler config, S3 setup, CI workflow, or deploy procedure MUST update this file in the same commit. Drift signal: if a memory item references infra detail (port, version, env var) not listed here, this file is stale.

## Scope

- §2 — Dev environment (local Windows/PowerShell)
- §3 — Docker Compose services
- §4 — PostgreSQL configuration
- §5 — Scheduler (APScheduler + SQLAlchemyJobStore)
- §6 — S3 storage abstraction
- §7 — CI workflow split (Level 1 + Level 2)
- §8 — Production deploy procedure (placeholder until first deploy)

For go-live readiness items, see `DEPLOYMENT_READINESS_CHECKLIST.md`.

**Security note:** this document captures STRUCTURE only. Production values (DB passwords, S3 bucket names, API keys) are NOT in this file. Source: env vars + secrets manager.

## 2. Dev environment (local)

### Platform

**Source:** memory item, ROADMAP §2.3.

- **OS:** Windows / PowerShell (NOT Unix shell)
- **Tools assuming Unix shell are friction.** Prompts and scripts must be PowerShell-compatible OR cross-platform.
- **bash-only commands** in agent prompts are an anti-pattern when those commands run on founder's machine. Always provide PowerShell equivalents OR ensure command runs in container.

### Standard layout

- Monorepo at `C:\B\summa_vision\Summa-vision-can`
- Backend: `backend/`
- Frontend public: `frontend-public/`
- Flutter admin: `frontend/` (Dart/Flutter app)

### Standard commands

PowerShell run-tests pattern (memory item):
```powershell
# Backend test run
cd backend
poetry run pytest -v

# Frontend public test run
cd frontend-public
npm test

# Flutter admin test run
cd frontend
flutter test
```

(Adapt to actual project commands — these are illustrative.)

## 3. Docker Compose services

### Dev environment

**Source:** memory item.

Docker Compose configures dev infrastructure. Standard services (subject to confirmation from compose file):
- `postgres` — PostgreSQL database
- `redis` — caching / rate-limiting (if used; confirm from compose)
- `minio` — S3-compatible storage for local dev (if S3 abstraction enabled in dev)
- `scheduler` — APScheduler worker (may run in same process as API in dev)

### Standard ports (DEV — local only)

(Confirm exact ports from `docker-compose.yml`. Document here as DEV ports, redacted production.)

| Service | Dev port | Notes |
|---|---|---|
| PostgreSQL | 5432 | Default Postgres port; bound to localhost only |
| Redis | 6379 | If used |
| MinIO | 9000 + 9001 | If used; 9000 API, 9001 console |
| Backend API | 8000 | FastAPI dev server |
| Frontend public | 3000 | Next.js dev server |

### Bring up + tear down

```powershell
docker-compose up -d
docker-compose down
docker-compose down -v   # also drops volumes (use sparingly — drops dev DB)
```

## 4. PostgreSQL

### Version + features used

- PostgreSQL 14+ (confirm from project)
- Features: tsvector + GIN full-text search (memory item), pg_trgm trigram extension
- Enum types: PostgreSQL native enums (NOT Python enum-as-string), see migration rules below

### Dev credentials

**DEV ONLY. Production uses secrets manager.**

- Database name: `summa`
- Username/password: `summa` / `devpassword` (memory item)
- Host: localhost in dev; secrets in prod

### Migration rules (Alembic)

**Source:** memory items.

1. Use `subprocess.run(['alembic', 'upgrade', 'head'])` in tests — NOT programmatic Alembic API. Programmatic conflicts with `pytest-asyncio`. (See `TEST_INFRASTRUCTURE.md` §2.6.)
2. Teardown: `alembic downgrade base` — NOT `Base.metadata.drop_all`. The Alembic path drops PostgreSQL enum types; `drop_all` does not.
3. Enum migrations require `postgresql.ENUM(..., create_type=False)` with `checkfirst=True` everywhere they appear.
4. Naming convention for Alembic revisions: timestamp + descriptive slug (confirm project convention).

### Postgres-specific patterns in queries

- FTS: `to_tsvector('english', column)` with GIN index for search
- Trigram similarity: `column % 'query'` with GIN index using gin_trgm_ops
- JSON columns: `JSONB` (not `JSON`) for indexable nested queries
- Timestamp columns: `TIMESTAMP WITH TIME ZONE`, stored as UTC

## 5. Scheduler (APScheduler)

### Architecture

**Source:** memory item, ROADMAP_v8_FINAL.md.

- APScheduler with `SQLAlchemyJobStore` — jobs persisted to Postgres, survive restarts
- Single scheduler instance (NOT distributed) — at single-operator scale, no need for distributed worker pool
- Lifespan-managed in FastAPI: scheduler starts in `app.lifespan` startup, shuts down gracefully on shutdown

### Job retry / zombie reaper

- Stale-aware zombie reaper runs once on startup (per `ROADMAP_v8_FINAL.md:295`). Reaper kills jobs in RUNNING state past stale threshold; does NOT list them for inspection.
- Phase 2.5 Exception Inbox plans listing for zombies — see `BACKEND_API_INVENTORY.md` §1 for endpoint details when added.

### Concurrency primitives (lifespan-init)

`ROADMAP_v8_FINAL.md:295` mentions:
- `data_sem(2)` — concurrency limit for data fetch jobs
- `render_sem(2)` — concurrency limit for render/export jobs
- `io_sem(10)` — concurrency limit for general I/O

Initialized in `src/main.py` lifespan. Constructor DI per ARCH-DPEN-001 (see `ARCHITECTURE_INVARIANTS.md` §2).

### Graceful shutdown (R20)

Scheduler lifespan registers shutdown hook. In-flight jobs complete (with timeout); new jobs blocked.

## 6. S3 storage abstraction

### Abstraction layer

**Source:** memory item.

S3 storage abstracted behind a `StorageClient` interface (constructor DI per ARCH-DPEN-001). Concrete impls:
- `MinIOStorageClient` for dev (Docker)
- `S3StorageClient` for prod (AWS S3 / R2 / equivalent)
- Test fakes (in-memory) for unit tests

### Use cases

- Generated PNG outputs (per-preset)
- Cube data Parquet files
- Distribution ZIP packages (Phase 2.2)
- Background images, palette assets

### Key conventions

- Keys are hierarchical: `<resource_type>/<resource_id>/<filename>`
- Temp uploads: `temp/uploads/<key>` with TTL (cleanup via `temp_cleanup.py`)
- Versioned outputs: `publications/<pub_id>/<config_hash>/<preset>.png` (R19 lineage in path)

### temp_cleanup.py rules

**Source:** memory item, DEBT-021.

`temp_cleanup.py` deletes temp uploads older than TTL. MUST exclude keys still referenced by queued/running `graphics_generate` jobs before deletion. Otherwise `STORAGE_NOT_FOUND` failures on delayed processing.

(Memory item: DEBT-021 fully resolved 2026-04-25 with FR2-FR8 fixes.)

## 7. CI workflow

### Two-level split

**Source:** memory item.

CI is split into Level 1 + Level 2:
- **Level 1:** fast checks — unit tests, linters, type-check. Runs on every PR push.
- **Level 2:** integration tests with Testcontainers (PostgreSQL), end-to-end-ish tests. May run on push to main + nightly + manual dispatch.

(Confirm exact workflow file paths from `.github/workflows/`.)

### Integration tests location

- All in `backend/tests/integration/`
- Use Testcontainers PostgreSQL, `subprocess` Alembic upgrade (see §4 + `TEST_INFRASTRUCTURE.md` §2.6)

### Flutter test workflow

- Workflow file: `.github/workflows/frontend-admin.yml` (memory item)
- Runs `flutter test` (default — multi-isolate, NOT `--concurrency=1`)
- Multi-isolate concurrency means tests must be safe under parallel execution. See `TEST_INFRASTRUCTURE.md` §3.8.

### Frontend public test workflow

- Confirm workflow file (likely `.github/workflows/frontend-public.yml`)
- Jest + RTL standard setup

## 8. Production deploy procedure

**Status:** Placeholder until first production deploy completes. This section will be filled by the first deploy PR.

Required content (when filled):
- Hosting provider (decided + tracking)
- Deploy method (Docker image push? VPS rsync? Platform-as-Service?)
- Database migration step (timing + rollback procedure)
- Environment variable management (secrets manager + access pattern)
- Frontend deploy (Vercel? Cloudflare Pages? Self-hosted?)
- DNS / CDN configuration
- Smoke test checklist post-deploy
- Rollback procedure with timing constraints
- On-call / monitoring setup (which metrics, which alerts)

Cross-ref `DEPLOYMENT_READINESS_CHECKLIST.md` for go-live items.

DO NOT remove this placeholder. The placeholder itself is a signal that production deploy procedure has not been documented.

## 9. Phase 1.3 — DEBT-042 hardening flip

**One-time procedure.** Phase 1.3 ships with `PATCH /admin/publications/{id}` in tolerate-absent mode for the `If-Match` header (warn-log + proceed). This avoids breaking old browser tabs mid-deploy. After the deploy window stabilises, the handler must be hardened to require `If-Match` and return 428 Precondition Required when absent.

**Trigger:** at least 2 weeks after Phase 1.3 production deploy AND 7 consecutive days of negligible warn-log volume on the `patch_publication_missing_if_match` codepath.

**Verification before flipping:**

1. Read warn-log volume for the trailing 7 days:

   ```bash
   # backend log query — adapt to actual log infra
   grep -c "patch_publication_missing_if_match" <log-source-for-trailing-7d>
   ```

2. Volume MUST be near-zero. If non-negligible, extend the toleration window rather than breaking active clients. A non-negligible volume indicates either old frontend tabs still in flight OR a frontend regression that stopped sending `If-Match`.

3. If volume is near-zero, proceed to the flip.

**The flip (single PR):**

1. In `backend/src/api/routers/admin_publications.py`, change the `if_match is None` branch from warn-log + proceed to:

   ```python
   if if_match is None:
       raise HTTPException(
           status_code=status.HTTP_428_PRECONDITION_REQUIRED,
           detail={
               "error_code": "PRECONDITION_REQUIRED",
               "message": "If-Match header is required for this endpoint.",
           },
       )
   ```

   (Or use a typed `PublicationPreconditionRequiredError` mirroring `PublicationPreconditionFailedError` — preferred, follows the existing exception class pattern.)

2. Update `BACKEND_API_INVENTORY.md` PATCH row: change "If-Match recommended in v1 (tolerated absent per DEBT-042)" to "If-Match required; absent → 428 Precondition Required".

3. Mark DEBT-042 as `Status: resolved` with the resolving PR # and date in the Resolution field.

4. Update `ARCHITECTURE_INVARIANTS.md` §7 "v1 tolerate-absent posture" subsection: replace with "Required as of <PR#>; missing If-Match returns 428."

**No client-side change needed for the flip.** All Phase 1.3 client paths already send `If-Match` from the seeded `etagRef`. The flip hardens the contract on the server side; clients that were correctly sending `If-Match` continue to work unchanged. Clients that were relying on tolerate-absent (e.g. an unfixed Phase 1.3 regression in the seed path) will start receiving 428s and surface as user-visible breakage — which is the desired signal.

## 10. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from aggregated memory items + ROADMAP_v8_FINAL.md infra references |
