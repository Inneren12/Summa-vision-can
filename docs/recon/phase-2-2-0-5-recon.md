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
| Type | `String(200)` | `headline` max is 500, but slugification compresses punctuation/spacing. A 5-headline sanity sample yields ~28, 36, 52, 71, 88 chars (avg 55). Budgeting worst-case long headline truncation + reserved/collision suffix overhead (`-99` = 3 chars; reserved disambiguation can start at `-1`) still fits safely with 200. Existing model already uses bounded strings (`lineage_key` 36; hash columns 64 class), so 200 is consistent bounded design. |
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
