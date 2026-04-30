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
- Truncation interaction: §A3 Step 7 already truncates the slug body to `MAX_SLUG_LEN = 196`, reserving 4 chars for worst-case `-99` suffix (1 hyphen + 2 digits + 1 char headroom). The collision loop receives the base directly and uses it without further truncation; any `-NN` variant fits within the 200-char column.

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

Decisions: `_COPY_PREFIX` duplicated intentionally (avoid cross-module coupling; sync test deferred to Chunk D). `_slugify_internal` exists for testability and purity boundary. `existing_slugs` optional supports first-row/test contexts. Forward reference `"Publication"` for type hint avoids circular import (mirrors existing `derive_clone_lineage_key` pattern).

### §C4. `existing_slugs` collision context query strategy

Per X1 founder lock: full table scan. Query lives in `publication_repository.py`.

```python
async def _get_existing_slugs(self, session: AsyncSession) -> set[str]:
    """Fetch all publication slugs for collision context.

    Performance: full scan acceptable at <10k rows. Postgres index-only
    scan on uq_publications_slug; ~50ms at projected 2026 prod scale.

    Future optimization (deferred): if scale exceeds 10k rows, replace
    with prefix-filtered query (SELECT slug FROM publications WHERE slug LIKE :prefix).

    Per ARCH-DPEN-001: session injected via constructor DI, not module-global.
    """
    result = await session.execute(sa.select(Publication.slug))
    return {row for row in result.scalars().all() if row is not None}
```

Decisions:
- No caching in 2.2.0.5; each create call re-queries.
- This is the ONLY new DB query introduced by Chunk C; all other slug logic is pure (per §A2 ARCH-PURA-001 contract).
- Defensive `if row is not None` filter handles migration-window NULL transients.

---

### §C5. Repository layer changes — `publication_repository.py`

**Inventory verification (paste output in Summary Report):**

```bash
grep -n "Publication(\|^    async def \|^    def " backend/src/repositories/publication_repository.py | head -30
```

Confirm 4 `Publication()` construction sites at lines 116, 167, 204, 469 (per pre-recon §D1). State actual line numbers if shifted.

| Method | Construction site | Slug computation pattern |
|---|---|---|
| `create_full` | `Publication(**payload)` style | Repo computes: `existing = await self._get_existing_slugs(session)`; `payload["slug"] = generate_slug(payload["headline"], existing_slugs=existing)` BEFORE `Publication(**payload)` |
| `create_clone` | Explicit constructor | Repo computes: `existing = await self._get_existing_slugs(session)`; `clone_slug = derive_clone_slug(source, existing_slugs=existing)`; pass into constructor as `slug=clone_slug` |
| `create_with_versioning` | Pipeline-driven, retry loop | **Per Q-CC2 lock: compute slug per retry attempt** (each retry may have different headline state). Inject as `slug=generate_slug(headline, existing_slugs=existing)` per attempt. **Q-impl-C1 flag: confirm pipeline caller does not pre-compute slug.** |
| `create` | Minimal DRAFT create | Repo computes inline. Same pattern as `create_full`. **Q-impl-C2 flag: grep audit of callers — may be legacy/test-only.** |

**Construction body change pattern** (sites 167, 204, 469):

```python
# Before:
publication = Publication(
    headline=...,
    chart_type=...,
    lineage_key=lineage_key,
    # ... existing fields ...
)
# After:
existing_slugs = await self._get_existing_slugs(session)
slug = generate_slug(headline, existing_slugs=existing_slugs)
publication = Publication(
    headline=...,
    chart_type=...,
    lineage_key=lineage_key,
    slug=slug,
    # ... existing fields ...
)
```

**Q-CC2 ratification:** in `create_with_versioning` retry loop, slug is computed per attempt because each retry may operate on different headline state and a different `existing_slugs` snapshot. The in-memory set check is essentially free; correctness wins over micro-optimization.

**Imports added to `publication_repository.py`:**

```python
from src.services.publications.lineage import (
    derive_clone_slug,
    generate_slug,
)
```

Insertion point: alphabetical, between existing `compute_config_hash` and `derive_clone_lineage_key` lineage imports.

**Divergence from Phase 2.2.0 callout:** Phase 2.2.0 lineage_key is service-computed (pure function, no DB) and passed INTO repo as kwarg. Phase 2.2.0.5 slug is repo-computed because it needs DB query for `existing_slugs`. Future readers should NOT assume parity between these two patterns.

---

### §C6. Service layer call sites

#### §C6a. Create path — `admin_publications.py`

**Per X2 lock: NO CHANGE required.**

```python
# admin_publications.py (UNCHANGED):
data = body.model_dump()
publication = await repo.create_full(data)
```

This is a divergence from Phase 2.2.0 §C3a (which adds `data["lineage_key"] = generate_lineage_key()` at service layer). For slug, the repo handles it.

#### §C6b. Clone path — `clone.py`

**Per X2 lock: NO CHANGE to clone.py for slug.**

The `_COPY_PREFIX` strip happens INSIDE `derive_clone_slug` (per §C3), not in clone.py. clone.py's `new_headline` calculation (which prepends `_COPY_PREFIX`) is unchanged.

```python
# clone.py:62 (UNCHANGED — no slug kwarg in repo call):
clone = await repo.create_clone(
    source=source,
    new_headline=new_headline,
    new_config_hash=new_config_hash,
    new_version=new_version,
    fresh_review_json=fresh_review_json,
    lineage_key=derive_clone_lineage_key(source),  # Phase 2.2.0
    # Repo computes slug internally via derive_clone_slug(source).
)
```

`source=source` is already passed to `repo.create_clone`, so repo has access for `derive_clone_slug(source)` internal call.

---

### §C7. Audit — all `Publication()` constructor sites

**Inventory verification (paste output):**

```bash
grep -rn "Publication(" backend/src/ | grep -v test | grep -v __pycache__
```

| Site | Path:line | Method | Purpose | Phase 2.2.0.5 treatment |
|---|---|---|---|---|
| 1 | `publication_repository.py:116` | `create_with_versioning` | Pipeline-driven retry loop | Repo computes slug per attempt (Q-CC2 lock). Q-impl-C1 flag (pipeline caller verification). |
| 2 | `publication_repository.py:167` | `create` | Minimal DRAFT create | Repo computes slug inline. Q-impl-C2 flag (caller audit). |
| 3 | `publication_repository.py:204` | `create_clone` | Service clone path | Repo computes via `derive_clone_slug(source)`. |
| 4 | `publication_repository.py:469` | `create_full` | Admin REST create via `Publication(**payload)` | Repo injects `payload["slug"] = generate_slug(...)` before construction. |

**Surprise sites outside repository:** state "none" or list any surprises found.

The two `models/publication.py` matches (class def + `__repr__`) are NOT constructor sites; discard from audit.

---

## D. Schema and API surface

**What's here:** `Publication{Create,Update,Response,PublicResponse}` field treatment, immutability enforcement for PublicationUpdate (Q-2.2.0.5-9), and the existing `extra="forbid"` defence chain.

**Source files cited:** `schemas/publication.py`, pre-recon §A2 (PublicationUpdate explicit class with `extra="forbid"`).

### §D1. `PublicationResponse` field add

**Inventory verification (paste output):**

```bash
grep -n "lineage_key\|^class " backend/src/schemas/publication.py
```

Confirm `lineage_key` already in `PublicationResponse` (Phase 2.2.0 added it).

```python
class PublicationResponse(BaseModel):
    # ... existing fields ...
    lineage_key: str   # Phase 2.2.0
    slug: str          # NEW — Phase 2.2.0.5; required (NOT NULL post-migration)

    model_config = ConfigDict(from_attributes=True)   # unchanged
```

- Type `str` (not `Optional[str]`): post-migration column is NOT NULL.
- No `Field(...)` constraints: server-generated, never operator-provided.
- `from_attributes=True` covers ORM→schema mapping automatically.

### §D2. `PublicationPublicResponse` — must include slug (DIVERGENCE)

**Critical divergence from Phase 2.2.0 §D2.** Phase 2.2.0 chose NOT to expose `lineage_key` on PublicationPublicResponse (analytics-internal). Slug **MUST** be exposed because public response IS used by frontend to construct `/p/${slug}` URLs.

```python
class PublicationPublicResponse(BaseModel):
    # ... existing fields ...
    headline: str
    slug: str   # NEW — Phase 2.2.0.5; public URL identity
    # NO lineage_key here (Phase 2.2.0 §D2 decision stands)
```

`lineage_key` is internal analytics, slug is public URL — opposite exposure decisions for opposite reasons.

### §D3. `PublicationCreate` — slug NOT in input fields

```python
class PublicationCreate(BaseModel):
    headline: str = Field(..., min_length=1, max_length=500)
    chart_type: str = Field(..., min_length=1, max_length=100)
    # ... other input fields ...
    # NO slug field — server-stamped via repo.generate_slug

    model_config = ConfigDict(extra="forbid")  # blocks operator-supplied slug
```

`extra="forbid"` is the defence (not field absence alone). Without it, an attacker POST `{"slug": "attacker", ...}` would have it silently ignored but request still passes Pydantic. With `extra="forbid"`, request fails 422 BEFORE reaching repo.

### §D4. `PublicationUpdate` — Q-2.2.0.5-9 immutability ratification

**Inventory verification (paste output):**

```bash
sed -n '161,205p' backend/src/schemas/publication.py
```

Confirm:
- `PublicationUpdate` is explicit class (not inheritance alias)
- `model_config = ConfigDict(extra="forbid")` present
- All current fields enumerated (none should be `slug`)

Immutability mechanism: `slug` is omitted from PublicationUpdate field list. Any PATCH/PUT request including `{"slug": "..."}` triggers Pydantic 422 via `extra="forbid"`. **No new validator needed.** Field absence + existing `extra="forbid"` is the enforcement.

**Verification gate (deferred to Chunk D):**
- `PATCH /api/v1/admin/publications/{id}` with `{"slug": "x"}` body → 422
- `PATCH /api/v1/admin/publications/{id}` with `{"headline": "new"}` body → 200, slug UNCHANGED in response

**UX rule — headline change does NOT regenerate slug:**

If operator PATCHes headline, slug stays. The headline-slug coupling is one-way at create time only.

> Why no auto-regenerate on headline change: breaking inbound URL stability is worse than slight slug-headline drift. If operator wants new URL identity, they should clone the publication (clone gets fresh slug per §A2 derive_clone_slug) and edit the clone, leaving the original at its public URL.

Per Q-CC3 lock: this UX rule is **NOT documented in 2.2.0.5 recon as operator-facing copy**. Phase 2.2 frontend impl prompt MUST add the operator-facing tooltip ("URL identity is immutable. Clone the publication for a new URL.") in the admin edit view.

---

## E. Scope locks for Chunk C (deferred to Chunk D + impl phase)

| Surface | Status |
|---|---|
| Migration file actual creation in `backend/migrations/versions/` | Impl phase (Chunk D specifies test fixtures, impl writes migration per §B2 spec) |
| `make_publication` factory default in `backend/tests/conftest.py:82` | Chunk D (Q-2.2.0.5-8) |
| Migration tests (upgrade, downgrade, backfill behavior) | Chunk D |
| Unit tests for `generate_slug` (Chinese transliteration, empty headline, collision exhaustion, reserved blacklist) | Chunk D |
| Unit tests for `derive_clone_slug` (`_COPY_PREFIX` strip, chained clone, `source.headline=None` defensive) | Chunk D |
| Repository tests for `_get_existing_slugs` query + integration with `create_full` / `create_clone` | Chunk D |
| Schema tests for PublicationUpdate slug rejection (422 contract per §D4) | Chunk D |
| Integration tests for end-to-end slug flow (admin POST → DB → admin GET → public GET) | Chunk D |
| `_COPY_PREFIX` cross-module sync test (lineage.py constant === clone.py constant) | Chunk D |
| DEBT.md entry text + ID assignment | Chunk D |
| ROADMAP_DEPENDENCIES.md Phase 2.2.0.5 row | Chunk D |
| Frontend `/p/${slug}` blacklist verification against `frontend/app/` route tree | Chunk D |
| Q-impl-C1 (pipeline caller for `create_with_versioning`) | Impl phase grep audit |
| Q-impl-C2 (`create()` caller audit, may be legacy/test-only) | Impl phase grep audit |
| Phase 2.2 frontend distribution kit consumer changes | Separate Phase 2.2 unblock work post-2.2.0.5 |
| Operator-facing tooltip "URL identity is immutable" (Q-CC3) | Phase 2.2 frontend impl prompt |

Chunk D covers tests + DEBT + roadmap + factory. Phase 2.2.0.5 recon is COMPLETE after Chunk D, and impl can begin.

---

### §F. Test strategy + DEBT + roadmap (Chunk D)

**What's here:** test contracts for migration / unit / repo / schema / integration layers, `make_publication` factory spec, DEBT entry, ROADMAP row, frontend blacklist verification, final Q-impl audit list, and recon-complete sign-off.

**Source files cited:** `backend/tests/conftest.py`, `DEBT.md`, `docs/architecture/ROADMAP_DEPENDENCIES.md`, `frontend/app/` route tree.

#### §F1. Migration tests

Test file: `backend/tests/migrations/test_phase_2_2_0_5_slug_migration.py` (new file).

Test contracts:

| Test name | Asserts |
|---|---|
| `test_upgrade_adds_slug_column` | After upgrade, `publications.slug` column exists, type VARCHAR(200), NOT NULL, UNIQUE constraint `uq_publications_slug` present |
| `test_upgrade_backfills_existing_rows` | Pre-populate 5 publications with various headlines (English, Ukrainian, Chinese, empty, only-punctuation), upgrade, assert all rows have NOT NULL slug values matching expected slugify output |
| `test_upgrade_handles_collision_in_backfill` | Pre-populate 3 rows with identical headline "Same Title", upgrade, assert slugs are `same-title`, `same-title-2`, `same-title-3` |
| `test_upgrade_empty_headline_fallback` | Pre-populate row with `headline=""` and id=42, upgrade, assert slug = `publication-42` |
| `test_upgrade_only_punctuation_headline_fallback` | Pre-populate row with `headline="!!!"` and id=99, upgrade, assert slug = `publication-99` |
| `test_upgrade_99_collisions_succeeds` | Pre-populate 99 rows with identical headline, upgrade, assert all assigned bare → `-2` → ... → `-99` |
| `test_upgrade_100_collisions_raises` | Pre-populate 100 rows with identical headline, upgrade raises `RuntimeError` with "manual intervention required" message |
| `test_downgrade_drops_slug_column_and_constraint` | Upgrade then downgrade, assert column gone, constraint gone |
| `test_downgrade_then_upgrade_idempotent_with_same_data` | Upgrade, downgrade, upgrade again, assert same slug values (deterministic backfill via id-ASC ordering) |

Fixture pattern: use existing `subprocess.run(['alembic', 'upgrade', 'head'])` pattern from memory entry "integration test fixtures must use subprocess.run". Teardown via `alembic downgrade base` (memory entry: drops PostgreSQL enum types correctly).

#### §F2. Unit tests for `generate_slug`

Test file: `backend/tests/services/publications/test_lineage_slug.py` (new file).

Test contracts:

| Test name | Asserts |
|---|---|
| `test_generate_slug_basic_ascii` | `generate_slug("Canada GDP Q3 2026")` returns `"canada-gdp-q3-2026"` |
| `test_generate_slug_ukrainian_transliteration` | `generate_slug("Інфляція в Україні")` returns ASCII-only slug matching expected python-slugify transliteration |
| `test_generate_slug_chinese_transliteration` | `generate_slug("中国GDP增长")` returns ASCII-only slug; record actual library output as the test expectation (TODO from §A3 worked examples) |
| `test_generate_slug_empty_headline_raises` | `generate_slug("")` raises `PublicationSlugGenerationError` |
| `test_generate_slug_too_short_raises` | `generate_slug("ab")` raises `PublicationSlugGenerationError` (body < 3 chars) |
| `test_generate_slug_only_punctuation_raises` | `generate_slug("!!!")` raises `PublicationSlugGenerationError` |
| `test_generate_slug_no_collision_returns_bare` | `generate_slug("Canada GDP", existing_slugs=set())` returns `"canada-gdp"` |
| `test_generate_slug_one_collision_returns_dash_2` | `generate_slug("Canada GDP", existing_slugs={"canada-gdp"})` returns `"canada-gdp-2"` |
| `test_generate_slug_collision_chain` | `existing_slugs={"canada-gdp", "canada-gdp-2", "canada-gdp-3"}` returns `"canada-gdp-4"` |
| `test_generate_slug_99_collisions_returns_dash_99` | existing_slugs containing bare + `-2`..`-98` returns `"canada-gdp-99"` |
| `test_generate_slug_100_collisions_raises` | existing_slugs containing bare + `-2`..`-99` raises `PublicationSlugCollisionError` with `attempts=99` |
| `test_generate_slug_reserved_admin_returns_dash_2` | `generate_slug("Admin", existing_slugs=set())` returns `"admin-2"` (reserved → unified collision algo) |
| `test_generate_slug_reserved_collides_with_existing` | `generate_slug("Admin", existing_slugs={"admin-2"})` returns `"admin-3"` |
| `test_generate_slug_truncation_at_max_len` | `generate_slug(<200-char headline>)` returns slug body truncated to 196 chars |
| `test_generate_slug_does_not_touch_db` | Test runs without DB session; raises no DB-related errors (purity contract per §A2 ARCH-PURA-001) |

#### §F3. Unit tests for `derive_clone_slug`

Test contracts:

| Test name | Asserts |
|---|---|
| `test_derive_clone_slug_strips_copy_prefix` | source.headline=`"Copy of Canada GDP"`, derive_clone_slug returns slug from `"Canada GDP"` (prefix stripped before slugify) |
| `test_derive_clone_slug_no_prefix_returns_normal_slug` | source.headline=`"Canada GDP"` (no prefix), derive_clone_slug returns same as `generate_slug("Canada GDP")` |
| `test_derive_clone_slug_chained_clone_strips_one_prefix` | source.headline=`"Copy of Copy of A"`, returns slug from `"Copy of A"` (only one prefix stripped per §A2 chained-clone edge case) |
| `test_derive_clone_slug_none_headline_defensive` | source.headline=`None`, returns slug from empty string OR raises `PublicationSlugGenerationError` (state which behavior is correct based on §C3 implementation) |
| `test_derive_clone_slug_collision_with_source_slug` | source.slug=`"canada-gdp"`, existing_slugs={"canada-gdp"}, derive_clone_slug returns `"canada-gdp-2"` (clone never inherits source.slug per §A2 fresh-slug rule) |

#### §F4. Repository tests

Test file: `backend/tests/repositories/test_publication_repository_slug.py` (new file).

Test contracts:

| Test name | Asserts |
|---|---|
| `test_get_existing_slugs_empty_db` | Empty publications table, `_get_existing_slugs()` returns `set()` |
| `test_get_existing_slugs_returns_all` | Insert 3 publications with slugs `a`, `b`, `c`, `_get_existing_slugs()` returns `{"a", "b", "c"}` |
| `test_get_existing_slugs_filters_none` | Insert row with `slug=None` (migration-window simulation), `_get_existing_slugs()` excludes it |
| `test_create_full_assigns_slug_from_headline` | `create_full({"headline": "Canada GDP", ...})` returns Publication with `slug == "canada-gdp"` |
| `test_create_full_collision_assigns_dash_2` | Pre-create publication with slug `canada-gdp`, `create_full({"headline": "Canada GDP"})` returns slug `canada-gdp-2` |
| `test_create_full_rejects_slug_in_payload` | `create_full({"slug": "attacker", "headline": "X"})` — but this should be blocked at PublicationCreate schema level (`extra="forbid"`); test schema rejection, not repo behavior |
| `test_create_clone_assigns_fresh_slug` | Source publication with slug `canada-gdp`, clone returns Publication with slug `canada-gdp-2` (NOT inherited per §A2) |
| `test_create_clone_strips_copy_prefix_in_slug` | Source headline `"Canada GDP"`, clone headline `"Copy of Canada GDP"`, clone slug = `canada-gdp-2` (prefix stripped, then collision suffix) |
| `test_create_published_assigns_slug_per_attempt` | (Site 116 in repo audit) Q-CC2: simulate retry loop, assert slug computed per attempt |

#### §F5. Schema tests

Test file: `backend/tests/schemas/test_publication_slug_schema.py` (new file).

Test contracts:

| Test name | Asserts |
|---|---|
| `test_publication_create_rejects_slug_field` | `PublicationCreate(headline="X", chart_type="bar", slug="forbidden")` raises Pydantic ValidationError with `extra="forbid"` |
| `test_publication_update_rejects_slug_field` | `PublicationUpdate(slug="x")` raises Pydantic ValidationError with `extra="forbid"` (Q-2.2.0.5-9 immutability) |
| `test_publication_response_includes_slug` | `PublicationResponse(...)` from ORM Publication has `slug` field as str, NOT optional |
| `test_publication_public_response_includes_slug` | `PublicationPublicResponse(...)` from ORM Publication has `slug` field exposed (DIVERGENCE from lineage_key) |
| `test_publication_public_response_excludes_lineage_key` | `PublicationPublicResponse` does NOT have `lineage_key` field (Phase 2.2.0 §D2 stand-up preserved) |

#### §F6. Integration tests

Test file: `backend/tests/integration/test_slug_e2e.py` (new file).

Test contracts:

| Test name | Asserts |
|---|---|
| `test_admin_post_assigns_slug` | `POST /api/v1/admin/publications {"headline": "X", ...}` → 201, response includes slug |
| `test_admin_get_returns_slug` | After POST, `GET /api/v1/admin/publications/{id}` → slug present in PublicationResponse |
| `test_public_get_by_slug_returns_publication` | `GET /api/v1/public/p/{slug}` → 200 with PublicationPublicResponse including slug |
| `test_public_get_by_slug_404_for_unknown` | `GET /api/v1/public/p/nonexistent` → 404 |
| `test_admin_patch_slug_returns_422` | `PATCH /api/v1/admin/publications/{id} {"slug": "x"}` → 422 (Q-2.2.0.5-9) |
| `test_admin_patch_headline_does_not_regenerate_slug` | `PATCH /api/v1/admin/publications/{id} {"headline": "new"}` → 200, slug UNCHANGED in response (UX rule per §D4) |
| `test_clone_via_admin_endpoint_assigns_fresh_slug` | `POST /api/v1/admin/publications/{id}/clone` → 201, clone slug differs from source slug |
| `test_reserved_slug_admin_post_returns_disambiguated` | POST headline "Admin" → response slug = `admin-2` (reserved blacklist) |

**Q-impl-D1 flag:** verify exact public endpoint path. The recon assumes `GET /api/v1/public/p/{slug}` based on `${PUBLIC_SITE_URL}/p/${slug}` URL contract from §A1, but actual backend route may differ. Impl phase confirms via `grep -rn "/p/" backend/src/api/`.

#### §F7. `_COPY_PREFIX` cross-module sync test

Test file: `backend/tests/services/publications/test_copy_prefix_sync.py` (new file, single test).

Test contract:

```
test_copy_prefix_sync:
    Asserts:
        from src.services.publications.clone import _COPY_PREFIX as clone_prefix
        from src.services.publications.lineage import _COPY_PREFIX as lineage_prefix
        assert clone_prefix == lineage_prefix
    Rationale:
        §C3 duplicates _COPY_PREFIX intentionally (Alembic-style decoupling).
        This test catches drift if either module's value changes without the other.
```

#### §F8. `make_publication` factory default — Q-2.2.0.5-8 ratification

**Inventory verification:**

```bash
sed -n '78,108p' backend/tests/conftest.py
```

Confirm `make_publication` factory at line 82 with current keyword arg pattern.

**Spec change:**

Add `slug` to factory defaults using deterministic-from-headline pattern (per Chunk A FR-2 framing):

```python
def make_publication(**overrides: Any) -> Publication:
    defaults = {
        "headline": "Test Headline",
        "chart_type": "bar",
        "lineage_key": "01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c",  # existing
        "slug": _make_test_slug(overrides.get("headline", "Test Headline")),  # NEW
        # ... other defaults ...
    }
    defaults.update(overrides)
    return Publication(**defaults)


def _make_test_slug(headline: str) -> str:
    """Deterministic test slug generator. Mirrors prod logic but with
    UUID suffix to avoid collisions across test fixtures.

    Format: <slugified-headline>-<uuid4-hex-8>
    Example: "test-headline-a3b9c7d2"
    """
    from uuid import uuid4
    base = slugify(headline or "test-publication", max_length=180)
    return f"{base}-{uuid4().hex[:8]}"
```

**Q-2.2.0.5-8 ratification:** factory uses `<slugified-headline>-<uuid8>` pattern. Mirrors prod slugify logic, no collisions across test fixtures. Tests can override via `make_publication(slug="custom")`.

**Why uuid suffix:** test fixture isolation. Multiple `make_publication()` calls in the same test session share default headline → would collide on bare slug without suffix. Per memory entry "Test isolation hides dead production plumbing — green tests ≠ working pipeline" — this protects against false-green tests.

#### §F9. DEBT entry

**Inventory verification:**

```bash
grep -nE "^DEBT-[0-9]+|^## DEBT-[0-9]+|DEBT-[0-9]{3}" DEBT.md | head -20
```

Observed max existing ID in `DEBT.md` inventory: **DEBT-047**. Assigned Phase 2.2.0.5 follow-up ID: **DEBT-048**.

**Entry text** (insert at appropriate location in DEBT.md):

```markdown
## DEBT-048 — Phase 2.2.0.5 follow-ups

**Status:** Active (recon complete, impl pending)
**Created:** 2026-04-30
**Phase:** 2.2.0.5 (post-impl tracking)
**Owner:** founder

**Scope of follow-ups (post-impl):**

1. **Q-impl-C1** — Verify `create_published` (line 80) caller does not pre-compute slug; confirm slug-per-retry pattern works correctly for graphics pipeline. Grep audit: `rg "create_published\(" backend/src/`.

2. **Q-impl-C2** — Audit callers of `create()` (line 139) repo method. May be legacy/test-only. If only tests use it, consider deprecation in a separate cleanup PR.

3. **Q-impl-D1** — Confirm public endpoint path `GET /api/v1/public/p/{slug}`. Recon assumed based on `${PUBLIC_SITE_URL}/p/${slug}` URL contract; backend route may differ.

4. **Chinese transliteration test expectation** — §F2 `test_generate_slug_chinese_transliteration` records actual python-slugify output as test expectation. Confirm the recorded output matches operator expectations (or document divergence).

5. **Frontend route blacklist verification** — §F11 confirmed reserved slug list against `frontend/app/` at recon time. Re-verify before Phase 2.2 frontend ships.

6. **`_COPY_PREFIX` sync drift** — §F7 test catches drift but does NOT prevent it. If drift occurs in either module, founder decides whether to consolidate to single source-of-truth (separate cleanup PR).

7. **DEBT-035 / DEBT-036 from Phase 2.2.0** — Verify these (if active) are not blocked by Phase 2.2.0.5 changes. Per memory entry "always re-verify DEBT.md state fresh".

8. **Migration downgrade safety** — §B4 documented that prod downgrade after Phase 2.2 frontend ships causes dead URLs. Add to release ops checklist before Phase 2.2 frontend deploys.
```

#### §F10. ROADMAP_DEPENDENCIES.md row

**Inventory verification:**

```bash
grep -nE "^\| Phase 2\.2|^### Phase 2\.2" docs/architecture/ROADMAP_DEPENDENCIES.md | head -10
```

If the Phase 2.2 table/heading is present, insert the following row between Phase 2.2.0 and Phase 2.2. If it is absent, add this row at the corresponding roadmap table in impl phase while preserving existing column count.

**Row text:**

```markdown
| Phase 2.2.0.5 | Backend slug infrastructure (column, generator, migration, schema, immutability) | Phase 2.2.0 (lineage_key) | Phase 2.2 frontend distribution kit |
```

**Dependency chain update:**

```
Phase 2.1 → Phase 2.2.0 → Phase 2.2.0.5 → Phase 2.2 (frontend C/D) → Phase 2.3
```

Document this in the chain section of ROADMAP_DEPENDENCIES.md during impl documentation pass.

#### §F11. Frontend route blacklist verification

**Inventory verification:**

```bash
ls frontend/app/ 2>/dev/null
find frontend/app -type d -maxdepth 2 -not -path '*/node_modules*' 2>/dev/null
```

Observed in this repo snapshot: `frontend/app/` is not present (`ls` exit 2; `find` exit 1). Therefore, route-to-blacklist verification cannot be completed in recon from this working tree.

Status:
- Mark `Q-impl-D3` as open for impl/frontend dispatch.
- Re-run route inventory against the actual frontend app tree before Phase 2.2 frontend ships.
- Continue to treat current §A5 reserved set as baseline; extend only after concrete route inventory confirms additional collisions.

#### §F12. Final Q-impl audit list

| Q-impl ID | Description | Resolution path |
|---|---|---|
| Q-impl-C1 | `create_published` (formerly `create_with_versioning`) caller verification | Impl phase grep audit |
| Q-impl-C2 | `create()` minimal-DRAFT caller audit (legacy/test-only?) | Impl phase grep audit |
| Q-impl-D1 | Public endpoint path `/p/{slug}` confirmation | Impl phase route inventory |
| Q-impl-D2 | Chinese transliteration exact token recording | Chunk D test fixture (§F2) |
| Q-impl-D3 | Frontend route blacklist re-verification before Phase 2.2 frontend ships | Phase 2.2 frontend dispatch |

#### §F13. Recon-complete sign-off

Phase 2.2.0.5 recon-proper is **COMPLETE**.

Chunks landed:
- Chunk A — column shape + generator interface + algorithm + collision + reserved blacklist + scope locks (§A1-§A6) — APPROVED 2026-04-30
- Chunk B — migration design + dependency add + backfill strategy + rollback + scope locks (§B1-§B5) — APPROVED 2026-04-30
- Chunk C — exceptions + ORM + runtime generators + query strategy + repo wiring + service callers + audit + schemas + immutability + scope locks (§C1-§C7, §D1-§D4, §E) — APPROVED 2026-04-30
- Chunk D — test contracts + factory + DEBT + roadmap + frontend verification + Q-impl audit (§F1-§F12) — this section

**Impl phase can begin.** Suggested impl chunk split:
1. Migration + dependency add (`backend/migrations/versions/<rev>_add_slug_to_publications.py` + pyproject.toml)
2. Exceptions + ORM + runtime generators (`exceptions.py`, `models/publication.py`, `services/publications/lineage.py`)
3. Repo wiring (`publication_repository.py` 4 sites + new `_get_existing_slugs` query)
4. Schemas (`schemas/publication.py` 4 classes)
5. Tests (per §F1-§F7 contracts) + factory update (per §F8)
6. DEBT.md + ROADMAP_DEPENDENCIES.md edits (per §F9 + §F10)

Sequential or parallel split per founder preference. Memory entry recommends: review-first workflow with explicit blocking/non-blocking categorization for each impl PR.
