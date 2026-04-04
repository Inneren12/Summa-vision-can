# Agent Workflow Guide

This guide describes the mandatory step-by-step process for implementing any PR in the Summa Vision project.

## Pre-Implementation Phase

### Step 1: Read the Task File
```bash
# Read task JSON for the assigned PR
cat specs/tasks/task-SN-PRX.json
```

Understand:
- `depends_on` — Are all prerequisite PRs merged?
- `touches.include` — What files am I ALLOWED to edit?
- `touches.exclude` — What files am I FORBIDDEN from editing?
- `ac_id` — Which AC block to validate against?
- `branch` — What git branch to create?

### Step 2: Resolve Scope

```powershell
# PowerShell (Windows)
powershell -ExecutionPolicy Bypass -File .ai/tools/resolve_scope.ps1 specs/tasks/task-SN-PRX.json
```

```bash
# Bash (Linux/Mac)
.ai/tools/resolve_scope.sh specs/tasks/task-SN-PRX.json
```

This outputs:
- **Allowed Scope** — Only these files may be modified
- **Excluded** — These files must NOT be touched
- **Dependencies** — Other tasks that must be complete first

### Step 3: Extract and Validate AC Block

```powershell
# PowerShell (Windows)
powershell -ExecutionPolicy Bypass -File .ai/tools/get_ac_content.ps1 SN-PRX-AC1 specs/tasks/task-SN-PRX.json
```

```bash
# Bash (Linux/Mac)
.ai/tools/get_ac_content.sh SN-PRX-AC1 specs/tasks/task-SN-PRX.json
```

- If `STALE_CONTEXT` error → **STOP immediately**. The spec has changed since the task was created. Alert the human.
- If successful → proceed with the returned AC content.

### Step 4: Status Check → STOP

Output a summary:
1. Task ID and title
2. AC criteria (bulleted list)
3. Files in scope
4. Architecture rules that apply
5. Dependencies status

**Then STOP processing. Wait for the human to say "PROCEED".**

## Implementation Phase

### Step 5: Load Context
Read:
- `specs/arch/domain_core.json` — Architecture rules
- `specs/glossary/{scopes}.json` — Domain terms
- `docs/modules/<module>.md` — Existing code context

### Step 6: Implement
- Write production code matching ALL AC checkboxes
- Write tests achieving >90% coverage
- Follow architecture rules strictly (ARCH-PURA-001, ARCH-DPEN-001)
- Stay within `touches.include` scope

### Step 7: Update Documentation
In the SAME commit:
- Update `docs/modules/<module>.md` with new classes/methods
- Update `docs/SPRINT_STATUS.md` (PR → 🔄)
- Update any other relevant docs (ARCHITECTURE.md, TESTING.md)

### Step 8: Final Report
Output:
1. Files created/modified (list)
2. AC checklist with ✅/❌ for each criterion
3. Test results summary
4. Coverage percentage
5. Any deviations or notes

**Do NOT commit. Do NOT push.** The human handles git operations.

## Error Handling

| Error | Action |
|-------|--------|
| `STALE_CONTEXT` from hash validation | STOP. Alert human. Spec has drifted. |
| File outside `touches.include` | STOP. Do not edit. Report scope violation. |
| Dependency not met (`depends_on`) | STOP. Report which prerequisite is missing. |
| Architecture rule violation | Fix the code. Never ship violations. |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
