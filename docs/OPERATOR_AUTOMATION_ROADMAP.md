# Operator Automation Roadmap

**Status:** Active
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-23
**Supersedes:** N/A (first canonical version)
**Related:** `ROADMAP_v8_FINAL.md`, `EDITOR_ARCHITECTURE.md`, `ARCH_RULES.md`, `DEBT.md`, `I18N_PLAN.md`

---

## 0. Context & purpose

This document is the canonical plan for simplifying and automating the daily work of two operators (designer + data worker) joining post-Stage-4. It is the synthesis of two independent deep-research passes over the operator workflow and supersedes any ad-hoc planning prior to 2026-04-23.

**Scope:**
- Operator-facing workflows in Next.js Editor (`/admin/editor/*`) and Flutter operational app
- Distribution pipeline (Reddit / X / LinkedIn posting, UTM attribution, lead funnel instrumentation)
- Institutional memory — how editorial decisions accumulate as reusable assets
- Observability loop tying publications to outcomes

**Out of scope:**
- i18n implementation (tracked separately in `I18N_PLAN.md`)
- Launch/deploy tasks (tracked in `docs/deployment.md`)
- Backend architecture changes unrelated to operator UX

---

## 1. Guiding thesis

The working hypothesis before this plan was: *make the current manual steps faster*. That framing would lead us to data binding, template suggestion, and multi-preset export as the top priorities.

The revised thesis is: **the bottleneck is not speed of re-entry — it is that good editorial decisions don't accumulate as reusable assets**. Templates capture visual form. What is missing is the composite: slice + editorial angle + template + bindings + channel package + post-outcome.

This reframes the roadmap: build the **shared asset model first** (cloning, distribution packaging, outcome attribution), then layer the faster-entry features (binding, suggestion) on top of an asset model that already has signal.

Corollary: we deliberately postpone end-to-end data binding (Q1) from Week 1 to Week 3-4. Cloning a published graphic gives the operator all bound values for free. Binding is only strictly necessary when there is nothing to clone from — which is a Week 3+ problem, not a Week 1 problem.

---

## 2. Hard constraints

These are non-negotiable for every item in this roadmap. Any proposal violating them must explicitly justify the violation and be approved by the founder.

### 2.1 Architectural rules (from `ARCH_RULES.md`)

- **ARCH-PURA-001** — pure functions for hashing & data transformation
- **ARCH-DPEN-001** — constructor DI, no global state
- **R6** — short-lived DB sessions
- **R15** — hard caps on result sizes
- **R16** — idempotent retry
- **R17** — token flow security
- **R19** — publication versioning: `source_product_id` + `config_hash` → lineage key
- No pandas in Polars-path files
- AsyncMock for all async test mocks

### 2.2 Product constraints

- **No LLM in critical pipeline.** LLM is acceptable only as (a) one-off local scripts or (b) a narrow post-launch opt-in button. No cost-tracking infrastructure, no caching with `prompt_hash + data_hash`, no budget alerts.
- **Template lock.** The editor is template-driven. Do not propose replacing it with a free-form canvas.
- **Deterministic export.** Same input → same pixel output. Any binding or resolution mechanism must preserve this.
- **Minimal role system.** Admin only now. Editor + reviewer roles are architectural preparation, not Week-1 features.
- **Operators are not developers.** Designer = Figma/Canva culture. Data worker = Excel culture. Neither knows SQL, Polars schemas, or CLI. Command palettes and keyboard-driven interfaces are a misfit.

### 2.3 Process constraints

- **Windows/PowerShell dev environment.** Tools assuming Unix shell are friction.
- **AI-assisted dev loop.** Every item must be implementable by Jules/Cursor agents given a structured fix prompt. Agents never commit/push — founder responsibility.
- **PR review capacity.** ~15-25 agent PRs per week given 10-20 min review per PR. Phases are sized around this.
- **Content-factory economics.** Recurring API cost requires justification. One-off scripts are free.

---

## 3. Operator personas (reference)

### 3.1 Designer

- Primary surface: Next.js Editor (`/admin/editor/*`)
- Tool reference: Figma, Canva, Notion
- Comfortable with: visual inspection, mouse interaction, forms
- Uncomfortable with: SQL, Polars schemas, command palettes, keyboard-first UX
- Typical output: 3-10 infographics/day once ramped

### 3.2 Data worker

- Primary surface: Flutter operational app
- Tool reference: Excel, Google Sheets
- Comfortable with: CSVs, pivot tables, reading schemas
- Uncomfortable with: CLI, Git, writing SQL
- Typical load: 10-50 cube operations/day, occasional incident retry bursts

### 3.3 Founder

Active on both surfaces plus backend/deploys. Design mode unlocked. Reviews PRs from Jules/Cursor. Writes fix prompts via Claude.

---

## 4. Asset model (the core abstraction)

This is the foundation everything else rests on.

### 4.1 Hierarchy

```
Publication (existing)
  └── visual_config (JSON, versioned via R19)
        ├── blocks[] (26 types, 5 categories)
        ├── theme, palette, background
        └── bindings (hybrid snapshot + refresh — Phase 3)

StoryRecipe (FUTURE, observe-first)
  = composite of: slice + template + editorial angle + channel package
  promoted from a successful publication with a one-line editorial note

DistributionPackage (Phase 2)
  = per-publication artifact bundle containing:
      - PNGs for each enabled preset
      - distribution.json / publish_kit.txt
      - UTM-tagged links per channel
      - platform-specific captions (optional LLM draft)
      - alt-text drafts

Post ledger (Phase 2)
  = flat table: publication_id × channel × post_url × posted_at × UTM campaign

Outcome attribution (Phase 2+)
  = UTM-encoded lineage_key → lead/download events → back to publication
```

### 4.2 Why recipe is deferred

`StoryRecipe` as a formal entity is seductive but premature. We cannot design a good taxonomy for editorial angles before we have 4-6 weeks of actual published graphics to learn from. Cloning a published graphic — as `visual_config` duplicate with a lineage reset — gives 80% of the recipe benefit at 10% of the engineering cost.

**Decision:** build cloning in Phase 1. Observe which graphics operators clone and why. If after 4-6 weeks the patterns are distinct enough to warrant formal `StoryRecipe` with tags/angles/notes, promote it. If cloning alone suffices, skip the formal model entirely.

---

## 5. Phased roadmap

Five phases, sized for ~15-25 agent PRs/week. Phase boundaries are review gates, not calendar weeks — a phase can compress or slip without reordering.

### Phase 1 — Immediate leverage (Week 1)

**Goal:** make the current manual process fast without changing underlying architecture. Unlock cloning as primary reuse mechanism.

| # | Item | Effort | PRs | Depends on |
|---|---|---|---|---|
| 1.1 | Clone from Published (new lineage + `cloned_from_publication_id` FK) | S | 1 | Q-A resolved (see §10) |
| 1.2 | Golden Example drafts (infrastructure only; content populated in Stage C) | XS | 0 (manual) | 1.1 merged |
| 1.3 | Optimistic Concurrency (ETag + 412) | S | 1 | — |
| 1.4 | Platform Crop Zone overlays | S | 1 | — |
| 1.5 | Visual Data Diffing in Flutter `/data/preview` | S | 1-2 | — |
| 1.6 | Right-click Context Menus in Editor | S | 1 | — |

**Definition of done for Phase 1:**
- A designer can duplicate any published infographic as a new draft with one click
- Cloned publication has its own lineage key (new `source_product_id` + `config_hash`) but retains `cloned_from_publication_id` for audit trail
- Golden Example drafts infrastructure ready (content populated by founder during Stage C)
- Concurrent editing by two operators cannot silently overwrite each other's work
- Editor preview shows Reddit/Twitter timeline crop zones as overlay
- Flutter data preview highlights cells that changed since last sync in `#FBBF24`
- Right-click on any block in the Editor opens lock/hide/duplicate/delete menu

### Phase 2 — Distribution & observability (Week 2)

**Goal:** close the distribution-side gap. Every graphic ships with its distribution package. Every lead/download attributes back to a publication via UTM.

| # | Item | Effort | PRs | Depends on |
|---|---|---|---|---|
| 2.1 | Multi-preset ZIP export (client-side fflate) | M | 2-3 | — |
| 2.2 | Publish Kit Generator (distribution.json in ZIP) | M | 2 | 2.1 |
| 2.3 | UTM-to-lineage attribution pipeline | S | 1 | 2.2 |
| 2.4 | Opt-in Draft Social Text (Gemini Flash, no cache) | S | 1 | 2.2 |
| 2.5 | Exception Inbox (Flutter) | M | 2 | — |

**Definition of done for Phase 2:**
- "Export all valid" button produces a ZIP with per-preset PNGs + `distribution.json` + `publish_kit.txt`
- `publish_kit.txt` contains Reddit/X/LinkedIn captions with UTM-tagged URLs (`?utm_content=<lineage_key>`)
- Lead submissions with `utm_content` log the lineage_key and are queryable per publication
- An opt-in "Draft social text" button in the Editor returns 3 platform-specific captions (single Gemini Flash call, no cache, no retry — manual fallback on failure)
- Phase 2.5a (v1, ships independently): Flutter Exception Inbox aggregates failed exports + zombie jobs in a single list at /exceptions. UI framing: "items needing attention" (review surface, not strict actionable-only — zombie jobs are diagnostic-only without backend requeue/cancel endpoint).
- Phase 2.5b (deferred, ships when dependencies land): stale bindings (depends on Phase 3 Binding entity), missing post URLs (depends on Phase 2.3 post_ledger), unresolved validation blockers (depends on backend persistence of validator state — no phase currently owns). Each row type attaches to existing /exceptions screen as its dependency phase ships; no architectural placeholder reserved in 2.5a (per Q-C.3 = wait).

### Phase 3 — Data binding (Weeks 3-4)

**Goal:** replace manual copy from StatCan preview to Editor text fields with hybrid snapshot binding. Only meaningful after cloning is deployed, because cloning already carries bound values.

| # | Item | Effort | PRs | Depends on |
|---|---|---|---|---|
| 3.1 | Semantic Layer backend (Dimension → Category → Metric) | M | 3-4 | — |
| 3.2 | Hybrid binding frontend (Zustand snapshot state) | L | 4-5 | 3.1 |
| 3.3 | Binding status UI (subtle color dots, no heavy iconography) | S | 1 | 3.2 |
| 3.4 | Template Suggestion (silent prefill from `subject_code`) | S | 1 | 3.1 |
| 3.5 | Publish-time stale binding warn-and-confirm dialog | S | 1 | 3.2 |

**Definition of done for Phase 3:**
- Operator selects a cube, sees semantic picker ("Current rate", "YoY change", "Top 10 by X"), no Polars schema exposed
- Bound block stores `snapshotValue`, `resolvedAt`, source hash — rendering uses snapshot, never live read
- Status dots next to bound blocks: empty / gray (current) / yellow (stale) / red (broken schema)
- "Check for updates" action compares snapshot to live source, creates new R19 version on re-resolve
- Publish with stale binding shows confirm: "Dataset has newer data. Publish with current snapshot or update?"
- Partial failure: broken field renders last known snapshot with yellow warning tape (editor-only, never exported)
- Clicking a cube in `/cubes/:productId` can open Editor with template, background, eyebrow, source pre-filled

**Explicit non-goals in Phase 3:**
- No live-resolving bindings (violates R19 determinism)
- No bindings saved as standalone reusable slices — bindings stay coupled to their publication
- No confidence scores or AI-driven template suggestion — deterministic lookup only

### Phase 4 — Operational resilience (Week 5)

**Goal:** reduce founder support load. Make incidents self-service.

| # | Item | Effort | PRs | Depends on |
|---|---|---|---|---|
| 4.1 | Flutter Bulk Job Retry (with jitter) | S | 1-2 | — |
| 4.2 | Range-select (Shift-click) in Flutter lists | S | 1 | 4.1 |
| 4.3 | Localizable error/status contract | S | 1 | — |
| 4.4 | Contextual help drawer (Editor + Flutter) | M | 2 | 4.3 |
| 4.5 | Validator: duplicate-headline detection across published corpus | S | 1 | — |

**Definition of done for Phase 4:**
- Incident retry of 50 zombie jobs is a 10-second action, with sequential dispatch or jitter to avoid thundering herd on APScheduler
- Shift-click range select + fixed bottom action bar (Approve/Retry/Delete) in Flutter `/queue` and `/jobs`
- All error messages have a structured error code (RU/EN translatable) — frees Stage 5 DEBT item
- Help drawer opens from `?` key, shows context-aware guidance without leaving the screen
- Editor warns if headline substring-matches a published headline from the last 90 days

### Phase 5 — Observe and decide (Week 6+)

**Goal:** not a fixed plan. After Phases 1-4, review what operators actually do with the new tools.

**Decision points at Phase 5:**
- Did cloning produce patterns distinct enough to warrant formal `StoryRecipe` model? (Tagging, angle notes, promotion workflow.)
- Did UTM-to-lineage attribution produce enough signal, or do we need selective channel API ingestion (X Measurements API first, LinkedIn only if access exists)?
- Did Golden Examples reduce founder support enough, or is a first-run tour still needed?
- Are there patterns in the Exception Inbox that justify proactive automation (auto-retry for specific error classes, auto-disable of stale bindings)?

No items are pre-committed for Phase 5. This is the observe-first buffer.

---

## 6. Deferred / explicitly not doing now

These were considered and deferred with rationale. Do not re-propose without new evidence.

| Item | Why deferred |
|---|---|
| Formal `StoryRecipe` / `SavedSlice` DB models | Wait 4-6 weeks post-cloning. Premature taxonomy risk. |
| Third-party API ingestion (Reddit, X, LinkedIn) | UTM-first is less fragile. Revisit only if UTM under-samples. |
| Command palette (Cmd+K) | Developer-culture pattern. Operators come from Figma/Excel. |
| Auto-resize across preset families (e.g. Long → Story) | This is a redesign problem, not a resize problem. Force operator to choose compatible base template. |
| LLM headline generation at runtime | Explicit Section 2.2 constraint. Distribution copy pack is the one runtime LLM call on the roadmap. |
| CRDT or patch-based merge for concurrent editing | Overkill for 2 operators at 3-10 graphics/day. ETag + 412 + "fork as new draft" is sufficient. |
| Mobile-view simulation in validator | Deferred until distribution analytics show it matters. |
| Color-blindness simulation in validator | Deferred until evidence of issue. WCAG contrast already checked. |
| First-run tour / tooltips | Golden Examples replace this. Tours get dismissed, tooltips annoy. |
| Bulk approve/reject in queue triage | At 10-20 briefs/day, reading takes longer than clicking. Not a bottleneck. |
| Headline style guide surfaced inline | Deferred. Clone-from-published carries editorial tone implicitly. |

---

## 7. PR implementation conventions

All items in this roadmap follow the existing project conventions. Enforced per PR:

- **Implementation prompts** written by founder via Claude in the established structured format (before/after snippets, grep verification, explicit "DO NOT" constraints, Summary Report output)
- **Pre-recon / recon / impl / fix phases** as per `agent-workflow.md`
- **Testing:** unit tests required, integration tests where a PostgreSQL interaction exists, coverage >85%
- **Architectural review:** every PR self-checks against Section 2.1 rules. Violations block merge.
- **Documentation:** every PR updates relevant `.md` files in the same commit (per `api.md`, `core.md` maintenance rule)
- **DEBT tracking:** non-blocking issues go into `DEBT.md` with severity + category + target

---

## 8. Success criteria

This roadmap is judged against operator-observable outcomes, not PR count.

### After Phase 1:
- Time to create a clone of a published graphic: under 30 seconds
- Concurrent-edit data loss incidents: zero
- Operator export unusable due to platform crop: zero (preview catches it)

### After Phase 2:
- Time from "graphic approved" to "posted with UTM on 3 channels": under 3 minutes (was ~15)
- Lead → publication attribution coverage: 100% of UTM-tagged leads
- Founder Slack pings about "where do I post this" or "what's the UTM": zero

### After Phase 3:
- Time to bind 10 StatCan data points to a Ranked Bar: under 90 seconds (was ~5-10 minutes of copy-paste)
- Manual copy-paste from data preview to Editor: operator's choice, not necessity
- R19 lineage integrity: every publish with updated data produces a new version, no in-place mutation

### After Phase 4:
- Founder time spent answering "how do I" questions per week: under 30 minutes
- Recovery from a 50-zombie-job incident: under 1 minute of operator time

### After Phase 5 observation window:
- Decision made on `StoryRecipe` promotion (yes / no, with evidence)
- Decision made on channel API ingestion (which platforms, if any)

---

## 10. Resolved decisions and open questions

### Resolved (locked)

- **Q-A RESOLVED (2026-04-23).** Clone-from-published uses **new lineage + `cloned_from_publication_id` FK field**. Rationale: preserves R19 integrity (each publication has its own `source_product_id` + `config_hash` lineage key — clones typically have modified data/config) while keeping a lightweight audit trail for future pattern analysis. The `cloned_from_publication_id` field is nullable, indexed, and never used for cascade operations. It powers future "clone tree" visualizations and the Phase 5 decision on `StoryRecipe` promotion.
- **Q-B RESOLVED (2026-04-23).** Golden Example drafts written by founder, sourced from launch batch during Stage C (see §11 Execution Sequence). Founder picks 3 graphics from the launch batch, clones them to DRAFT, renames to `TUTORIAL: <template>`. No code change required beyond Phase 1.1 being merged.
- **i18n strategy RESOLVED (2026-04-23).** Each roadmap PR adds required strings to both locale files (`en.json` + `ru.json` for Next.js, `en.arb` + `ru.arb` for Flutter) in the same PR. No separate i18n pass is scheduled. Every implementation prompt must include the explicit constraint: *"DO NOT add hardcoded English strings — every new UI text must be added to both locale files in this PR."*

### Open (decidable at phase boundary)

- **Q-C.** Exception Inbox location: new Flutter route `/exceptions` or overlay on `/jobs`? Decide at start of Phase 2.5.
- **Q-D.** UTM schema: is `utm_content=<lineage_key>` sufficient, or also `utm_campaign=<recipe_tag>` for future grouping? Decide at start of Phase 2.3.
- **Q-E.** Semantic Layer backend (3.1): hardcoded per-cube mappings maintained by founder, or derived from cube metadata by convention? Decide at start of Phase 3.1.

---

## 11. Execution sequence (the when)

This section binds the phased roadmap from §5 to a real sequence of stages. Stages are units of sequencing, not calendar weeks — each stage is a review gate with explicit entry and exit criteria.

### Stage A — Pre-batch foundation

**Exit criteria for Stage A:**
- i18n Phase 1 (Next.js editor) and Phase 3 (Flutter) finalized — last remaining keys translated and verified (see `DEPLOYMENT_READINESS_CHECKLIST.md` §5)
- Blocker tech debt closed: DEBT-008 (startup secrets validation), DEBT-020 (dead routers unmounted), DEBT-016/019 (docs cleanup of removed LLM Gate references)
- Other DEBT entries handled opportunistically if time permits (not gated)
- Launch content batch scope confirmed (founder-only decision, recorded in `CONTENT_PLAN_v2.md`)

**Estimated effort:** ~3-5 days of focused work.

**Work happens in:** local dev environment only. No production deploy during Stage A.

### Stage B — Operator tooling + roadmap Phase 1-2 in parallel

This stage runs two tracks simultaneously.

**Track 1 — Agent PRs (founder reviews):**
- Roadmap Phase 1 (6 items, see §5 Phase 1)
- Roadmap Phase 2 (5 items, see §5 Phase 2)
- Each PR adds required strings to `en.json`/`ru.json` + `en.arb`/`ru.arb` in the same commit

**Track 2 — (deferred to Stage C per founder decision 2026-04-23):**
Content batch creation is **not** started during Stage B. Originally this stage was planned to include parallel content work; founder opted to concentrate batch creation in Stage C for personal customization and expansion.

**Exit criteria for Stage B:**
- Roadmap Phase 1 + Phase 2 merged and verified on local
- Clone from Published (1.1) works end-to-end
- Golden Example template infrastructure ready (but not yet populated — that happens in Stage C)
- Publish Kit Generator (2.2) produces valid `distribution.json` + `publish_kit.txt` in test ZIP
- UTM-to-lineage pipeline (2.3) logs lineage_key on test lead submission
- All new UI strings present in both locale files; runtime switcher works

**Estimated effort:** ~3-4 weeks.

**Work happens in:** local dev environment only. No production deploy during Stage B.

### Stage C — Launch batch creation + onboarding (founder-personal)

This is founder's hands-on stage. Content creation is intentionally not parallelized with roadmap work — founder wants to personally customize and expand the launch batch using the Stage B tooling.

**Launch batch scope (founder's call, recorded here for traceability):**

Initial launch set of 6 graphics from `CONTENT_PLAN_v2.md` waves 1.1 and 1.2:

- Wave 1.1: #1 Анатомия $100k, #5 Челюсти (2 graphics)
- Wave 1.2: #6 GDP per capita, #7 Бюрократия, #25 (pair with #7) (3 graphics, released as 2 posts)

Mix: 3 resonant/provocative topics (#1, #7+#25) + 3 framing forensic topics (#5, #6). Total 5 distinct posts, 6 graphic artifacts.

**Prepared but not launched immediately (scheduled post-launch):**
- Wave 1.3: #4 Telecom, #8 Картели — second resonant wave

**Founder may extend the launch batch.** This scope is a floor, not a ceiling. Founder retains discretion to add graphics during Stage C.

**Stage C activities:**
1. Founder creates launch batch using existing Editor + Stage B tooling (Clone from Published accelerates from graphic #2 onward)
2. Founder selects 3 of the completed graphics, clones them, renames to `TUTORIAL: <template>` — populates Golden Example drafts (Phase 1.2 content)
3. Deployment Readiness Checklist (`DEPLOYMENT_READINESS_CHECKLIST.md`) worked top-to-bottom
4. Operators granted local access, prompted to reproduce 1-2 graphics using Golden Examples as reference

**Exit criteria for Stage C:**
- Launch batch created and saved as PUBLISHED records in local DB (DNS still points to old env)
- Golden Example drafts populated
- `DEPLOYMENT_READINESS_CHECKLIST.md` 🔴 items all ✅; 🟡 items ✅ or mitigation documented
- Operators report onboarding friction (or lack thereof) — feeds Phase 4 help-drawer scoping

**Estimated effort:** 1-2 weeks (flexible — founder sets pace).

### Stage D — Production cutover + continuous improvement

**Cutover day:**
1. DNS Porkbun → Cloudflare cutover
2. Verify public gallery renders launch batch
3. First post to Reddit/X/LinkedIn: wave 1.1 resonant (#1 Анатомия $100k)

**Post-launch cadence:**
- Week 1: publish waves 1.1 graphics (#1, #5) per `CONTENT_PLAN_v2.md` schedule
- Weeks 2-4: publish wave 1.2 (#6, #7+#25), prepare wave 1.3 (#4, #8)
- Weeks 4-6: Roadmap Phase 3 (data binding) — informed by what operators actually found painful during manual batch creation
- Weeks 6-8: Roadmap Phase 4 (operational resilience) — informed by real incident patterns
- Week 8+: Phase 5 observation window

**Continuous improvement (ongoing):**
- Founder observes operator workflow, logs pain points
- Monthly review: what to prioritize next from backlog / new observations
- Quarterly: revisit deferred items in §6, promote any that accumulated evidence

### Sequence summary

```
Stage A (3-5 days)  — i18n finish + blocker debt + checklist defined
    ↓
Stage B (3-4 weeks) — Agent work: Roadmap Phase 1 + Phase 2 (no content, no deploy)
    ↓
Stage C (1-2 weeks) — Founder: Launch batch creation + onboarding + checklist work
    ↓
Stage D (cutover)   — Deploy. Post #1. Begin publishing cadence.
    ↓
Stage D continues   — Roadmap Phase 3, Phase 4, Phase 5 (post-launch, informed by real use)
```

### Why this sequence

- **Stage B before content work:** Phase 1 Clone from Published and Phase 2 Publish Kit Generator make content creation materially faster. Creating batch before them means doing the slow version of work that will shortly have a fast version.
- **Content concentrated in Stage C:** founder wants personal control over launch batch editorial angle, not to split attention across agent PR reviews and content simultaneously.
- **Phase 3-4 after deploy:** data binding (Phase 3) is designed based on which copy-paste patterns operators actually find painful. Building it before seeing operators work is guessing. Operational resilience (Phase 4) requires real incident data to prioritize help-drawer content.
- **i18n in every PR, not as a separate pass:** the i18n infrastructure is already in place (per founder's note 2026-04-23). Adding keys per PR is cheap; double-pass would be waste.

---

## 12. Revision log

| Date | Change | Reason |
|---|---|---|
| 2026-04-23 | Initial version | Synthesis of two deep-research passes over operator workflow |
| 2026-04-23 | Added §11 Execution sequence; resolved Q-A, Q-B, i18n strategy | Founder confirmed sequencing after review of CONTENT_PLAN_v2 and I18N_PLAN |

---

**End of roadmap.**
