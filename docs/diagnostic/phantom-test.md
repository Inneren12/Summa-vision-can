# Diagnostic — Phantom Test File `data_preview_diff_pipeline_test.dart`

**Run date:** 2026-04-26
**Branch:** `claude/diagnose-test-timeout-Xbqiv`
**Mode:** READ-ONLY diagnostic (no fixes, no commits, no push)
**Reported symptom:** CI reports a 10-minute `TimeoutException` for
`frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart` —
test case `"first view no baseline, refresh shows 1 change and highlight"`.

---

## Section 1 — Disk verification

### 1.1 `git ls-files | grep -i 'data_preview_diff_pipeline'`
```
NO_MATCHES_IN_LS_FILES
```

### 1.2 `find . -type f -name '*data_preview_diff_pipeline*' 2>/dev/null`
```
(no output)
```

### 1.3 `find . -type d -name '.dart_tool' -prune -o -type f -name '*pipeline*test*' -print | head -50`
```
./frontend-public/tests/components/editor/cropZone-pipeline.test.tsx
```
(unrelated TypeScript test in `frontend-public/`, not Flutter)

### 1.4 Frontend test directory inspection
```
frontend/test/features/data_preview/
├── domain/
│   └── data_preview_models_test.dart
└── presentation/
    └── data_preview_screen_test.dart
```
No file at `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart`.
No `.dart_tool/` directory present in `frontend/` (no Flutter build state cached locally).

### Verdict
**`FILE_ABSENT_ON_DISK`**

---

## Section 2 — Reference scan results

### 2.1 `git grep -ni 'data_preview_diff_pipeline'`
```
docs/recon/phase-1-5-frontend-recon.md:396:Add `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart` with single E2E scenario:
docs/recon/phase-1-5-frontend-recon.md:457:   - `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart`
```
**Only matches are inside the recon spec doc — not in any code/test/CI file.**

### 2.2 `git grep -ni 'diff_pipeline_test'`
```
docs/recon/phase-1-5-frontend-recon.md:396:Add `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart` with single E2E scenario:
docs/recon/phase-1-5-frontend-recon.md:457:   - `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart`
```

### 2.3 `git grep -ni 'first view no baseline'`  ← test name fingerprint (PRIMARY)
```
NO_MATCHES_TEST_NAME
```

### 2.4 `git grep -ni 'refresh shows 1 change and highlight'`  ← full test case fingerprint
```
NO_MATCHES_TEST_CASENAME
```

### Critical fingerprint result
The test case name string `first view no baseline, refresh shows 1 change and highlight`
**does NOT appear ANYWHERE in tracked content**. The path string itself appears only
in a planning document (recon spec); no `group()` / `testWidgets()` / `test(` declaration
anywhere in the tree references this name.

---

## Section 3 — CI configuration findings

### 3.1 Workflow files
```
.github/workflows/backend.yml
.github/workflows/frontend-admin.yml
.github/workflows/frontend-public.yml
.github/workflows/smoke-test.yml
```

### 3.2 Flutter test invocations (relevant workflow only)
**`.github/workflows/frontend-admin.yml`** — the only workflow that runs Flutter:
```yaml
defaults:
  run:
    working-directory: frontend

steps:
  - name: Checkout repository
    uses: actions/checkout@v4

  - name: Set up Flutter
    uses: subosito/flutter-action@v2
    with:
      channel: stable
      cache: true

  - name: Install dependencies
    run: flutter pub get

  - name: Run tests
    run: flutter test
```

- **No per-file test list, no `--name`/`--plain-name`/`--tags`, no manifest.**
- `flutter test` performs **auto-discovery** of every `*_test.dart` under `test/`.
- For CI to report a failure on `data_preview_diff_pipeline_test.dart`, that file
  **must have been physically present in the checkout at the moment `flutter test` ran**.

### 3.3 Cache strategy
```
.github/workflows/frontend-admin.yml:          cache: true       # Flutter SDK only (subosito/flutter-action)
.github/workflows/frontend-public.yml:          cache: "npm"     # node_modules (other project)
.github/workflows/backend.yml:                  cache: "pip"     # backend (unrelated)
.github/workflows/backend.yml:                  uses: actions/cache@v4   # ~/.cache/pip (unrelated)
```
- The frontend Flutter workflow caches **only the Flutter SDK** via `subosito/flutter-action@v2`.
- `actions/cache@v4` is **NOT used** for Flutter; nothing under `frontend/.dart_tool/`,
  `frontend/build/`, or `frontend/test/` is restored across runs.
- A previously-deleted test file in the checkout cannot resurface from this cache.

### 3.4 Project-local scripts / configs (`.sh` / `.ps1` / Makefile / `dart_test.yaml` / `build.yaml` / `melos.yaml`)
```
NO_SCRIPT_MATCHES
```
No scripts, `dart_test.yaml`, or `build.yaml` reference `data_preview_diff_pipeline` or
`data_preview` for routing. (No `dart_test.yaml` / `build.yaml` / `melos.yaml` exist in
the repo at all.)

### 3.5 `flutter_test_config.dart`
File present at `frontend/test/flutter_test_config.dart`. Inspected — only disables
`GoogleFonts.allowRuntimeFetching`. Does **not** synthesize, generate, or reference any
test path or test name. Cannot be the source of a phantom test name.

---

## Section 4 — Git history finding

### 4.1 `git log --all --full-history -- '**/data_preview_diff_pipeline_test.dart'`
```
(no output)
```

### 4.2 `git log --all -p -S 'first view no baseline, refresh shows 1 change'`
```
(no output)
```

### 4.3 `git log --all -S 'data_preview_diff_pipeline' --oneline`
```
08b0e4a planning(phase-1-5-frontend): recon for Visual Data Diffing
```
That single commit only adds `docs/recon/phase-1-5-frontend-recon.md` — a planning
document. No source/test code adds, references, or implements the file.

### 4.4 Remote-branch scan
```
git for-each-ref refs/remotes/origin → claude/diagnose-test-timeout-Xbqiv, main
```
Both branches scanned via `git ls-tree -r`:
```
(no output — file present in neither tracked tree)
```

### 4.5 Recent merge history (relevance check)
```
6558ff6 Merge PR #167  codex/implement-crop-zone-overlays
ed4664d Merge PR #169  codex/create-frontend-recon-for-visual-data-diffing
6578a90 Merge PR #168  codex/implement-product_id-in-previewresponse
```
**No merged PR titled "implement visual data diffing" exists** in either local or
remote-tracking branches. The Phase 1.5 frontend impl PR (which would have written
the 21 whitelisted files in §F of the recon, including
`data_preview_diff_pipeline_test.dart`) is **not present in this repo's reachable
history**.

### Verdict
**`NEVER_EXISTED_IN_HISTORY`**
- File path never appears in any tracked tree across all branches.
- Test case name never appears in any blob in all-history pickaxe search.
- Path string only ever appeared in the recon planning doc (one commit, `08b0e4a`).

---

## Section 5 — Hypothesis ranking

### H-A — Phantom file in CI cache / build artifact
**`INCONSISTENT_WITH_EVIDENCE`** —
- `frontend-admin.yml` uses only `subosito/flutter-action@v2`'s `cache: true`, which
  caches the Flutter SDK only, not project files (§3.3).
- No `actions/cache@v4` step targets `.dart_tool/`, `build/`, or `test/`.
- No path-resurrection vector exists in the configured pipeline.

### H-B — Implicit reference via test runner conventions
**`INCONSISTENT_WITH_EVIDENCE`** —
- No `dart_test.yaml`, `build.yaml`, or `melos.yaml` exists (§3.4).
- `flutter_test_config.dart` is a 13-line GoogleFonts shim with no path generation
  (§3.5).
- `package_config.json` does not exist locally (no `.dart_tool/`); CI generates a
  fresh one each run via `flutter pub get`, which cannot synthesize a non-existent
  test file.

### H-C — Hallucinated agent execution
**`CONFIRMED`** (with caveat in §5-note) — strongest-supported hypothesis.
Evidence chain:
1. The file is the explicit "B.9.4 Pipeline" deliverable in the Phase 1.5 frontend
   recon (`docs/recon/phase-1-5-frontend-recon.md` lines 396 and 457, §F whitelist).
2. The file has **never been written into git history** anywhere
   (§4.1, §4.2, §4.4).
3. The test case name fingerprint
   `"first view no baseline, refresh shows 1 change and highlight"`
   has **never appeared in any tracked blob** across all-history pickaxe search
   (§2.3, §2.4, §4.2). The only place this string could plausibly originate is a
   prior agent's chat summary or a CI log it transcribed.
4. The recon explicitly says "anything outside list → stop" (§F whitelist), so the
   intended outcome was that the impl PR would write this file. No such impl PR
   has been merged (§4.5).
5. CLAUDE.md `userMemories` references DEBT-021 FR4 / Slice 3.8 FR5/FR6 as a
   recurring "agent reports a file as written that wasn't" failure mode —
   matches the signature here.

**Caveat (§5-note):** This evidence shows the file was *never written*. Whether the
quoted CI failure line was *actually emitted by a real GitHub Actions run* against
this repo cannot be determined from the local checkout — see §6 / §7.

### H-D — Test file lives in another branch
**`INCONSISTENT_WITH_EVIDENCE`** for the branches reachable here. `git ls-tree`
across `origin/main` and `origin/claude/diagnose-test-timeout-Xbqiv` returns no
match (§4.4). Whether an unmerged PR branch carries the file
**`UNDETERMINED_FROM_LOCAL_REPO`** — only the two remote branches above are visible
locally; an open PR branch could exist on GitHub.

### H-E — Generated/dynamic test
**`INCONSISTENT_WITH_EVIDENCE`** —
- No `flutter_driver` / `integration_test` runner is configured (no
  `frontend/integration_test/` directory exists).
- No build_runner step in CI (`flutter test` only).
- No code generator could synthesize a path that fails open as a 10-minute
  hang — that signature is a real Dart isolate `_handleMessage` blocking on
  `await`, which requires actual test code to exist and execute.

### Top hypothesis
**H-C — Hallucinated agent execution.** Evidence chain: §2.3 + §2.4 + §4.1 + §4.2
+ §4.5 (test name never existed; file never existed; impl PR never merged;
deliverable comes only from a planning doc).

---

## Section 6 — Recommended next action

**Primary recommendation: `INVESTIGATE_GH_ACTIONS_LOG`** (decisive disambiguation)
combined with `WRITE_TEST_FROM_SPEC` (substantive fix) once the log is read.

Reasoning:
- The local repo state is *internally consistent and complete*: the file has
  never existed, the test name has never existed, and CI uses pure auto-discovery
  with no caching of project files. There is no local mechanism by which
  `flutter test` on this checkout could fail on that path.
- This makes two scenarios observationally indistinguishable from local data:
  1. **(H-C strict)** The CI failure line was reported to the founder by an
     intermediary (an agent) that hallucinated it. No real Actions run produced
     it. → fix is `NO_ACTION_NEEDED_LOCAL_FIX_AGENT_HALLUCINATION` (correct the
     agent's status report; nothing to change in CI or code).
  2. **(H-C + side branch)** A real Actions run on an *unmerged* impl-PR branch
     wrote the file but with a buggy test that hangs. The branch is not merged
     into main, so the file isn't in the tree we see locally. → fix is to find
     that PR and either fix the test there or close the branch.
- **Action for founder:**
  1. Pull up the failing GitHub Actions run page. Confirm:
     - The branch / commit SHA the run was triggered on.
     - The full `flutter test` invocation in the log (look for
       `Run flutter test` step output and the file list it discovers).
     - Whether the SHA matches a head currently in the local repo. If not, the
       run came from a branch we don't have locally → switch into that branch
       and re-diagnose.
  2. If no real Actions run exists for this failure
     (no run number / no run URL produced the line) → confirmed
     `NO_ACTION_NEEDED_LOCAL_FIX_AGENT_HALLUCINATION`. The fix is upstream of
     code: the Phase 1.5 frontend agent's CI-status report needs to be
     audited / discarded.
  3. If a real Actions run *did* produce the line, the SHA points to where the
     file lives. From there: either restore (`RESTORE_FILE_FROM_HISTORY` of
     that SHA, requires impl PR access) or scope a fresh impl prompt to write
     the file from the recon B.9.4 spec (`WRITE_TEST_FROM_SPEC`).

**Subordinate recommendations** (do NOT take without §7 answers):
- `RESTORE_FILE_FROM_HISTORY`: rejected for now — no SHA to restore from
  (§4.1, §4.4 both empty).
- `CACHE_INVALIDATION_NEEDED`: rejected — the configured cache (`subosito` SDK
  cache only) cannot carry test files across runs (§3.3).
- `WRITE_TEST_FROM_SPEC`: deferrable — the recon B.9.4 (lines 393–399) gives a
  4-step scenario that is sufficient to write the test from scratch, but only
  do this once founder confirms the test is wanted *and* that no impl PR
  already attempted it.

---

## Section 7 — Open questions for founder

1. **Provenance of the failure line.** Is the quoted `TimeoutException` line
   from (a) a clickable GitHub Actions run URL, (b) a previous agent's chat
   summary / status report, or (c) a local `flutter test` you ran? — this
   single answer collapses H-C-strict vs. H-C-side-branch.
2. **Run number / SHA.** If (a): what is the workflow run URL or the commit
   SHA of the failing run? Local SHAs reachable: anything ancestor of `main`
   or `claude/diagnose-test-timeout-Xbqiv` only.
3. **Is there an open impl PR for Phase 1.5 frontend ("Visual Data Diffing")?**
   No merged PR with that title exists (§4.5). If an unmerged PR branch
   exists on GitHub, its SHA may carry the file — local clone has only
   `origin/main` and `origin/claude/diagnose-test-timeout-Xbqiv`.
4. **Is the file's existence still required for Phase 1.5 frontend "done"?**
   The recon §F whitelist lists it as one of 21 expected files; if Phase 1.5
   is being declared done without it, the recon needs an updated note (or the
   test needs to be written).
5. **Authorization to scope a follow-up `WRITE_TEST_FROM_SPEC` prompt** —
   only if §7-q1 establishes that no real failing run exists and the test is
   genuinely wanted.

---

**End of diagnostic.**
