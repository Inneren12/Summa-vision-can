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
