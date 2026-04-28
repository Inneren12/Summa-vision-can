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

## D. Schema and API surface

**What's here:** PublicationResponse field add, request schema treatment (lineage_key is server-generated and already blocked at the request boundary by `extra="forbid"`), and OpenAPI doc impact.

**Source files cited:** schemas/publication.py, pre-recon §E2, admin_publications.py:265 context from Chunk 1b-ii.

### D1. `PublicationResponse` field add

(per pre-recon §E2 — actual schema name is `PublicationResponse`, not `AdminPublicationResponse`)

Schema classes detected in `backend/src/schemas/publication.py`:
```
42:class BrandingConfig(BaseModel):
60:class VisualConfig(BaseModel):
96:class ReviewPayload(BaseModel):
128:class PublicationCreate(BaseModel):
152:class PublicationUpdate(BaseModel):
196:class PublicationResponse(BaseModel):
267:class PublicationPublicResponse(BaseModel):
```

`grep -n "lineage_key" backend/src/schemas/publication.py` → **zero matches**, confirming pre-recon §E2.

**Add field to `PublicationResponse` (line 196):**
```python
class PublicationResponse(BaseModel):
    # ... existing 17 fields ...
    cloned_from_publication_id: Optional[int] = None
    lineage_key: str   # NEW — Phase 2.2.0; required (NOT NULL post-migration)

    model_config = ConfigDict(from_attributes=True)   # unchanged (line 222)
```

**Why `str`, not `Optional[str]`:** post-migration the column is `NOT NULL` (per Chunk 1a §A1, Chunk 1b-i §B2 step 3). Surface type should mirror DB nullability; `Optional[str]` would lie about the contract and force every consumer to write defensive `if k is not None` branches.

**Why no `Field(...)` constraints:** lineage_key is internally-generated (UUID v7), never operator-provided. No `min_length`, `max_length`, `pattern` needed at the response layer — the service-layer generator is the single point of truth for format.

**Pydantic V2 ConfigDict:** existing `model_config = ConfigDict(from_attributes=True)` at line 222 covers ORM→schema attribute access for the new field automatically. No config change.

### D2. `PublicationPublicResponse` — explicit decision NOT to expose

`PublicationPublicResponse` (line 267, public-gallery counterpart) MUST NOT include `lineage_key`. Rationale: the public gallery is unauthenticated; exposing lineage_key there leaks internal cross-version grouping to anyone, which is information the UTM scheme is supposed to keep on Summa's analytics side. Phase 2.3 attribution queries run server-side off the admin-visible field.

If a future phase needs the public response to surface lineage_key (e.g. for client-side share-URL composition), revisit then. Phase 2.2.0 keeps it admin-only.

### D3. Request schema treatment — `extra="forbid"` already blocks operator override

Verified from `schemas/publication.py`:
- `PublicationCreate` (line 128): `model_config = ConfigDict(extra="forbid")` at line 171 — comment at line 167: "`extra='forbid'` rejects unknown fields with HTTP 422 to prevent ..."
- `PublicationUpdate` (line 152): `model_config = ConfigDict(extra="forbid")` at line 110

**Implication:** if an attacker tries `POST /api/v1/admin/publications` with `{"lineage_key": "attacker-controlled-uuid", ...}`, Pydantic rejects with HTTP 422 BEFORE the request body reaches `repo.create_full(...)`. The `extra="forbid"` config is the existing defence; lineage_key being absent from `PublicationCreate` is sufficient — no new field, no new validator needed.

**Service layer pattern** (refines Chunk 1b-ii §C3a now that we know the dict from `body.model_dump()` is guaranteed not to contain `lineage_key`):
```python
# admin_publications.py around line 265:
data = body.model_dump()                  # guaranteed clean: extra="forbid" rejected any lineage_key
data["lineage_key"] = generate_lineage_key()   # server-side stamp
publication = await repo.create_full(data)
```

The `data["lineage_key"] = ...` injection is safe because `body.model_dump()` produces a fresh dict — mutation does not bleed back into the request.

**Clone request schema** (whatever the body of the clone endpoint accepts — `clone.py:25` takes only `source_id` from URL; per `admin_publications.py` clone-endpoint pattern there may or may not be a body schema): no change. lineage_key is derived internally from `source` via `derive_clone_lineage_key(source)`. If a future clone endpoint adds a request body, it MUST also use `extra="forbid"` (same defence pattern).

### D4. OpenAPI doc impact

OpenAPI schema regeneration after Phase 2.2.0:
- `PublicationResponse` gains required field `lineage_key: string`
- `PublicationPublicResponse` unchanged (per D2)
- No new endpoints, no new request fields
- No API version bump (additive output-only field)

**Compatibility:** existing admin clients reading `PublicationResponse` ignore unknown fields by default (most JSON parsers, including Next.js client code per Phase 2.2 frontend roadmap). The frontend will start consuming `lineage_key` when Phase 2.2 ships; in the gap between Phase 2.2.0 backend ship and Phase 2.2 frontend ship, the field is harmlessly present-but-unused.

## E. Test plan

**What's here:** unit + integration tests for the new lineage helpers, migration scenarios, schema serialization, and a fixture-update audit.

**Source files cited:** test directory listings from verification, existing `test_lineage.py`, `test_clone.py`, `test_publication_repository.py`.

**Test layout drift:** the prompt's `backend/tests/unit/services/publications/` and `backend/tests/migrations/` paths do NOT exist. Actual layout (from `find backend/tests`):
- `backend/tests/services/publications/test_lineage.py` (EXISTS — extend)
- `backend/tests/services/publications/test_clone.py` (EXISTS — extend)
- `backend/tests/repositories/test_publication_repository.py` (EXISTS — extend)
- `backend/tests/api/test_admin_publications.py` (EXISTS — extend)
- `backend/tests/api/test_clone_publication_endpoint.py` (EXISTS — extend)
- `backend/tests/integration/` exists (alongside `backend/tests/` proper) — no `migrations/` subdir; new migration test goes in `backend/tests/integration/migrations/test_lineage_key_backfill.py` (new directory)

### E1. Unit tests — extend `tests/services/publications/test_lineage.py`

**Test cases for `generate_lineage_key()`:**
1. **Returns 36-char canonical UUID v7 format** — regex `^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
2. **Distinct calls return distinct values** — call 100 times, assert `len(set(results)) == 100`
3. **Time-sortable (UUID v7 invariant)** — call N=10 with `time.sleep(0.001)` between; assert `results == sorted(results)`

**Test cases for `derive_clone_lineage_key(source)`:**
1. **Returns source.lineage_key verbatim** — pass mock `Publication(lineage_key="01923f9e-...")`, assert exact return
2. **Raises ValueError on null lineage_key** — pass mock `Publication(lineage_key=None)`, assert `ValueError` whose message contains "data integrity"
3. **Pure function — no DB / I/O** — call requires only an in-memory Publication instance; no `session` / `repo` fixtures

**Coverage target:** 100% on the two new functions (≥6 cases total).

### E2. Migration test — new file `tests/integration/migrations/test_lineage_key_backfill.py`

(no existing migration tests detected; this is a new pattern. Recommend `subprocess.run(['alembic', 'upgrade', 'head'])` style with `alembic downgrade base` teardown — programmatic Alembic API conflicts with the pytest-asyncio event loop.)

**Test scenarios** (per Chunk 1b-i §B3):

1. **Linear clone chain inheritance**
   - Setup: insert A (root), B (`cloned_from=A`), C (`cloned_from=B`), all with `lineage_key=NULL` AT REVISION `b4f9a21c8d77`
   - Run: upgrade to head
   - Assert: `A.lineage_key == B.lineage_key == C.lineage_key`; matches UUID v7 regex

2. **Multiple independent roots**
   - Setup: insert P1, P2, P3, no clone FKs
   - Run: upgrade
   - Assert: 3 distinct lineage_keys

3. **Orphaned clone (parent SET NULL via cascade)**
   - Setup: insert parent, insert clone with `cloned_from=parent.id`, then `DELETE FROM publications WHERE id=parent.id` (FK has `ondelete="SET NULL"` per pre-recon §E1) — clone's `cloned_from_publication_id` is now NULL
   - Run: upgrade
   - Assert: orphan gets fresh lineage_key (not NULL)

4. **Idempotency of upgrade → downgrade → upgrade**
   - Setup: empty publications table
   - Run: upgrade, downgrade, upgrade
   - Assert: schema correct after second upgrade; index re-created; no errors

5. **NOT NULL enforcement after backfill**
   - Setup: insert one row, run upgrade
   - Assert: `INSERT INTO publications (headline, chart_type) VALUES (...)` (omitting lineage_key) fails with `IntegrityError` / NOT NULL constraint

**CI level:** integration (Postgres-backed; can also run on SQLite via `aiosqlite` per existing test patterns, but the NOT NULL alter step needs SQLite-compatible Alembic batch_alter_table — flag for impl).

### E3. Integration tests — extend service write-path test files

**Extend `tests/api/test_admin_publications.py` (create path):**
1. `POST /api/v1/admin/publications` returns response with non-null `lineage_key` matching UUID v7 regex
2. Two consecutive POSTs return distinct `lineage_key`s (no caching/reuse)
3. After POST, `GET /api/v1/admin/publications/{id}` returns the same `lineage_key`
4. POST with `{"lineage_key": "attacker"}` in body returns HTTP 422 (per D3 — `extra="forbid"` defence)

**Extend `tests/api/test_clone_publication_endpoint.py` (clone path):**
1. `POST /api/v1/admin/publications/{id}/clone` returns clone where `clone.lineage_key == source.lineage_key`
2. Clone-of-clone preserves chain: A → B → C all share same `lineage_key`
3. Cloning a source with `source.lineage_key=None` (impossible post-migration but tested defensively) → endpoint returns 500 with diagnostic mentioning "data integrity" (matches `derive_clone_lineage_key` ValueError message)

**Extend `tests/repositories/test_publication_repository.py` (repo signatures):**
- `create_full({"lineage_key": "01923...", "headline": ..., ...})` persists the value
- `create_clone(source=src, lineage_key="01923...", ...)` persists the value
- `create(lineage_key="01923...", ...)` persists the value (Site 2, line 158)
- `create_with_versioning(lineage_key="01923...", ...)` persists the value (Site 1, line 112)

### E4. Schema serialization tests — extend `tests/services/publications/test_clone.py` or new schema test file

1. `PublicationResponse.model_validate(pub)` populates `lineage_key` from ORM — given `Publication(lineage_key="01923...")`, assert `.lineage_key == "01923..."`
2. `PublicationResponse.model_validate(pub)` raises `ValidationError` when `pub.lineage_key is None` — because the field type is `str` (not `Optional[str]`)
3. `PublicationCreate.model_validate({"lineage_key": "x", ...valid_fields})` raises `ValidationError` (HTTP 422 in router) — because `extra="forbid"`. **This test pins the D3 defence.**
4. `PublicationPublicResponse.model_dump()` MUST NOT contain key `lineage_key` (per D2 — admin-only field).

### E5. Fixture audit + CI gates

**Test-side `Publication(...)` constructor sites** (`grep -rn "Publication(" backend/tests/`):
```
backend/tests/services/publications/test_etag.py:25
backend/tests/services/publications/test_clone.py:29, :177
backend/tests/api/test_clone_publication_endpoint.py:82
backend/tests/api/test_lead_capture_scoring.py:28
backend/tests/api/test_download.py:60
backend/tests/api/test_lead_capture.py:48
backend/tests/models/test_publication_extended.py:45, :76, :95, :127, :147
```
(`backend/tests/api/test_public_graphics.py:66, :351` use `_FakePublication`, a test-only double — only needs `lineage_key` if a code path under test calls `PublicationResponse.model_validate(fake)`.)

**Treatment:** every site above must add `lineage_key="01923f9e-...-fixture"` (any valid UUID v7 string) OR rely on a new shared fixture helper `make_publication(...)` that defaults `lineage_key=generate_lineage_key()`. Recommendation: add the helper in `backend/tests/conftest.py` and migrate the 11+ call sites in one impl PR; new tests use the helper from day one.

**CI gates:**
- New code coverage: 100% on `lineage.py` new functions (E1)
- Migration coverage: all 5 scenarios (E2) green before merge
- Integration coverage: all create + clone routes (E3) cover lineage_key
- Schema coverage: 4 cases (E4)
- Fixture sites updated: 11+ enumerated above; flagged as Q-impl-3 in Chunk 2b §F if any are missed during impl-PR review

## F. Open questions for impl

**What's here:** the questions that surfaced during recon but cannot be fully resolved without exploration of unrelated code paths. Impl prompts pick these up. Recon-proper documents the question + recommended resolution path.

### Q-impl-1 — `create_with_versioning` is dead production code

**Discovered in:** Chunk 1b-ii §C4 (Site 1, `publication_repository.py:112`).

**Question:** `create_with_versioning` is a `Publication()` constructor site distinct from `create_full` and `create_clone`. Phase 2.2.0 must populate `lineage_key` here — does the call site treat the new publication as a root (fresh `generate_lineage_key()`) or as a derivation (inherit)?

**Verification command output** (`grep -rn "create_with_versioning\b" backend/src/ backend/tests/ backend/scripts/`):
```
(zero matches)
```

**Finding:** the method has **zero callers** across `backend/src/`, `backend/tests/`, and `backend/scripts/`. It is dead production code (or called only via dynamic dispatch / reflection, which is uncommon in this codebase).

**Resolution:** Phase 2.2.0 impl adds `lineage_key: str` as a required keyword argument to the method signature. Impl prompt should ALSO file a follow-up DEBT entry for "delete dead `create_with_versioning` repo method" once it confirms no dynamic callers (separate cleanup PR; not in scope for 2.2.0). Choosing `generate_lineage_key()` (root-style) at the future call site is conservative: pipeline-generated rows that share a recipe with another row should rely on `cloned_from_publication_id` + `derive_clone_lineage_key` if/when that pattern is needed.

### Q-impl-2 — `create` (line 158) is dead production code

**Discovered in:** Chunk 1b-ii §C4 (Site 2, `publication_repository.py:158`).

**Question:** Same pattern as Q-impl-1 — third constructor site, caller(s) unknown from Chunk 1b-ii's scope.

**Verification command output** (`grep -rn "\.create(" backend/src/ | grep -v "create_full\|create_clone\|create_with_versioning\|create_lead\|create_engine\|create_async_engine\|create_task\|create_connection\|create_default"`):
```
backend/src/api/routers/public_leads.py:330:        new_token = await token_repo.create(
backend/src/api/routers/public_leads.py:374:    download_token = await token_repo.create(
```

(Both hits are `token_repo.create` on `DownloadTokenRepository`, NOT `PublicationRepository.create`.)

**Finding:** `PublicationRepository.create` has zero callers in `backend/src/` and `backend/tests/`. Like Q-impl-1, this is dead code.

**Resolution:** add `lineage_key: str` kwarg to method signature for consistency. File a follow-up DEBT for deletion alongside `create_with_versioning`. The two together likely formed an early-Phase-1 API that was superseded by `create_full` (admin endpoint) + `create_clone` (clone service) and never removed.

### Q-impl-3 — Test fixture migration to `make_publication` helper

**Discovered in:** Chunk 2a §E5 (test fixture audit).

**Question:** 11+ test sites construct `Publication()` directly. Phase 2.2.0 NOT NULL constraint will break all of them at the ORM layer. Per memory pattern, the right fix is a centralized factory helper (`make_publication()` in `backend/tests/conftest.py`) that defaults `lineage_key=str(uuid7())`, accepts override kwarg.

**Why it matters:** without a helper, every test maintainer must remember to pass `lineage_key`. The helper makes the right thing the default, and bonus: also future-proofs against the next NOT NULL column add.

**Resolution:** impl prompt creates `make_publication` factory in `backend/tests/conftest.py` (or a sibling test-utils module), migrates all 11+ sites in a single PR. Search command for impl: `grep -rn "Publication(" backend/tests/`. Sites enumerated in Chunk 2a §E5.

### Q-impl-4 — Migration test infrastructure directory

**Discovered in:** Chunk 2a §E2 + E5.

**Question:** `backend/tests/integration/migrations/` does not exist. Per memory pattern (integration tests must use `subprocess.run(['alembic', 'upgrade', 'head'])`, NOT programmatic Alembic API), this directory needs creating with proper conftest.py and a teardown using `alembic downgrade base`.

**Resolution:** impl prompt creates the directory + a `conftest.py` defining the alembic-driven test session pattern (per-test transactional rollback or per-module DB reset). The 5 migration scenarios from Chunk 2a §E2 live in `backend/tests/integration/migrations/test_lineage_key_backfill.py`.

### Q-impl-5 — `uuid-utils` version pin convention

**Discovered in:** Chunk 1b-i §B1.

**Question:** Chunk 1b-i proposed pin `"uuid-utils>=0.10.0,<1.0.0"`. Confirm against repo convention.

**Verification command output** (pyproject.toml dep audit):
- exact-pin (`==`) count: **1** (`kaleido==0.2.1` only)
- range-pin (`>=X,<Y`) count: **36** (every other entry)

**Finding:** repo overwhelmingly uses range pins. The proposed `"uuid-utils>=0.10.0,<1.0.0"` matches the dominant convention; keep as-is.

**Resolution:** no change to Chunk 1b-i §B1's recommendation. Use `"uuid-utils>=0.10.0,<1.0.0"`.

### Q-impl-6 — Defence already present (NOT a question)

**Discovered in:** Chunk 2a §D3.

**Note:** `PublicationCreate.model_config = ConfigDict(extra="forbid")` (schemas/publication.py:171) already blocks operator-supplied `lineage_key` with HTTP 422. The "attacker injects lineage_key into POST body" concern is auto-resolved by existing schema configuration. Impl prompt's E4.3 test case verifies this defence still holds; no remediation work needed.

## G. DEBT and roadmap state updates

**What's here:** DEBT.md entries that touch Phase 2.2.0 and any new entries Phase 2.2.0 introduces.

**Source files cited:** DEBT.md, pre-recon §G.

### G1. Existing DEBT entries referenced

Verification output (`grep -n "DEBT-035\|lineage" DEBT.md | head -10`):
```
276:### DEBT-035: Parallel config_hash computation in pipeline + lineage helper
283:- **Description:** `_compute_hashes` in `backend/src/services/graphics/pipeline.py:182` inlines its own SHA-256 hashing logic, parallel to the centralized `compute_config_hash` in `backend/src/services/publications/lineage.py`. Both produce the same hash for the same inputs today, but divergence risk exists if either path is updated independently.
```

**DEBT-035 (Resolved):** existing `services/publications/lineage.py` houses `compute_config_hash`. Phase 2.2.0 extends this same module with `generate_lineage_key` + `derive_clone_lineage_key`. No DEBT-035 status change needed; just a cross-reference in Phase 2.2.0 impl prompt's "Files modified" list.

**DEBT-040 (per pre-recon §G2):** Phase 2.5b "missing post URLs" row depends on Phase 2.3 post_ledger which depends on Phase 2.2 distribution kit which depends on Phase 2.2.0 (this phase). No DEBT-040 status change in Phase 2.2.0; the dependency chain stays intact.

### G2. New DEBT entries from Phase 2.2.0 recon

Verification confirmed `grep -n -i "lineage_key" DEBT.md` returns **zero hits** — Phase 2.2.0 is the first formal mention.

**Proposed new entries** (impl prompt drafts the actual DEBT.md text and assigns next-available DEBT-NNN numbers):

#### DEBT-NNN: Manual lineage break UI

- **Severity:** P3 (deferred — no operator demand yet)
- **Category:** product-ux
- **Source:** Phase 2.2.0 recon Chunk 1a §A2 edge case
- **Description:** Operators cloning a publication for editorial purposes (preserve attribution) get a different need from operators cloning for "this is fundamentally a new story" (start fresh). Today, all clones inherit `lineage_key` via `derive_clone_lineage_key(source)`. No UI for breaking lineage. Wrapper function exists as a future hook (Chunk 1a §A3, §C1) but is unreachable from any UI today.
- **Status:** pending; deferred until operator hits the friction point
- **Target:** Phase 4 polish or post-MVP UX iteration

#### DEBT-NNN: Migration downgrade orphans Phase 2.3 UTM data

- **Severity:** P2 (operational risk, not bug)
- **Category:** ops-runbook
- **Source:** Phase 2.2.0 recon Chunk 1b-i §B4
- **Description:** Once Phase 2.3 starts logging `?utm_content=<lineage_key>` on lead funnels, downgrading then re-upgrading the `b4f9a21c8d77 → <new>` migration regenerates fresh root keys (`uuid7()` is non-deterministic). Historical UTM data orphans (recorded keys no longer match any current row). Document in migration docstring + ops runbook.
- **Status:** pending; ops note + migration docstring add are the resolution
- **Target:** Phase 2.2.0 impl includes both the migration docstring (per Chunk 1b-i §B2 boilerplate) and a runbook entry; resolves on merge.

#### DEBT-NNN: Dead `create_with_versioning` + `create` repo methods

- **Severity:** P3 (cleanup)
- **Category:** code-hygiene
- **Source:** Phase 2.2.0 recon Chunk 2b §F Q-impl-1, Q-impl-2
- **Description:** `PublicationRepository.create_with_versioning` (line 112) and `PublicationRepository.create` (line 158) have zero callers in `backend/src/`, `backend/tests/`, and `backend/scripts/`. They are dead code, likely superseded by `create_full` + `create_clone`. Phase 2.2.0 still updates their signatures with `lineage_key` for consistency; deletion belongs in a separate cleanup PR.
- **Status:** pending; deletion deferred so 2.2.0 stays scoped
- **Target:** post-2.2.0 cleanup PR

### G3. ROADMAP_DEPENDENCIES.md update

Phase 2.2.0 was NOT in the roadmap as a separate sub-phase before founder split decision (2026-04-28; per pre-recon Q-2.2-1 founder lock). Impl prompt updates `docs/architecture/ROADMAP_DEPENDENCIES.md`:

```
| 2.2.0 Backend lineage_key infrastructure | M | 1 | 2.1 |
| 2.2 Publish Kit Generator | M | 2 | 2.2.0 |   <-- update existing row's depends-on (was 2.1)
```

The 2.2 row currently lists `2.1` as dependency (per pre-recon §G2 line 51); that becomes `2.2.0`. The DAG section is also updated to insert `2.1 → 2.2.0 → 2.2 → {2.3, 2.4}`.

This is a documentation update only; impl prompt covers it as part of the Phase 2.2.0 PR.

## Appendix — file paths verified during Phase 2.2.0 recon

All files actually opened during Chunks 1a + 1b-i + 1b-ii + 2a + 2b (allows impl to confirm coverage):

**Chunk 1a (Section A):**
- docs/recon/phase-2-2-pre-recon.md (consumed §E1, §E2, §G1)
- backend/src/services/publications/lineage.py
- backend/src/models/publication.py
- backend/pyproject.toml

**Chunk 1b-i (Section B):**
- backend/pyproject.toml (verified PEP 621 dependency layout)
- backend/migrations/versions/ (path drift — actual location, NOT backend/alembic/versions/)
- Alembic head: `b4f9a21c8d77` (file `b4f9a21c8d77_add_cloned_from_to_publication.py`)

**Chunk 1b-ii (Section C):**
- backend/src/services/publications/clone.py
- backend/src/repositories/publication_repository.py (path drift — actual location, NOT services/publications/)
- backend/src/api/routers/admin_publications.py

**Chunk 2a (Sections D + E):**
- backend/src/schemas/publication.py
- docs/recon/phase-2-2-pre-recon.md (cross-reference §E2)
- backend/tests/ tree (directory listings; flatter than prompt assumed — no `unit/`, no `migrations/` subdirs)

**Chunk 2b (Sections F + G + Appendix):**
- DEBT.md (greps only — DEBT-035 cross-ref at line 276)
- docs/recon/phase-2-2-pre-recon.md (Appendix cross-reference)
- Plus grep audits across `backend/src/`, `backend/tests/`, `backend/scripts/` for Q-impl-1, Q-impl-2 caller resolution

**Path drift summary** (impl prompts MUST use actual paths):
- Alembic dir: `backend/migrations/versions/` (NOT `backend/alembic/versions/`)
- Repository: `backend/src/repositories/publication_repository.py` (NOT `backend/src/services/publications/publication_repository.py`)
- Test layout: flat under `backend/tests/` (NOT nested `backend/tests/unit/services/publications/`)
- Migration tests: new dir `backend/tests/integration/migrations/` needed (no existing `migrations/` subdir under tests)

---

**Phase 2.2.0 Recon-proper status: COMPLETE.**

Recon-proper output is consumed by impl prompts. Recommended impl prompt split:

- **Impl Chunk 1:** Migration + dependency add (per §B1 + §B2). Single Alembic revision, single pyproject.toml edit.
- **Impl Chunk 2:** Generator functions in lineage.py (per §C1). Pure code, no callers yet.
- **Impl Chunk 3:** Repository constructor sites (per §C2 + §F Q-impl-1/2). All four sites updated with `lineage_key` kwarg / dict-key.
- **Impl Chunk 4:** Schema field add (per §D1) + service-layer call sites (per §C3a, §C3b).
- **Impl Chunk 5:** Test fixture migration to `make_publication` helper (per §F Q-impl-3) + new tests (per §E1-§E4) + new migration test directory (per §F Q-impl-4).
- **Impl Chunk 6:** DEBT.md updates (per §G2, three entries) + ROADMAP_DEPENDENCIES.md update (per §G3) + migration ops-runbook entry (per §G2 second entry).

Founder reviews recon document, approves, then dispatches impl Chunk 1.
