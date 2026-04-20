# Production hardening (Stage 4 Task 10)

## Overview

Task 10 was split across two PRs:

- **Task 10a** — blockers (admin auth, InquiryForm CAPTCHA). See that PR for implementation details.
- **Task 10b** — polish (this PR): error boundaries, console hygiene, FastAPI docs gate, config docs.

## logError indirection

`frontend-public/src/lib/log-error.ts` exposes a single `logError(error, context?)` function. All client-side error paths route through it. Today it calls `console.error`; a future telemetry task (Sentry/PostHog/etc.) wires at this single point without touching call sites.

## console stripping

`next.config.ts` sets `compiler.removeConsole: { exclude: ['error'] }`. Effect in production builds:

- `console.log/warn/debug/info` — stripped
- `console.error` — preserved (logError uses it)

Dev builds are unaffected.

Three call sites exist:

- Client: `LoadMoreButton.tsx`, `METRCalculator.tsx` — routed through `logError`
- Server: `admin/editor/[id]/page.tsx` — stays as raw `console.error` (server logs, no client impact)

## Error boundaries

Next.js App Router conventions:

- `app/global-error.tsx` — root-level; owns html/body tags; renders on total crash. Replaces Next's unstyled fallback.
- `app/error.tsx` — per-route fallback applied to any route without its own `error.tsx`.
- `app/graphics/[id]/error.tsx` and `app/admin/editor/[id]/error.tsx` — route-specific (existed pre-Task-10).

Both root-level components render an inline-styled UI that does not depend on any design token module, so a crash inside TK import / editor subtree still renders a usable error page.

## FastAPI /docs

`backend/src/main.py` sets `docs_url`, `redoc_url`, `openapi_url` to `None` when `settings.environment == "production"`. Dev keeps the endpoints. Admin endpoint schema is not visible to the public in production.

The `AuthMiddleware` bypass list in `backend/src/core/security/auth.py` still includes `/docs`, `/openapi.json`, `/redoc`; it is harmless in both states (dev: requests reach the endpoints without auth as intended; prod: endpoints return 404 before any middleware logic matters).

## .env.example

`NEXT_PUBLIC_TURNSTILE_SITE_KEY` added — TurnstileWidget renders null without it.

## CORS

`http://localhost:3000` removed from the prod CORS allow-list in `backend/src/main.py`. Explicit origin pattern preserved (no wildcard).

## Out of scope

- Real telemetry provider wiring (future task)
- Full WCAG sweep (separate effort)
- `settings.cors_origins` unused-setting reconciliation (cosmetic)
- Component-level `<ErrorBoundary>` inside editor canvas (future discussion)
- npm audit / dependency updates (human-driven post-merge)
