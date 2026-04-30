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
- `lineage_key: str` field on `AdminPublicationResponse`
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
| Q-2.2-1 | (a) explicit column on Publication, split into Phase 2.2.0 sub-PR | Stable cross-version identity per `lineage_key` semantic | Phase 2.2 frontend assumes `lineage_key: string` available in `AdminPublicationResponse` (already shipped) |
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
// Reads AdminPublicationResponse type — already exists post-Phase-2.2.0
import type { AdminPublicationResponse } from "@/lib/types/publication";
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
 * on which AdminPublicationResponse field carries the URL slug — pre-recon
 * §B4 noted slug not yet wired). For now utm.ts accepts slug as input
 * to avoid coupling.
 *
 * @param slug - URL slug for the publication path
 * @param lineageKey - publication.lineage_key (from AdminPublicationResponse)
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
- Slug source resolution (Chunk B — depends on AdminPublicationResponse
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

## B. templates.ts + builder.ts caption design

**What's here:** design for the two modules that produce per-platform
caption text strings, plus the validation module for Q-2.2-7 (c)
pre-flight length checks.

**Founder decisions in scope:**
- Q-2.2-5 = (a) plain text === separators (publish_kit.txt format
  assembly is Chunk C; this section ensures templates return raw
  per-channel strings ready for === wrapping)
- Q-2.2-7 = (c) pre-flight non-blocking validation (this section
  designs validation surface; Chunk C wires modal UX)

**Source files cited:** Chunk A §A2 (utm.ts API), pre-recon §A1/§A4
(zipExport.ts pre-render gate pattern), pre-recon §B3 (block prop
sources for headline/source/eyebrow), pre-recon §C1 (PlatformId union).

### B1. `distribution/templates.ts` module

**File path:** `frontend-public/src/components/editor/distribution/templates.ts`

**Purpose:** holds per-platform caption template strings. Templates are
**hardcoded EN** per Q-2.2-6 lock; not in next-intl `messages/*.json`.
Templates are **content** (editorial voice), not interface labels.

**Imports (no cycles):**

```typescript
import type { PlatformId } from "../types";
```

`templates.ts` has no other imports. No `utm.ts`, no React, no API
clients. Single-responsibility: hold strings.

**Public API:**

```typescript
/**
 * Caption template per platform.
 *
 * Templates are EN-only per Q-2.2-6 lock (2026-04-28). They are
 * editorial content, not UI labels — operator's brand voice.
 *
 * Variable interpolation is positional, not named, to avoid template
 * engine dependencies. The {0}/{1}/{2}/{3} placeholders match the
 * order builder.ts passes them.
 */
export interface CaptionTemplate {
  /**
   * For Reddit: title (first {0}) and body ({1} headline + {2} source +
   * {3} URL). Reddit posts are title + selftext.
   * For X / LinkedIn: single {0} text combining headline/source/URL.
   */
  reddit: { title: string; body: string };
  twitter: string;
  linkedin: string;
}

/**
 * Default caption templates (EN, hardcoded).
 *
 * Variable slots:
 *   {0} = headline
 *   {1} = source citation (e.g. "Statistics Canada, Apr 2026")
 *   {2} = URL (full UTM-tagged share URL)
 *
 * Reddit body uses 4 slots:
 *   {0} = headline
 *   {1} = source
 *   {2} = description (1-2 sentences from CanonicalDocument)
 *   {3} = URL
 *
 * Multi-line strings use \n. Operator's copy-paste preserves line breaks.
 */
export const DEFAULT_TEMPLATES: CaptionTemplate;

/**
 * Per-platform character limits. Chunk D's validation rule uses this.
 *
 * Sources:
 * - X: 280 free / 4000 paid; we target free tier (B2B audience baseline)
 * - Reddit: title 300 chars / body 40000; title is the primary risk
 * - LinkedIn: 3000 chars per post
 */
export const PLATFORM_LIMITS: Record<PlatformId, number>;

/**
 * Reddit-specific subset (title separately tracked since it has its
 * own limit independent from body).
 */
export const REDDIT_TITLE_LIMIT: 300;
export const REDDIT_BODY_LIMIT: 40000;
```

### B2. `distribution/builder.ts` module

**File path:** `frontend-public/src/components/editor/distribution/builder.ts`

**Purpose:** assembles per-platform caption strings from
AdminPublicationResponse + UtmParams + DEFAULT_TEMPLATES. Pure function
factory; no side effects.

**Imports (no cycles):**

```typescript
import type { AdminPublicationResponse } from "@/lib/types/publication";
import type { PlatformId } from "../types";
import { buildShareUrl, type UtmParams } from "./utm";
import { DEFAULT_TEMPLATES, type CaptionTemplate } from "./templates";
```

Layer hierarchy: `templates` (pure data) ← `utm` (URL construction) ←
`builder` (assembly) ← future `kit` (Chunk C orchestrator).
`builder` consumes `templates` + `utm`, never the reverse.

**Public API:**

```typescript
export interface BuiltCaptions {
  reddit: { title: string; body: string };
  twitter: string;
  linkedin: string;
}

export interface CaptionInput {
  headline: string;
  source: string;
  description: string;
  lineageKey: string;
  slug: string;
}

export function buildCaptions(
  input: CaptionInput,
  templates?: CaptionTemplate
): BuiltCaptions;

export function buildCaptionFor(
  input: CaptionInput,
  platform: PlatformId,
  templates?: CaptionTemplate
): { title: string; body: string } | string;
```

**Behaviour notes:**

1. **`templates` parameter is for testing only.** Production code calls
   `buildCaptions(input)` and gets DEFAULT_TEMPLATES.
2. **No length validation here.** Q-2.2-7 (c) lock — caption builder is
   pure.
3. **Interpolation primitive:** uses local `interpolate(template,
   ...slots)` helper and `replaceAll`.
4. **URL construction order:** builder calls `buildShareUrl(slug,
   lineageKey, platform)` once per platform.
5. **Reddit special case:** builder produces TWO strings (title + body).
6. **Field nullability:** non-empty required for all 5 fields.
7. **No retries, no caching.** Pure synchronous function.

### B3. `validation/captionLength.ts` module — Q-2.2-7 (c) implementation

**File path:** `frontend-public/src/components/editor/validation/captionLength.ts`

**Purpose:** pre-flight check that catches captions exceeding platform
limits BEFORE export. Per Q-2.2-7 (c) lock: **non-blocking** — surfaces
warnings, operator can proceed.

**Public API:**

```typescript
export interface CaptionLengthWarning {
  platform: PlatformId;
  field?: "title" | "body";
  actualLength: number;
  limit: number;
  overBy: number;
  message: string;
}

export function validateCaptionLengths(
  captions: BuiltCaptions
): CaptionLengthWarning[];

export function checkOneCaption(
  text: string,
  limit: number,
  platform: PlatformId,
  field?: "title" | "body"
): CaptionLengthWarning | null;
```

**Behaviour notes:**
- Pure function, returns warnings array, never raises on overflow.
- Reddit title/body validated separately.
- Uses String.length for char counting (DEBT candidate if needed later).
- No truncation, no blocking, no modal ownership (Chunk C wires UX).

### B4. Module layering (Phase 2.2 distribution + validation)

- `templates.ts`: constants only, EN content + limits.
- `utm.ts`: URL construction only.
- `builder.ts`: caption assembly only.
- `captionLength.ts`: non-blocking validation only.
- `kit.ts` (Chunk C TBD): orchestration entrypoint.

### B5. Open questions surfaced for impl phase

These are implementation questions, not new founder UX decisions.

- **Q-impl-2.2-1 — Slug source resolution**
  - Pre-flight outcome in this repo is **SLUG-C** (no `slug` or `public_url`
    field visible on `AdminPublicationResponse` schema as of 2026-04-30).
  - Escalate as Q-2.2-9 in impl if schema remains unchanged.
- **Q-impl-2.2-2 — Empty-headline behaviour**
  - Recommendation: throw fail-fast; enforce headline before export.
- **Q-impl-2.2-3 — Reddit description source**
  - Choose `(b)` computed from existing props or `(d)` headline fallback for v1.
- **Q-impl-2.2-4 — Interpolation helper test granularity**
  - Recommendation: small standalone helper tests in Chunk D strategy.

### B6. §B summary

**What this section produced:**
1. `distribution/templates.ts` API (EN templates + limits)
2. `distribution/builder.ts` API (pure caption assembly)
3. `validation/captionLength.ts` API (non-blocking warning surface)
4. Layering constraints across modules
5. Impl-phase questions to resolve before coding

**Founder action requested:** none for this chunk.
