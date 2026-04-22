# Phase 3 Slice 0 — Cyrillic Font Blocker Check

Date: 2026-04-22
Scope: frontend/ Flutter app
Status: INVESTIGATION COMPLETE

## 1. Font stack inventory

| Font family | Mechanism | Used for | Files/references |
|---|---|---|---|
| Bricolage Grotesque | `google_fonts` runtime loader | display / headings | `frontend/lib/core/theme/app_theme.dart:581`, `frontend/lib/core/theme/app_theme.dart:609` |
| DM Sans | `google_fonts` runtime loader | body text | `frontend/lib/core/theme/app_theme.dart:590`, `frontend/lib/core/theme/app_theme.dart:606` |
| JetBrains Mono | `google_fonts` runtime loader | data / mono labels | `frontend/lib/core/theme/app_theme.dart:598`, `frontend/lib/core/theme/app_theme.dart:612` |

`google_fonts` constraint in `pubspec.yaml`: `^6.0.0`.
Resolved `google_fonts` in lockfile: `6.3.3`.

Bundled font assets (`flutter: fonts:` section): **none found** in `frontend/pubspec.yaml`.

Custom font loading code location: `frontend/lib/core/theme/app_theme.dart` via direct `GoogleFonts.*` calls and `GoogleFonts.*TextTheme` wrappers.

## 2. Cyrillic coverage per font

| Font | Cyrillic (U+0400–U+04FF) | Source of truth | Notes |
|---|---|---|---|
| Bricolage Grotesque | ❌ No (known) | Google Fonts specimen metadata (known state referenced in task context) | Latin + Latin-Extended only; expected Cyrillic miss |
| DM Sans | ✅ Yes (known, added in variable release era) | Google Fonts specimen metadata (known state referenced in task context) | Should render Russian with current package versions |
| JetBrains Mono | ✅ Yes | Google Fonts specimen metadata (known state referenced in task context) | Includes Cyrillic / Cyrillic-Extended |

Note: This report uses the known font support states provided in the prompt context and code inspection only (no live specimen re-check performed in this slice).

## 3. Render prediction

If Russian text is introduced today with current font configuration:
- Display (headings, section titles): **BROKEN / inconsistent** — Bricolage likely falls back to system font (or tofu boxes in strict render paths)
- Body (most UI copy): **OK** — DM Sans expected to render Cyrillic
- Data (numbers, status codes, mono labels): **OK** — JetBrains Mono expected to render Cyrillic

Platform impact:
- **Flutter Web:** most visible risk because CDN/runtime font loading and fallback behavior varies by browser.
- **Desktop (macOS/Windows/Linux):** same logical issue; missing glyphs trigger fallback chains, causing style mismatch in headings.
- **Mobile (iOS/Android):** same logical issue; body/data likely fine, heading font inconsistency remains.

## 4. Test artifact

Created `frontend/lib/dev/font_cyrillic_test.dart` (dev-only, not wired to router).
Founder can temporarily attach it to a route/screen for visual verification.

## 5. Verdict

**Phase 3 is PARTIALLY BLOCKED** by the display font pipeline.

- Blocker severity: medium-high (heading typography is high-visibility in UX)
- Body + data fonts appear non-blocking for Cyrillic
- Estimated mitigation effort: 2–4 hours for Option A (font family swap + QA)

## 6. Recommended mitigation

**Option A — replace Bricolage Grotesque with a Cyrillic-capable alternative.**

Candidates:
- **Manrope** — modern geometric sans, strong Cyrillic support, low migration friction
- **IBM Plex Sans** — robust multilingual coverage, slightly different voice
- **Onest** — stylistically close for display usage with Cyrillic support

Recommendation: **Manrope** as pragmatic default for Phase 3 unblock; smallest engineering risk with acceptable visual continuity for heading use.

Action items for Phase 3 Slice 1 (planning):
1. Founder compares Manrope vs current display look and approves direction.
2. Implement swap in theme (and any related references) once approved.
3. Run visual QA on key screens in EN + RU.

## 7. Next steps

- Founder: run quick visual check using `lib/dev/font_cyrillic_test.dart` (optional if swap decision is pre-approved)
- Phase 3 Slice 1: integrate font mitigation into i18n technical plan
- Phase 3 Slice 2: hardcoded-string recon for Queue / Editor / Preview flows
