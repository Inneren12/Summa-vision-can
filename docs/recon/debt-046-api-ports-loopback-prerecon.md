# DEBT-046 Pre-recon — api.ports loopback in base compose

**Date:** 2026-04-30
**Branch (harness-pinned):** work
**Baseline detected:** work
**Phase:** pre-recon (discovery only)
**Founder gate:** awaiting approval before impl prompt

---

## D-1 — Compose file inventory

```text
##D1_ls1
ls: cannot access 'docker-compose*.yaml': No such file or directory
-rw-r--r-- 1 root root 1771 Apr 30 01:25 docker-compose.dev.yml
-rw-r--r-- 1 root root 2157 Apr 30 02:04 docker-compose.yml
##D1_ls2
ls: cannot access 'compose*.yml': No such file or directory
ls: cannot access 'compose*.yaml': No such file or directory
##D1_find
./docker-compose.dev.yml
./docker-compose.yml
##D1_wc_mtime
70 ./docker-compose.dev.yml
2026-04-30 01:25:28.771631877 +0000 ./docker-compose.dev.yml
65 ./docker-compose.yml
2026-04-30 02:04:44.078417169 +0000 ./docker-compose.yml
```

**Files found:** `./docker-compose.dev.yml`, `./docker-compose.yml`
**Total compose files:** 2

## D-2 — Base `docker-compose.yml` ports sections

```text
##D2_ports
6:    ports:
##D2_ctx
1-services:
2-  api:
3-    build:
4-      context: ./backend
5-      dockerfile: Dockerfile
6:    ports:
7-      - "8000:8000"
8-    # NOTE: api.environment is an explicit whitelist — only the vars listed
9-    # below reach the container. Vars present in .env files but not enumerated
10-    # here are silently dropped. When backend Settings gains a new field that
11-    # must be runtime-configurable, add it here deliberately.
12-    environment:
```

**Services with `ports:` in base file:** `api`
**Current binding for api service:** `- "8000:8000"`
**Binding pattern:** `"8000:8000"`

## D-3 — Secondary compose files' ports sections

```text
##D3_./docker-compose.dev.yml
3-services:
4-  api:
5-    build:
6-      context: ./backend
7-      dockerfile: Dockerfile
8-    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
9:    ports:
10-      - "8001:8000"
11-    env_file:
12-      - ./backend/.env
13-    environment:
14-      STORAGE_BACKEND: s3
15-      # Dev-only fallback: localhost MinIO bucket. Production uses real CDN.
--
25-  db:
26-    image: postgres:16-alpine
27-    environment:
28-      POSTGRES_DB: ${POSTGRES_DB:-summa}
29-      POSTGRES_USER: ${POSTGRES_USER:-summa}
30-      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-devpassword}
31:    ports:
32-      - "5432:5432"
33-    volumes:
34-      - pgdata_dev:/var/lib/postgresql/data
35-    healthcheck:
36-      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-summa}"]
37-      interval: 10s
38-      timeout: 5s
39-      retries: 5
40-
41-  minio:
42-    image: minio/minio
43-    command: server /data --console-address ":9001"
44:    ports:
45-      - "9000:9000"   # S3 API
46-      - "9001:9001"   # Console
47-    environment:
48-      MINIO_ROOT_USER: minioadmin
49-      MINIO_ROOT_PASSWORD: minioadmin
50-    volumes:
```

**Override files redefine ports?:** yes (`docker-compose.dev.yml`)
**Dev override binding:** `- "8001:8000"`
**Prod override binding:** no prod override file in repo

## D-4 — IP-bind patterns

```text
##D4_127
rg: docker-compose*.yaml: No such file or directory (os error 2)
##D4_0000
rg: docker-compose*.yaml: No such file or directory (os error 2)
docker-compose.dev.yml:8:    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Explicit binds found:** `docker-compose.dev.yml:8 --host 0.0.0.0`
**Currently safe (loopback) bindings:** none in compose files
**Currently exposed (0.0.0.0) bindings:** `docker-compose.dev.yml:8 --host 0.0.0.0` (app bind)

## D-5 — Environment-variable port binding

```text
##D5
rg: docker-compose*.yaml: No such file or directory (os error 2)
rg: .env*: No such file or directory (os error 2)
```

**Env-var binding pattern in use?:** no evidence

## D-6 — All services with ports — programmatic inventory

```text
=== docker-compose.dev.yml ===
  api: ['8001:8000']
  db: ['5432:5432']
  minio: ['9000:9000', '9001:9001']
=== docker-compose.yml ===
  api: ['8000:8000']
```

**Services exposing ports across all compose files:**
| Service | File | Ports | Binding |
|---|---|---|---|
| api | docker-compose.yml | `8000:8000` | 0.0.0.0 (implicit) |
| api | docker-compose.dev.yml | `8001:8000` | 0.0.0.0 (implicit) |
| db | docker-compose.dev.yml | `5432:5432` | 0.0.0.0 (implicit) |
| minio | docker-compose.dev.yml | `9000:9000`, `9001:9001` | 0.0.0.0 (implicit) |

**Scope question for impl:** which of these need loopback treatment beyond `api`?
- postgres: yes in dev file if security-hardening scope includes all host-exposed services
- redis (if exists): n/a
- other: minio also host-exposed in dev compose

## D-7 — VPS override mechanism evidence

```text
##D7_1
##D7_2
##D7_3
##D7_4
-rw-r--r--  1 root root 15456 Apr 30 01:25 DEPLOYMENT_READINESS_CHECKLIST.md
-rw-r--r--  1 root root  6479 Apr 30 01:25 deployment.md
```

**VPS override mechanism (best-evidence determination):**
- (a) Separate compose file in repo: no direct evidence in this search output
- (b) Inline edit on VPS (drift): no evidence
- (c) Env-var substitution: no evidence
- (d) Other: insufficient evidence in queried files; only deployment docs presence detected

**If (b) — drift from repo:** n/a

## D-8 — VPS deploy runbook findings

```text
##D8_1
-rw-r--r-- 1 root root  1872 Apr 30 01:25 SESSION_HANDOFF.md
##D8_2
docs/recon/phase-1-3-D1-tests.md
docs/recon/phase-1-3-D4-polish-questions.md
docs/recon/phase-1-3-D3-debt.md
docs/recon/phase-1-3-C2c-frontend.md
docs/recon/phase-1-3-C1-etag.md
docs/recon/phase-1-3-C2d-backcompat.md
docs/recon/phase-1-3-B-frontend-inventory.md
docs/recon/phase-1-3-D2-migration.md
docs/recon/phase-1-3-A-backend-inventory.md
docs/architecture/FLUTTER_ADMIN_MAP.md
=== docs/recon/phase-1-3-D1-tests.md ===
6-**Date:** 2026-04-27
7-**Branch:** `claude/test-plan-stable-ids-qRUkg`
8:**Git remote:** `http://local_proxy@127.0.0.1:35025/git/Inneren12/Summa-vision-can`
9-
10-**Prereqs read:**
=== docs/recon/phase-1-3-D4-polish-questions.md ===
6-**Date:** 2026-04-27
7-**Branch:** `claude/polish-founder-questions-DNtrj`
8:**Git remote:** `http://local_proxy@127.0.0.1:41181/git/Inneren12/Summa-vision-can`
9-
10-This document is **READ-ONLY**. The P3-006 entry is **drafted** here for review
=== docs/recon/phase-1-3-D3-debt.md ===
6-**Date:** 2026-04-27
7-**Branch:** `claude/add-debt-section-h-CRfsZ`
8:**Git remote:** `http://local_proxy@127.0.0.1:44945/git/Inneren12/Summa-vision-can`
9-
10-**Prereqs read:**
=== docs/recon/phase-1-3-C2c-frontend.md ===
5-**Date:** 2026-04-27
6-**Branch:** `claude/frontend-412-error-modal-BK4eq`
7:**Git remote:** `http://local_proxy@127.0.0.1:34059/git/Inneren12/Summa-vision-can`
8-
9----
=== docs/recon/phase-1-3-C1-etag.md ===
218-
219-```
220:GIT REMOTE: http://local_proxy@127.0.0.1:34577/git/Inneren12/Summa-vision-can
221-DOC PATH: docs/recon/phase-1-3-C1-etag.md
222-
=== docs/recon/phase-1-3-C2d-backcompat.md ===
5-**Date:** 2026-04-27
6-**Branch:** `claude/backcompat-policy-design-CKQ4k`
7:**Git remote:** `http://local_proxy@127.0.0.1:44571/git/Inneren12/Summa-vision-can`
8-
9-**Cited references:**
=== docs/recon/phase-1-3-B-frontend-inventory.md ===
3-**Type:** READ-ONLY DISCOVERY
4-**Scope:** Next.js admin/editor code that the 412 client-side handling will touch.
5:**Git remote:** `http://local_proxy@127.0.0.1:44233/git/Inneren12/Summa-vision-can`
6-**Generated:** 2026-04-27
7-
--
347-
348-```
349:GIT REMOTE: http://local_proxy@127.0.0.1:44233/git/Inneren12/Summa-vision-can
350-DOC PATH:   docs/recon/phase-1-3-B-frontend-inventory.md
351-
=== docs/recon/phase-1-3-D2-migration.md ===
6-**Date:** 2026-04-27
7-**Branch:** `claude/migration-rollout-analysis-JauAD`
8:**Git remote:** `http://local_proxy@127.0.0.1:36411/git/Inneren12/Summa-vision-can`
9-
10-**Prereqs read:**
=== docs/recon/phase-1-3-A-backend-inventory.md ===
521-
522-```
523:GIT REMOTE: http://local_proxy@127.0.0.1:38769/git/Inneren12/Summa-vision-can
524-DOC PATH: docs/recon/phase-1-3-A-backend-inventory.md
525-
=== docs/architecture/FLUTTER_ADMIN_MAP.md ===
```

**Relevant docs:** `SESSION_HANDOFF.md` plus listed docs/recon files from grep
**Port-binding mentions in deploy docs:** no deploy-specific port-binding hits found by provided pattern; matches were mostly `127.0.0.1` in git remote URLs.

## D-9 — Compose invocation patterns

```text
##D9_1
ls: cannot access 'Makefile*': No such file or directory
ls: cannot access 'makefile*': No such file or directory
##D9_2
./backend/entrypoint.sh
./.ai/tools/get_ac_content.sh
./.ai/tools/resolve_scope.sh
##D9_3
rg: Makefile*: No such file or directory (os error 2)
rg: makefile*: No such file or directory (os error 2)
.github/workflows/smoke-test.yml:40:        run: docker compose -f docker-compose.dev.yml up -d --build
.github/workflows/smoke-test.yml:52:              docker compose -f docker-compose.dev.yml logs api | tail -30
.github/workflows/smoke-test.yml:115:          HEAD_COUNT=$(docker compose -f docker-compose.dev.yml exec -T api \
.github/workflows/smoke-test.yml:120:            docker compose -f docker-compose.dev.yml exec -T api alembic heads
.github/workflows/smoke-test.yml:128:          docker compose -f docker-compose.dev.yml exec -T api python3 -c "
.github/workflows/smoke-test.yml:171:          if docker compose -f docker-compose.dev.yml logs api 2>&1 | \
.github/workflows/smoke-test.yml:176:            docker compose -f docker-compose.dev.yml logs api 2>&1 | tail -30
.github/workflows/smoke-test.yml:183:          docker compose -f docker-compose.dev.yml exec -T api \
.github/workflows/smoke-test.yml:193:          docker compose -f docker-compose.dev.yml exec -T api \
.github/workflows/smoke-test.yml:207:          docker compose -f docker-compose.dev.yml exec -T api \
.github/workflows/smoke-test.yml:213:          docker compose -f docker-compose.dev.yml stop api
.github/workflows/smoke-test.yml:215:          SHUTDOWN_LOG=$(docker compose -f docker-compose.dev.yml logs api 2>&1 | tail -20)
.github/workflows/smoke-test.yml:228:        run: docker compose -f docker-compose.dev.yml down -v --remove-orphans
scripts/bootstrap-backend.ps1:103:        Write-Host "  Run: docker compose -f docker-compose.dev.yml up -d" -ForegroundColor DarkYellow
```

**Local dev invocation:** documented/used as `docker compose -f docker-compose.dev.yml up -d`
**CI/VPS invocation:** CI smoke test uses `-f docker-compose.dev.yml`; VPS invocation not found in these outputs
**Uses `-f file1 -f file2` override pattern?:** no evidence; single `-f docker-compose.dev.yml`

## D-10 — `.env*` port-binding env vars

```text
##D10_1
ls: cannot access '.env*': No such file or directory
##D10_2
rg: .env*: No such file or directory (os error 2)
```

**Existing env-var binding pattern:** no evidence

## D-11 — [DEBT.md](http://DEBT.md) state

```text
##D11_1
##D11_2
36:### DEBT-031: Unify generation phase enums across preview and chart config stacks
51:> Updated 2026-04-24: errorCode plumbing in both notifier stacks completed in Slice 3.8 Fix Round 1 (GitHub review caught dead mapper). DEBT-031 remains open for the phase enum unification proper.
55:> Updated 2026-04-25: FR2 resolved stale success artifact regressions in both notifier stacks (ChartGenerationNotifier and GenerationNotifier clear result/resultUrl on terminal failure/timeout). RU hardcoded localized literals in chart_config_screen_localization_test.dart replaced with l10n.<key>-derived assertions. These are improvements ADJACENT to DEBT-031 — the phase enum unification proper remains open.
57:### DEBT-032: Locale-switch smoke test harness harmonization
86:### DEBT-029: Locale-aware bootstrap-error fallback in Flutter admin app
100:### DEBT-030: Editor endpoints lack structured error codes for localized operator messaging
116:### DEBT-034: Admin/publication backend envelopes are not yet unified
118:- **Source:** DEBT-030 PR2 follow-up
128:### DEBT-027: Autosave retry-reset effect uses exhaustive-deps exception
154:### DEBT-033: Broaden temp_cleanup beyond temp/uploads/ after job-type audit
156:- **Source:** DEBT-021 + temp_cleanup safety fix (`claude/debt-021-temp-cleanup-safe`)
183:| DEBT-010 | No audit event retention cleanup | Final Debts | 2026-04-12 |
184:| DEBT-015 | GraphicPipeline generate() method is monolithic | Final Debts | 2026-04-12 |
185:| DEBT-001 | Cooldown query uses text match on JSON | Docs & Quality | 2026-04-12 |
186:| DEBT-002 | Integration tests use metadata.create_all | Docs & Quality | 2026-04-12 |
187:| DEBT-003 | Dockerfile doesn't run migrations on startup | Pre-deploy Hardening | 2026-04-12 |
188:| DEBT-004 | Old in-memory TaskManager not yet removed | Dead Code Cleanup | 2026-04-12 |
189:| DEBT-005 | StorageInterface upload_bytes/download_bytes | PR B-3 | 2026-04-09 |
190:| DEBT-006 | Dead code in services/cmhc/ directory | Dead Code Cleanup | 2026-04-12 |
191:| DEBT-007 | Dead code in services/ai/ directory | Dead Code Cleanup | 2026-04-12 |
##D11_3
DEBT-033
DEBT-034
DEBT-035
DEBT-036
DEBT-040
DEBT-041
DEBT-042
DEBT-043
DEBT-044
DEBT-045
```

**DEBT-046 entry already exists?:** no
**Highest DEBT number currently used:** DEBT-045
**DEBT-046 is next available?:** yes

## D-12 — Cross-host dev considerations

```text
##D12_1
##D12_2
```

**Evidence of cross-host dev needs:** no evidence found by queried patterns
**Docker Desktop on Windows behavior implication:** loopback in base is likely compatible for local Docker Desktop workflows

---

## Summary for founder

### Current state

- Base compose api.ports binding: `- "8000:8000"`
- Override files: `docker-compose.dev.yml` defines api `8001:8000`, db `5432:5432`, minio `9000:9000/9001:9001`
- VPS protected via: (d) unknown from available evidence

### Surprises encountered

- No `.env*` files at repo root matched by `.env*` glob.
- D-8 query pulled many recon docs where `127.0.0.1` appeared inside historical git-remote URLs, not deployment bind configs.

### Approach options for impl phase

Based on findings, recommended approach:

**Option 1 — Loopback in base, no override needed:**
- Change base `docker-compose.yml` api.ports to `[`"127.0.0.1:8000:8000"`]`
- No dev override file needed (Docker Desktop on Windows forwards 127.0.0.1 from host to container automatically)
- Affected files: `docker-compose.yml` only
- VPS: stays as-is / unknown override mechanism unaffected

**Option 2 — Loopback in base + dev override file with 0.0.0.0:**
- Change base to `[`"127.0.0.1:8000:8000"`]`
- Add or modify `docker-compose.dev.yml` to override ports back to `[`"0.0.0.0:8000:8000"`]` for dev workflow
- Document in README how to invoke: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`
- Affected files: `docker-compose.yml` + `docker-compose.dev.yml` + README

**Option 3 — Env-var-driven binding:**
- Change base to `[`"${API_BIND_ADDR:-127.0.0.1}:8000:8000"`]`
- Default safe (loopback); operator can set `API_BIND_ADDR=0.0.0.0` if they actually need exposure
- Affected files: `docker-compose.yml` only + `.env.example` documentation
- Most flexible but adds env var surface

### Other services scope question

If D-6 found postgres / redis / other services with `ports` exposing 0.0.0.0:
- db (dev): in-scope only if DEBT-046 broadens beyond api
- minio (dev): same consideration

### Out-of-scope confirmed

- `backend/src/main.py` — not touched
- Application-level binding (uvicorn host) — not touched (this is a Docker port-mapping concern, not application concern)

### Founder approval needed for

1. Confirm Option 1 / 2 / 3 — which approach
2. Confirm scope of "other services" — postgres/minio loopback treatment in same PR or separate
3. If VPS uses inline drift (option b in D-7) — separate cleanup PR or fold into this one
4. DEBT-046 entry text — recommended draft below
5. Green-light impl prompt drafting

### DEBT-046 entry draft (for impl phase to add to [DEBT.md](http://DEBT.md) Active Debt section)

```text
### DEBT-046: Base compose binds API port to 0.0.0.0 (defense-in-depth)

- **Source:** VPS Section E.3.5 finding (2026-04-28)
- **Added:** 2026-04-30
- **Severity:** P2
- **Category:** infra-security
- **Status:** active
- **Description:** `docker-compose.yml` api service exposes `ports: ["8000:8000"]`
  which binds to `0.0.0.0:8000` on the host. Docker bypasses UFW via the
  DOCKER iptables chain, so any fresh deploy without override would expose
  the API publicly. Production is currently protected by <override mechanism
  per D-7> and Cloudflare in front, but base file is unsafe by default.
- **Impact:** Future operator deploying without override = public API exposure.
  No current incident; defense-in-depth concern.
- **Resolution:** Change base compose to `127.0.0.1:8000:8000` (or env-var-
  driven binding). Dev override file or env var allows opt-in 0.0.0.0 if
  cross-host dev is needed.
- **Target:** Next debt cycle. Sequencing #2 after DEBT-045.
```

### Estimated impl effort after approval

- **Option 1:** XS — single line change in `docker-compose.yml` + `DEBT.md` entry
- **Option 2:** S — base + override file + README
- **Option 3:** XS-S — base line + `.env.example` doc

---

## Branch / commit deviation note

Per `[CLAUDE.md](http://CLAUDE.md)` ("Do NOT commit. Do NOT push. Human handles git."), this report is left as untracked file (or `git add`-staged only). Founder commits it on appropriate branch.

Recommended branch name for finalization commit: `prerecon/debt-046-api-ports-loopback`
