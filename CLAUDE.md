# Summa Vision

> StatCan & CMHC data ingestion, normalization, and analytics platform.

## Docs Navigation

| Document | Purpose |
|----------|---------|
| [Architecture](docs/ARCHITECTURE.md) | Module graph, dependency flow, build commands |
| [Arch Rules](docs/ARCH_RULES.md) | Hard constraints (ARCH-PURA-001, ARCH-DPEN-001) |
| [Sprint Status](docs/SPRINT_STATUS.md) | PR tracking table with ✅/🔄/⬜ |
| [Testing](docs/TESTING.md) | Test strategy, coverage thresholds, mocking |
| [Module: StatCan](docs/modules/statcan.md) | StatCan ETL pipeline classes & signatures |
| [Module: CMHC](docs/modules/cmhc.md) | CMHC scraping pipeline classes & signatures |
| [Module: Core](docs/modules/core.md) | Shared infra (config, rate limit, storage, scheduler) |
| [Module: API](docs/modules/api.md) | REST endpoints (FastAPI routers) |
| [Agent Workflow](docs/guides/agent-workflow.md) | Step-by-step for AI agent implementation |

## Rules That Always Apply

1. **ARCH-PURA-001**: Data processing must be pure functions — no I/O inside transformers.
2. **ARCH-DPEN-001**: Strict Dependency Injection — classes cannot instantiate their own heavy dependencies.
3. Rely on Pydantic V2 schemas and exact `snake_case` vs `camelCase` field maps via `Field(alias=...)`.
4. Keep HTTP clients asynchronous, using `httpx`.
5. Every PR MUST update relevant docs in `docs/`.
6. Do NOT commit. Do NOT push. Human handles git.

## Spec-Driven Workflow (MANDATORY)

1. Read task file: `specs/tasks/task-SN-PRX.json`
2. Run: `.ai/tools/resolve_scope.ps1 <task_file>` (Windows) or `.ai/tools/resolve_scope.sh <task_file>` (Unix)
3. Run: `.ai/tools/get_ac_content.ps1 <AC_ID> <task_file>` (Windows) or `.ai/tools/get_ac_content.sh <AC_ID> <task_file>` (Unix)
4. Output status check → **STOP** → wait for "PROCEED"
5. Implement → verify → update docs → report

## Quick Commands

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Start dev server
uvicorn src.main:app --reload

# Regenerate AC hashes after editing sprint spec
powershell -ExecutionPolicy Bypass -File .ai/tools/hash_ac_blocks.ps1 -SprintFile specs/sprints/sprint-1.md
```
