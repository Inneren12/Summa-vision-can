# Technical Debt Registry

> Source of truth for known technical debt.
> Maintained per-PR: creating debt -> add entry; resolving -> move to Resolved.

## Format

| Field | Description |
|-------|-------------|
| **ID** | `DEBT-NNN` (sequential, never reused) |
| **Source** | PR number or review that identified it (e.g. `PR #16 review`, `Roadmap R18`) |
| **Added** | Date added (YYYY-MM-DD) |
| **Severity** | `critical` / `high` / `medium` / `low` |
| **Category** | `architecture` / `testing` / `security` / `ops` / `code-quality` |
| **Status** | `active` -> confirmed, needs work; `accepted` -> known, deferred intentionally; `in-progress` -> being fixed |
| **Description** | Factual statement of what the debt IS (not hypotheses) |
| **Impact** | What breaks or degrades if not fixed |
| **Resolution** | Concrete action to resolve |
| **Target** | Specific PR, etape, or milestone |

Rules:
- Every entry must be a **verified fact**, not a hypothesis.
- Do NOT add speculative or unverified items -> verify first, then add.
- Backlog features and future enhancements go in ROADMAP, not here.
- When resolving: move entry to Resolved table with PR link and date.
- When updating severity/target: edit in-place and append a changelog
  line at the bottom of the entry:
  `> Updated YYYY-MM-DD: severity high->medium, moved target to B-3.`

---

## Active Debt



### DEBT-031: Unify generation phase enums across preview and chart config stacks

- **Source:** Phase 3 Slice 3.7 recon (`docs/phase-3-slice-7-recon.md` §4 Decision 4)
- **Added:** 2026-04-24
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** Two parallel generation notifier stacks exist:
  - `frontend/lib/features/graphics/domain/generation_notifier.dart` + `generation_state.dart` use `GenerationPhase { idle, submitting, polling, completed, timeout, failed }`
  - `frontend/lib/features/graphics/application/generation_state_notifier.dart` uses `GenerationPhase { idle, submitting, polling, success, failed, timeout }`
  The semantic difference `completed` vs `success` causes both screens to maintain local phase→ARB-key switches in Slice 3.8 impl, duplicating mapping logic.
- **Impact:** Minor code duplication in 3.8 impl (2 switch statements, 5-7 lines each). No runtime issue, no user-facing bug.
- **Resolution:** Refactor to a single shared `GenerationPhase` enum used by both notifier stacks. Update all consumers. Delete the duplicate.
- **Target:** Opportunistic — during a future graphics refactor or when the chart config flow is re-architected for backend Phase 2 integration.

> Updated 2026-04-24: errorCode plumbing in both notifier stacks completed in Slice 3.8 Fix Round 1 (GitHub review caught dead mapper). DEBT-031 remains open for the phase enum unification proper.

> Updated 2026-04-24: Slice 3.11 pre-recon confirmed phase enum divergence persists but has limited practical impact — the 5 generationStatus* ARB keys are rendered directly from screen widgets via conditional branches, not via a centralized phase→key mapper (Part A2 §3.6). Enum unification remains opportunistic with no UX-blocking symptom.

> Updated 2026-04-25: FR2 resolved stale success artifact regressions in both notifier stacks (ChartGenerationNotifier and GenerationNotifier clear result/resultUrl on terminal failure/timeout). RU hardcoded localized literals in chart_config_screen_localization_test.dart replaced with l10n.<key>-derived assertions. These are improvements ADJACENT to DEBT-031 — the phase enum unification proper remains open.

### DEBT-032: Locale-switch smoke test harness harmonization

- **Source:** Phase 3 Slice 3.11 Consolidation recon
- **Added:** 2026-04-24
- **Severity:** low
- **Category:** code-quality
- **Status:** resolved
- **Description:** Four existing locale-switch smoke tests (queue, editor,
  graphics, shell-level locale_switch_smoke_test) plus the new aggregator
  smoke added in Slice 3.11 have inconsistent patterns (A3 §5.3):
  - Mixed `MaterialApp.router` vs `MaterialApp(home:)` patterns
  - Mixed drawer vs AppBar.actions switcher mounts
  - No shared `pumpLocalizedRouter` helper — ~18-25 lines of scaffolding
    duplicated per file
  - All assertions use hardcoded literals instead of `l10n.<key>`-derived
    values
- **Impact:** Minor maintenance overhead; tests remain green; no runtime
  issue. Cross-file regression risk is low because each smoke is
  independently validated.
- **Resolution:** Refactor all locale-switch smokes to share a common
  `pumpLocalizedRouter` helper in `frontend/test/helpers/`. Replace
  hardcoded literal assertions with `l10n.<key>`-derived values.
  Preserve test semantics; this is a harness-only refactor.
- **Target:** Opportunistic during future test infrastructure work or
  when adding a fifth+ locale-switch smoke (trigger: any new locale
  smoke proves harness duplication painful).

> Updated 2026-04-26: RESOLVED. Introduced shared `pumpLocalizedRouter` helper in `frontend/test/helpers/pump_localized_router.dart` plus `l10n(tester)` and `switchLocaleVia(tester, ...)` utilities. Refactored all 5 locale-switch smokes (queue/editor/graphics/shell/aggregator) to use the helper. All hardcoded literal assertions replaced with `l10n.<key>`-derived values. ~180 lines of duplicated scaffolding removed across the 5 files. No semantic test changes; all 9 tests still pass.

### DEBT-029: Locale-aware bootstrap-error fallback in Flutter admin app

- **Source:** Phase 3 Slice 3.3+3.4 recon (`docs/phase-3-slice-3-recon.md` §6)
- **Added:** 2026-04-23
- **Severity:** low
- **Category:** code-quality
- **Status:** resolved
- **Description:** `_BootstrapError` in `frontend/lib/main.dart` renders hardcoded EN text (`App bootstrap failed: $error`) as an EN-kept Category B diagnostic path.
- **Impact:** In rare bootstrap-failure sessions, RU operators see an untranslated diagnostic message.
- **Resolution:** Add locale-aware pre-localization fallback using `PlatformDispatcher.instance.locale` with a tiny EN/RU const map, defaulting to EN for unsupported locales.
- **Target:** Opportunistic fix during future Flutter bootstrap refactor.

> Updated 2026-04-24: RESOLVED. Implemented `bootstrapErrorMessage()` in `frontend/lib/core/bootstrap/bootstrap_error_messages.dart` with EN/RU map keyed on `PlatformDispatcher.instance.locale.languageCode`. Defaults to EN for unsupported locales. Wired into `_BootstrapError` in `main.dart`. 5 unit tests cover RU/EN/unsupported/country-variant/error-string-append cases.

### DEBT-030: Editor endpoints lack structured error codes for localized operator messaging

- **Source:** Phase 3 Slice 3.5+3.6 recon (`docs/phase-3-slice-5-recon.md` §5/§9)
- **Added:** 2026-04-24
- **Severity:** medium
- **Category:** architecture
- **Status:** resolved
- **Description:** Frontend admin PATCH publication error handling was status/message based, not aligned to backend error_code envelopes. Resolved 2026-04-26: dictionary + extractor + autosave wiring cover PATCH /admin/publications/{id} (errorCodes.ts + BackendApiError + autosave consumer). Backend contract for publish/unpublish endpoints emits structured codes (PR1), but no frontend caller exists today; if/when added, errorCodes.ts dictionary already covers PUBLICATION_NOT_FOUND for those endpoints — only consumer-side wiring will be needed.
- **Impact:** RU operators receive partially localized failure messaging (localized wrapper + backend detail that may remain EN), reducing precision and consistency across error cases.
- **Resolution:** Introduce endpoint-level structured `error_code` values and mapping docs for admin_publications flows; add Flutter mapper (`lib/l10n/backend_errors.dart`) from code → specific ARB messages; keep generic wrapper only as fallback for unknown codes.
- **Target:** PR #TBD 2026-04-26

> Updated 2026-04-24: Slice 3.8 `backend_errors.dart` mapper established for 7 job-level error_codes (CHART_EMPTY_DF, CHART_INSUFFICIENT_COLUMNS, UNHANDLED_ERROR, COOL_DOWN_ACTIVE, NO_HANDLER_REGISTERED, INCOMPATIBLE_PAYLOAD_VERSION, UNKNOWN_JOB_TYPE) covering graphics generation errors. Editor-action endpoints (PATCH /publications/{id}, publish, unpublish) still emit no structured error_code and fall back to `editorActionError` generic wrapper. Full resolution requires backend contract PR separate from frontend Phase 3.

> Updated 2026-04-26: RESOLVED. Frontend-public admin editor now parses both nested (`detail.error_code`) and flat (`error_code`) backend envelopes through a shared extractor (`extractBackendErrorPayload`) and maps known codes to localized next-intl keys for EN/RU. Autosave pipeline tests cover 404/422/401/429 + legacy raw-error fallback.

### DEBT-034: Admin/publication backend envelopes are not yet unified

- **Source:** DEBT-030 PR2 follow-up
- **Added:** 2026-04-26
- **Severity:** low
- **Category:** architecture
- **Status:** accepted
- **Description:** AuthMiddleware uses flat error envelope while publication endpoints use nested envelope; frontend extractor handles both. Once auth migrates to nested, the flat-envelope branch in `extractBackendErrorPayload` becomes obsolete.
- **Impact:** Minor client-side complexity (dual-envelope parsing and diagnostics). No current user-facing bug because both are handled.
- **Resolution:** Migrate auth handlers to the nested envelope contract, then remove flat branch from frontend extractor and narrow `BackendErrorPayload.envelope`.
- **Target:** Backend follow-up: migrate auth handlers to nested envelope. Then remove flat branch + update `BackendErrorPayload.envelope` enum.

> Updated 2026-04-30: AuthMiddleware migrated to nested envelope via direct helper (`format_error_envelope`) in `backend/src/core/error_handler.py`. Status `active` → `accepted` because partial: global `SummaVisionError` handler still emits flat envelope and frontend extractor still has flat-envelope branch. Full envelope unification + flat-branch removal tracked by DEBT-048.

### DEBT-027: Autosave retry-reset effect uses exhaustive-deps exception

- **Source:** Stage 4 Task 2 implementation (`claude/stage4-task2-autosave`)
- **Added:** 2026-04-20
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** In `frontend-public/src/components/editor/index.tsx` a
  `useEffect(() => { if (state.saveError) retryAttemptRef.current = 0; },
  [doc])` uses `// eslint-disable-next-line react-hooks/exhaustive-deps`
  to avoid including `state.saveError` in its dependency array.
  Including it would cause the effect to re-run on every `SAVE_FAILED`
  dispatch, resetting the attempt counter and defeating the exponential
  backoff progression. The effect is intended to reset retries only
  when the user edits the doc during error state.
- **Impact:** One ESLint disable directive. No runtime consequence ->
  the behaviour is correct and fully covered by the autosave test
  "user edit during error resets retry budget".
- **Resolution:** Refactor autosave orchestration into a small reducer
  (or a hand-rolled state machine) where attempt count lives alongside
  saveError, replacing the pair of effect + ref with a single state
  transition table. Out of scope for Task 2.
- **Target:** Future autosave refactor (no concrete milestone).



### DEBT-033: Broaden temp_cleanup beyond temp/uploads/ after job-type audit

- **Source:** DEBT-021 + temp_cleanup safety fix (`claude/debt-021-temp-cleanup-safe`)
- **Added:** 2026-04-25
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `temp_cleanup_prefixes` is currently scoped to `["temp/uploads/"]`.
  Other temp namespaces (in-flight transient artifacts, scheduler-internal
  staging, future job types) may also accumulate untracked. Broader sweep is
  deferred to avoid deleting in-flight artifacts whose payload structures
  have not been inventoried.
- **Impact:** Slow accumulation of unrelated `temp/*` objects increases
  storage cost over time. Not user-facing.
- **Resolution:** Inventory all job types that write to `temp/*`. Confirm
  payload extractors exist for each (extending `temp_payload_inspector.py` if
  needed). Add their prefixes to `temp_cleanup_prefixes` default. Verify
  `max_keys` cap is sufficient or add per-prefix caps.
- **Target:** Opportunistic — bundle with next job-pipeline refactor or
  Phase 2 AI Brain integration if it introduces new temp namespaces.

> **Updated 2026-04-26: RESOLVED as UNFOUNDED.** Recon (`docs/debt-033-recon.md`, branch `claude/debt-033-recon-temp-writers`) ran exhaustive `grep -rn "\"temp/\|'temp/" backend/src/ --include="*.py"` and found exactly one writer: `admin_graphics.py:269` writing to `temp/uploads/`, already covered by current cleanup. The original hypothesis ("other temp namespaces may also accumulate") was refuted by code evidence — no additional `temp/*` writer namespaces exist in the current codebase. No work required. Recon also flagged a minor opportunistic improvement (`RETRYING` fallback in `temp_cleanup.py:42,70` is dead code given current `JobStatus` enum); this is queued in founder memory for the next backend PR that touches `JobStatus` or `temp_cleanup`, not as standalone work.

### DEBT-046: Base compose binds API port to 0.0.0.0 (defense-in-depth)

- **Source:** VPS Section E.3.5 finding (2026-04-28); pre-recon `docs/recon/debt-046-api-ports-loopback-prerecon.md`
- **Added:** 2026-04-30
- **Severity:** medium
- **Category:** security
- **Status:** in-progress
- **Description:** Base `docker-compose.yml` api service exposed `ports: ["8000:8000"]`, which binds to `0.0.0.0:8000` on the host. Docker bypasses UFW via the DOCKER iptables chain, so any fresh deploy without override would expose the API publicly. Production VPS is currently safe via local `docker-compose.override.yml` (with `!override` YAML tag forcing ports replacement) plus Cloudflare in front; base file was unsafe by default.
- **Impact:** Any fresh deploy of base compose without the production override exposes the API on `0.0.0.0:8000` past UFW. No current incident; defense-in-depth gap. Future operator deploying without runbook context = public API exposure.
- **Resolution:** Change base compose to bind `127.0.0.1:8000:8000`. Add `docker-compose.override.yml.example` template documenting the production override pattern (db bind mount + api ports `!override` tag). Add `docker-compose.override.yml` to `.gitignore`. Failure mode flips: missing override = unreachable, not exposed.
- **Target:** This PR (`codex/debt-046-api-ports-loopback`).

### DEBT-047: Production `docker-compose.override.yml` not version-controlled

- **Source:** DEBT-046 pre-recon discovery (2026-04-30) — VPS uses local override file not in repo
- **Added:** 2026-04-30
- **Severity:** low
- **Category:** ops
- **Status:** active
- **Description:** Production deploy on VPS uses `docker-compose.override.yml` (db bind mount to `/opt/summa/data/postgres` + api ports `!override` tag) created locally on the VPS, not committed to repo. After DEBT-046, missing override = unreachable (safe failure mode), but environment configuration drift between repo and prod is still a concern. Cross-reference: DEBT-046 fixed the immediate exposure surface; this entry tracks the durability concern.
- **Impact:** If VPS is rebuilt or migrated, override file must be recreated from memory or runbook. No automated guarantee that prod config matches operator intent. Risk: silent omission of intended prod-only tweaks (db bind mount path, ports replacement) in disaster-recovery scenario. Not a security risk after DEBT-046; durability/operability risk only.
- **Resolution:** Pick one of: (a) commit `docker-compose.prod.yml` and deploy via explicit `-f` flags (changes CI/runbook), or (b) document override requirement in `OPERATIONS.md` runbook with exact file content for operator recreation, or (c) move template to `scripts/templates/` committed in repo with deploy procedure that copies it into place. No path chosen yet — opportunistic next time deploy hygiene is touched.
- **Target:** Opportunistic, no specific milestone. Next deploy-hygiene PR or VPS deploy Section J runbook work.

### DEBT-048: Global SummaVisionError handler emits flat envelope; frontend extractor retains flat branch

- **Source:** DEBT-034 recon (2026-04-30) — discovered global handler `_summa_vision_exception_handler` emits flat envelope while publication-specific handlers emit nested
- **Added:** 2026-04-30
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** `backend/src/core/error_handler.py:_summa_vision_exception_handler` emits flat envelope `{error_code, message, detail}` for all `SummaVisionError` subclasses NOT covered by a more specific handler. Publication-specific handlers emit nested `{detail: {error_code, message, details}}`. Three envelope shapes coexist after DEBT-034: nested-publication, nested-auth (via direct helper), flat-global. Frontend `extractBackendErrorPayload` still has flat-envelope branch to handle global-handler responses; cannot be removed until backend unifies on nested.
- **Impact:** Frontend extractor carries dual-envelope parsing logic. Future backend code raising arbitrary `SummaVisionError` subclasses gets flat envelope without operator-visible warning. Code-quality drift across error paths; no current user-facing bug.
- **Resolution:** Migrate `_summa_vision_exception_handler` to emit nested envelope (one-line change in handler body, but blast radius is every backend route raising `SummaVisionError`). Update all backend tests asserting flat shape. Remove flat branch from `frontend-public/src/lib/api/errorCodes.ts` and narrow `BackendErrorPayload.envelope` enum to `'nested' | 'none'`. Atomic backend + frontend PR per DEBT-034 precedent.
- **Target:** Opportunistic; before any new admin router is added (each new router compounds the migration scope).

### DEBT-049: Phase 2.2.0.5 slug infrastructure follow-ups

- **Source:** Phase 2.2.0.5 impl (PR slug column, generators, repo wiring, schemas)
- **Added:** 2026-04-30
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** Phase 2.2.0.5 ships backend slug infrastructure in expand-contract sequence: Chunk 1 nullable column + backfill, Chunk 2 ORM/exceptions/runtime generators, Chunk 3 repo wiring, Chunk 4 schemas. Several follow-ups remain open after the impl PRs merge:
  1. `create_published` (publication_repository.py) caller verification — confirm graphics pipeline does not pre-compute slug and slug-per-retry pattern works end-to-end.
  2. `create()` repo method caller audit — likely legacy/test-only; consider deprecation if no production callers.
  3. Public endpoint path confirmation — recon assumed `GET /api/v1/public/p/{slug}`; verify against actual backend route.
  4. Chinese transliteration test expectation — `test_generate_slug_chinese_transliteration` records python-slugify output as expectation; confirm it matches operator expectations.
  5. Frontend route blacklist verification — `RESERVED_SLUGS` (25 entries) was not verified against `frontend/app/` routes during recon (frontend dir was not present at recon time). Re-verify before Phase 2.2 frontend ships.
  6. Migration downgrade safety — slug migration `77889c0ea7e3` must not be downgraded after Phase 2.2 frontend ships (slug is public URL path; down→up regenerates slugs and breaks inbound links). Add to release ops checklist.
  7. NOT NULL + UNIQUE migration (Chunk 4.5) — pending; runs after Chunks 2-4 deploy and write paths populate slug. ORM types tighten from `Mapped[str | None]` / `str | None` to `Mapped[str]` / `str` in same PR.
- **Impact:** Items 1-2 are audit tasks; if pipeline pre-computes slug or `create()` is legacy, current code may have dead paths or double-compute. Item 5 risk: a frontend route name (e.g. `/admin`) could collide with a slug if blacklist is incomplete, breaking either the route or the publication URL. Item 6 risk: production downgrade after frontend ships breaks all inbound `/p/{slug}` links. Item 7 is required before slug becomes a stable public contract.
- **Resolution:** Sequential follow-up work post-impl: items 1-4 are grep audits and test fixture confirmations (1-2 hours total); item 5 runs alongside Phase 2.2 frontend dispatch; item 6 added to release checklist before Phase 2.2 frontend deploy; item 7 is the Chunk 4.5 migration PR (separate scope).
- **Target:** Items 1-4 in next maintenance window; items 5-6 before Phase 2.2 frontend deploy; item 7 as standalone Chunk 4.5 PR after Chunks 2-4 deployed and stable.

> Updated 2026-04-30: Phase 2.2.0.5 Part B merged. Production routers (admin_publications._serialize, public_graphics) now pass slug; PublicationResponse and PublicationPublicResponse tightened to `slug: str`. Items 2 and 7 closed. Items 1, 3, 4, 5, 6 remain open per their scheduled targets.

---

### DEBT-050: Phase 3.1 deferred chunks

- **Source:** Phase 3.1a Semantic Mapping foundation
- **Added:** 2026-04-30
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** Phase 3.1a ships the semantic_mappings DB schema, ORM,
  repository, and seed CLI. Remaining Phase 3.1 work is split across
  3.1aa (cube_metadata_cache + StatCanMetadataCacheService),
  3.1ab (validator using cache), 3.1b (admin CRUD endpoints + minimal
  Flutter admin UI), 3.1c (semantic discovery + resolve endpoints),
  and 3.1d (staleness check + hardening).
- **Impact:** Mappings can only be saved via CLI seed script until 3.1b
  ships. cube_id existence and dimension correctness are not validated
  at save time until 3.1ab ships — operator must manually review YAML
  before seeding. Frontend has no semantic picker until 3.1c ships;
  legacy copy-paste workflow continues until then.
- **Resolution:** Ship 3.1aa → 3.1ab → 3.1b → 3.1c → 3.1d in sequence.
  Each is a separate PR.
- **Target:** Phase 3.1d closure unblocks Phase 3.2 (frontend hybrid binding).

---

### DEBT-051: Event-driven StatCan metadata cache invalidation

- **Source:** Phase 3.1aa recon (`docs/recon/phase-3-1aa.md` §G1)
- **Added:** 2026-05-01
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `cube_metadata_cache` is refreshed by a nightly APScheduler
  cron job (`statcan_metadata_cache_refresh` at 15:00 UTC) using a blind stale
  sweep over all rows older than 23h. StatCan publishes a `getChangedCubeList`
  endpoint that returns cubes modified in a given window, but it is not yet
  consumed by the cache invalidation path.
- **Impact:** Cube metadata changes published by StatCan during the day are
  reflected in the cache only after the next nightly run (up to ~24h delay).
  No correctness impact for the validator (cache-required mode tolerates
  staleness). Mild over-fetching: nightly job refreshes all rows even when
  most haven't changed.
- **Resolution:** Add a delta refresh path keyed by `getChangedCubeList`
  results. Retain the nightly stale sweep as a safety fallback.
- **Target:** Opportunistic — post-Phase 3.1 closure, when StatCan ETL
  pipeline gets next material work.

> Note 2026-05-01: recon proposed this as DEBT-045, but DEBT-045 is already
> assigned (resolved) — next available ID was DEBT-051.

### DEBT-052: EN-only fuzzy member-name suggestion in mapping validator

- **Source:** Phase 3.1ab impl (`docs/recon/phase-3-1ab.md` §B3, founder lock 3)
- **Added:** 2026-05-02
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `validate_mapping_against_cache` produces fuzzy hints
  (`suggested_member_name_en`) using `difflib.get_close_matches` against
  cached EN member names only. FR member names are not considered. The
  StatCan metadata cache stores both EN and FR names, but the mapping
  schema is EN-canonical (project memory: "EN-canonical labels").
- **Impact:** In bilingual edge cases (e.g. an operator typos a member name
  in FR while editing an EN-canonical mapping) no fuzzy suggestion is
  produced. The blocking decision (MEMBER_NOT_FOUND error) is unchanged —
  no correctness risk; only reduced UX hint quality.
- **Resolution:** Extend `_maybe_fuzzy_suggest` to also search FR names, or
  use locale-aware normalization. Surface bilingual hints in the
  `ValidationResult` (e.g. `suggested_member_name_fr` field).
- **Target:** Opportunistic — post-3.1c UX refinement when admin UI
  internationalization is reviewed.

### DEBT-053: cube-metadata read endpoint hybrid prime mode

- **Source:** Phase 3.1b impl (`docs/recon/phase-3-1b.md` §F2)
- **Added:** 2026-05-02
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** `GET /api/v1/admin/cube-metadata/:cube_id` defaults to
  read-only (returns 404 on cache miss). Operators must opt-in to a
  fresh fetch via `?prime=true&product_id=N`. This shifts cache-warming
  responsibility to the operator workflow rather than the autocomplete
  read path, keeping the default operator-facing call cheap.
- **Impact:** Operators editing brand-new cubes will see a 404 +
  free-text fallback in the form. They can either submit (the save
  endpoint auto-primes via `service.upsert_validated`) or manually
  trigger prime via the explicit query param. Mild UX friction for the
  first-time-cube workflow.
- **Resolution:** If friction surfaces in operator usage, change the
  default to `prime=true` or add a Flutter form button "Fetch from
  StatCan" that calls the prime endpoint before submit.
- **Target:** Opportunistic post-Phase 3.1.

### DEBT-054: concurrency convention divergence (header AND body)

- **Source:** Phase 3.1b impl (`docs/recon/phase-3-1b.md` §A7)
- **Added:** 2026-05-02
- **Severity:** medium
- **Category:** architecture
- **Status:** accepted
- **Description:** `POST /api/v1/admin/semantic-mappings/upsert` accepts
  the optimistic concurrency token via EITHER `If-Match` request header
  OR `if_match_version` body field (header takes precedence). Returns
  `412 PRECONDITION_FAILED` on mismatch with envelope `error_code`
  `VERSION_CONFLICT`. The existing publications endpoint uses
  header-only convention. Both forms are accepted for Flutter form
  ergonomics + future tooling flexibility.
- **Impact:** API has a hybrid convention specific to semantic mappings.
  Future endpoints may inherit confusion about which approach to follow.
- **Resolution:** When adding a 3rd endpoint with optimistic concurrency,
  decide on a unified standard. Options: deprecate the body field on
  semantic-mappings (header-only); or migrate publications to also
  accept a body field; or document the divergence as intentional in
  `ARCHITECTURE_INVARIANTS.md`.
- **Target:** Phase 4 architecture review.

### DEBT-055: dimension_filters editor has no row reorder UX

- **Source:** Phase 3.1b impl (`docs/recon/phase-3-1b.md` §B6.4)
- **Added:** 2026-05-02
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** The `DimensionFiltersEditor` widget supports add and
  remove but no drag-to-reorder. Filters are semantically unordered
  (dict in storage), but operator workflow may want a stable display
  order across edits.
- **Impact:** Minor UX friction when editing mappings with 5+ filter
  rows.
- **Resolution:** Use `ReorderableListView` with drag handles. Storage
  stays a dict (no backend change needed); display order is local-only
  state.
- **Target:** Opportunistic UX pass.

### DEBT-056: Flutter backend_errors.dart full backfill needed

- **Source:** Phase 3.1b impl (`docs/recon/phase-3-1b.md` §F9)
- **Added:** 2026-05-02
- **Severity:** medium
- **Category:** code-quality
- **Status:** accepted
- **Description:** `frontend/lib/l10n/backend_errors.dart` previously
  mapped graphics/jobs codes only. Phase 3.1b added the seven
  semantic-mapping codes (5 from 3.1ab + 2 new in 3.1b:
  `VERSION_CONFLICT`, `BULK_VALIDATION_FAILED`). However a comprehensive
  sweep over ALL backend error codes (`KNOWN_BACKEND_ERROR_CODES` in
  `frontend-public/src/lib/api/errorCodes.ts`) to ensure parity is
  deferred work — the Dart mapper still has gaps for codes outside
  graphics, jobs, and semantic mappings.
- **Impact:** Errors from non-mapped backend modules (e.g. publications
  validation, statcan ETL) display as raw `error_code` rather than a
  user-friendly l10n string in the admin Flutter app.
- **Resolution:** Audit `KNOWN_BACKEND_ERROR_CODES` (TS), sync the Dart
  mapper to the full set, add corresponding ARB keys EN+RU.
- **Target:** Post-Phase 3.1 polish PR.

### DEBT-057: Reviewer P2/P3 polish backlog from PR #274

- **Source:** Phase 3.1b reviewer feedback round 2 (PR #274)
- **Added:** 2026-05-02
- **Severity:** medium
- **Category:** code-quality
- **Status:** accepted
- **Description:** Three semantic-mapping admin polish items deferred
  from Phase 3.1b R3. The first two are correctness/API-semantics
  concerns (not cosmetic), hence the medium severity rating:
  (1) the `IntegrityError` catch in `SemanticMappingService._upsert_atomic`
      is too broad — should narrow to unique-constraint violation only
      (`uq_semantic_mappings_cube_key`) so other DB constraint failures
      are not misinterpreted as "row already exists" and silently
      converted to UPDATE-on-mismatch [correctness];
  (2) `If-Match` against a missing row currently falls through to the
      CREATE branch — semantically should raise `MappingNotFoundError`
      so a stale editor cannot silently resurrect a row that was
      deleted between fetch and save [API semantics];
  (3) the Flutter form sends BOTH `If-Match` header AND
      `if_match_version` body simultaneously. The backend hybrid resolves
      the header first, so behaviour is correct, but cleaner to send
      header-only from the form and keep the body field for scripts and
      tests [cosmetic].
- **Impact:** (1) misleading 409-via-fall-through under rare non-unique
  DB violations; (2) stale-editor revive edge case; (3) cosmetic
  redundancy in admin save requests.
- **Resolution:** Narrow `except IntegrityError` to inspect
  `exc.orig.diag.constraint_name` (or driver equivalent); raise
  `MappingNotFoundError` when `if_match_version` is supplied but the
  row does not exist; switch the Flutter form to header-only.
- **Target:** Post-Phase 3.1 polish PR.

### DEBT-058: WDS data batch ceiling is a conservative guess

- **Source:** Phase 3.1aaa implementation (recon Q-impl-1)
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** correctness
- **Status:** accepted
- **Description:** `StatCanClient.get_data_batch` caps batch size at
  100 (`_MAX_BATCH_SIZE`) because the StatCan WDS documentation does
  not publish an explicit ceiling for
  `getDataFromCubePidCoordAndLatestNPeriods`. 100 was chosen as a
  generous upper bound that empirically does not hit 413 / payload
  limits in spot checks, but the real ceiling is unknown.
- **Impact:** Nightly refresh issues N/100 HTTP requests for N targets.
  Larger batches would reduce request count and rate-limit pressure.
  No correctness impact at the current 100 ceiling.
- **Resolution:** Confirm the actual ceiling with StatCan support OR
  empirically measure (binary search, fail at 413 or 5xx). Bump
  `_MAX_BATCH_SIZE` if a higher safe value is found.
- **Target:** Phase 3.2 polish.

### DEBT-059: WDS batch mixed-success behaviour assumed, not documented

- **Source:** Phase 3.1aaa implementation (recon Q-impl-2)
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** correctness
- **Status:** accepted
- **Description:** `StatCanClient.get_data_batch` assumes the WDS
  endpoint returns one envelope per input item — a per-item
  `{status: "FAILED"}` for invalid coords interleaved with
  `{status: "SUCCESS"}` for valid ones. This matches `getCubeMetadata`
  behaviour but is not explicitly documented for
  `getDataFromCubePidCoordAndLatestNPeriods`. The implementation logs
  + tolerates a per-item parse failure and emits `None`; the nightly
  refresh skips that target.
- **Impact:** Per-item parse failures are tolerated and emit None,
  matching observed metadata-endpoint behaviour. If StatCan instead
  fails the entire batch on a single bad item, all items in that
  batch lose this refresh cycle and are reported in
  RefreshSummary.errors. The nightly retry recovers on the next run.
- **Resolution:** Verify the per-item failure semantics with StatCan
  support; if confirmed, document in code. If contradicted, switch
  the batch path to single-item fallback on top-level failure.
- **Target:** Phase 3.2 polish.

### DEBT-063: semantic_key length asymmetry between mapping and cache tables

- **Source:** Phase 3.1c impl Round 3 (Codex auto-review on PR)
- **Added:** 2026-05-03
- **Severity:** medium
- **Category:** architecture
- **Status:** active
- **Description:** `semantic_key` length is asymmetric between the
  mapping table and the cache table. `SemanticMapping.semantic_key`
  is `String(200)` and `SemanticMappingCreate` accepts
  `max_length=200`, but `semantic_value_cache.semantic_key` is
  `varchar(100)`. The 3.1c resolve endpoint accepts up to 200 chars
  to remain reachable for admin-created mappings, but `auto_prime`
  writes to the cache will fail at the DB level for keys with
  101..200 chars (insertion violates length constraint).
- **Impact:** Mappings with `semantic_key` length 101..200 chars can
  be created via admin CRUD but cannot be cached. Resolve endpoint
  accepts the lookup, mapping is found, `auto_prime` triggers, and
  the cache-write fails. Caller sees `RESOLVE_CACHE_MISS` (or an
  upstream error envelope) on every miss-then-prime round-trip. The
  cache will never warm for those keys.
- **Resolution:** Align both schemas. Recommended: migrate
  `semantic_value_cache.semantic_key` from `varchar(100)` to
  `varchar(200)` to match the mapping table. Includes Alembic
  migration + downgrade path. Coordinate with 3.1aaa scheduler
  refresh schedule (cache-table column widening is non-destructive
  — no row-level data change needed).
- **Target:** Phase 3.1c follow-up — before Phase 3.2 frontend
  contract hardening. Phase 3.2 frontend will rely on resolve for
  bound publication blocks; latent cache-write failure for keys
  101..200 chars becomes user-visible the moment the first long-key
  mapping ships. Migration:
  `ALTER TABLE semantic_value_cache ALTER COLUMN semantic_key TYPE varchar(200);`
  — non-destructive widening, low risk. Coordinate with 3.1aaa
  scheduler refresh — column widening is metadata-only, no row-level
  data change. Not blocking 3.1c launch since current
  operator-created mappings observed in production are <100 chars,
  but MUST land before 3.2 ships.

### DEBT-062: Nightly refresh skips active mappings without cached coord

- **Source:** Phase 3.1aaa FIX-R2 (Blocker 2 fix collateral)
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** correctness
- **Status:** accepted
- **Description:** ``SemanticValueCacheRepository.list_active_lookup_keys``
  now LEFT-JOINs ``semantic_value_cache`` so active mappings without
  any cached row are included. Such mappings have ``coord=None`` in
  the result tuple. ``StatCanValueCacheService.refresh_all`` skips
  these (debug-logged) because deriving ``coord`` requires running
  the validator over the mapping config + cached metadata —
  duplicate of the auto-prime path.
- **Impact:** A mapping whose first auto-prime failed (StatCan
  unavailable at save time) will not be retried by the nightly job
  until a subsequent successful resolve or a manual re-save primes
  the cache. Acceptable for the best-effort retry contract; first-
  resolve will trigger a fresh prime.
- **Resolution:** Add an explicit prime-on-refresh path that, for
  ``coord=None`` rows, runs the validator against the latest
  ``semantic_mappings.config`` + cached cube metadata, derives
  ``coord``, and primes. Reuse the auto-prime helper.
- **Target:** Phase 3.1c, alongside the resolve service work.

### DEBT-061: Phase 3.1aaa P2 follow-ups (4 sub-items)

- **Source:** Phase 3.1aaa impl reviewer round 2026-05-03
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** code-quality
- **Status:** accepted
- **Description:** Four P2 items from the 3.1aaa impl reviewer not
  addressed in fix R1:
  1. ``parse_ref_period_to_date`` is named generically — rename to
     ``parse_semantic_value_ref_period_to_date`` (or scope via comment)
     to prevent future migration name collision when another module
     wants its own period parser with different dialect support.
  2. Confirm via grep / coverage that every integration test
     exercising the GENERATED ``period_start`` column, the partial
     ``ix_semantic_value_cache_is_stale`` index, and the FK CASCADE
     to ``semantic_mappings`` actually runs against PostgreSQL — the
     SQLite ``Base.metadata.create_all`` path will silently no-op
     those features.
  3. Add an explicit timestamp-exclusion test for
     :func:`compute_source_hash`: identical data fields with
     different ``fetched_at`` / ``release_time`` MUST produce the
     same hash. Today the test suite covers most exclusions but
     does not pin this guarantee.
  4. Add a Pydantic test for :class:`StatCanDataPoint`: WDS sometimes
     serialises ``value`` as a string-encoded numeric (``"165.7"``),
     and ``missing=true`` accompanies ``value=null``. Pin both
     branches at the schema layer so downstream consumers never see
     surprises.
- **Impact:** Low — cosmetic + test-coverage gaps. No runtime
  correctness risk.
- **Resolution:** Single follow-up cleanup PR after 3.1c.
- **Target:** Post-3.1c, before 3.1d.

### DEBT-060: ResolvedValue.units lacks a canonical mapping source

- **Source:** Phase 3.1aaa implementation (recon Q-impl-4)
- **Added:** 2026-05-03
- **Severity:** medium
- **Category:** product
- **Status:** accepted
- **Description:** `ResolvedValue.units` is reserved as a string
  field for the API boundary but is currently always `None`. The
  semantic mapping config has `"unit"` operator-typed text; cube
  metadata exposes `member_uom_code` (a numeric); neither is yet
  mapped to a canonical units string ("CAD", "%", "index", etc.).
  3.1c will need this populated to render values usefully.
- **Impact:** ResolvedValue.units is None for every cached row.
  3.1c resolve cannot render unit suffixes or perform unit-aware
  comparisons until a canonical mapping is wired.
- **Resolution:** Build a canonical units lookup keyed by either
  `member_uom_code` or the validator-resolved member name; populate
  `ResolvedValue.units` in 3.1c's resolve service. Document the
  source-of-truth (cube metadata UOM dimension vs operator config).
- **Target:** Phase 3.1c.

---

## Resolved

| ID | Description | Resolved in | Date |
|----|-------------|-------------|------|
| DEBT-010 | No audit event retention cleanup | Final Debts | 2026-04-12 |
| DEBT-015 | GraphicPipeline generate() method is monolithic | Final Debts | 2026-04-12 |
| DEBT-001 | Cooldown query uses text match on JSON | Docs & Quality | 2026-04-12 |
| DEBT-002 | Integration tests use metadata.create_all | Docs & Quality | 2026-04-12 |
| DEBT-003 | Dockerfile doesn't run migrations on startup | Pre-deploy Hardening | 2026-04-12 |
| DEBT-004 | Old in-memory TaskManager not yet removed | Dead Code Cleanup | 2026-04-12 |
| DEBT-005 | StorageInterface upload_bytes/download_bytes | PR B-3 | 2026-04-09 |
| DEBT-006 | Dead code in services/cmhc/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-007 | Dead code in services/ai/ directory | Dead Code Cleanup | 2026-04-12 |
| DEBT-008 | No startup validation for required secrets | Pre-deploy Hardening | 2026-04-12 |
| DEBT-012 | Admin graphics API uses placeholder data | PR B-3 | 2026-04-09 |
| DEBT-013 | Admin graphics uploads same file for high-res variant | PR B-3 | 2026-04-09 |
| DEBT-014 | database.py creates engine at module level | PR A-1 fix | 2026-04-06 |
| DEBT-016 | ARCHITECTURE.md references removed MVP features | Docs & Quality | 2026-04-12 |
| DEBT-017 | Job handlers violate ARCH-DPEN-001 with inline httpx | Docs & Quality | 2026-04-12 |
| DEBT-018 | TESTING.md coverage table is stale | Docs & Quality | 2026-04-12 |
| DEBT-019 | Orphaned LLM infrastructure outside services/ai/ | Dead Code Cleanup | 2026-04-12 |
| DEBT-020 | CMHC and Tasks routers still mounted for deferred features | Dead Code Cleanup | 2026-04-12 |
| DEBT-021 | Temp upload Parquet files not cleaned up | codex/fix-contrast-slot-validation | 2026-04-20 |
| DEBT-028 | Contrast validator only checks 'primary' slot per block | Stage 4 post-merge fix | 2026-04-21 |
| DEBT-027 | Autosave retry-reset effect uses exhaustive-deps exception | claude/fix-autosave-deps-warning-NoqvL | 2026-04-21 |
| DEBT-022 | `validateImport` dual-signature (string + throwing) | Stage 3 PR 2a (`claude/add-workflow-state-machine-mUM3P`) | 2026-04-17 |
| DEBT-023 | `validateImportStrict` does not deep-validate `Comment` entries | Stage 3 PR 2b (`claude/recon-comments-subsystem-HwvB1`) | 2026-04-17 |
| DEBT-024 | Rename `validateDocumentShape` -> `assertCanonicalDocumentV2Shape` | Stage 3 PR 4 (`claude/reconnaissance-persistence-cleanup-EJ4uX`) | 2026-04-19 |
| DEBT-026 | Lossy round-trip between `CanonicalDocument` and `AdminPublicationResponse` | Stage 4 Task 0 full close (`claude/close-infographic-blockers-wkjVX`) | 2026-04-19 |
| DEBT-045 | `cors_origins` Settings field declared but unused | codex/debt-045-cors-origins-remove | 2026-04-30 |

### DEBT-026: Lossy round-trip between CanonicalDocument and AdminPublicationResponse

- **Source:** PR review of `claude/wire-infographic-editor-9w3wr` (Stage 4 Task 0 initial commit `550c336`)
- **Added:** 2026-04-19
- **Severity:** high
- **Category:** architecture
- **Status:** resolved
- **Description:** `buildUpdatePayload` emitted only editorial / text / review fields; `hydrateDoc` reconstructed from a template and overlaid the narrow subset. Block-level props, chart data, and layout fields did not survive a save -> reload cycle. Size mapping (`instagram_1080` / `instagram_port` -> backend `instagram`) was additionally lossy on the inverse.
- **Impact:** Opening an existing publication, pressing Ctrl+S, and reloading silently reset block props and chart data to template defaults. Effective data loss on every save of any doc whose state exceeded the mapped subset.
- **Resolution:** Added opaque `document_state` JSON column on `Publication` (nullable, Alembic `a3e81c0f5d21`). Frontend sends the full canonical document as a JSON string in every PATCH; backend stores verbatim with no parsing or shape validation. Derived editorial columns (`headline`, `chart_type`, `visual_config`, `review`, `eyebrow`, `description`, `source_text`, `footnote`) are kept in sync for search indexing and the public gallery. `hydrateDoc` prefers `document_state` when present (parse + `validateImportStrict`); falls back to the legacy field-level hydrate with `deriveWorkflowFromStatus` for rows predating this column (those rows become lossless on first subsequent PATCH). `HydrationError` surfaces malformed `document_state` through `error.tsx`.
- **Target:** Stage 4 Task 0 full close (`claude/close-infographic-blockers-wkjVX`)
- **Resolved:** 2026-04-19
- **Resolution PR:** `claude/close-infographic-blockers-wkjVX` (fix commit `d46edf6`)

### DEBT-021: Temp upload Parquet files not cleaned up

- **Source:** JSON/CSV upload PR (`claude/add-data-upload-graphics-i8IWc`)
- **Added:** 2026-04-14
- **Severity:** low
- **Category:** ops
- **Status:** resolved
- **Description:** `POST /api/v1/admin/graphics/generate-from-data` writes a
  temporary Parquet to S3 under `temp/uploads/{uuid}.parquet` before
  enqueuing the existing `graphics_generate` job. The `GraphicPipeline`
  does not delete its input object, and no cleanup cron exists yet,
  so these temp Parquet files accumulate indefinitely.
- **Impact:** Low — individual objects are small (≤ 10 000 rows × columns
  of CSV/JSON data). Growth is proportional to upload volume; eventually
  increases storage cost and clutters bucket listings.
- **Resolution:** Add a scheduled task that deletes objects under
  `temp/uploads/` with a `LastModified` older than
  `settings.temp_upload_ttl_hours` (default 24 h).
- **Target:** Follow-up PR (not blocking for the upload feature).

- **Updated:** 2026-04-25 (UTC)
- **Updated 2026-04-25:** RESOLVED. Combined with post-Phase-3 ``temp_cleanup.py``
  safety fix in a single PR. Cleanup now scans ``temp/uploads/`` and
  ``temp/`` prefixes and excludes keys still referenced by ``Job`` rows in
  pending status before deletion (`queued`/`running`, plus `retrying` when that status exists in the enum). New settings:
  ``temp_upload_ttl_hours`` (24h default),
  ``temp_cleanup_max_keys_per_cycle`` (1000), and
  ``temp_cleanup_prefixes``. Added unit + integration coverage including an
  end-to-end pipeline test (upload -> pending job -> cleanup preserves ->
  job completion -> cleanup deletes).
- **Updated 2026-04-25:** FR2 addressed max_keys semantic bug surfaced in review. Storage listings are key-ordered (lexicographic), so capping raw listings could hide expired keys behind fresh ones. Cleanup now lists full prefix, filters by TTL, then caps the EXPIRED set (oldest-first). Warning logged when cap is hit so operators know to increase cycle frequency or cap size. New integration test `test_expired_beyond_fresh_listing_still_reached` covers the regression directly.
- **Updated 2026-04-25:** FR3 restored hard cap on listing side. Switched from list-all to paginated scan via new iter_objects_with_metadata on StorageInterface. Introduced two caps: max_list_keys_per_cycle (bounds memory/storage cost) and max_delete_keys_per_cycle (bounds DELETE work). Oldest expired candidates prioritized across pages via min-heap. Separate warnings emitted for each cap-hit scenario so operators can tune cycle frequency or cap sizes. Regression tests cover both cap paths and oldest-first ordering.
- **Updated 2026-04-26:** FR8 fixed three CI failures plus B-starve.
  (F1) Heap eviction comparison was inverted since FR2 — kept newest, not oldest.
  Replaced with `if ts < newest_selected_ts` using positive-timestamp comparison
  via `-oldest_expired[0][0]`. New regression
  test_oldest_expired_chosen_when_newer_keys_listed_first.
  (F2) Warning assertion substring updated from "delete cap reached" to
  "exceed delete cap" matching production log message.
  (F3) List cap halt verified BEFORE listed_total increment;
  global_list_cap_hit short-circuits subsequent prefixes.
  (F4 / B-starve) New collect_all_referenced_temp_keys() pre-listing collects
  pending-referenced keys; skipped at admission so max_delete_keys counts only
  deletable candidates. New regression
  test_referenced_pending_keys_do_not_consume_delete_cap.

  BREAKING CONFIG RENAME (from FR3, re-noted):
    TEMP_CLEANUP_MAX_KEYS_PER_CYCLE → REMOVED
    Replaced by:
      TEMP_CLEANUP_MAX_DELETE_KEYS_PER_CYCLE
      TEMP_CLEANUP_MAX_LIST_KEYS_PER_CYCLE
- **Updated 2026-04-25:** FR5 completed global per-cycle cap contract. Heap and both listing/delete counters hoisted outside prefix loop (review found FR4 did not fully apply this). Added two regression tests: test_max_delete_keys_is_global_across_prefixes and test_max_list_keys_is_global_across_prefixes. LocalStorageManager docstring clarified as dev/test-only.

### DEBT-035: Parallel config_hash computation in pipeline + lineage helper

- **Source:** Phase 1.1 Clone impl recon
- **Added:** 2026-04-26
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** `_compute_hashes` in `backend/src/services/graphics/pipeline.py:182` inlines its own SHA-256 hashing logic, parallel to the centralized `compute_config_hash` in `backend/src/services/publications/lineage.py`. Both produce the same hash for the same inputs today, but divergence risk exists if either path is updated independently.
- **Impact:** None today. Risk of silent hash drift if either path changes.
- **Resolution:** Refactor `_compute_hashes` to call `compute_config_hash` directly. Single helper for `config_hash`; only `content_hash` (which is bytes-based, different inputs) stays inline.
- **Target:** Opportunistic — bundle with next graphics pipeline refactor.

### DEBT-036: Verify crop zone dimensions against current platform layouts

- **Source:** Phase 1.4 Crop Zone overlays impl
- **Added:** 2026-04-26
- **Severity:** low
- **Category:** code-quality
- **Status:** active
- **Description:** `frontend-public/src/components/editor/config/cropZones.ts` currently ships with working-default crop dimensions for Reddit/Twitter/LinkedIn cross-post guides. Those dimensions are estimates and may drift as platform layouts evolve.
- **Impact:** Operator-visible crop guidance reflects the values currently encoded in `cropZones.ts`. These values are estimates pending live platform verification; they have not been audited against current Reddit/Twitter/LinkedIn cross-post layouts.
- **Resolution:** Capture screenshots from each platform preview flow, measure crop region, then update `CROP_ZONES` to stable ratios (not absolute pixels).
- **Target:** Opportunistic — bundle with first operator feedback round during Stage C onboarding.

### DEBT-040: Phase 2.5b — three deferred Exception Inbox row types

- **Source:** Phase 2.5 recon (Part C1 §2 row-type bucket classification) + PR #205 review
- **Added:** 2026-04-27
- **Severity:** medium
- **Category:** scope-deferred
- **Status:** active
- **Description:** Phase 2.5 DoD (per `OPERATOR_AUTOMATION_ROADMAP.md` line 180, post-update) calls for 5 row types in the Exception Inbox: failed exports, zombie jobs, stale bindings, missing post URLs, unresolved validation blockers. PR #205 (Phase 2.5a) ships the first two; the other three are blocked on backend entities that do not yet exist: `staleBindings` requires `Binding` model + `BindingRepository` + listing endpoint (owned by Phase 3 Data binding); `missingPostUrls` requires `post_ledger` table + listing endpoint (owned by Phase 2.3 Post URL ledger); `unresolvedValidationBlockers` requires either backend persistence of validation status on `Publication` or editor pushing validation results to a new backend endpoint (no phase currently owns this).
- **Impact:** Phase 2.5 DoD formally remains open until all 5 row types ship. Operators cannot triage stale bindings, missing post URLs, or validation-blocker exceptions through the inbox in v1; they must use other tools (manual queries, editor sessions). Acceptable for launch since the 2 v1 row types cover the highest-volume exception classes (failed exports, zombie jobs).
- **Resolution:** as each dependent phase ships, add a new `ExceptionFilter` enum value, a new branch in `exceptionsRowsProvider`, a new filter chip in `_ExceptionsFilterChips`, and ARB key pairs (filter chip label + any row-type-specific empty/error states). Append to existing `/exceptions` screen — no architectural restructure required (per Q-C.5 = flat, no drill-in routes). Subitem: before Phase 4 closure, founder + Claude must explicitly decide whether validation-blocker persistence belongs in a future Phase or stays as an "operator runs editor and notices" UX pattern.
- **Target:** Phase 3 ships `staleBindings`; Phase 2.3 ships `missingPostUrls`; validation-blocker scope assessment before Phase 4 closure.

### DEBT-041: PATCH publications has no idempotency-key short-circuit

- **Source:** Phase 1.3 implementation (R16 idempotency tension decision)
- **Added:** 2026-04-27
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** v1 of optimistic concurrency applies the ETag check unconditionally on every PATCH. A legitimate retry of an already-successful PATCH (e.g. network drop on the response leg) returns 412 because the server's stored ETag has advanced past the client's If-Match. The client treats the 412 as "reload and retry" — correct for both genuine concurrent edit AND rare network retry, but adds one extra round trip per dropped response.
- **Impact:** One extra round trip per dropped-response retry. Acceptable cost; the alternative (project-wide idempotency-key infrastructure) is materially more expensive than tolerating spurious 412s on a rare failure mode.
- **Resolution:** when HTTP idempotency-key infrastructure lands project-wide, integrate a cache-hit short-circuit BEFORE the ETag check inside the PATCH handler. On cache hit, replay the stored response verbatim. On cache miss, fall through to the existing ETag check. Ordering is load-bearing — cache-hit MUST short-circuit BEFORE the ETag check, returning the cached 200 OK; the ETag check applies only on cache miss.
- **Target:** when project-wide HTTP idempotency-key infrastructure is added.

### DEBT-042: PATCH publications tolerates missing If-Match for v1 deploy compat

- **Source:** Phase 1.3 implementation (Q3=(a) backcompat decision)
- **Added:** 2026-04-27
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** v1 server tolerates an absent If-Match header on PATCH (warn-log, proceed without ETag check) to avoid breaking old browser tabs mid-deploy. Without this tolerance, every open tab still running the old frontend would 412-fail on its next autosave the moment the new backend rolls out, producing a thundering herd of "reload and retry" prompts during the deploy window.
- **Impact:** Operator-visible warn-log noise during the rollout window; rollout-period tabs do not get optimistic-concurrency protection. Once frontend is fully deployed, warn-log volume drops to near-zero.
- **Resolution:** after two weeks of clean deploy (frontend rolled out everywhere AND no warn-log entries for the missing-If-Match codepath for 7 consecutive days), change the handler to require If-Match and return 428 Precondition Required if absent. Update `docs/architecture/BACKEND_API_INVENTORY.md` to reflect the new strictness. Remove the warn-log emitter.
- **Target:** 2 weeks after Phase 1.3 production deploy + 7 consecutive days of negligible warn-log volume.

### DEBT-043: PATCH publications has narrow TOCTOU window between ETag check and UPDATE

- **Source:** Phase 1.3 implementation (concurrency-hardening note)
- **Added:** 2026-04-27
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** v1 of optimistic concurrency relies on PostgreSQL's implicit row-level UPDATE serialization to defend against the narrow TOCTOU window between (a) the get_by_id SELECT, (b) the If-Match-vs-server-ETag comparison, and (c) the update_fields UPDATE. All three operations execute on the same per-request AsyncSession in the same transaction; the UPDATE acquires a row-level lock implicitly, so a second concurrent writer's UPDATE serialises behind the first. The SELECT in step (a) is NOT itself locked, so a window exists where two writers observe the same If-Match-valid state before either UPDATE runs. Defence is "second UPDATE produces a stale ETag", not "second UPDATE rejected at SELECT time".
- **Impact:** Under sustained concurrent-write load on the same publication row, lost-update probability rises. For v1 traffic patterns (single editor per publication is the dominant case), this is acceptable. Under contention, last-writer-wins on the second UPDATE.
- **Resolution:** if telemetry surfaces lost-update races (operationally: increased rate of 412s on this code path, or audit-log evidence of overlapping successful PATCHes that should have conflicted), promote the get_by_id SELECT to `.with_for_update()`. That converts step (a) into a row lock, eliminating the TOCTOU window at the cost of one Postgres row lock per PATCH. Add a regression test exercising two concurrent PATCHes asserting at most one succeeds.
- **Target:** telemetry-triggered. Verify before flipping that the `.with_for_update()` change passes a load test on a multi-connection pool to confirm the lock is per-row not per-table.


### DEBT-044: Phase 1.6 — multi-block selection + bulk context-menu actions

- **Source:** Phase 1.6 implementation (Q7 = single-block-only locked for v1)
- **Added:** 2026-04-27
- **Severity:** small (UX gap, not blocking — single-block path covers the v1 critical path)
- **Category:** scope-deferred
- **Status:** active
- **Description:** Phase 1.6 ships per-block right-click context menu (Lock / Hide / Duplicate / Delete) and matching keyboard shortcuts. Multi-block selection (marquee drag, shift-click extend, aggregated menu state) is explicitly out of scope for v1. Right-clicking a different block while a menu is open already closes the prior menu and reopens for the new block; the editor still treats selection as single-only.
- **Impact:** Operators must perform structural cleanup (lock 5 blocks, hide 3 blocks, duplicate a section's worth of optional blocks) one block at a time. Acceptable for v1 traffic — operators rarely chain identical mutations across more than 2–3 blocks per editing session per current usage.
- **Resolution:**
  - Add marquee-drag selection on Canvas (rectangular selection over hit-test rects)
  - Add shift-click to extend the current selection
  - Aggregate context-menu state with mixed-state indicators ("Lock 3 blocks" / "Show 2 of 4" etc.)
  - Bulk Delete confirms once for the entire selection if any block is non-empty
  - Bulk Duplicate inserts copies after each source preserving relative order
  - The reducer's per-block `TOGGLE_LOCK` / `DUPLICATE_BLOCK` / `REMOVE_BLOCK` already form the underlying primitives; multi-select is a UI layer on top, not a refactor of state shape.
- **Target:** post-Phase-3 polish — operator productivity refinement after the binding system ships. Not roadmap-critical for Phase 2.
