# Phase 3.1aaa Recon — `semantic_value_cache` infrastructure

**Branch:** `claude/phase-3-1aaa-recon`  
**Mode:** Reconnaissance (design-spec only; no implementation code changes).  
**Generated:** 2026-05-03 (UTC).

> This document intentionally mirrors the 3.1b recon structure and expands pre-recon findings into implementation-ready contracts.

## Evidence commands

> Note: command outputs not pasted in this recon. Future revisions or
> audits may re-run these to capture exact verbatim output.

```bash
$ rg -n "scheduled_metadata_cache_refresh|coalesce|max_instances|misfire_grace_time|hour=15" backend/src/core/scheduler.py -S
```

```bash
$ rg -n "ResolvedDimensionFilter|resolved_filters|dimension_position_id|member_id" backend/src/services/semantic_mappings/validation.py -S
```

```bash
$ rg -n "AsyncTokenBucket|rate_limiter|acquire" backend/src/services/statcan/client.py -S
```

---

## §A — StatCan WDS data endpoint contract (deep dive)

### A1 — Endpoint URL and verb
- Confirmed endpoint: `POST https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods`.
- Source: StatCan WDS User Guide (official): https://www.statcan.gc.ca/en/developers/wds/user-guide

### A2 — Request body shape
Canonical request body is an **array** of request objects:
```json
[
  {"productId": 18100004, "coordinate": "1.10.0.0.0.0.0.0.0.0", "latestN": 12}
]
```
Field contract:
- `productId`: integer, StatCan cube product identifier.
- `coordinate`: string, dot-separated member coordinate across fixed 10 positions.
- `latestN`: integer, count of most recent periods requested.

### A3 — Response envelope
Expected top-level response is an array; each entry corresponds to request item position.

```json
[
  {
    "status": "SUCCESS",
    "object": {
      "responseStatusCode": 0,
      "productId": 18100004,
      "coordinate": "1.10.0.0.0.0.0.0.0.0",
      "vectorId": 41690914,
      "vectorDataPoint": [
        {
          "refPer": "2026-04-01",
          "refPer2": "",
          "refPerRaw": "2026-04-01",
          "refPerRaw2": "",
          "value": "165.7",
          "decimals": 1,
          "scalarFactorCode": 0,
          "symbolCode": 0,
          "securityLevelCode": 0,
          "statusCode": 0,
          "frequencyCode": 6,
          "releaseTime": "2026-05-21T08:30:00",
          "missing": false
        }
      ]
    }
  }
]
```
Notes:
- `value` can be string-encoded numeric or null for missing points.
- `releaseTime` is local publication timestamp-like string (timezone not explicit in payload).
- `refPer` may include full date even when conceptual period is month/quarter/year.

### A4 — Failure envelope
For invalid coordinate or item-specific failure:
```json
[{"status": "FAILED", "object": "Invalid coordinate"}]
```
Difference vs metadata endpoint: data endpoint commonly returns status/object per item; metadata cache path currently mostly handles object payload validation and datasource exceptions in service layer.

### A5 — Batch limits
- Official hard limit not explicitly surfaced in currently-crawled public guide text.
- **Recon decision:** Use conservative batch size constant **100** for nightly refresh.
- Add DEBT to validate empirical upper bound in staging/prod observation.

### A6 — Per-item failure semantics in batches
- Public docs do not clearly assert whole-request-fail vs mixed array semantics.
- **Recon decision:** assume mixed per-item status array and code defensively with item-level parse/error handling.
- Carry forward as Q-impl blocker.

### A7 — Pydantic schema contract
```python
class StatCanDataPoint(BaseModel):
    ref_per: str = Field(alias="refPer")
    ref_per2: str = Field(default="", alias="refPer2")
    ref_per_raw: str = Field(alias="refPerRaw")
    ref_per_raw2: str = Field(default="", alias="refPerRaw2")
    value: Decimal | None
    decimals: int
    scalar_factor_code: int = Field(alias="scalarFactorCode")
    symbol_code: int = Field(alias="symbolCode")
    security_level_code: int = Field(alias="securityLevelCode")
    status_code: int = Field(alias="statusCode")
    frequency_code: int = Field(alias="frequencyCode")
    release_time: datetime = Field(alias="releaseTime")
    missing: bool

class StatCanDataResponse(BaseModel):
    response_status_code: int = Field(alias="responseStatusCode")
    product_id: int = Field(alias="productId")
    coordinate: str
    vector_id: int = Field(alias="vectorId")
    vector_data_point: list[StatCanDataPoint] = Field(alias="vectorDataPoint")
```
Naming style intentionally mirrors existing `backend/src/services/statcan/schemas.py` snake_case + aliases convention.

### A8 — Rate limit interaction
- Existing StatCan client already requires an `AsyncTokenBucket` and calls `await self._rate_limiter.acquire()` before outbound request.
- Recon decision: value-cache service shares same client/token bucket behavior; no separate limiter type needed in 3.1aaa.

---

## §B — Coord derivation (algorithm finalization)

### B1 — Function signature
```python
def derive_coord(resolved_filters: list[ResolvedDimensionFilter]) -> str:
    """Convert validator-resolved (position_id, member_id) pairs to StatCan coord.

    Uses 10-position dot-separated format. Unset positions are 0.
    """
```

### B2 — Full body walkthrough
```python
def derive_coord(resolved_filters: list[ResolvedDimensionFilter]) -> str:
    slots = ["0"] * 10
    seen_positions: set[int] = set()

    for item in resolved_filters:
        pos = item.dimension_position_id
        member = item.member_id

        if pos < 1 or pos > 10:
            raise ValueError(f"dimension_position_id out of range: {pos}")
        if pos in seen_positions:
            raise ValueError(f"duplicate dimension_position_id: {pos}")

        seen_positions.add(pos)
        slots[pos - 1] = str(member)

    return ".".join(slots)
```
Defensive policy: duplicate position raises error (not last-write-wins).

### B3 — Test matrix
1. 2D happy path.
2. 5D happy path.
3. Empty filters => all zeros.
4. Gap positions (1 and 3 set) => zero placeholder at 2.
5. Invalid low position.
6. Invalid high position.
7. Duplicate position.

### B4 — Module location
Recon choice: `backend/src/services/semantic/coord.py` (new dedicated pure helper module). Justification: semantic-domain logic using validator output, but not owned by StatCan HTTP client internals.

---

## §C — `semantic_value_cache` schema (final)

### C1 — Migration SQL (alembic-ready draft)
```sql
CREATE OR REPLACE FUNCTION parse_ref_period_to_date(period TEXT)
RETURNS DATE AS $$
DECLARE
  y INT;
  m INT;
  q INT;
BEGIN
  IF period ~ '^\d{4}-\d{2}-\d{2}$' THEN
    RETURN period::date;
  ELSIF period ~ '^\d{4}-\d{2}$' THEN
    y := substring(period from 1 for 4)::int;
    m := substring(period from 6 for 2)::int;
    RETURN make_date(y, m, 1);
  ELSIF period ~ '^\d{4}-Q[1-4]$' THEN
    y := substring(period from 1 for 4)::int;
    q := substring(period from 7 for 1)::int;
    RETURN make_date(y, ((q - 1) * 3) + 1, 1);
  ELSIF period ~ '^\d{4}$' THEN
    y := period::int;
    RETURN make_date(y, 1, 1);
  ELSE
    RAISE EXCEPTION 'Unsupported ref_period format: %', period;
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE TABLE semantic_value_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cube_id VARCHAR(50) NOT NULL,
    product_id BIGINT NOT NULL,
    semantic_key VARCHAR(100) NOT NULL,
    coord VARCHAR(50) NOT NULL,
    ref_period VARCHAR(20) NOT NULL,
    period_start DATE GENERATED ALWAYS AS (parse_ref_period_to_date(ref_period)) STORED,
    value NUMERIC(18, 6),
    missing BOOLEAN NOT NULL DEFAULT FALSE,
    decimals INTEGER NOT NULL DEFAULT 0,
    scalar_factor_code INTEGER NOT NULL DEFAULT 0,
    symbol_code INTEGER NOT NULL DEFAULT 0,
    security_level_code INTEGER NOT NULL DEFAULT 0,
    status_code INTEGER NOT NULL DEFAULT 0,
    frequency_code INTEGER,
    vector_id BIGINT,
    response_status_code INTEGER,
    source_hash VARCHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    release_time TIMESTAMPTZ,
    is_stale BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_semantic_value_cache_mapping
      FOREIGN KEY (cube_id, semantic_key)
      REFERENCES semantic_mappings (cube_id, semantic_key)
      ON DELETE CASCADE,
    CONSTRAINT uq_semantic_value_cache_lookup
      UNIQUE (cube_id, semantic_key, coord, ref_period)
);
CREATE INDEX ix_semantic_value_cache_product_id
  ON semantic_value_cache (product_id);
CREATE INDEX ix_semantic_value_cache_coord
  ON semantic_value_cache (cube_id, semantic_key, coord);
CREATE INDEX ix_semantic_value_cache_fetched_at
  ON semantic_value_cache (fetched_at);
CREATE INDEX ix_semantic_value_cache_period_start
  ON semantic_value_cache (period_start);
CREATE INDEX ix_semantic_value_cache_is_stale
  ON semantic_value_cache (is_stale) WHERE is_stale = true;
```

### C2 — `period_start` GENERATED decision
Adopt GENERATED STORED column using immutable parser function (`parse_ref_period_to_date`).

### C3 — FK decision
Include FK to `semantic_mappings (cube_id, semantic_key)` with `ON DELETE CASCADE`.

### C4 — `value` nullability
Store rows even when missing; use `value=NULL` + `missing=true`.

### C5 — Capacity
Planning baseline: 7,000 mappings × 12 periods = 84,000 rows initial; monthly growth roughly one period per active mapping frequency cycle. Postgres capacity acceptable.


### C6 — `source_hash` canonical derivation

```python
source_hash = sha256(
    json.dumps(
        {
            "product_id": product_id,
            "cube_id": cube_id,
            "semantic_key": semantic_key,
            "coord": coord,
            "ref_period": ref_period,
            "value": str(value) if value is not None else None,
            "missing": missing,
            "decimals": decimals,
            "scalar_factor_code": scalar_factor_code,
            "symbol_code": symbol_code,
            "security_level_code": security_level_code,
            "status_code": status_code,
            "frequency_code": frequency_code,
            "vector_id": vector_id,
            "response_status_code": response_status_code,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
).hexdigest()
```

Excludes `fetched_at`, `release_time`, `created_at`, `updated_at` to avoid false-stale drift from non-value timestamps.

---

## §D — ORM model
```python
"""Phase 3.1aaa: SemanticValueCache ORM model.

Persistent cache of resolved StatCan data points keyed by
(cube_id, semantic_key, coord, ref_period). Populated by
:class:`StatCanValueCacheService` (auto-prime on mapping upsert per Q-2 lock)
and refreshed nightly by the ``statcan_value_cache_refresh`` scheduler job
(per §H, 16:00 UTC). Read by 3.1c semantic resolve service.

Style and structure intentionally mirror
`backend/src/models/cube_metadata_cache.py` from Phase 3.1aa.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class SemanticValueCache(Base):
    """Cached StatCan data point keyed by (cube_id, semantic_key, coord, ref_period).

    `period_start` is a Postgres GENERATED ALWAYS AS STORED column populated
    by the `parse_ref_period_to_date` SQL function (defined in the migration).
    SQLAlchemy treats it as a read-only column; service code MUST NOT attempt
    to set it explicitly on insert/update.
    """

    __tablename__ = "semantic_value_cache"
    __table_args__ = (
        UniqueConstraint(
            "cube_id", "semantic_key", "coord", "ref_period",
            name="uq_semantic_value_cache_lookup",
        ),
        ForeignKeyConstraint(
            ("cube_id", "semantic_key"),
            ("semantic_mappings.cube_id", "semantic_mappings.semantic_key"),
            ondelete="CASCADE",
            name="fk_semantic_value_cache_mapping",
        ),
        Index("ix_semantic_value_cache_product_id", "product_id"),
        Index(
            "ix_semantic_value_cache_coord",
            "cube_id", "semantic_key", "coord",
        ),
        Index("ix_semantic_value_cache_fetched_at", "fetched_at"),
        Index("ix_semantic_value_cache_period_start", "period_start"),
        Index(
            "ix_semantic_value_cache_is_stale",
            "is_stale",
            postgresql_where=sa.text("is_stale = true"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    cube_id: Mapped[str] = mapped_column(String(length=50), nullable=False)
    product_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(length=100), nullable=False)
    coord: Mapped[str] = mapped_column(String(length=50), nullable=False)
    ref_period: Mapped[str] = mapped_column(String(length=20), nullable=False)

    # GENERATED ALWAYS AS STORED via Postgres parser function.
    # Declared via SQLAlchemy Computed() so Alembic autogenerate sees the
    # generation expression and doesn't false-flag drift. SQLAlchemy reads
    # this column; service code MUST NOT set it explicitly.
    period_start: Mapped[date | None] = mapped_column(
        Date,
        Computed("parse_ref_period_to_date(ref_period)", persisted=True),
        nullable=True,
    )

    value: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=18, scale=6),
        nullable=True,
    )
    missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scalar_factor_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symbol_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    security_level_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frequency_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    vector_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source_hash: Mapped[str] = mapped_column(String(length=64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    release_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
```

## §E — Pydantic schemas
Draft classes: `StatCanDataPoint`, `StatCanDataResponse`, `ValueCacheRow`, `ResolvedValue`, `AutoPrimeResult`, `RefreshSummary`, `ValueCacheUpsertItem`.

## §F — Repository
`SemanticValueCacheRepository` methods:
- `upsert_period`
- `upsert_periods_batch`
- `get_by_lookup`
- `get_latest_by_lookup`
- `mark_stale_outside_window`
- `delete_older_than`

Each method includes async signature + brief behavior contract.

## §G — Service layer
`StatCanValueCacheService` methods:
- `auto_prime(...)`
- `refresh_all(...)`
- `get_cached(...)`
- `evict_stale(...)`

auto_prime contract (best-effort, NOT blocking):
- Called synchronously from SemanticMappingService.upsert_validated AFTER metadata validation succeeds.
- Mapping save MUST NOT fail because the StatCan WDS data endpoint is unavailable, rate-limited, or returns FAILED. Mapping is already valid at this point (metadata validator passed); value cache is a derived read-optimization layer.
- On failure: log structured warning with reason, optionally write a refresh_failed marker on the mapping (deferred to impl), return control to caller. Caller commits the mapping save normally.
- Nightly refresh job (refresh_all) retries on subsequent runs.
- Future explicit admin "Refresh values now" endpoint may surface STATCAN_UNAVAILABLE directly to operator, but THAT is out of 3.1aaa scope.

This is a deliberate divergence from 3.1aa metadata-cache pattern. 3.1aa fails mapping save on metadata cache miss because the validator cannot run without metadata. 3.1aaa's value cache is consumed by 3.1c resolve, not by mapping validation, so its absence does not invalidate the mapping.

**Q-3 RE-LOCKED on reviewer feedback round, 2026-05-03:** auto-prime executes synchronously but failure does not propagate to mapping save; log warning + continue.

## §H — Scheduler integration
- Existing metadata refresh cron: 15:00 UTC.
- StatCan releases published in The Daily at 8:30 a.m. ET (official release schedule statement).
- Recon decision: schedule value refresh at **16:00 UTC** daily so metadata refresh (15:00 UTC) runs first and publication window has passed in both EST/EDT.
- Job config: `coalesce=True`, `max_instances=1`, `misfire_grace_time=3600`, `replace_existing=True`.

## §I — Test plan
- Coord unit: 7 tests.
- Service auto_prime: 10 tests.
- Service refresh_all: 8 tests.
- Repository: 10 tests.
- Integration migration/ORM: 6 tests.
- Scheduler: 3 tests.
- Total target: **44 tests**.

## §J — Founder questions (Q-impl)
1. Confirm exact batch max from authoritative WDS contract/testing.
2. Confirm mixed-success array semantics for partial failures.
3. Confirm all real-world `refPer` formats encountered across cubes.
4. Confirm scalar/symbol code-to-units mapping table source.
5. Confirm fixture strategy for integration tests using realistic WDS payload samples.

## §K — DEBT entries
Next free ID from DEBT.md scan: **DEBT-058**.

### DEBT-058: StatCan WDS batch-size ceiling verification
- **Source:** Phase 3.1aaa recon §A5
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** ops
- **Status:** accepted
- **Description:** 3.1aaa recon sets batch size to 100 conservatively because official hard limit is not conclusively captured in current source snapshot.
- **Impact:** Potentially suboptimal nightly runtime and elevated request count.
- **Resolution:** Validate 200/500/1000 in staging with telemetry and adjust constant.
- **Target:** First post-3.1aaa production observation window.

### DEBT-059: StatCan mixed-success semantics verification
- **Source:** Phase 3.1aaa recon §A6
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** testing
- **Status:** accepted
- **Description:** Per-item mixed SUCCESS/FAILED semantics for batched endpoint are assumed but not explicitly proven by authoritative sample in current recon.
- **Impact:** Error handling path may be over/under-defensive.
- **Resolution:** Capture and store fixture showing mixed batch behavior; align parser/tests.
- **Target:** 3.1aaa implementation PR.

### DEBT-060: Units derivation mapping canonicalization
- **Source:** Phase 3.1aaa recon §E (`ResolvedValue.units`)
- **Added:** 2026-05-03
- **Severity:** low
- **Category:** architecture
- **Status:** accepted
- **Description:** Conversion from `(scalar_factor_code, symbol_code)` to stable units string is required for hash determinism/documentation and remains pending canonical source mapping.
- **Impact:** Risk of inconsistent units labels across services/tests.
- **Resolution:** Introduce a single shared mapping table + tests sourced from StatCan documentation.
- **Target:** 3.1c dependency preparation.

## §L — Glossary additions
- **semantic_value_cache:** Table storing resolved StatCan datapoints per mapping+coord+period.
- **coord:** Dot-separated StatCan coordinate across 10 slots.
- **ref_period:** Raw period text key from StatCan datapoint.
- **period_start:** Normalized date parsed from `ref_period`.
- **auto-prime:** synchronous cache fill during mapping upsert.
- **value cache refresh:** nightly scheduled refresh across active mappings.

---
