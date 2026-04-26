# DEBT-033 Recon — Inventory of `temp/*` writers and cleanup scope

## 1) Summary
This recon found exactly one production code path in `backend/src/` that writes S3 objects under a `temp/*` prefix: `generate_from_data` in `admin_graphics.py`, which writes to `temp/uploads/{uuid}.parquet`. The current cleanup config is intentionally scoped to `temp/uploads/`, and the payload inspector currently includes exactly one extractor for `graphics_generate.data_key`. `temp_cleanup.py` pre-collects referenced keys via `collect_all_referenced_temp_keys` before listing/deleting, and pending protection is applied for `QUEUED` and `RUNNING` (plus optional `RETRYING` if present). No additional `temp/*` writer prefixes were found in non-test backend Python code, so there is no evidence-backed prefix extension ready beyond the current default. Proposed implementation is staged and focused on hardening coverage/detection rules before any broadening attempt.

## 2) Current state

### 2.1 Cleanup config
`backend/src/core/config.py` currently defines:
- `temp_upload_ttl_hours` default `24`.
- `temp_cleanup_max_delete_keys_per_cycle` default `1000`.
- `temp_cleanup_max_list_keys_per_cycle` default `50000`.
- `temp_cleanup_prefixes` default factory: `["temp/uploads/"]`.

### 2.2 `temp_payload_inspector.py` coverage
Current extractors in `backend/src/services/storage/temp_payload_inspector.py`:
- `extract_graphics_generate_data_key(payload)`
  - Returns `payload["data_key"]` when payload can be coerced to a mapping and `data_key` is a non-empty string.
  - Returns one key only (single string), no multi-key extraction.

Observed TODO/BACKLOG comments in this file: none.

### 2.3 Cleanup pre-listing collector
`backend/src/services/storage/temp_cleanup.py` defines both:
- `collect_keys_referenced_by_pending_jobs(session, *, candidates)` (candidate-intersection variant)
- `collect_all_referenced_temp_keys(session)` (full pre-listing reference set)

Pre-listing collection used in cleanup flow is `collect_all_referenced_temp_keys`, called before listing loop in `cleanup_temp_uploads`.

## 3) Writer inventory

### 3.1 `temp/*` candidate grep output classification
Matches in non-test backend Python code were:
1. `backend/src/api/routers/admin_graphics.py:269` → **Writer** (actual S3 write key assignment used in `upload_bytes`).
2. `backend/src/core/config.py:116` → **Config/constant only** (cleanup prefix default declaration, not a writer).

### 3.2 Writer table

| Writer File:Line | Function | Job Type | Prefix | Naming | Consumer | Safe-to-delete signal |
|---|---|---|---|---|---|---|
| `backend/src/api/routers/admin_graphics.py:269` | `generate_from_data` | `graphics_generate` (enqueued in same function) | `temp/uploads/` | `uuid.uuid4().hex + ".parquet"` | `handle_graphics_generate` → `GraphicPipeline.generate(...data_key...)` → `_load_data` downloads same key | Safe after terminal job state (`SUCCESS`/`FAILED`/`CANCELLED`) and TTL cutoff; pending (`QUEUED`/`RUNNING` + optional `RETRYING`) is explicitly protected by cleanup reference scan |

## 4) Pending-status audit

### 4.1 Statuses checked by cleanup
`temp_cleanup.py` builds pending statuses as:
- `JobStatus.QUEUED`
- `JobStatus.RUNNING`
- plus `getattr(JobStatus, "RETRYING", None)` if enum member exists.

### 4.2 Full `JobStatus` enum
`backend/src/models/job.py` defines:
- `QUEUED`
- `RUNNING`
- `SUCCESS`
- `FAILED`
- `CANCELLED`

Non-terminal statuses in this enum are `QUEUED` and `RUNNING`, both covered directly. `RETRYING` is not currently defined in this repository enum, so no uncovered non-terminal status was found in current code state.

## 5) Storage cost analysis
S3 cost metrics are unavailable from this environment for two reasons in recon run:
1. Prompt placeholder bucket command `s3://<bucket>/...` is not executable as-is (shell interprets `<bucket>`).
2. No verified staging/prod bucket + credentials were provided in-task.

Given no accessible bucket telemetry, this recon cannot produce measured object-count/bytes growth for `temp/*`. Current driver classification: **unknown (likely hygiene-driven until metrics are collected)**.

## 6) Proposed scope

### Tier 1 — ready now
- `temp/uploads/` (already included)
  - Extractor exists: `extract_graphics_generate_data_key`.
  - Consumer and lifecycle are clear.

### Tier 2 — needs new extractor first
- None identified from evidence in `backend/src/` non-test Python grep for `"temp/` or `'temp/`.

### Tier 3 — deferred for founder review
- No concrete additional `temp/*` prefixes found in current evidence set.
- Deferred decision: whether to intentionally broaden discovery to non-Python assets/services (other repos, workers, scripts, infra) before declaring DEBT-033 complete.

### Proposed `temp_cleanup_prefixes` default
Keep unchanged until new verified writers exist:

```python
["temp/uploads/"]
```

### Extractor additions required before expansion
None currently required for in-repo discovered writers.

### Integration test expansion plan (`test_temp_cleanup_integration.py`)
- If/when a new prefix is discovered, add variant objects under new prefix and add pending-job payload fixture for corresponding job type extractor.
- Add cross-prefix cap behavior tests validating oldest-first selection remains global across all configured prefixes.

### `max_keys` cap considerations
Current global caps (`max_delete_keys`, `max_list_keys`) are acceptable for single prefix (`temp/uploads/`). If multi-prefix expansion is later approved, evaluate per-prefix fairness/starvation and optionally introduce per-prefix list caps.

## 7) Founder questions
### Q1
Should DEBT-033 include a broader discovery sweep outside `backend/src/**/*.py` (e.g., scripts, infra repos, other services) before concluding no additional `temp/*` prefixes exist?

Context: This recon followed the requested grep scope and found one writer only; other components may still write `temp/*` without appearing in this tree.

Options:
- A) Keep scope strictly this backend repo and proceed with no prefix extension.
- B) Expand recon scope across adjacent services/repos and infra definitions first.

Recommendation: B) if DEBT-033 goal is organization-wide `temp/*` cleanup confidence; A) if goal is backend-local only.

### Q2
Should we formalize pending-status selection by explicit helper or keep optional `getattr(JobStatus, "RETRYING", None)` behavior?

Context: Current code is safe for existing enum, but silently changes behavior if `RETRYING` is introduced later.

Options:
- A) Keep current getattr fallback for forward-compat.
- B) Replace with centralized status policy + explicit test that fails when enum adds non-terminal statuses.

Recommendation: B) for stronger change detection and to prevent silent policy drift.

### Q3
Should we collect real storage telemetry before implementing any DEBT-033 scope extension?

Context: No measurable S3 cost data was accessible in this run.

Options:
- A) Proceed as hygiene work without telemetry.
- B) Gate expansion on measured object count/bytes + growth rate.

Recommendation: B) if prioritization is cost-based; A) if risk-reduction of stale temp artifacts is the primary driver.

## 8) Implementation plan
Recommended staged plan:

### PR1 (policy hardening, no prefix expansion)
- Add pending-status policy test to detect new non-terminal enum values lacking cleanup protection.
- Add/strengthen assertions around `collect_all_referenced_temp_keys` semantics.

### PR2 (optional, only if new writers found)
- Add extractor(s) in `temp_payload_inspector.py` for each verified new job payload shape.
- Add integration variants in `test_temp_cleanup_integration.py` per new prefix/job type.

### PR3 (optional, after PR2)
- Expand `temp_cleanup_prefixes` default to include only prefixes with extractor + verified lifecycle.

## 9) `DEBT.md` update draft
Proposed draft text once implementation begins:

> DEBT-033 — Expand temp cleanup scope beyond temp/uploads/
>
> Recon completed: backend codebase currently verifies one active `temp/*` writer (`graphics_generate` upload path) under `temp/uploads/`, already covered by cleanup + payload extractor. No additional backend Python writers were found. Before any prefix expansion, enforce explicit pending-status policy tests and (if broader org scope is desired) complete cross-service writer inventory. Prefix expansion remains gated on extractor coverage and lifecycle proof per prefix.
