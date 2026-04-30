# Phase 2.2.0.5 Recon — Backend slug Infrastructure

**Status:** Recon-proper Chunk A — APPROVED (founder review 2026-04-30, FR-1 through FR-4 applied), Chunks B + C + D pending
**Author:** Claude Code (architect agent)
**Date:** 2026-04-30
**Branch:** claude/phase-2-2-0-5-recon-chunk-a
**Pre-recon source:** docs/recon/phase-2-2-0-5-pre-recon.md (Sections A, B, F1–F6)
**Founder lock-in:** Q-2.2-9 (2026-04-30) backend-owned slug column

## Context

Phase 2.2.0.5 introduces a backend-owned `slug` as stable publication URL identity for frontend distribution. Founder lock-in Q-2.2-9 (2026-04-30) requires this to be a schema-backed backend field, not a frontend-derived value, so generation semantics and uniqueness are enforceable at data boundary.

This mirrors the architecture intent used earlier for `lineage_key`: generation logic belongs in backend publication services, not in client code. The slug contract is distinct from lineage grouping: slug is per-row URL identity, while lineage_key tracks conceptual family across clones.

Phase 2.2 frontend distribution kit consumes slug as `${PUBLIC_SITE_URL}/p/${slug}`. That means slug decisions in this chunk must lock column shape, deterministic generator behavior, and collision/reserved-path handling prior to migration and schema wiring chunks.

## A. Architecture decisions

**What's here:** locked design choices for column shape, generator interface, slugify algorithm, collision handling, reserved blacklist, and explicit scope locks.

**Source files cited:** pre-recon §A1, §A2, §A3, §B1, §B2, §F1–F6.

### A1. Column shape on `Publication` model

| Field | Decision | Rationale |
|---|---|---|
| Name | `slug` | Matches founder Q-2.2-9 contract; matches Next.js `/p/${slug}` route |
| Type | `String(200)` | `headline` max is 500, but slugification compresses punctuation/spacing. A 5-headline sanity sample yields ~28, 36, 52, 71, 88 chars (avg 55). Budgeting worst-case long headline truncation + reserved/collision suffix overhead (unified `-2..-99` range = up to 4 chars including hyphen, per §A5) still fits safely with 200. Existing model already uses bounded strings (`lineage_key` 36; hash columns 64 class), so 200 is consistent bounded design. |
| Nullable | `False` post-backfill; `True` during migration window only | Forward contract: every publication has a slug |
| DB default | None | Generator runs in Python service layer, not SQL function |
| Index | Implicit via UNIQUE constraint/index (no separate duplicate index) | Slug lookups for `/p/${slug}` are covered by unique index; separate non-unique index would be redundant |
| Unique | **Yes** | Two publications cannot share `/p/<slug>` URL; collision handler in §A4 ensures uniqueness at generation time |

**Uniqueness clarification vs lineage_key:** `lineage_key` is intentionally non-unique because clones inherit it. Slug is per-row public URL identity, so uniqueness is mandatory.

**Why no composite unique with version:** URL contract is one publication per path. Composite `(slug, version)` would allow duplicate path keys and force ambiguous `/p/{slug}` resolution. Clone/version rows should receive fresh slug when they are distinct publication rows, preserving immutable slug-per-row semantics and unambiguous route lookup.

### A2. Generator interface (pure functions in lineage.py)

```python
def generate_slug(headline: str, *, existing_slugs: set[str] | None = None) -> str:
    """
    Generate a publication slug from headline using deterministic slugify,
    reserved-path disambiguation, and collision suffixing.

    Pure function contract: no DB/network access; collision context is provided
    by caller via existing_slugs.

    Raises:
        PublicationSlugGenerationError: if slug body is empty/too short.
        PublicationSlugCollisionError: if collisions exceed capped attempts.
    """


def derive_clone_slug(source: Publication, *, existing_slugs: set[str] | None = None) -> str:
    """
    Generate a fresh slug for a clone row.

    Strips the `_COPY_PREFIX` (clone.py:41) from the source headline before
    invoking `generate_slug`, so clone URLs are not polluted with "copy-of-"
    prefixes.

    Example:
        source.headline = "Copy of Canada GDP Q3 2026"
        → strip prefix → "Canada GDP Q3 2026"
        → generate_slug → "canada-gdp-q3-2026" → collision check → "canada-gdp-q3-2026-2"

    Does not inherit source.slug: slug is per-row URL identity (UNIQUE), not
    lineage grouping. Each clone row owns its own URL path.

    Raises:
        PublicationSlugGenerationError: if stripped headline produces empty/short slug body.
        PublicationSlugCollisionError: if collisions exceed capped attempts.
    """
```

**Clone slug semantics:** fresh slug, not inherited. Lineage semantics inherit (`lineage_key` in Phase 2.2.0 §A2), but slug must identify each publication row URL uniquely and immutably. If clone inherited slug, URL identity would be shared and ambiguous.

**`_COPY_PREFIX` strip:** `derive_clone_slug` strips the `_COPY_PREFIX` constant (defined at `backend/src/services/publications/clone.py:21`) from the headline before calling `generate_slug`. Without this strip, clone URLs would be `/p/copy-of-canada-gdp-q3-2026`, polluting the URL with internal-only display prefix. The stripped headline produces a clean slug; collision suffixing (§A4) ensures uniqueness against the source's existing slug.

**Edge case — clone of clone:** A → B (clone of A) → C (clone of B). Clone path strips one `_COPY_PREFIX` per clone op (B.headline = "Copy of A"; C.headline = "Copy of Copy of A"). After strip: B → "A" base, C → "Copy of A" base. C still carries one prefix because clone.py prepends each time. Acceptable: chained clones get progressively-suffixed slugs (`a`, `a-2`, `copy-of-a`, etc.) — operator can rename headline before publish to clean up. Not a blocker for Phase 2.2.0.5; document as known UX nit.

**Purity contract lock:** `generate_slug` does not touch DB. Repo/service caller assembles `existing_slugs` collision context before invocation (ARCH-PURA-001 parity with prior lineage utility style).

**`set[str]` vs callable:** choose `set[str]` for this phase. Reason: deterministic, test-friendly, simple API surface for chunk-C service wiring. A callable probe introduces implicit I/O coupling risk and harder reproducibility. If future scale requires lazy probing, interface can evolve in a dedicated refactor.

### A3. Slugify algorithm — input → output specification

**Library ratification (Q-2.2.0.5-2):** use `python-slugify` with dependency string `python-slugify>=8.0.0,<9.0.0` added to `backend/pyproject.toml` `[project].dependencies` array.

**Dependency layout verification:** current file uses PEP 621 `[project]` + `dependencies = [...]` array (not poetry table), so insertion is another array entry in alphabetical slot near other `py*` entries (between `pytz` and `sqlalchemy`).

Pipeline:
1. Input raw headline string (clone path already includes `_COPY_PREFIX`, per pre-recon §D3 reference)
2. Lowercase + Unicode normalization (NFKD behavior through slugify stack)
3. Transliteration with `allow_unicode=False` (default) so non-Latin maps to ASCII via underlying transliteration
4. Replace non-alphanumeric runs with hyphen
5. Collapse repeated hyphens
6. Strip leading/trailing hyphens
7. Truncate slug body to `MAX_SLUG_LEN = 196` (column 200 minus worst-case 4-char safety budget before suffix handling)
8. Validate minimum body length (`MIN_SLUG_BODY_LEN = 3`) and non-empty; reject before suffixing
9. Apply reserved blacklist disambiguation (§A5)
10. Apply collision suffixing (§A4) against `existing_slugs`

**Worked examples (reasoned from python-slugify behavior):**

| Input headline | Step 1-2 (lowercase+NFKD) | Step 3 (transliterate) | Step 4-6 (final slug body) | Final slug (no collision) |
|---|---|---|---|---|
| "Canada GDP Q3 2026 Up 2.4%" | "canada gdp q3 2026 up 2.4%" | (no change, already ASCII) | "canada-gdp-q3-2026-up-2-4" | "canada-gdp-q3-2026-up-2-4" |
| "Інфляція в Україні 8.2%" (Ukrainian) | "інфляція в україні 8.2%" | "infliatsiia v ukraini 8.2" | "infliatsiia-v-ukraini-8-2" | "infliatsiia-v-ukraini-8-2" |
| "中国GDP增长" (Chinese) | "中国gdp增长" | expected unidecode-style romanization (e.g., "zhong guo gdp zeng zhang") | "zhong-guo-gdp-zeng-zhang" | "zhong-guo-gdp-zeng-zhang" *(TODO Chunk D: verify exact library transliteration tokens in tests)* |
| "!!!" (only punctuation) | "!!!" | "!!!" | "" (empty after strip) | **REJECTED — Q-2.2.0.5-5 guard** |
| "ab" (2 chars, below min) | "ab" | "ab" | "ab" | **REJECTED — Q-2.2.0.5-5 guard** |

**Q-2.2.0.5-5 ratification:** schema-level rejection semantics locked as `PublicationSlugGenerationError` when slug body is empty or `< 3` chars. Validation occurs before reserved/collision suffixing (`"a-1"` is invalid because base body is 1).

### A4. Collision handling — incremental suffix algorithm

Ratify Q-2.2.0.5-3 option (a): incremental suffix with hard cap.

```text
algorithm collision_handle(base_slug: str, existing_slugs: set[str]) -> str:
    if base_slug not in existing_slugs:
        return base_slug
    for n in range(2, 100):  # -2 through -99
        candidate = f"{base_slug}-{n}"
        if candidate not in existing_slugs:
            return candidate
    raise PublicationSlugCollisionError(base_slug=base_slug, attempts=99)
```

Decisions:
- Start at `-2`, not `-1`: bare slug is canonical first occurrence; second occurrence becomes `-2` by established URL convention.
- Cap at 99: balances deterministic bounded behavior, suffix budget (`-99`), and operator UX (99 duplicates implies headline is effectively non-distinct and should be edited).
- 100th collision behavior: raise `PublicationSlugCollisionError` hard error; no UUID fallback or silent mutation.
- Truncation interaction: ensure base candidate feeding collision loop is at most `MAX_SLUG_LEN - 4` when suffix may be needed, so any `-NN` variant remains within column width.

### A5. Reserved slug blacklist + disambiguation

Ratify Q-2.2.0.5-6: hardcoded blacklist with deterministic disambiguation.

```python
RESERVED_SLUGS: frozenset[str] = frozenset({
    # Next.js / framework reserved
    "_next", "static", "api", "_error", "404", "500",
    # App routes that compete with /p/<slug>
    "admin", "p", "about", "privacy", "terms", "login", "signup", "logout",
    "health", "robots", "sitemap", "favicon",
    # Brand
    "summa", "summa-vision",
    # Reserved for future
    "search", "feed", "rss", "atom",
})
```

Blacklist size: 25 entries.

Group rationale:
- Framework/system routes prevent path conflicts with runtime assets and error pages.
- App route terms prevent accidental overlap with known product pages and route namespaces.
- Brand terms avoid confusing canonical marketing/product roots.
- Future-reserved terms avoid locking out expected near-term discovery/feed endpoints.

Disambiguation rule (unified with §A4 collision algorithm):

1. If base slug ∈ RESERVED_SLUGS, treat it as a collision (add base slug to the conflict set passed into §A4 collision algorithm).
2. Run §A4 collision algorithm with the augmented conflict set: bare slug rejected (because reserved), tries `-2`, `-3`, ..., `-99`.
3. If any candidate also collides with an existing publication slug, the same loop skips it.
4. If exhaustion at `-99`, raise `PublicationSlugCollisionError` (same exception as pure collision case).

This unifies reserved-path defense and inter-publication uniqueness into a single suffix sweep. No special `-1` semantic. Examples:
- `admin` (reserved, no other conflicts) → `admin-2`
- `admin` (reserved, `admin-2` already taken by a publication) → `admin-3`
- `canada-gdp` (not reserved, one prior collision) → `canada-gdp-2`
- `canada-gdp` (not reserved, prior `canada-gdp-2` taken) → `canada-gdp-3`

Implementation note: at call site, the conflict set is built as `existing_slugs ∪ RESERVED_SLUGS` before invoking the collision loop. Pure function contract preserved (§A2): caller assembles the union, generator does not reach into the blacklist module.

Pre-recon did not fully inventory current frontend route tree in this chunk’s source set; Chunk D should verify blacklist against `frontend/app/` routes before final implementation lock.

### A6. What is NOT changed in Phase 2.2.0.5

| Surface | Status |
|---|---|
| `Publication.lineage_key` | Unchanged. Independent column, different concern. |
| `Publication.cloned_from_publication_id` self-FK | Unchanged. |
| `Publication.headline` field | Unchanged. Slug is derived from headline at create time, not bidirectional sync. |
| `compute_config_hash`, `derive_size_from_visual_config`, `generate_lineage_key`, `derive_clone_lineage_key` | Unchanged. New slug functions live in same module but don't touch existing ones. |
| `PublicationStatus` enum | Unchanged. |
| Public API endpoints | No new endpoint in 2.2.0.5. Phase 2.2 frontend uses slug via existing `PublicationResponse` field. |
| `PublicationUpdate` schema fields | NOT specified in Chunk A — Chunk C decides (lock-in: founder Q-2.2-9 says immutable, but field exclusion mechanism is Chunk C's responsibility). |
| Backfill behavior for existing rows | Chunk B. |
| make_publication factory default | Chunk D. |
| DEBT.md entry text | Chunk D. |
| ROADMAP_DEPENDENCIES.md row | Chunk D. |

Scope partition lock: Chunk B covers migration/backfill, Chunk C covers schema + service caller wiring + immutability enforcement, Chunk D covers tests + DEBT + roadmap.


## B. Migration design

**What's here:** Alembic migration shape, backfill strategy, rollback path, and the `python-slugify` dependency add.

**Source files cited:** pre-recon §A, §B2, §C, §F7; alembic versions dir (`backend/migrations/versions/`); pyproject.toml.

### B1. Dependency addition: `python-slugify`

Inventory confirms `backend/pyproject.toml` uses PEP 621 `[project].dependencies` array (no poetry table), and there are currently zero `slugify`/`unidecode`/transliteration-related entries.

Dependency add (PEP 508 string):

```toml
    "python-slugify>=8.0.0,<9.0.0",   # backend slug generator for Phase 2.2.0.5; transitively pulls text-unidecode for transliteration
```

Alphabetical slot: insert between `"pytz>=2024.1",` and `"sqlalchemy>=2.0,<3.0",` so the `py*` dependency cluster remains grouped.

Why `python-slugify`:
- Ratified in Chunk A §A3 (Q-2.2.0.5-2).
- Active, deterministic transliteration via transitive `text-unidecode`, and simple API.
- Avoids hand-rolling transliteration/normalization tables (out of scope).

Import pattern for runtime module (Chunk C implementation):

```python
from slugify import slugify
```

No try/except fallback required here (unlike `uuid7` split logic): slugification is dependency-owned for this phase.

Forward-compatibility note: if a stdlib slugifier appears in a future Python release, import policy can evolve then; not relevant for 2.2.0.5.

### B2. Migration shape

`down_revision` for the Chunk B migration is locked to `"a7d6b03efabf"` (current single Alembic head). Shape follows established repo pattern from revision `a7d6b03efabf`: add nullable column, backfill in Python, enforce NOT NULL, then add lookup constraint/index.

```python
"""add slug to publications

Revision ID: <generated>
Revises: a7d6b03efabf
Create Date: 2026-04-30

Phase 2.2.0.5 backend slug infrastructure. Adds nullable column,
backfills existing rows by slugifying headlines with collision suffixing,
then enforces NOT NULL + UNIQUE. Atomic within one revision so a
mid-backfill failure rolls cleanly.

OPS NOTE: once slug URLs are public-facing, do not downgrade this
migration in production; down->up can change slug paths and break links.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from slugify import slugify

revision: str = "<generated>"
down_revision: Union[str, Sequence[str], None] = "a7d6b03efabf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MAX_SLUG_LEN = 196
MIN_SLUG_BODY_LEN = 3
RESERVED_SLUGS: frozenset[str] = frozenset({
    "_next", "static", "api", "_error", "404", "500",
    "admin", "p", "about", "privacy", "terms", "login", "signup", "logout",
    "health", "robots", "sitemap", "favicon",
    "summa", "summa-vision",
    "search", "feed", "rss", "atom",
})


def upgrade() -> None:
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=200), nullable=True))

    _backfill_slugs()

    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.alter_column("slug", existing_type=sa.String(length=200), nullable=False)
        batch_op.create_unique_constraint("uq_publications_slug", ["slug"])


def downgrade() -> None:
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_constraint("uq_publications_slug", type_="unique")
        batch_op.drop_column("slug")


def _backfill_slugs() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, headline FROM publications ORDER BY id ASC")).fetchall()

    assigned: set[str] = set()
    for row in rows:
        slug = _generate_slug_for_backfill(row.id, row.headline, assigned)
        assigned.add(slug)
        bind.execute(
            sa.text("UPDATE publications SET slug = :s WHERE id = :i"),
            {"s": slug, "i": row.id},
        )


def _generate_slug_for_backfill(pub_id: int, headline: str | None, assigned: set[str]) -> str:
    base = slugify(headline or "", max_length=MAX_SLUG_LEN)
    if not base or len(base) < MIN_SLUG_BODY_LEN:
        return f"publication-{pub_id}"  # id-based fallback (never collides)

    blocked = assigned | RESERVED_SLUGS
    if base not in blocked:
        return base

    for n in range(2, 100):
        candidate = f"{base}-{n}"
        if candidate not in blocked:
            return candidate

    raise RuntimeError(
        f"Slug collision exhausted for id={pub_id}, headline={headline!r}; manual intervention required."
    )
```

Locked decisions:
1. Single revision bundle (add → backfill → enforce) for atomicity and clean rollback behavior.
2. Python-loop backfill (not pure SQL) because transliteration + normalization + suffix loop are application-level semantics.
3. `ORDER BY id ASC` for deterministic assignment and deterministic reruns when input headlines are unchanged.
4. Named unique constraint (`uq_publications_slug`) for explicit downgrade drop path.
5. Empty/short fallback ratified as `f"publication-{id}"` (Q-2.2.0.5-7 handling choice): globally unique, deterministic, debuggable.
6. Migration duplicates `MAX_SLUG_LEN`, `MIN_SLUG_BODY_LEN`, `RESERVED_SLUGS` intentionally: Alembic revisions are immutable records and must not import mutable runtime constants.

### B3. Backfill edge cases

| Scenario | Handling |
|---|---|
| Empty publications table | Loop is no-op; ALTER NOT NULL + UNIQUE succeed vacuously |
| Single publication, normal headline | Slug from headline, no collision |
| Two publications with identical headline | First gets bare slug, second gets `-2` |
| 99 publications with identical headline | Suffixes `-2` through `-99` exhaust; 99th publication reaches limit |
| 100 publications with identical headline | Backfill RAISES — manual intervention (founder edits headlines pre-migration) |
| Publication with empty/null headline | Fallback to `f"publication-{id}"` (per §B2 decision 5) |
| Publication with only-punctuation headline ("!!!") | After slugify produces "" → fallback to `f"publication-{id}"` |
| Publication with non-Latin headline (e.g., Ukrainian) | Transliterates via `python-slugify` default (text-unidecode); produces ASCII slug |
| Publication with reserved-path headline ("Admin") | Slugifies to "admin" → reserved → unified algo returns `admin-2` |
| Composite uniq `uq_publication_lineage_version` | Untouched — backfill writes only to `slug`, leaves 3-tuple constraint and its columns alone (§A6 scope lock) |

### B4. Rollback safety + ops note

`downgrade()` drops the unique constraint and slug column; data loss is total but recoverable by re-running upgrade. With unchanged headline data and stable id ordering, regenerated slugs are deterministic. If headlines are edited between downgrade and re-upgrade, slug values can differ.

Operationally this is more sensitive than lineage_key rollback. Slug is the URL path itself (`/p/{slug}`), so slug drift after down->up can produce dead inbound links, bookmarks, and SEO breakage. Therefore migration docstring and release ops notes should treat this as one-way in production once slug URLs are public.

Practical rule: downgrade path exists for dev/staging recovery. Production downgrade is discouraged after Phase 2.2 frontend distribution kit exposes slug links.

### B5. What is NOT changed in Chunk B (deferred to C/D)

| Surface | Status |
|---|---|
| `Publication` ORM model `slug` field declaration | Chunk C — Chunk B only specifies migration column; ORM declaration is deferred |
| `services/publications/lineage.py` runtime `generate_slug` / `derive_clone_slug` implementations | Chunk C — Chunk B documents migration semantics only |
| `services/publications/exceptions.py` new exceptions (`PublicationSlugGenerationError`, `PublicationSlugCollisionError`) | Chunk C — referenced conceptually only |
| `repositories/publication_repository.py` constructor sites | Chunk C |
| `services/publications/clone.py` `_COPY_PREFIX` strip integration | Chunk C |
| `api/routers/admin_publications.py` slug surface in PublicationResponse | Chunk C |
| `PublicationCreate` / `PublicationUpdate` schema fields | Chunk C (Q-2.2.0.5-9 PublicationUpdate immutability) |
| `make_publication` factory default | Chunk D (Q-2.2.0.5-8) |
| Migration tests + backfill regression tests | Chunk D |
| DEBT.md entry text + ID assignment | Chunk D |
| ROADMAP_DEPENDENCIES.md Phase 2.2.0.5 row | Chunk D |
| Frontend `/p/${slug}` route handler verification | Chunk D (per §A5 trailing note) |

Scope lock: Chunk C covers schema + service callers + immutability enforcement. Chunk D covers tests + DEBT + roadmap.

## C. Service layer changes

**What's here:** new exceptions in `exceptions.py`, runtime generators in `lineage.py`, repository-layer slug computation (X2 lock), and service-layer caller integration in `admin_publications.py` and `clone.py`.

**Source files cited:** `lineage.py`, `exceptions.py`, `publication_repository.py`, `clone.py`, `admin_publications.py`, pre-recon §A2/§A3/§B/§D/§E.

### C1. New exceptions in `exceptions.py`

Inventory confirms the base pattern is `PublicationApiError(HTTPException)` with class attributes (`status_code_value`, `error_code`, `message`) and optional `details` payload via base `__init__`. New slug exceptions must inherit this same pattern, not pass `status_code`/`detail` directly.

```python
from src.services.publications.lineage import MIN_SLUG_BODY_LEN


class PublicationSlugGenerationError(PublicationApiError):
    """Slug body empty/too short after slugification."""

    status_code_value = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "PUBLICATION_SLUG_GENERATION_FAILED"
    message = (
        f"headline produces empty/short slug body "
        f"(min={MIN_SLUG_BODY_LEN} chars)."
    )

    def __init__(self, *, headline: str) -> None:
        super().__init__(details={"headline": headline})


class PublicationSlugCollisionError(PublicationApiError):
    """Slug suffix space -2..-99 exhausted."""

    status_code_value = status.HTTP_409_CONFLICT
    error_code = "PUBLICATION_SLUG_COLLISION_EXHAUSTED"
    message = "Slug collision suffix range exhausted; rename headline."

    def __init__(self, *, base_slug: str, attempts: int) -> None:
        super().__init__(details={"base_slug": base_slug, "attempts": attempts})
```

Status mapping rationale: 422 matches existing payload-invalid semantics; 409 matches existing conflict semantics (`PublicationCloneNotAllowedError`). `MIN_SLUG_BODY_LEN` source of truth remains runtime constant in `services/publications/lineage.py`.

### C2. ORM model addition in `models/publication.py`

`slug` should be inserted immediately after `lineage_key` and before `status` (identity-related cluster). Locked declaration:

```python
slug: Mapped[str] = mapped_column(
    String(length=200),
    nullable=False,
    unique=True,
    doc="Per-row public URL identity; immutable post-create. Phase 2.2.0.5.",
)
```

Why both ORM `unique=True` and migration named unique constraint: ORM metadata consistency vs migration-time explicit DB constraint lifecycle (`create_unique_constraint`/drop by name). No explicit `Index(...)` needed because UNIQUE implies index.

### C3. Runtime generators in `services/publications/lineage.py`

Append new slug helpers after existing `derive_clone_lineage_key` (current line ~145). No name clashes in current module.

```python
from slugify import slugify as _slugify_lib

from src.services.publications.exceptions import (
    PublicationSlugCollisionError,
    PublicationSlugGenerationError,
)

MAX_SLUG_LEN: int = 196
MIN_SLUG_BODY_LEN: int = 3
RESERVED_SLUGS: frozenset[str] = frozenset({
    "_next", "static", "api", "_error", "404", "500",
    "admin", "p", "about", "privacy", "terms", "login", "signup", "logout",
    "health", "robots", "sitemap", "favicon",
    "summa", "summa-vision",
    "search", "feed", "rss", "atom",
})

_COPY_PREFIX = "Copy of "  # mirror clone.py:21; keep in sync (Chunk D test gate)


def _slugify_internal(text: str) -> str:
    """Pure slugify transform only (no collision / reserved logic)."""
    return _slugify_lib(text or "", max_length=MAX_SLUG_LEN)


def generate_slug(headline: str, *, existing_slugs: set[str] | None = None) -> str:
    """Generate final slug from headline using §A3+§A4+§A5 rules.

    Pure function: no DB access; caller injects collision context.
    """
    base = _slugify_internal(headline)
    if not base or len(base) < MIN_SLUG_BODY_LEN:
        raise PublicationSlugGenerationError(headline=headline)

    blocked = (existing_slugs or set()) | RESERVED_SLUGS
    if base not in blocked:
        return base

    for n in range(2, 100):
        candidate = f"{base}-{n}"
        if candidate not in blocked:
            return candidate

    raise PublicationSlugCollisionError(base_slug=base, attempts=99)


def derive_clone_slug(
    source: "Publication",
    *,
    existing_slugs: set[str] | None = None,
) -> str:
    """Generate fresh clone slug after stripping one `_COPY_PREFIX` if present."""
    headline = source.headline or ""
    if headline.startswith(_COPY_PREFIX):
        headline = headline[len(_COPY_PREFIX):]
    return generate_slug(headline, existing_slugs=existing_slugs)
```

Decisions: `_COPY_PREFIX` duplicated intentionally (avoid cross-module coupling; sync test deferred to Chunk D). `_slugify_internal` exists for testability and purity boundary. `existing_slugs` optional supports first-row/test contexts. Forward reference `
