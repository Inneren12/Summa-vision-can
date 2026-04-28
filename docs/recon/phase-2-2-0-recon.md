# Phase 2.2.0 Recon — Backend lineage_key Infrastructure

**Status:** Recon-proper — IN PROGRESS, Chunks 1b + 2a + 2b pending
**Author:** Claude Code (architect agent)
**Date:** 2026-04-28
**Branch:** claude/phase-2-2-0-recon
**Pre-recon source:** docs/recon/phase-2-2-pre-recon.md (Sections E1, E2, G1)

## Context

Phase 2.2.0 introduces `lineage_key` infrastructure on the backend. Pre-recon §E1/E2 confirmed the column does NOT exist on `Publication` model and is NOT in `PublicationResponse`. Phase 2.2.0 ships backend infra; Phase 2.2 frontend distribution kit consumes it.

Founder-locked decisions (from pre-recon Q&A round, 2026-04-28):
- Q-2.2-1 = (a) explicit column with split into Phase 2.2.0
- Q-2.2-2 = (a) UUID v7 generation
- Q-2.2-3 = (a) NEXT_PUBLIC_SITE_URL — Phase 2.2 frontend chunk, not 2.2.0
- Generator location = extend `backend/src/services/publications/lineage.py` (per pre-recon §G1, DEBT-035 reference)

## A. Architecture decisions

**What's here:** locked design choices for column shape, generator interface, clone semantics, and explicit scope locks.

**Source files cited:** pre-recon §E1/E2, lineage.py, publication.py.

### A1. Column shape on `Publication` model

(per pre-recon §E1)

| Field | Decision | Rationale |
|---|---|---|
| Name | `lineage_key` | Matches founder Q-D contract |
| Type | `String(36)` | Storage portability (not Postgres-native UUID); UUID v7 canonical form is always 36 chars |
| Nullable | `False` post-backfill; `True` during migration window only | Forward contract: every publication has a lineage_key |
| DB default | None | Generator runs in Python service layer, not SQL function |
| Index | `Index('ix_publications_lineage_key', 'lineage_key')` | Phase 2.3 attribution queries by lineage_key |
| Unique | **No** | Clones share lineage_key; uniqueness contract sits at `(lineage_key, version)` if extended later |

**Why not Postgres native `UUID` type:** matches existing `id String` pattern on Publication; portability if backend ever swaps DB; no functional benefit since UUID v7 strings are never compared as integers.

**Why not unique:** lineage = "same idea across versions". Two clones of the same source publication share a lineage_key. Uniqueness would prevent the entire clone semantics.

### A2. Clone semantics — lineage_key inheritance

**Pre-recon §E1 finding:** `cloned_from_publication_id` self-FK exists but is NOT a stable group key (it's a parent pointer, walked one hop at a time).

**Decision:**
- Non-clone (root) publication → generates a fresh `lineage_key`
- Clone → INHERITS source's `lineage_key` (does NOT generate new one)

**Rationale:** UTM attribution needs cross-version aggregation. If operator clones publication A → B → C, all three share `lineage_key`. Audience tracking by `?utm_content=<lineage_key>` aggregates engagement across the whole lineage.

**Edge case — chained clones (clone of clone):** `lineage_key` chains through. A → B (clone of A) → C (clone of B): all three share the same `lineage_key`. The `cloned_from_publication_id` chain shows immediate parents; `lineage_key` shows root-level identity.

**Edge case — manual lineage break:** if operator says "this clone is fundamentally a new story", they have no UI for that today. Phase 2.2.0 does NOT add it. Filed as future scope (Phase 4 or later); will register a DEBT entry in Chunk 2b if no existing one covers it.

**Edge case — orphaned clone:** if `cloned_from_publication_id=X` but parent X was hard-deleted, the clone became orphaned. Migration backfill handles this by treating orphan as a new root (generates fresh lineage_key). Documented in Chunk 1b §B2.

### A3. Generator interface

(cite verification command output for current `lineage.py` shape)

```
28:def compute_config_hash(
44:def derive_size_from_visual_config(
```

Existing surface (per DEBT-035, pre-recon §G1):
- `compute_config_hash(...) -> str` — already used by clone.py and graphics pipeline
- `derive_size_from_visual_config(...) -> tuple[int, int]` — already used by clone path

**New surface — Phase 2.2.0 adds two functions to the same module:**

```python
def generate_lineage_key() -> str:
    """
    Generate a fresh UUID v7 for a new publication's lineage.
    Used by create_publication for non-clone publications.
    Returns canonical 36-char UUID v7 string (time-sortable).
    """

def derive_clone_lineage_key(source: Publication) -> str:
    """
    Returns source.lineage_key directly. Wrapper exists to make
    the inheritance contract explicit at clone call sites.
    Future hook for "manual lineage break" UI.
    """
```

**Why a wrapper for clone instead of direct field access:** at the call site (`clone.py`), `derive_clone_lineage_key(source)` reads as intent ("derive clone's lineage from source"), not as field access (`source.lineage_key`). Makes future "manual lineage break" trivial — change wrapper body, no caller changes.

**Module purity (ARCH-PURA-001):** `generate_lineage_key` is a pure function (no DB, no I/O); `derive_clone_lineage_key` reads an attribute off a passed-in ORM instance, no I/O. Both fit the existing module contract (`Pure functions per ARCH-PURA-001. No DB access here.` — module docstring line 3).

### A4. UUID v7 generator backing

(cite verification command outputs)

Python version detected: `Python 3.11.15`
`uuid.uuid7` available in stdlib: `False`
`uuid` references in pyproject.toml: none (zero matches)

**Library decision:**

| Python version | Library | Notes |
|---|---|---|
| 3.13+ | `uuid.uuid7` from stdlib | Preferred — zero new deps |
| <3.13 | `uuid-utils` package added to pyproject.toml | Drop-in: `from uuid_utils import uuid7` |

**Active path for this repo:** `requires-python = ">=3.11"` (pyproject.toml line 5) and detected interpreter is 3.11.15 → stdlib `uuid.uuid7` is unavailable. Phase 2.2.0 MUST add `uuid-utils` to `[project].dependencies` in `backend/pyproject.toml` (Chunk 1b §C will spec the exact version pin).

**Format:** canonical `xxxxxxxx-xxxx-7xxx-yxxx-xxxxxxxxxxxx` (36 chars). The first 48 bits encode milliseconds since epoch → time-sortable when stored as string and ORDER BY ascending.

**Fallback (NOT for prod):** if neither stdlib nor `uuid-utils` available (test env without deps installed), generator falls back to UUID v4 with explicit log warning. Migration + service layer must NEVER hit this path in prod; it exists only for unit-test isolation.

### A5. What is NOT changed in Phase 2.2.0

Explicit scope lock — these stay untouched:

| Surface | Status |
|---|---|
| `Publication.cloned_from_publication_id` self-FK | Unchanged. Still tracks immediate parent. |
| Composite uniq `uq_publication_lineage_version` over `(source_product_id, config_hash, version)` | Unchanged. Independent constraint, different concern. |
| `compute_config_hash` function | Unchanged. DEBT-035 was a separate cleanup. |
| `derive_size_from_visual_config` function | Unchanged. Clone-path size helper, orthogonal to lineage_key. |
| `PublicationStatus` enum | Unchanged. |
| Public API endpoints (e.g. `GET /lineage/<key>`) | Not added in 2.2.0. Phase 2.3 may add for analytics. |
| Frontend hydration | Phase 2.2 frontend chunk, not 2.2.0. |
| `NEXT_PUBLIC_SITE_URL` env mirror | Phase 2.2 frontend chunk, not 2.2.0. |
| distribution.json / publish_kit.txt builders | Phase 2.2 frontend chunk, not 2.2.0. |
| UTM URL composer | Phase 2.2 frontend chunk, not 2.2.0. |

(Sections B + C in Chunk 1b cover migration + service layer changes. Sections D + E in Chunk 2a cover schema + tests. Section F in Chunk 2b covers open questions for impl.)

## B. Migration design

**What's here:** Alembic migration shape, backfill strategy, rollback path, and the `uuid-utils` dependency add.

**Source files cited:** pre-recon §E1, alembic versions dir (path: `backend/migrations/versions/`), pyproject.toml.

### B1. Dependency addition: `uuid-utils`

(Chunk 1a confirmed Python 3.11.15, no `uuid.uuid7` in stdlib; pyproject.toml currently has zero `uuid` references.)

pyproject.toml dependency section pattern detected (PEP 621, NOT poetry):
```
1:[project]
6:dependencies = [
```

i.e. `[project].dependencies` is a flat TOML array of PEP 508 strings (lines 6–35), not a `[tool.poetry.dependencies]` table. No `[tool.poetry]` section exists. Insertion is therefore as a single string entry inside the existing array, between any two existing entries (alphabetical placement preferred — slot it next to `tzdata` / `uvicorn` block, e.g. after `structlog`).

Add to `backend/pyproject.toml` under `[project].dependencies`:
```toml
    "uuid-utils>=0.10.0,<1.0.0",   # uuid7 generator; stdlib uuid.uuid7 only in Python 3.13+
```

(PEP 508 string with PEP 440 specifier, matching the `>=X.Y.Z,<NEXT_MAJOR.0.0` pattern used by every other entry in the array, e.g. `httpx>=0.27.0,<1.0.0`, `structlog>=24.1.0,<25.0.0`.)

Import pattern in `services/publications/lineage.py` (Section C will pin exact code):
```python
try:
    from uuid import uuid7  # Python 3.13+ stdlib
except ImportError:
    from uuid_utils import uuid7  # uuid-utils package
```

This try/except keeps the code forward-compatible for the eventual Python 3.13 upgrade — same call site, library swap is invisible to callers. Once `requires-python` bumps to `>=3.13`, the `uuid-utils` dep can be dropped and the try/except collapsed in a follow-up cleanup.

### B2. Migration shape

Alembic head detected at: `backend/migrations/versions/`
Current head revision: `b4f9a21c8d77` (file: `b4f9a21c8d77_add_cloned_from_to_publication.py`)

Single revision file: `backend/migrations/versions/<rev>_add_lineage_key_to_publications.py`

```python
"""add lineage_key to publications

Revision ID: <generated>
Revises: b4f9a21c8d77
Create Date: 2026-04-28

Phase 2.2.0 backend lineage_key infrastructure. Adds nullable column,
backfills existing rows by walking the cloned_from_publication_id graph
in id-ascending order, then enforces NOT NULL + adds index. Atomic
within one revision so a mid-backfill failure rolls cleanly.
"""
import sqlalchemy as sa
from alembic import op

revision = "<generated>"
down_revision = "b4f9a21c8d77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: add nullable column
    op.add_column(
        "publications",
        sa.Column("lineage_key", sa.String(length=36), nullable=True),
    )
    # Step 2: backfill via Python loop (UUID v7 unavailable in pure SQL)
    _backfill_lineage_keys()
    # Step 3: enforce NOT NULL after backfill
    op.alter_column(
        "publications",
        "lineage_key",
        existing_type=sa.String(length=36),
        nullable=False,
    )
    # Step 4: index for Phase 2.3 attribution queries
    op.create_index(
        "ix_publications_lineage_key",
        "publications",
        ["lineage_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_publications_lineage_key", table_name="publications")
    op.drop_column("publications", "lineage_key")


def _backfill_lineage_keys() -> None:
    """Walk publications by id ASC. Roots get fresh uuid7. Clones inherit
    from parent — guaranteed already-processed since clones have higher id."""
    try:
        from uuid import uuid7
    except ImportError:
        from uuid_utils import uuid7

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, cloned_from_publication_id "
        "FROM publications ORDER BY id ASC"
    )).fetchall()

    key_by_id: dict[int, str] = {}
    for row in rows:
        pub_id = row.id
        parent_id = row.cloned_from_publication_id
        if parent_id is not None and parent_id in key_by_id:
            key = key_by_id[parent_id]
        else:
            # Root, OR orphaned clone (parent hard-deleted)
            key = str(uuid7())
        key_by_id[pub_id] = key
        bind.execute(
            sa.text("UPDATE publications SET lineage_key = :k WHERE id = :i"),
            {"k": key, "i": pub_id},
        )
```

**Why three steps in one revision:** atomic forward path. Mid-backfill failure rolls cleanly via downgrade. Splitting into three migrations leaves ops in mid-state.

**Why Python loop, not SQL:** UUID v7 in Postgres requires `pg_uuidv7` extension (not standard). Migration runs in Python where `uuid-utils` is available via B1.

**Why id-ASC ordering is sufficient:** the `cloned_from_publication_id` FK in pre-recon §E1 (lines 90-94 of `backend/src/models/publication.py`) is populated only at clone time, by which point the source row already exists with a strictly smaller `id` (auto-increment PK). Therefore at the moment the loop processes any clone row, its parent's lineage_key is already in `key_by_id`. No second pass needed.

### B3. Backfill edge cases

| Scenario | Handling |
|---|---|
| Root publication (no parent) | Fresh `uuid7()` |
| Linear clone chain A → B → C | All three share A's lineage_key (B inherits from A; C inherits from B's already-resolved key) |
| Multiple independent roots | Each gets own `uuid7()` |
| Orphaned clone (parent_id set, parent hard-deleted via `ondelete="SET NULL"`) | `parent_id` is now NULL post-deletion → falls into "root" branch → fresh `uuid7()`. The branch also covers the impossible-but-defensive case where `parent_id` somehow points at a row not yet in `key_by_id`. |
| Empty publications table | `rows` is empty list; loop is no-op; ALTER NOT NULL succeeds vacuously |
| Composite uniq `uq_publication_lineage_version` (over `source_product_id, config_hash, version`) | Untouched — backfill writes only to `lineage_key`, leaves the existing 3-tuple constraint and its columns alone (Chunk 1a §A5 scope lock) |

### B4. Rollback safety + ops note

`downgrade()` drops index + column. Data loss is total but recoverable: re-running `upgrade()` regenerates. Clone-graph topology preserves grouping (same lineage groups stay grouped), but root key VALUES change on each upgrade run.

**Ops implication:** once Phase 2.3 starts logging `?utm_content=<lineage_key>` on lead funnels, downgrade-and-reupgrade orphans historical UTM data (recorded keys no longer match current rows). Document in migration docstring; add to Phase 2.2.0 release checklist as "do not downgrade once Phase 2.3 ships."
