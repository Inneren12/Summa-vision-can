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

## C. Service layer changes

**What's here:** call-site changes in `lineage.py` (new functions), `publication_repository.py` (constructor sites accept `lineage_key` argument), and the two service-layer callers (`clone.py`, `admin_publications.py`) which compute lineage_key and pass to repo.

**Source files cited:** `lineage.py` (existing, Chunk 1a), `publication_repository.py`, `clone.py`, `admin_publications.py`.

**Path drift discovered:** repository file lives at `backend/src/repositories/publication_repository.py`, NOT `backend/src/services/publications/publication_repository.py` as the prior plan assumed. The `services/publications/` package contains only `lineage.py`, `clone.py`, and `exceptions.py` — repositories are sibling to `services/` under `src/`.

**Architectural finding:** `Publication()` constructor calls live in `publication_repository.py` (4 sites). Service layer delegates via `repo.create_clone(...)` / `repo.create_full(...)`. lineage_key must therefore flow as a method argument from service → repo, not be generated inside the repo.

### C1. New functions in `services/publications/lineage.py`

(Chunk 1a §A3 specified the surface; this section pins exact code.)

Append to existing module after `compute_config_hash` (line 28) and `derive_size_from_visual_config` (line 44):

```python
try:
    from uuid import uuid7  # Python 3.13+ stdlib
except ImportError:
    from uuid_utils import uuid7  # uuid-utils package per Section B1


def generate_lineage_key() -> str:
    """
    Generate a fresh UUID v7 string for a new (non-clone) publication's
    lineage. Time-sortable + globally unique. Used by the create path.

    Returns:
        Canonical 36-char UUID v7 string, e.g.
        '01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c'.

    Pure function (ARCH-PURA-001 compliant): module-imported uuid7 is
    deterministic given current wall-clock; no I/O, no DB.
    """
    return str(uuid7())


def derive_clone_lineage_key(source: "Publication") -> str:
    """
    Returns source.lineage_key directly. Wrapper exists to make the
    inheritance contract explicit at clone call sites.

    Future hook for "manual lineage break" UI (Phase 4+): this function
    would consult an override flag and call generate_lineage_key()
    instead when set. Today, always inherits.

    Pure function: no I/O, no side effects.

    Raises:
        ValueError: if source.lineage_key is None (data integrity
            violation; should be impossible post-Phase-2.2.0 migration).
    """
    if source.lineage_key is None:
        raise ValueError(
            f"Publication id={source.id} has null lineage_key; "
            "data integrity violation post-Phase-2.2.0 migration"
        )
    return source.lineage_key
```

**Why type hint quoted as `"Publication"`:** avoids circular import. `lineage.py` is imported by `clone.py` which already imports the `Publication` model; the existing module avoids `from src.models.publication import Publication` at top-level. Quoted forward reference resolves at type-check time only. Module-level docstring's "No DB access here" purity claim (line 3) is preserved.

### C2. Repository layer changes — `publication_repository.py`

`Publication()` constructor sites in `backend/src/repositories/publication_repository.py`:
```
112:                publication = Publication(   # inside create_with_versioning (def @ line ~88)
158:        publication = Publication(           # inside create (def @ line 134)
182:        clone = Publication(                 # inside create_clone (def @ line 172)
446:        publication = Publication(**payload) # inside create_full (def @ line ~423)
```

**4 sites confirmed.** Each repo method gains a way to receive `lineage_key`; the repository never generates the value.

**Method signature changes:**

| Method (line) | New required arg | Caller computes via |
|---|---|---|
| `create_with_versioning` (line ~88) | `lineage_key: str` (kwarg) | `generate_lineage_key()` (pipeline-side) |
| `create` (line 134) | `lineage_key: str` (kwarg) | `generate_lineage_key()` (any caller) |
| `create_clone` (line 172) | `lineage_key: str` (kwarg) | `derive_clone_lineage_key(source)` from `clone.py` |
| `create_full` (line ~423) | accepted via `data` dict | Caller injects `lineage_key` into the dict before passing in |

**Constructor body change pattern** (sites 112, 158, 182):
```python
# Before:
publication = Publication(
    headline=...,
    chart_type=...,
    # ... existing fields ...
)
# After:
publication = Publication(
    headline=...,
    chart_type=...,
    # ... existing fields ...
    lineage_key=lineage_key,  # NEW — passed in as kwarg
)
```

**Site 446 (`create_full`) — dict-style construction:** the method already does `Publication(**payload)` from a dict produced by `body.model_dump()`. Two options:
- **(preferred)** caller injects `lineage_key` into the dict before calling `repo.create_full(data)`. Keeps lineage_key visible at the route boundary (route → repo data flow stays explicit).
- **(alternative)** repo accepts `lineage_key` as a separate kwarg and `payload["lineage_key"] = lineage_key` before construction. More defensive but hides the value inside the repo.

C3a uses the preferred option.

**Repository imports:** no new imports needed in `publication_repository.py`. Generation lives in `services/publications/lineage.py`; the repo just stores the value.

### C3. Service layer call sites

#### C3a. Create path — `admin_publications.py:265`

Verbatim from `sed -n '258,275p'`:
```
async def create_publication(
    body: PublicationCreate,
    repo: PublicationRepository = Depends(_get_repo),
) -> PublicationResponse:
    """Create a new publication in ``DRAFT`` status."""
    publication = await repo.create_full(body.model_dump())
```

**Change:**
```python
# Add to imports:
from src.services.publications.lineage import generate_lineage_key

# At call site (line 265):
data = body.model_dump()
data["lineage_key"] = generate_lineage_key()  # NEW — pure call, no DB
publication = await repo.create_full(data)
```

`generate_lineage_key()` is called BEFORE `repo.create_full(...)`. Pure function, no DB access. Note: `PublicationCreate` schema (in `schemas/publication.py`) does NOT include `lineage_key` as an input field — operators don't pass it in via the request body. It's stamped server-side. Chunk 2a §D will pin this in the schema design.

#### C3b. Clone path — `clone.py:61`

Verbatim from `sed -n '55,75p'`:
```
        try:
            clone = await repo.create_clone(
                source=source,
                new_headline=new_headline,
                new_config_hash=new_config_hash,
                new_version=new_version,
                fresh_review_json=fresh_review_json,
            )
```

**Change:**
```python
# Add to existing import block (lineage.py is already imported):
from src.services.publications.lineage import (
    compute_config_hash,
    derive_clone_lineage_key,   # NEW
    derive_size_from_visual_config,
)

# At call site (line 61):
clone = await repo.create_clone(
    source=source,
    new_headline=new_headline,
    new_config_hash=new_config_hash,
    new_version=new_version,
    fresh_review_json=fresh_review_json,
    lineage_key=derive_clone_lineage_key(source),  # NEW — inherits source's
)
```

`derive_clone_lineage_key(source)` runs BEFORE `repo.create_clone(...)`. Pure function operating on the already-fetched ORM `source` object — no extra DB round-trip. The retry loop around `create_clone` (lines 54-78) is unchanged: lineage_key is invariant across version-bump retries, so it's safe to compute once outside the loop or once per attempt; recommendation is once per attempt for clarity (the call is essentially free).

### C4. Audit — all `Publication()` constructor sites

Full audit output (`grep -rn "Publication(" backend/src/ | grep -v test | grep -v __pycache__`):
```
backend/src/repositories/publication_repository.py:112:                publication = Publication(
backend/src/repositories/publication_repository.py:158:        publication = Publication(
backend/src/repositories/publication_repository.py:182:        clone = Publication(
backend/src/repositories/publication_repository.py:446:        publication = Publication(**payload)
backend/src/models/publication.py:27:class Publication(Base):
backend/src/models/publication.py:159:            f"<Publication(id={self.id}, headline={self.headline!r}, "
```

The two `models/publication.py` hits are not constructors — line 27 is the class definition itself, line 159 is a `__repr__` format string. Discard from audit. **4 real constructor sites, all in `publication_repository.py`.**

**Categorization table:**

| Site | Path:line | Method | Purpose | Phase 2.2.0 treatment |
|---|---|---|---|---|
| 1 | `publication_repository.py:112` | `create_with_versioning` | Pipeline-driven create with versioning loop (S3 keys, virality, content_hash). Caller is the graphics pipeline, NOT covered by C3a/C3b. | Add `lineage_key: str` kwarg to method; populate in constructor. Caller (pipeline) passes `generate_lineage_key()`. **Flag for Chunk 2b §F as Q-impl-1: confirm pipeline call site.** |
| 2 | `publication_repository.py:158` | `create` | Minimal DRAFT create (no versioning, no editorial fields). Caller(s) unknown from this scope. | Add `lineage_key: str` kwarg; populate in constructor. **Flag for Chunk 2b §F as Q-impl-2: grep audit of callers — may be legacy/test-only; if so, accept default `lineage_key=Field(default_factory=generate_lineage_key)` style or deprecate.** |
| 3 | `publication_repository.py:182` | `create_clone` | Service clone path (called by `clone.py:61` per C3b). | Add `lineage_key: str` kwarg; populate in constructor. Caller passes `derive_clone_lineage_key(source)`. |
| 4 | `publication_repository.py:446` | `create_full` | Admin REST create (called by `admin_publications.py:265` per C3a). Uses `Publication(**payload)` style. | Caller injects `lineage_key` into the `data` dict via `data["lineage_key"] = generate_lineage_key()`. No method-signature change. |

**Surprise sites outside repository:** none. All 4 production constructor calls are in `publication_repository.py`.

**Treatment rules:**
- Sites 3 + 4 are fully covered by C3a + C3b (service-layer callers known and changed).
- Sites 1 + 2 require an impl-time grep audit of their callers — the 3 allowed files for this chunk did not include the graphics pipeline or any caller of `repo.create()`. Both are flagged for Chunk 2b §F as Q-impl items.
- No background job / scheduler / sync writer surfaced in the audit. If Chunk 2b's broader scan finds one, it's a surprise to flag.

**Expected outcome:** Chunk 2b §F will pin the open questions (Q-impl-1 pipeline caller, Q-impl-2 `create()` callers) so impl phase has a checklist before touching repo signatures.
