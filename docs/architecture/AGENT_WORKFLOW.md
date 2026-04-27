# Agent Workflow — Claude-Architect to Implementor Protocol

**Status:** Living document — update on every workflow change or new agent-failure pattern
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-26
**Sources:** Memory items aggregated from Phase 1.1, 1.4, 1.5, DEBT-021, DEBT-030, Slice 3.8

**Maintenance rule:** any new agent-reliability pattern (hallucinated execution, sandbox quirk, push race condition, fixture mistake) MUST be added here in the same PR that addresses it. The point is that the next agent in the next session doesn't repeat the same mistake.

## Roles

- **Claude (architect)** — generates pre-recon, recon, impl, fix prompts. Diagnoses failures, writes targeted fix prompts. Never edits code directly in this project.
- **Jules / Codex / Cursor (implementor)** — receives prompts from founder, executes them in agent sandbox. Returns Summary Reports + diffs.
- **Founder (Oleksii)** — reviews prompts before sending, approves recon, reviews PR diffs, commits planning artifacts to repo, makes architectural decisions on open questions.

Agents NEVER commit or push code without explicit auto-fix-mode authorization. Founder commits planning artifacts on dedicated branches.

## 2. PR cycle stages

### 2.1 Pre-recon

**Purpose:** inventory existing code in the area touched by the upcoming PR. Read-only.
**Inputs:** roadmap reference, scope statement.
**Outputs:** structured inventory document.
**Verification:** structural completeness of sections, NOT length. Length-padding gates introduce noise (memory item).
**File location:** `docs/recon/<phase>-pre-recon.md` if remote available, else `/mnt/user-data/outputs/`.

### 2.2 Recon-proper

**Purpose:** consume pre-recon, produce architectural design proposals + open founder questions.
**Inputs:** pre-recon document, founder Q&A on ambiguities.
**Outputs:** recon document with sections per phase template (typically A through J).
**Verification:** every architectural decision has a Source citation; every open question is explicit.
**Format:** EXTENDED Summary Report required (full ARB key map table, complete text of every ambiguity/founder question, full glossary proposals, full DEBT entry draft) — recon is the founder-approval gate, needs review-grade detail in chat, not just counts (memory item).

### 2.3 Impl prompt

**Purpose:** translate approved recon into a step-by-step implementation specification for the implementor agent.
**Inputs:** approved recon document, founder answers to open questions.
**Outputs:** detailed prompt with numbered steps, exact code, verification grep commands, explicit "DO NOT" constraints.
**Verification:** prompt MUST include strict execution patterns (§4) for any file edits.

### 2.4 Implementation (agent execution)

**Purpose:** agent receives impl prompt, executes in sandbox, opens PR.
**Founder review:** every PR goes through explicit blocking vs non-blocking categorization. All issues including non-blockers are fixed before merging. Bot reviewer findings are treated as blocking. Clean merges over speed.

### 2.5 Fix rounds

**Purpose:** when implementation review finds issues, generate targeted fix prompt.
**Cycle:** Claude reads diff → diagnoses regressions → generates targeted fix prompt → agent implements → repeat until merge-ready.
**Round limit:** see §5.4 diagnostic-first rule — 2 rounds of speculation maximum, round 3+ is diagnostic-only.

## 3. Summary Report formats

### 3.1 Pre-recon / impl / fix prompts — concise dashboard

15–30 lines. Counts and gate outcomes:

```
GIT REMOTE: <empty/url>
DOC PATH: <path>
SECTIONS COMPLETED: yes/no per section
COUNTS: <metric>: <N>
OPEN QUESTIONS: <N>
VERIFICATION GATES PASSED: yes/no per gate
VERDICT: COMPLETE | INCOMPLETE (reason)
```

### 3.2 Recon prompts — EXTENDED format

Recon is the founder-approval gate. Concise dashboard is insufficient. EXTENDED format required:
- Full ARB key map table with EN+RU inline (if i18n is in scope)
- Complete text of every ambiguity / founder question (NOT "5 questions raised — see doc")
- Full glossary proposals
- Full DEBT entry draft (severity, category, source, resolution path, target)

The Summary IS the founder review surface for recon. Founder reads chat output to approve before reading the doc.

### 3.3 Recap formats are NOT optional

Every prompt outputs a Summary Report. The report is the contract: founder reads Summary first, then opens doc only if Summary surfaces concerns. A prompt without a Summary Report is incomplete.

## 4. Strict execution patterns

### 4.1 Hallucinated agent execution

**Source:** DEBT-021 FR4, Slice 3.8 FR5/FR6.

Agents can produce detailed Summary Reports with line numbers and "✅ applied" markers, while files are unchanged. Memory item: "FR7 strict-execution template worked after 2 hallucinated rounds."

### 4.2 Required verification gates for file-editing prompts

Any prompt editing existing files MUST include:

1. **md5sum baseline + post-edit comparison.** Before edit:
   ```bash
   md5sum <file>
   ```
   After edit:
   ```bash
   md5sum <file>  # must differ from baseline
   ```

2. **Verbatim `git diff <file>` paste in Summary** after every edit, not summarized.

3. **Honest STOP if gate fails.** Failure protocol: agent must STOP and report which gate failed, not improvise. No "I tried X and it didn't work, so I tried Y."

4. **Forbidden-pattern grep at end.** After all edits, grep for patterns that should NOT exist post-edit (e.g. old function names if renamed). Empty grep result = success.

### 4.3 Verification commands MUST be runnable

Prompts include exact bash/grep/python commands the agent can run to verify each step. Not pseudocode; not "check that X is true."

### 4.4 Workspace cleanliness gate phrasing

**Source:** memory item #17.

Workspace cleanliness gate must be phrased to avoid false-fail when output goes to `/mnt/user-data/outputs/`:

- If writing inside repo: `git status --short` may show only the new doc as untracked
- If writing to `/mnt/user-data/outputs/`: `git status --short` must be empty (no edits to existing files)
- `git diff --name-only` must be empty in both cases (no modifications to existing files)

DO NOT use phrasing that conflates these two cases.

## 5. Operational lessons

### 5.1 Sandbox-aware pre-flight

**Source:** memory item #14.

Agent sandboxes often have empty `git remote -v`. Push fails fatally in those sandboxes. Other sessions on same agent platform may have working remotes — assume nothing.

Required pre-flight:
1. Run `git remote -v` first
2. Empty → sandbox mode: write to `/mnt/user-data/outputs/`, hand off via `cat` in chat
3. Non-empty → with-remote mode: write to repo path, agent commits to planning branch (does NOT push if planning artifact)

DO NOT treat `git pull --ff-only` failure as repo-state issue when it's actually missing remote.

Workspace-clean gate (blocks) and remote-availability gate (informational) are separate gates.

### 5.2 Push authorization

- **Planning artifacts (pre-recon, recon docs, inventory MD):** founder commits, agent does NOT push. Agent writes file, founder reviews, founder commits.
- **Code PRs:** agent opens PR. First push by founder for new branch (`git push -u origin <branch>`). Subsequent rounds: if auto-fix mode is enabled, agent pushes; if not, founder pushes per round.
- **Auto-fix mode:** founder enables explicitly per task. Agent push allowed for fix rounds 2+ only after authorization. Summary Reports must explicitly state "founder authorized push for auto-fix mode round N" when agent pushes.

### 5.3 Duplicate PR anti-pattern

**Source:** memory item #2.

Agents dispatched in parallel (Jules + Cursor, or retry after timeout) can both complete the same task → duplicate PRs with merge conflicts on second.

Defense:
- Always check `gh pr list` or PRs tab before dispatching retry
- After first agent timeout, verify on-disk state (`git status`, branch list) before re-dispatching
- Close superseded PR without merge — never attempt rebase of stale baseline against current HEAD

### 5.4 Diagnostic-first rule

**Source:** Phase 1.5 frontend rounds 1-7. See TEST_INFRASTRUCTURE.md §5.2.

When 2 fix rounds fail to converge on the same symptom, STOP guessing. Round 3+ MUST be diagnostic-only (instrumentation), not another structural change.

Phase 1.5 frontend wasted rounds 1-3 on speculation; round 4 instrumentation localized exact deadlock line in one CI run; rounds 5-7 each closed exactly one diagnosed issue.

**Rule for Claude generating fix prompts:** by round 3, if root cause is not localized, the fix prompt MUST be diagnostic-only commit. NO structural changes alongside breadcrumb adds.

### 5.5 Test fixture audit on every main.py change

**Source:** DEBT-030 PR1, see TEST_INFRASTRUCTURE.md §2.4.

When `main.py` adds a new handler, middleware, or dependency override, audit all test fixtures that build app independently. Same wiring required, or tests diverge from prod silently.

Impl prompts that touch `main.py` MUST include this audit as a step.

### 5.6 Re-verify DEBT.md state at sprint planning

**Source:** memory item #22 (recent_updates).

Memory and handoff documents drift from DEBT.md. Always grep DEBT.md fresh before writing impl/fix prompts that reference DEBT-NNN:

```bash
rg -n DEBT-NNN DEBT.md
```

Confirm Active vs Resolved. Stale entries (still Active in handoff but Resolved in DEBT.md) waste a fix-prompt cycle.

### 5.7 Branch naming and PR status verification

**Source:** memory item.

- Codex auto-generates PR branches as `codex/<task-slug>`, NOT `claude/<task-slug>`
- After merge, PR branches are deleted from origin → grep for branch name returns empty BUT PR exists
- Always check `git log -10 main` (recent merges) BEFORE assuming PR is open
- Project default branch is `main` (verified 2026-04-26 via git log: merges go to main, origin/HEAD → origin/main)

### 5.8 Recon for HTTP→state→UI work must require integration test design

**Source:** memory items #5 + #21.

Recon for DEBT work touching HTTP→state→UI pipelines MUST explicitly require integration test design (mock fetch, not mock module), not just unit + consumer-mock.

Memory rule states this; recon prompts often defer to impl phase, where it gets simplified to consumer-mock-only. Future recon prompts: include section requiring real-wire test design with one scenario sufficient to prove pipeline integrity.

### 5.9 Sandbox vs CI as source of test truth

**Source:** memory item.

Sandbox tests may fail due to missing pytest plugins (`pytest-asyncio`, etc.), not code bugs. When all tests error with same root cause, suspect environment before code.

Validate via:
```bash
python -c "from X import Y"  # import smoke
pytest --collect-only         # collection check
```

If both succeed, code is structurally sound — push to CI for real validation. **CI is source of test truth.**

## 6. Prompt generation conventions

### 6.1 Mandatory elements in every prompt

- Operator context section (sandbox check, output path rules)
- Numbered steps
- Exact code (not pseudocode for the parts that go in the file)
- Verification grep / bash commands that the agent will run
- Explicit "DO NOT" constraints
- Summary Report specification at end
- Forbidden patterns section (what the agent must NOT do)

### 6.2 File location conventions

- **Drafts (in chat / sandbox):** `/mnt/user-data/outputs/<filename>.md`
- **Pre-recon, recon docs in repo:** `docs/recon/<phase>-<purpose>.md`
- **Discovery docs in repo:** `docs/discovery/<phase>-<part>.md`
- **Architecture MD (cross-cutting):** `docs/architecture/<NAME>.md`
- **Impl prompt drafts:** `/mnt/user-data/outputs/<phase>-impl.md` (transient, deleted after merge)

### 6.3 Read-existing-files rule

Agents MUST read existing files before writing/editing. Specifically:
- Implementation prompts on existing modules: `view` the file first
- Editing markdown: `view` first, str_replace second
- Updating tests: read existing test file structure before adding new test

### 6.4 Markdown updates in same commit

Every PR updates relevant `.md` files in the same commit. The architecture MD network has explicit maintenance rules per file.

### 6.5 No commits, no pushes by agent for planning artifacts

Founder commits planning artifacts. Agent writes file, returns Summary, founder reviews + commits.

For code PRs in auto-fix mode: agent pushes commits per round, but founder must have explicitly authorized auto-fix mode for the task.

### 6.6 Prompt size and streaming

If a prompt approaches 5KB+ and the streaming layer (web client) shows timeouts, split the prompt into 2+ sequential parts. Each part read prior parts' outputs and continues. Part dependency makes serial execution unavoidable in this case.

## 7. Maintenance log

| Date | PR / Phase | Sections touched | Notes |
|---|---|---|---|
| 2026-04-26 | initial | all | Created from aggregated memory items (Phase 1.1, 1.4, 1.5, DEBT-021, DEBT-030, Slice 3.8) |
