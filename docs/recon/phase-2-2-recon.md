# Phase 2.2 Recon — Publish Kit Generator

**Status:** Recon-proper IN PROGRESS — Chunk A complete, Chunks B/C/D pending
**Author:** Claude Code (architect agent)
**Date:** 2026-04-29
**Pre-recon source:** `docs/recon/phase-2-2-pre-recon.md` (COMPLETE 2026-04-28)
**Adjacent:** `docs/recon/phase-2-2-0-recon.md` (Phase 2.2.0 backend infra, MERGED)

## Context

Phase 2.2 ships the Publish Kit Generator: extends Phase 2.1 ZIP export
to additionally include `distribution.json` and `publish_kit.txt`
artifacts inside the ZIP, with platform-specific captions
(Reddit / X / LinkedIn) and UTM-tagged URLs encoding
`?utm_content=<lineage_key>`.

This recon-proper consumes pre-recon factual inventory and produces
architectural decisions + open founder questions for design ambiguities.

**Recon chunks:**
- §A: Q-2.2 lock-in verification + utm.ts module shape + 2 open Qs (this PR)
- §B: templates.ts + builder.ts caption design (TBD — Chunk B)
- §C: kit.ts ZIP wiring + manifest extension (TBD — Chunk C)
- §D: test strategy + DEBT entries + glossary (TBD — Chunk D)

**Phase 2.2.0 status reminder:** lineage_key infrastructure SHIPPED.
- Column on Publication, NOT NULL, indexed
- `generate_lineage_key()` + `derive_clone_lineage_key(source)` in
  `backend/src/services/publications/lineage.py`
- `lineage_key: str` field on `PublicationResponse`
- All 4 production constructor sites populate it

## A. Q-2.2 lock-in summary + utm.ts module design

**What's here:** verbatim founder-locked decisions for 6 of 8 questions
(Q-D + Q-2.2-1, 2, 3, 4, 6, 8), plus design proposal for the
`distribution/utm.ts` module that ships in Phase 2.2 PR#1.

Two questions remain open and are surfaced to founder at the end of
this section: Q-2.2-5 (publish_kit.txt format), Q-2.2-7 (character
limits per platform). Recon-proper Chunk B is **blocked on Q-2.2-7
resolution** because templates and validator behaviour depend on the
chosen approach. Q-2.2-5 has lower coupling but should resolve before
Chunk C (kit.ts assembles the publish_kit.txt content).

**Source files cited:** pre-recon §F (questions), pre-recon §B/C
(inventory), Phase 2.2.0 recon §A/D (lineage_key contracts).

### A1. Locked decisions table

The following are founder-locked. No re-design surface in this PR.

| Question | Locked answer | Rationale | Implication for design |
|---|---|---|---|
| Q-D | `utm_content = lineage_key` | Per-publication tracking; lineage_key aggregates clones | UTM URL builder reads `publication.lineage_key`, no other UTM source |
| Q-2.2-1 | (a) explicit column on Publication, split into Phase 2.2.0 sub-PR | Stable cross-version identity per `lineage_key` semantic | Phase 2.2 frontend assumes `lineage_key: string` available in `PublicationResponse` (already shipped) |
| Q-2.2-2 | (a) UUID v7 | Globally unique + time-sortable | URL aesthetic: 36-char hyphen-segmented; not human-readable but operator-debuggable via timestamp prefix |
| Q-2.2-3 | (a) `NEXT_PUBLIC_SITE_URL` env var | Deploy-time constant; standard Next.js pattern | Phase 2.2 PR#1 adds env entry; URL builder reads `process.env.NEXT_PUBLIC_SITE_URL` |
| Q-2.2-4 | (a) Separate `distribution.json` with own `schemaVersion: 1` | Independent evolution from manifest.json | Chunk C designs schema; manifest.json untouched (no schemaVersion bump) |
| Q-2.2-6 | (a) Hardcoded EN templates in `templates.ts` module | Captions are content (editorial voice), not UI | Chunk B designs templates module; not in next-intl `messages/*.json` |
| Q-2.2-8 | (a) `frontend-public/src/components/editor/distribution/utm.ts` | New `distribution/` namespace, future-proof for Phase 2.3+ | This PR (Chunk A §A2) designs utm.ts; sibling files in Chunks B/C |

### A2. `distribution/utm.ts` module design

The first concrete file Phase 2.2 PR#1 ships. Owns UTM URL composition
for caption builders (Chunk B) and any future per-publication share-link
surface (e.g. operator copy-button on /jobs page, deferred).

**File path:** `frontend-public/src/components/editor/distribution/utm.ts`

**Imports (no cycles):**

```typescript
// Reads PublicationResponse type — already exists post-Phase-2.2.0
import type { PublicationResponse } from "@/lib/api/admin";
// Reads PlatformId for utm_medium/utm_source mapping
import type { PlatformId } from "@/components/editor/types";
```

**No imports from `editor/export/`** — this module is consumed by
caption builders and ZIP wiring, never the reverse. Layering:
`distribution/` is below `export/` (consumed by, never consumes from).

**Public API:**

```typescript
/**
 * UTM tracking parameters per platform, locked to Q-D contract.
 *
 * Q-D (2026-04-27): utm_content carries lineage_key only.
 * Q-2.2-3 (locked): site URL via NEXT_PUBLIC_SITE_URL.
 *
 * utm_source = platform name (lowercase): 'reddit' | 'twitter' | 'linkedin'
 * utm_medium = 'social' (single value, all platforms)
 * utm_campaign = 'publish_kit' (Phase 2.2 distinct from organic share)
 * utm_content = publication.lineage_key (per Q-D)
 */
export interface UtmParams {
  source: "reddit" | "twitter" | "linkedin";
  medium: "social";
  campaign: "publish_kit";
  content: string; // lineage_key, UUID v7
}

/**
 * Build a fully-tagged share URL for a publication on a given platform.
 *
 * Resolution order for the base URL:
 * 1. process.env.NEXT_PUBLIC_SITE_URL (Q-2.2-3 locked)
 * 2. Throw configuration error — no localhost fallback to avoid
 *    leaking dev URLs to publish kits
 *
 * Slug derivation: pre-recon §B3 confirms publication has a routable
 * public path. Frontend pattern is `${baseUrl}/p/${slug}` per pre-recon
 * Q-2.2-3 recommendation context. Slug source: TBD in Chunk B (depends
 * on which PublicationResponse field carries the URL slug — pre-recon
 * §B4 noted slug not yet wired). For now utm.ts accepts slug as input
 * to avoid coupling.
 *
 * @param slug - URL slug for the publication path
 * @param lineageKey - publication.lineage_key (from PublicationResponse)
 * @param platform - which platform (reddit/twitter/linkedin)
 * @returns absolute URL with UTM query string
 * @throws ConfigError if NEXT_PUBLIC_SITE_URL not set
 *
 * Example:
 *   buildShareUrl("inflation-may-2026", "01923f9e-3c12-7c7e-...", "reddit")
 *   → "https://summa.vision/p/inflation-may-2026?utm_source=reddit
 *      &utm_medium=social&utm_campaign=publish_kit
 *      &utm_content=01923f9e-3c12-7c7e-..."
 */
export function buildShareUrl(
  slug: string,
  lineageKey: string,
  platform: UtmParams["source"]
): string;

/**
 * Smaller helper for testing + reuse: build the UTM query string only,
 * without base URL or path. Useful for unit tests and any consumer
 * that already has a base URL.
 *
 * @returns query string starting with '?', URL-encoded values
 */
export function buildUtmQuery(params: UtmParams): string;

/**
 * Configuration error class — distinct type for callers to catch
 * specifically. Caption builder MUST surface this as a hard error
 * (not silently render unbranded URL).
 */
export class UtmConfigError extends Error {
  constructor(message: string);
}
```

**Behaviour notes:**

1. **PlatformId mapping:** the existing `PlatformId` union in
   `frontend-public/src/components/editor/types.ts` (per pre-recon §C1)
   uses `'reddit' | 'twitter' | 'linkedin'` — utm.ts can reuse the type
   instead of redefining. Use `import type { PlatformId } from "../types"`
   and define `UtmParams.source` as `PlatformId`.

2. **URL construction order:** must use `URL` + `URLSearchParams` constructors,
   not string concatenation. Reasons: proper encoding of `lineage_key` (dashes
   are safe but defensive coding); resilience against future slug containing
   reserved characters.

3. **Order of UTM params:** preserve the order
   `utm_source → utm_medium → utm_campaign → utm_content` as written by
   `URLSearchParams` insertion order. This is purely cosmetic but
   matches Google Analytics convention and produces stable test
   snapshots.

4. **No persistence, no globals:** module is pure functions plus one
   error class. No module-level state, no caches, no `let` exports.
   Aligns with editor architectural conventions.

5. **Error contract:**
   - Missing NEXT_PUBLIC_SITE_URL → `UtmConfigError`, never silently
     fallback. Caller (caption builder, Chunk B) must catch and surface.
   - Empty/null `lineageKey` → `UtmConfigError` (defensive: lineage_key
     is required post-Phase-2.2.0; null indicates upstream contract
     violation).
   - Empty/null `slug` → `UtmConfigError` similarly.

**What this module does NOT do (out of Chunk A scope, deferred to other chunks):**

- Caption text composition (Chunk B — templates.ts + builder.ts)
- Slug source resolution (Chunk B — depends on PublicationResponse
  field choice)
- Bulk URL building for multiple platforms (Chunk B will introduce
  a per-platform iterator that calls `buildShareUrl` 3x)
- distribution.json output assembly (Chunk C)
- ZIP entry wiring (Chunk C)
- Test infrastructure (Chunk D)

### A3. Open questions for founder (2 remaining)

#### Q-2.2-5 — `publish_kit.txt` format

**Status:** OPEN — pre-recon recommended (a) but founder did not
explicitly lock.

**Question:** `publish_kit.txt` is plain text that operator copy-pastes
into Reddit/X/LinkedIn. What's the structure inside?

**Options (from pre-recon F-Q-2.2-5):**

- **(a)** Plain text with `===` channel separators:
  ```
  === Reddit ===
  <title line>
  <body, multi-paragraph allowed>

  === X / Twitter ===
  <single-paragraph caption>

  === LinkedIn ===
  <multi-paragraph caption>
  ```
  Pros: language-neutral, no parser needed, scrolling works trivially.
  Cons: visual cue weaker than headings.

- **(b)** Markdown headings:
  ```
  ## Reddit
  Title line

  Body paragraph one.
  Body paragraph two.

  ## X / Twitter
  ...
  ```
  Pros: renders nicely in any markdown viewer, copy-paste from
  rendered view works.
  Cons: operator pastes raw text into Reddit/X/LinkedIn — the
  `## ` prefix is noise to filter out.

- **(c)** Per-channel separate files inside the ZIP:
  ```
  reddit.txt
  twitter.txt
  linkedin.txt
  ```
  Pros: clean per-channel copy, no scrolling, no scanning for
  the right `===` block.
  Cons: ZIP layout grows; operator opens 3 files instead of 1.

**Recon-proper assessment:**

Pre-recon recommended (a). The recon-proper analysis still favours
(a), with one refinement worth raising: if the operator workflow
involves opening the ZIP, scanning past PNG previews, and finding
the txt file — having all captions in one place reduces friction.
Multiple txt files (option c) trade scrolling for file-open overhead.

**Open dimensions for founder:**

1. Does operator workflow involve ZIP opening (yes per Phase 2.2 DoD)
   or copy-paste from a rendered view in some future UI?
2. Should the format be designed to support adding a 4th platform
   later (e.g. Threads, Bluesky)? All three options support this
   trivially; not a deciding factor.
3. Is there a content-marketing brand-team review step where the
   `publish_kit.txt` is shared as a single artifact? If yes, (a) or
   (b) wins; (c) makes "share for review" awkward.

**Pre-recon recommendation:** (a). **Recon-proper recommendation:**
(a) with explicit blank line between `===` block end and next
`===` start to make scanning easier. Founder ratifies or chooses
(b)/(c).

**Decision needed before:** Chunk C (kit.ts assembles the .txt
content). Chunk B can proceed without this answer since templates.ts
returns per-platform caption strings; format is the
`assembly` step.

---

#### Q-2.2-7 — character limits per platform

**Status:** OPEN — pre-recon explicitly noted "no recommendation;
founder UX decision."

**Question:** Reddit/X/LinkedIn each enforce caption length limits.
Does the export pipeline enforce, warn, or document?

**Platform limits (per pre-recon F-Q-2.2-7):**

| Platform | Limit | Notes |
|---|---|---|
| X (Twitter) | 280 chars (free) / 4000 chars (paid) | Free tier dominant for B2B audience |
| Reddit | Title: 300 chars; Body: 40,000 chars | Title is the primary length risk |
| LinkedIn | Post: 3000 chars | Comfortable for most captions |

**Options:**

- **(a) Cap at template generation time, with `[truncated]` indicator:**
  Caption builder produces, say, 350-char text; output truncated to
  277 + `...` for X. Operator pastes truncated output, may not notice.
  Pros: ZIP always ships valid-length captions.
  Cons: silent destructive transformation; operator may post
  half-meaning caption.

- **(b) Document the limit but don't truncate:**
  Caption builder produces full-length text; ZIP ships it raw.
  publish_kit.txt may include a comment line per channel
  (`# X limit: 280 chars; current: 312 — manual edit required`).
  Operator decides what to cut.
  Pros: operator-respecting; no destructive automation.
  Cons: operator must manually edit before posting; adds workflow
  step.

- **(c) Validation rule that warns BEFORE export (pre-flight check):**
  When operator clicks Export, validator runs caption-length check
  per platform. If overflow detected, show modal: "X caption is
  312 chars, limit 280. Edit headline or proceed anyway." Operator
  picks proceed (and pastes operator-edits later) or back-to-edit
  (and shortens headline).
  Pros: catches at edit time, before ZIP ships; matches editor's
  existing validation pattern.
  Cons: validator surface grows; adds modal.

**Recon-proper assessment of trade-off:**

Phase 2.1 already has a validator/preflight surface
(`validatePresetSize`, the size-skip pattern in `zipExport.ts:86-99`,
per pre-recon §A1). Adding caption-length check to that surface is
**low marginal cost** infrastructure-wise. The UX cost is the modal
or warning row.

Counter-consideration: caption captions are wrapped around publication
fields (headline, source_text, etc) which the operator already controls
in the editor. If the operator's headline is too long, ALL platforms
inherit the issue. (c) gives the operator a single chance to shorten
the headline rather than 3 separate decisions per platform.

**The trade-off depends on founder's view of operator competence:**

- If operators are content-savvy and will edit captions themselves
  pre-posting → (b) is fine; trust the operator
- If operators are speed-focused and want "ZIP → paste → done" flow
  → (a) (silent truncate) gets shipped at QA cost, OR (c) (pre-flight)
  prevents at edit time

**Recon-proper recommendation:** **(c) pre-flight validation** with
**non-blocking** behaviour by default. Validator warns "X caption
will be 312 chars (limit: 280). Operator may proceed anyway or
return to editor."

Rationale:
1. Reuses Phase 2.1's existing validator/preflight surface
2. Operator gets one chance to fix at headline-edit time, not
   per-platform
3. Non-blocking respects operator autonomy (LinkedIn often actually
   wants longer captions; X strictly capped — let operator decide)
4. Caption builder remains pure (no truncation logic), preserving
   single-responsibility

**Decision needed before:** Chunk B (templates.ts/builder.ts) — caption
builder behaviour depends on truncate vs not. **Chunk B is BLOCKED on
Q-2.2-7 resolution.**

If founder picks (a), Chunk B adds truncation logic.
If founder picks (b), Chunk B emits raw + adds limit comment lines.
If founder picks (c), Chunk B emits raw, Chunk C adds validator hook,
new validation rule lives in `validation/captionLength.ts` (sibling to
existing rules).

### A4. §A summary

**What this section produced:**
1. Lock-in table for 6 founder-locked questions (Q-D, Q-2.2-1, 2, 3,
   4, 6, 8)
2. Concrete utm.ts module shape (interfaces, public API, error
   contract, behavior rules) for impl-agent consumption
3. Two open founder questions surfaced (Q-2.2-5, Q-2.2-7)

**What ships in Phase 2.2 PR#1 from this section:**
- `frontend-public/src/components/editor/distribution/utm.ts` (NEW)
- env config for NEXT_PUBLIC_SITE_URL (depends on §B/C wiring details)

**Block on next chunks:**
- Chunk B (templates.ts + builder.ts): **BLOCKED on Q-2.2-7**
- Chunk C (kit.ts + manifest extension): blocked on Q-2.2-5 by Chunk C
  start; can proceed pre-Q-2.2-5 for ZIP entry list design
- Chunk D (tests + DEBT + glossary): no blocks on open Qs

**Founder action requested:**
1. Ratify or override Q-2.2-5 (publish_kit.txt format) — pick (a), (b),
   or (c)
2. Decide Q-2.2-7 (caption length policy) — pick (a) silent truncate,
   (b) raw + document, or (c) pre-flight validate non-blocking
   (recommended)
3. Confirm Chunk B can proceed once Q-2.2-7 decision is recorded
