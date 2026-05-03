# Phase 3.1c — Impl prompt ADDENDUM (missing observation contract)

**Apply this addendum on top of `phase-3-1c-impl-prompt.md`.** Do NOT replace the impl prompt — append/modify the specific items below. The impl prompt remains the master spec; this addendum closes the `value` nullability gap that the recon FIX-2 commit added.

**Trigger:** before dispatching the impl agent, ensure the recon doc on the branch contains the FIX-2 changes (DTO `value: str | None` + `missing: bool` + map_to_resolved null-handling invariants). If FIX-2 not yet merged into recon, do not dispatch impl.

---

## ADDITIONS to STRICT EXECUTION RULES — forbidden patterns

Append two patterns to the existing F1-F10 forbidden-grep block:

```bash
# F11. value field MUST be nullable in DTO (str | None, not bare str)
rg -n "value:\s*str\s*=\s*Field" backend/src/schemas/resolve.py
# Expected: empty (must be `value: str | None = Field(...)`)

# F12. NEVER stringify None to literal "None" — defensive
rg -n "str\(.*row\.value.*\)|str\(.*\.value.*\)" backend/src/services/resolve
# Expected: any hit must be inside an `if ... is not None` branch.
# Flag for manual inspection — agent verifies each hit context.
```

F12 is "soft" — it can have legitimate hits inside guarded branches. Agent must paste each hit and confirm it's inside a `is not None` check.

---

## REPLACEMENT — Phase 6 schema content

Phase 6 in original impl prompt says: "ResolvedValueResponse per recon §2.4 verbatim." The recon §2.4 has changed via FIX-2. Re-state the schema explicitly here so impl agent has zero ambiguity:

```python
# backend/src/schemas/resolve.py

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResolvedValueResponse(BaseModel):
    cube_id: str = Field(description="Cube identifier.")
    semantic_key: str = Field(description="Semantic mapping key.")
    coord: str = Field(description="Service-derived StatCan coordinate string echoed from cache row.")
    period: str = Field(description="Resolved period token (ref_period).")
    value: str | None = Field(
        default=None,
        description="Canonical stringified numeric value. None when the observation is suppressed/missing upstream (paired with missing=True).",
    )
    missing: bool = Field(
        description="Raw passthrough from cache row. True when the upstream observation is absent/suppressed; in that case value is None.",
    )
    resolved_at: datetime = Field(description="Alias of cache row fetched_at timestamp.")
    source_hash: str = Field(description="Opaque cache provenance hash.")
    is_stale: bool = Field(description="Persisted stale marker from cache row.")
    units: str | None = Field(default=None, description="Unit from mapping.config.unit if string, else null.")
    cache_status: Literal["hit", "primed"] = Field(description="Resolve status.")
    mapping_version: int | None = Field(default=None, description="Optional semantic mapping version.")
```

11 fields. NO `populate_by_name`, NO `prime_warning`. `value` IS nullable; `missing` IS new and required.

---

## REPLACEMENT — Phase 5 `map_to_resolved` semantics

Phase 5 (resolve service) original prompt has a bullet for `map_to_resolved` saying "small private helper that builds ResolvedValueResponse from a cache row + mapping. units derived from mapping.config..." — EXTEND with these mandatory rules:

> `map_to_resolved(row, mapping, *, cache_status)` body MUST handle nullable `row.value`:
>
> ```python
> def map_to_resolved(
>     row: ValueCacheRow,
>     mapping: SemanticMapping,
>     *,
>     cache_status: Literal["hit", "primed"],
> ) -> ResolvedValueResponse:
>     # Critical: never str(None) → "None"
>     value_str: str | None
>     if row.value is None:
>         value_str = None
>     else:
>         value_str = canonical_str(row.value)  # whatever the project's numeric→str helper is, or repr/format
>
>     unit_raw = mapping.config.get("unit") if isinstance(mapping.config, dict) else None
>     units = unit_raw if isinstance(unit_raw, str) else None
>
>     return ResolvedValueResponse(
>         cube_id=row.cube_id,
>         semantic_key=row.semantic_key,
>         coord=row.coord,
>         period=row.ref_period,
>         value=value_str,
>         missing=row.missing,            # raw passthrough
>         resolved_at=row.fetched_at,     # L2 alias
>         source_hash=row.source_hash,
>         is_stale=row.is_stale,
>         units=units,
>         cache_status=cache_status,
>         mapping_version=mapping.version if hasattr(mapping, "version") else None,
>     )
> ```
>
> Invariants:
> - `row.value is None` → DTO `value=None`, NEVER the string `"None"`.
> - `row.missing` is raw-passed regardless of `value`. (Defensive: `value=None` should always pair with `missing=True` per cache schema, but pass through whatever the row says.)
> - `canonical_str(...)` choice: if no project helper exists, use a deterministic format (e.g. `format(Decimal(str(row.value)), 'f')` or `f"{row.value}"` — pick what matches existing serialization patterns in `value_cache_schemas.py` or wherever cache values are stringified today). Document the choice in code comment. If unclear, surface in chat.

---

## ADDITIONS — Phase 1 test scaffolding

Three new test cases, one per layer, per recon FIX-2 §6 additions. Add these to the corresponding test files:

**Phase 1.1 (integration test file):** add `test_resolve_missing_observation_round_trip`:
- Seed mapping (active) + seed `semantic_value_cache` row with `value=None, missing=True, source_hash=<any>, fetched_at=<now>, is_stale=False`.
- GET resolve endpoint with appropriate dim/member.
- Assert HTTP 200, response JSON has `"value": null, "missing": true, "cache_status": "hit"`.
- Assert response JSON does NOT contain literal string `"None"` anywhere — `assert '"None"' not in response.text`.

**Phase 1.2 (service test file):** add `test_resolve_hit_returns_missing_observation_faithfully`:
- Mock repo to return active mapping. Mock `value_cache_service.get_cached` to return `[ValueCacheRow(value=None, missing=True, ...)]`.
- Call `service.resolve_value(...)`.
- Assert returned DTO has `value is None`, `missing is True`, `cache_status == "hit"`.
- Assert `auto_prime` was NOT called (cache hit path).

**Phase 1.3 (unit test file):** add `test_map_to_resolved_missing_observation`:
- Build `ValueCacheRow` fixture with `value=None, missing=True`.
- Call `map_to_resolved(row, mapping_fixture, cache_status="hit")`.
- Assert DTO `value is None` (not `"None"` string), `missing is True`.
- Defensive variant: `value=None, missing=False` (shouldn't happen in real cache but test the function honors row state) → DTO `value=None, missing=False`. Confirms map function doesn't fabricate `missing=True` from `value=None` — passes both fields through truthfully.

---

## ADDITIONS — final verification gates

Append to the existing test gates section:

```bash
# Missing observation contract
grep -c "value: str | None\|value: str \| None" backend/src/schemas/resolve.py
# Expected: 1

grep -c "^    missing: bool" backend/src/schemas/resolve.py
# Expected: 1

grep -c "row.value is None\|if row\.value is None" backend/src/services/resolve/service.py
# Expected: ≥1 (the explicit None-check before stringify)

cd backend && pytest tests/services/resolve/ tests/integration/test_admin_resolve.py -v -k "missing" 2>&1 | tail -10
# Expected: 3 tests pass (one per layer)

# Final defensive: response JSON never contains "None" literal for missing values
cd backend && pytest tests/integration/test_admin_resolve.py::test_resolve_missing_observation_round_trip -v 2>&1 | tail -10
# Expected: pass; assertion that '"None"' not in response.text holds
```

---

## Summary Report — additional checklist

Add to the "Locked-rule respect" section of the impl Summary Report:

```
  F-fix-3 missing observation contract:  YES
    value: str | None in DTO:            YES
    missing: bool in DTO:                YES
    map_to_resolved None-safe:           YES
    3 missing-observation tests pass:    YES
    F11/F12 forbidden greps clean:       YES
```

---

## DO NOT (additions)

- DO NOT skip the `is None` guard in `map_to_resolved`. Stringifying None → "None" silently corrupts every suppressed-observation response.
- DO NOT pair `missing=True` with `value=<something>` or `missing=False` with `value=None` programmatically — pass row fields through faithfully even if they look inconsistent (defensive: data contract says they MUST agree, but the resolve layer doesn't enforce; cache writer is the contract owner).
- DO NOT skip the integration test assertion that response text contains no `"None"` literal. That assertion is the regression shield against future re-introduction of the bug.
