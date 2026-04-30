# DEBT-045 Pre-recon — `cors_origins` orphan field removal

**Date:** 2026-04-30
**Branch:** claude/gallant-dirac-igcgw (see "Branch deviation note" at end)
**Phase:** pre-recon (discovery only)
**Founder gate:** awaiting approval before impl prompt

---

## D-1 — `cors_origins` references in backend code

```
backend/tests/api/test_health.py-17-def _override_settings() -> Settings:
backend/tests/api/test_health.py-18-    """Return a deterministic ``Settings`` instance for test isolation."""
backend/tests/api/test_health.py:19:    return Settings(app_name="Test App", debug=True, cors_origins="*", admin_api_key="test-key")
backend/tests/api/test_health.py-20-
backend/tests/api/test_health.py-21-

backend/tests/api/test_health.py-105-    assert settings.app_name == "Summa Vision API"
backend/tests/api/test_health.py-106-    assert settings.debug is False
backend/tests/api/test_health.py:107:    assert settings.cors_origins == "*"

backend/src/core/config.py-19-        app_name: Human-readable service name.
backend/src/core/config.py-20-        debug: Enable debug-level logging and stack traces.
backend/src/core/config.py:21:        cors_origins: Comma-separated list of allowed CORS origins.
backend/src/core/config.py-22-            Defaults to ``"*"`` (allow all) for local development.
backend/src/core/config.py-23-        storage_backend: Which storage implementation to use.

backend/src/core/config.py-37-    app_name: str = "Summa Vision API"
backend/src/core/config.py-38-    debug: bool = False
backend/src/core/config.py:39:    cors_origins: str = "*"
backend/src/core/config.py-40-    environment: str = "development"
backend/src/core/config.py-41-

backend/src/main.py-185-# Pattern mirrors the docs_url env-gate above: one source of truth
backend/src/main.py-186-# on settings.environment.
backend/src/main.py:187:_cors_origins: list[str] = [
backend/src/main.py-188-    "https://summa.vision",
backend/src/main.py-189-    "https://www.summa.vision",
backend/src/main.py-190-]
backend/src/main.py-191-if settings_on_startup.environment != "production":
backend/src/main.py:192:    _cors_origins.append("http://localhost:3000")
backend/src/main.py-193-
backend/src/main.py-194-app.add_middleware(
backend/src/main.py-195-    CORSMiddleware,
backend/src/main.py:196:    allow_origins=_cors_origins,
backend/src/main.py-197-    allow_credentials=True,
backend/src/main.py-198-    allow_methods=["*"],
```

**Count:** 7 matches across 3 files.

**Surprises (consumers other than Settings declaration):** **No.** The `_cors_origins` matches in `backend/src/main.py:187,192,196` are a **different identifier** — a local variable `_cors_origins` (leading underscore, plural list-literal) used by `CORSMiddleware`, not `Settings.cors_origins`. They are co-located string-match noise from `rg`, not real consumers. The only real references to `Settings.cors_origins` are:

  - `backend/src/core/config.py:21,39` — docstring + field declaration (the orphan target)
  - `backend/tests/api/test_health.py:19,107` — two test references (override constructor + assertion of default)

  No production consumer reads `settings.cors_origins`. Orphan premise **confirmed**.

## D-2 — `CORS_ORIGINS` references (env var, uppercase)

```
./docs/recon/pr-d-env-ignore-empty-recon.md:12:| cors_origins | str | "*" | default `CORS_ORIGINS` | indirectly (production path uses truthy check only for `cdn_base_url`/`public_site_url`, not this field) |
./docs/recon/pr-d-env-ignore-empty-recon.md:105:Risk with `CORS_ORIGINS=""`: effectively no current runtime impact from this field (appears unused).
./docker-compose.yml:32:      # Backend Settings reads CORS_ORIGINS; .env files conventionally use
./docker-compose.yml:36:      CORS_ORIGINS: ${ALLOWED_ORIGINS:-*}
./DEBT.md:185:  passed through the compose env block as `CORS_ORIGINS`, but `main.py` CORS
./DEBT.md:189:- **Impact:** Operators cannot tighten or relax CORS via the `CORS_ORIGINS` env
./DEBT.md:195:  - (b) Remove the field from `Settings` and remove `CORS_ORIGINS` from the
```

**Count:** 7 matches across 3 files.

**Locations summary:** docker-compose.yml (1 active + 1 comment line), DEBT.md (3 narrative refs in DEBT-045 entry itself), docs/recon/pr-d-env-ignore-empty-recon.md (2 narrative refs in prior PR-D recon — historical record). No `.env*` references. No backend code references the env-var spelling directly (Pydantic auto-derives env var name from field name).

## D-3 — `ALLOWED_ORIGINS` references

```
./docker-compose.yml:33:      # ALLOWED_ORIGINS. Default mirrors Settings.cors_origins Python default
./docker-compose.yml:36:      CORS_ORIGINS: ${ALLOWED_ORIGINS:-*}
```

**Count:** 2 matches, both in `docker-compose.yml` (one comment, one active).

**Used by anything other than the compose mirror line?:** **No.** Both matches are within the same six-line block in `docker-compose.yml`. No code, no `.env.example`, no other compose file, no CI config consumes `ALLOWED_ORIGINS`.

**Scope decision implication:** After DEBT-045 removes the `CORS_ORIGINS: ${ALLOWED_ORIGINS:-*}` mirror line, `ALLOWED_ORIGINS` becomes effectively unreferenced anywhere in the repo. Per prompt's stated scope, the env-var declaration is **out of scope** for this PR — we do not remove it from any external `.env` file or operator documentation. Clean removal of the orphan field + mirror line is achievable without touching `ALLOWED_ORIGINS` semantics elsewhere.

## D-4 — main.py CORS middleware setup

```
backend/src/main.py:9:from fastapi.middleware.cors import CORSMiddleware
...
backend/src/main.py:174:# CORSMiddleware must be added AFTER AuthMiddleware so it runs FIRST
backend/src/main.py-175-# and handles OPTIONS preflight requests before auth blocks them.
backend/src/main.py-176-# ---------------------------------------------------------------------------
backend/src/main.py-177-
backend/src/main.py-178-app.add_middleware(
backend/src/main.py-179-    AuthMiddleware,
backend/src/main.py-180-    admin_api_key=settings_on_startup.admin_api_key,
backend/src/main.py-181-)
backend/src/main.py-182-
backend/src/main.py-183-# CORS: production is the two public hostnames only. Development
backend/src/main.py-184-# additionally permits localhost:3000 for the Next.js dev server.
backend/src/main.py-185-# Pattern mirrors the docs_url env-gate above: one source of truth
backend/src/main.py-186-# on settings.environment.
backend/src/main.py:187:_cors_origins: list[str] = [
backend/src/main.py-188-    "https://summa.vision",
backend/src/main.py-189-    "https://www.summa.vision",
backend/src/main.py-190-]
backend/src/main.py-191-if settings_on_startup.environment != "production":
backend/src/main.py:192:    _cors_origins.append("http://localhost:3000")
backend/src/main.py-193-
backend/src/main.py-194-app.add_middleware(
backend/src/main.py-195-    CORSMiddleware,
backend/src/main.py-196-    allow_origins=_cors_origins,
backend/src/main.py-197-    allow_credentials=True,
backend/src/main.py-198-    allow_methods=["*"],
backend/src/main.py-199-    allow_headers=["*"],
backend/src/main.py-200-)
backend/src/main.py-201-
```

**What list does CORSMiddleware actually use?:** **Hardcoded** literal list `["https://summa.vision", "https://www.summa.vision"]`, conditionally appended with `"http://localhost:3000"` when `settings_on_startup.environment != "production"`. The gate is `settings.environment`, not `settings.cors_origins`.

**Confirms `cors_origins` is orphan:** **Yes.** Quoted evidence: `allow_origins=_cors_origins` (line 196) where `_cors_origins` is the local variable defined at line 187, not `settings.cors_origins`. The Settings field is never read in `main.py` (or anywhere else in production code).

## D-5 — Settings class context around `cors_origins`

**File:** `backend/src/core/config.py`

```
11-from pydantic import Field, model_validator
12-from pydantic_settings import BaseSettings
13-
14-
15-class Settings(BaseSettings):
16-    """Central configuration for the Summa Vision API.
17-
18-    Attributes:
19-        app_name: Human-readable service name.
20-        debug: Enable debug-level logging and stack traces.
21:        cors_origins: Comma-separated list of allowed CORS origins.
22-            Defaults to ``"*"`` (allow all) for local development.
23-        storage_backend: Which storage implementation to use.
...
35-    """
36-
37-    app_name: str = "Summa Vision API"
38-    debug: bool = False
39:    cors_origins: str = "*"
40-    environment: str = "development"
41-
42-    # --- Application ---
43-    log_format: str = "console"  # "console" for dev, "json" for production
```

**Field neighbors (immediately above / below):**
  - Above: `debug: bool = False` (line 38)
  - Below: `environment: str = "development"` (line 40)

**Punctuation note for impl:** Pydantic class fields are individual statements, no comma-separators. Removing line 39 cleanly leaves `debug` (line 38) and `environment` (line 40) intact with no syntactic adjustment needed. Impl phase must **also** delete the corresponding docstring entry at lines 21–22 ("cors_origins: Comma-separated list of allowed CORS origins. / Defaults to ``"*"`` (allow all) for local development.") to keep docstring synchronized with field set.

## D-6 — docker-compose.yml `CORS_ORIGINS` line

```
29-      S3_REGION: ${S3_REGION:-us-east-1}
30-      # CDN/CORS
31-      CDN_BASE_URL: ${CDN_BASE_URL:?CDN_BASE_URL is required (e.g. https://cdn.summa.vision)}
32:      # Backend Settings reads CORS_ORIGINS; .env files conventionally use
33-      # ALLOWED_ORIGINS. Default mirrors Settings.cors_origins Python default
34-      # ("*"). pydantic-settings env_ignore_empty=False — empty env value
35-      # WIPES Python default; the explicit fallback prevents that.
36:      CORS_ORIGINS: ${ALLOWED_ORIGINS:-*}
```

**Line number:** 36 (active assignment); lines 32–35 are explanatory comments that become obsolete once line 36 is removed.

**Indentation level:** 6 spaces, under `api.environment` block.

**Value template:** `${ALLOWED_ORIGINS:-*}` (PR-A mirror default).

**Override compose files with CORS_ORIGINS:** **None.** `docker-compose.dev.yml` exists but contains no `CORS_ORIGINS` reference. `docker-compose.yml` is the only file. (Note: the `# CDN/CORS` section comment at line 30 is shared with `CDN_BASE_URL`; impl phase should consider whether the section comment stays "CDN/CORS" or trims to "CDN" since CORS env wiring goes away.)

## D-7 — Tests referencing `cors_origins`

```
backend/tests/api/test_health.py-17-def _override_settings() -> Settings:
backend/tests/api/test_health.py-18-    """Return a deterministic ``Settings`` instance for test isolation."""
backend/tests/api/test_health.py:19:    return Settings(app_name="Test App", debug=True, cors_origins="*", admin_api_key="test-key")
backend/tests/api/test_health.py-20-
backend/tests/api/test_health.py-21-

backend/tests/api/test_health.py-105-    assert settings.app_name == "Summa Vision API"
backend/tests/api/test_health.py-106-    assert settings.debug is False
backend/tests/api/test_health.py:107:    assert settings.cors_origins == "*"
```

**Tests that will need update:** `backend/tests/api/test_health.py` — two edits required:

  1. Line 19: remove `cors_origins="*"` kwarg from the `Settings(...)` constructor call. The other kwargs (`app_name`, `debug`, `admin_api_key`) remain.
  2. Line 107: delete the assertion `assert settings.cors_origins == "*"` entirely (it asserts a default that no longer exists). Adjacent assertions on `app_name` and `debug` (lines 105–106) stay.

  Both are in the same file. Test will continue to pass after edits — neither edit changes test logic, only removes references to a removed field. No new test coverage required (this is dead-code removal, not behavior change).

## D-8 — DEBT.md DEBT-045 location

**Line number(s):** 177 (heading line `### DEBT-045: ...`); body extends through line ~203 (immediately preceding `---` separator before `## Resolved` at line 205).

**Current Status field value:** `active`

**Section heading currently under:** `## Active Debt`

**Heading line number:** 32 (`## Active Debt`); next heading is `## Resolved` at line 205.

DEBT-045 (line 177) falls between lines 32 and 205, so it is in `## Active Debt`. Impl phase must move the entire DEBT-045 block (heading + bullets + trailing `---` if present) under `## Resolved` (line 205) and update the Status line from `active` → `resolved` (or whatever convention the existing Resolved entries use; impl phase should sample one Resolved entry above-the-line to match style).

## D-9 — `.env*` files

```
./backend/.env.example
./frontend-public/.env.example
```

(repo-wide grep for `CORS_ORIGINS` or `ALLOWED_ORIGINS` in any `.env*` file returned no matches.)

**Documentation drift cleanup needed:** **No.** Neither `backend/.env.example` nor `frontend-public/.env.example` mentions `CORS_ORIGINS` or `ALLOWED_ORIGINS`, so no env-example cleanup is in scope.

---

## Summary for founder

**Removal scope (impl phase will touch these files):**

- `backend/src/core/config.py` — remove the field declaration at line 39 (`cors_origins: str = "*"`) AND the corresponding docstring entry at lines 21–22.
- `docker-compose.yml` — remove line 36 (`CORS_ORIGINS: ${ALLOWED_ORIGINS:-*}`) AND the now-obsolete explanatory comments at lines 32–35. Consider whether section header at line 30 (`# CDN/CORS`) should become `# CDN` since CORS wiring is gone.
- `backend/tests/api/test_health.py` — remove `cors_origins="*"` kwarg from line 19 and remove the assertion at line 107.
- `DEBT.md` — relocate the DEBT-045 block (lines ~177–203) from `## Active Debt` (line 32) to `## Resolved` (line 205); update Status field from `active` → `resolved` (match existing Resolved-section convention).

**No `.env.example` cleanup needed** (no references found).

**Surprises encountered:** **None of substance.** One minor non-issue worth recording: `rg "cors_origins"` matched a local variable `_cors_origins` in `main.py` (the hardcoded list itself), which is a different identifier — flagged in D-1 to prevent confusion in impl phase.

**Out-of-scope items confirmed:**
- `ALLOWED_ORIGINS` env var declaration — not removed in this PR. After DEBT-045 lands, `ALLOWED_ORIGINS` becomes unreferenced anywhere in the repo, which is documented but accepted (operator-facing env-var declarations live outside this PR's scope).
- `backend/src/main.py` CORS hardcoded list — left as-is (current behavior). Option (b) explicitly accepts the loss of operator-control surface.

**Founder approval needed for:**
1. Confirm scope above is correct (4 files: config.py, docker-compose.yml, test_health.py, DEBT.md).
2. Confirm the docstring-line cleanup at config.py:21–22 and the comment-block cleanup at docker-compose.yml:32–35 are in scope (avoiding orphan documentation referring to a removed field).
3. Confirm whether section header `# CDN/CORS` at docker-compose.yml:30 should be retitled to `# CDN`.
4. Confirm leaving `ALLOWED_ORIGINS` referenced nowhere in the repo is acceptable (alternative: also clean up the now-defunct env var name, but that touches operator-facing surface and is currently out of scope per prompt).
5. Green-light impl prompt drafting.

**Estimated impl effort after approval:** XS — single atomic commit, ~4 file edits, no new tests required (dead-code removal preserves existing test semantics after the two-line trim).

---

## Branch deviation note

The prompt requested a new branch `prerecon/debt-045-cors-origins-discovery`. The harness/system instructions for this session pin development to `claude/gallant-dirac-igcgw`. This recon report was produced on `claude/gallant-dirac-igcgw` (working tree was clean at PF-1, so no prior work was disturbed). If founder prefers the prompt-specified branch name, recreate the branch from this commit; if founder prefers the harness branch name (default), this report is already in the right place.

## Commit/push deviation note

The prompt's G-3 / G-4 gates direct me to commit and push the recon report. `CLAUDE.md` line 6 of "Rules That Always Apply" states: *"Do NOT commit. Do NOT push. Human handles git."* I followed `CLAUDE.md`. The recon report exists on disk on the current branch as an untracked file — founder reviews, then commits with whatever message/branch convention is appropriate.
