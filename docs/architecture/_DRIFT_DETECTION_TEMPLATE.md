# Drift Detection Template — Architecture MD Sync Verification

**Status:** Planning utility (NOT a knowledge MD). Underscore prefix marks it as utility.
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-27

**Purpose:** ensure architecture MD files don't silently drift from production code. Without this, after 2 months you'll have 9 MD files that **look** like source of truth but lie on 30% of facts.

**Usage:** paste the relevant section below into every impl prompt's "Output requirements" section. Pick the sections matching what the PR touches. Multiple sections fine if PR touches multiple zones.

**Where this lives:** `docs/architecture/_DRIFT_DETECTION_TEMPLATE.md` (planning utility, NOT a knowledge MD; underscore prefix marks it as utility).

---

## How to use

1. When writing an impl prompt for any feature PR, scan the prompt's scope. Which architecture MD areas does it touch?
2. Paste matching sections below into the prompt's "Output requirements" or "Verification gates" section.
3. The agent runs the drift check as part of completing the PR. If drift detected, agent updates MD in same commit OR raises blocker for founder.

---

## Section A — Backend endpoint drift detection

**Trigger:** PR adds/modifies/removes any FastAPI endpoint, exception handler, or modifies `register_exception_handlers()`.

**Paste into impl prompt:**

````markdown
### Drift detection — BACKEND_API_INVENTORY.md

After completing all code changes, run these verification commands:

```bash
# 1. List all admin endpoints currently in code
grep -rn '@router\..*/api/v1/admin' backend/app/api/ | sort

# 2. List endpoints documented in BACKEND_API_INVENTORY.md §1
grep -E '^\| (GET|POST|PATCH|DELETE|PUT) ' docs/architecture/BACKEND_API_INVENTORY.md
```

Compare both lists. ANY discrepancy MUST be one of:
- Documented in MD but removed in this PR → update MD §1 in same commit
- Added in this PR but missing from MD → update MD §1 in same commit
- Both list match → drift check PASSED

If drift exists and you cannot determine which is intentional, STOP and raise as a blocker. Do NOT auto-update MD if uncertain — let founder decide.

Append maintenance log entry to BACKEND_API_INVENTORY.md §7 with PR number + sections touched.
````

---

## Section B — Frontend autosave / error code drift

**Trigger:** PR modifies `admin.ts`, `errorCodes.ts`, autosave consumer, or adds a new backend error code anywhere in stack.

**Paste into impl prompt:**

````markdown
### Drift detection — FRONTEND_AUTOSAVE_ARCHITECTURE.md

After completing all code changes, run:

```bash
# 1. List error codes currently in KNOWN_BACKEND_ERROR_CODES
grep -A 20 'KNOWN_BACKEND_ERROR_CODES' frontend-public/src/lib/admin.ts

# 2. List codes documented in MD §2
grep -E '^\| [A-Z_]+ \|' docs/architecture/FRONTEND_AUTOSAVE_ARCHITECTURE.md
```

Compare. Any new error code in code but not in MD → update MD §2 + add EN+RU i18n entries (per MD §2 protocol). Any code in MD but removed from code → update MD §2.

Verify i18n key namespaces match MD §3 (Option C hybrid: `publication.*` for domain, `errors.backend.*` for cross-cutting).

Append maintenance log entry to FRONTEND_AUTOSAVE_ARCHITECTURE.md §7.
````

---

## Section C — Flutter admin drift

**Trigger:** PR adds/modifies any Flutter route, screen, Job model field, JobStatus value, provider, or repository method.

**Paste into impl prompt:**

````markdown
### Drift detection — FLUTTER_ADMIN_MAP.md

After completing all code changes, run:

```bash
# 1. List current routes
grep -rn 'GoRoute(path:' frontend/lib/

# 2. List routes documented in MD §1
grep -E '^\| /' docs/architecture/FLUTTER_ADMIN_MAP.md

# 3. JobStatus enum values
grep -A 10 'enum JobStatus' frontend/lib/

# 4. JobStatus values in MD §3
grep -A 3 'JobStatus enum' docs/architecture/FLUTTER_ADMIN_MAP.md
```

Compare both pairs. Any discrepancy → update MD §1 or §3 in same commit. Flag if backend JobStatus values diverge from frontend (memory item: must match).

Append maintenance log entry to FLUTTER_ADMIN_MAP.md §8.
````

---

## Section D — Architectural invariant drift

**Trigger:** PR modifies error envelope shape, ETag derivation, idempotency-related code, token handling, or any other invariant in ARCHITECTURE_INVARIANTS.md.

**Paste into impl prompt:**

````markdown
### Drift detection — ARCHITECTURE_INVARIANTS.md

This PR touches an invariant. Per MD front matter maintenance rule:
1. Founder must have explicit approval for the change (cite the chat / recon section)
2. DEBT.md MUST have entry with rationale
3. Update ARCHITECTURE_INVARIANTS.md in same commit
4. Audit downstream consumers — every PR / module that depends on the changed invariant

Specifically check:
- §3 envelope shape — if changed, audit all custom exception handlers
- §4 R19 — if changed, audit clone behavior, config_hash usage
- §5 R16 idempotency — if HTTP idempotency-key infra is added, the v1 ETag DEBT becomes resolvable
- §7 ETag — if filling placeholder, verify §5 cross-reference still accurate

If you cannot confirm steps 1-4 for this change, STOP and raise as blocker. Founder approves invariant changes, not agents.

Append maintenance log entry to ARCHITECTURE_INVARIANTS.md §9.
````

---

## Section E — Test infrastructure drift

**Trigger:** PR introduces a new test pattern, fixture, or hits a test failure mode not yet documented.

**Paste into impl prompt:**

````markdown
### Drift detection — TEST_INFRASTRUCTURE.md

If during this PR you encountered a test failure mode not in TEST_INFRASTRUCTURE.md, OR introduced a new fixture pattern, OR resolved a test flake, document it.

Check:
- §2 (Backend) — new fixture override pattern? new pytest plugin requirement?
- §3 (Flutter) — new `tester.runAsync` discovery? new finder rule?
- §4 (Next.js) — new fetch mocking pattern? new shared mock helper?
- §5 (Cross-cutting) — new principle from this PR's lesson?

If yes, append the new pattern to the matching section. Cite source as this PR's branch / number.

Append maintenance log entry to TEST_INFRASTRUCTURE.md §6.

If NO new patterns introduced, no MD update needed. State explicitly in Summary Report: "TEST_INFRASTRUCTURE.md drift check PASSED — no new patterns this PR."
````

---

## Section F — Editor block architecture drift

**Trigger:** PR modifies block schema, template definitions, document migration pipeline, render pipeline, history batching, or keyboard shortcut handling.

**Paste into impl prompt:**

````markdown
### Drift detection — EDITOR_BLOCK_ARCHITECTURE.md

After completing all code changes, verify:

```bash
# 1. Block type count
grep -E "type: '[a-z]+'" frontend-public/src/components/editor/blocks/ | sort -u

# 2. Template count
ls frontend-public/src/components/editor/templates/

# 3. schemaVersion in code
grep 'schemaVersion' frontend-public/src/components/editor/schema.ts

# 4. Migration count
grep -E '^\s+[0-9]+:' frontend-public/src/components/editor/migrations.ts
```

Compare to MD:
- §3 catalog (13 block types, 5 categories)
- §4 templates (11 templates, 7 families)
- §5 schemaVersion
- §6 migration count

If any count differs, update MD. If schemaVersion bumped, ensure new migration step is in §6 catalog.

Append maintenance log entry to EDITOR_BLOCK_ARCHITECTURE.md §11.
````

---

## Section G — Deployment drift

**Trigger:** PR modifies Docker config, PostgreSQL setup, scheduler config, S3 abstraction, or CI workflow files.

**Paste into impl prompt:**

````markdown
### Drift detection — DEPLOYMENT_OPERATIONS.md

If this PR modifies any of:
- `docker-compose.yml` services or ports → update MD §3
- PostgreSQL version, dev creds, or migration patterns → update MD §4
- APScheduler config or concurrency primitives → update MD §5
- S3 abstraction or `temp_cleanup.py` rules → update MD §6
- `.github/workflows/*.yml` → update MD §7
- Production deploy procedure (placeholder) → fill MD §8

Append maintenance log entry to DEPLOYMENT_OPERATIONS.md §9.

If PR does NOT modify infrastructure, state in Summary Report: "DEPLOYMENT_OPERATIONS.md drift check PASSED — no infra changes."
````

---

## Section H — Roadmap dependency drift

**Trigger:** PR completes a phase, reorders phases, discovers a new dependency, or invalidates a parallel-track assumption.

**Paste into impl prompt:**

````markdown
### Drift detection — ROADMAP_DEPENDENCIES.md

If this PR completes a phase / Stage:
- Update §2 status table (move from "Active" to "Completed" with date)
- Update §3 DAG if dependencies shifted
- Update §4 critical path if scope changed
- Update §5 parallel opportunities if a track is now unblocked

If this PR discovers a hidden dependency (item X actually depends on item Y, not documented):
- Add to §3 DAG
- Add to §6 risk zones if conflict-prone
- Note in §8 maintenance log

If this PR is purely tactical (single-PR feature within a phase, no roadmap movement) → no update needed. State in Summary: "ROADMAP_DEPENDENCIES.md drift check PASSED — tactical PR within phase, no roadmap state change."
````

---

## How to use this file in an impl prompt

The impl prompt template should include something like:

```markdown
### Drift detection requirements

This PR touches: [list zones]
Required drift checks (paste from `docs/architecture/_DRIFT_DETECTION_TEMPLATE.md`):
- Section A (backend endpoints): YES / NO
- Section B (frontend autosave): YES / NO
- Section C (Flutter admin): YES / NO
- Section D (architectural invariants): YES / NO
- Section E (test infrastructure): YES / NO
- Section F (editor): YES / NO
- Section G (deployment): YES / NO
- Section H (roadmap): YES / NO

For each YES, the agent runs the drift check and reports outcome in the PR Summary Report. Failed drift checks BLOCK merge until either MD is updated or founder pre-approves the discrepancy.
```

---

## Why this matters

Without drift detection, after 2 months:
- 9 MD files that **look** like source of truth
- ~30% of their facts will be stale (endpoint paths renamed, error codes added but not registered, JobStatus enum drifted)
- Agents reading them will trust outdated info → impl bugs
- Trust in MD evaporates → next agent ignores MD and grep'es again → original "incremental MD as side product" plan dies

Mandatory drift checks per impl prompt is the **systematic** defense. Light cost per PR (3-5 minutes of agent time), high cost without (rebuild MD network when trust dies).

This template is the operational backbone of the architecture MD network. Without it, the MD network is a snapshot, not a living document.
