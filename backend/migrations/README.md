# Alembic Migrations

## Baseline

The initial migration (`05de14ff39c6_initial.py`) was created retroactively
after the models stabilized in Phase 1.5. It defines the baseline schema
for leads, publications, and llm_requests tables.

## Setting up a new environment
```bash
# From scratch (empty database):
cd backend
alembic upgrade head

# Existing database without alembic_version table:
# First, stamp to mark the current state, then upgrade:
alembic stamp 05de14ff39c6
alembic upgrade head
```

## Rules

- Every model change requires an Alembic migration in the same PR.
- Always run `alembic upgrade head` before `pytest`.
- Never edit a migration that has been merged to main.
- Use `alembic downgrade -1 && alembic upgrade head` to verify reversibility.
