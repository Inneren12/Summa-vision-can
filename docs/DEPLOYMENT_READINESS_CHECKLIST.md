# Summa Vision — Deployment Readiness Checklist

**Status:** Active
**Owner:** Oleksii Shulzhenko
**Last updated:** 2026-04-23
**Related:** `OPERATOR_AUTOMATION_ROADMAP.md`, `SESSION_HANDOFF.md`, `docs/deployment.md`

---

## Purpose

Explicit list of gates that must be green before DNS cutover and public launch. This document replaces vague "проверка готовности" with verifiable, single-responsibility items.

**Rule:** every item must be demonstrably true (screenshot, log, test run, or config file reference). Self-assessment is not sufficient.

---

## How to use

1. Work through sections top-to-bottom. Later sections assume earlier ones are green.
2. For each item, record evidence in the inline "Evidence" field (URL, file path, command output, or date verified).
3. Items marked 🔴 are hard blockers. Items marked 🟡 are soft blockers (launch possible with monitoring plan).
4. When a section is 100% green, mark it `✅ VERIFIED <date>` in the section header.
5. Launch is gated on every hard blocker being green.

---

## Section 1 — Infrastructure & DNS

| # | Check | Status |
|---|---|---|
| 1.1 🔴 | DNS migration Porkbun → Cloudflare completed for `summa.vision` | ☐ |
| 1.2 🔴 | Cloudflare SSL/TLS mode set to "Full (strict)" with valid origin cert | ☐ |
| 1.3 🔴 | A/AAAA records resolve correctly from non-local DNS resolver (verified via `dig @8.8.8.8`) | ☐ |
| 1.4 🔴 | Cloudflare Access configured for `/admin/*` — unauthenticated request returns 302 to CF Access login | ☐ |
| 1.5 🔴 | CF Access policy allows founder + two operator emails; others rejected | ☐ |
| 1.6 🟡 | Cloudflare rate-limiting rules active on `/api/leads/*` and `/admin/*` | ☐ |
| 1.7 🔴 | Origin server firewall allows only Cloudflare IP ranges on port 443 | ☐ |
| 1.8 🟡 | Cloudflare WAF rules reviewed (no over-blocking of legitimate API calls) | ☐ |
| 1.9 🔴 | `robots.txt` present with explicit allow/deny for crawlers (gallery allowed, `/admin/*` disallowed) | ☐ |
| 1.10 | `sitemap.xml` generated and references current published graphics | ☐ |

**Evidence section:**
- DNS cutover date: _____
- CF Access login URL: _____
- Firewall ruleset hash: _____

---

## Section 2 — Backend startup & secrets

| # | Check | Status |
|---|---|---|
| 2.1 🔴 | DEBT-008 resolved — `Settings` has `@model_validator(mode="after")` rejecting startup on missing required secrets | ✅ pre-existing — `backend/src/core/config.py` `@model_validator(mode="after")` validates DATABASE_URL/ADMIN_API_KEY/S3_BUCKET (+ prod secrets) and raises `ValueError` on missing values |
| 2.2 🔴 | Production `.env` file contains all required secrets; no placeholder values (`CHANGEME`, `REPLACE_ME`, empty strings) | ☐ |
| 2.3 🔴 | `DATABASE_URL` points to production PostgreSQL, not localhost/dev | ☐ |
| 2.4 🔴 | `ADMIN_API_KEY` is strong (≥32 char, randomly generated), stored in secrets manager | ☐ |
| 2.5 🔴 | `S3_BUCKET_PUBLIC` and `S3_BUCKET_PRIVATE` exist, correct CORS configured | ☐ |
| 2.6 🔴 | `GEMINI_API_KEY` validated — test call succeeds with minimal payload (for Phase 2 Draft Social Text opt-in) | ☐ |
| 2.7 🔴 | `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` configured, rendered in InquiryForm | ☐ |
| 2.8 🔴 | ESP provider API key configured (SES/Resend), test magic-link email delivered to test address | ☐ |
| 2.9 🔴 | Slack webhook URL configured, test B2B lead posts successfully | ☐ |
| 2.10 🟡 | Observability keys present (Sentry/PostHog) or deliberate decision to defer recorded | ☐ |
| 2.11 🔴 | Cold-start: `docker compose up` on clean state reaches healthy `/health` in <30s | ☐ |
| 2.12 🔴 | Missing-secret failure mode: removing any required env var causes startup refusal with clear error (not 500 on first request) | ✅ pre-existing — startup fail-fast in `backend/src/core/config.py` covered by `backend/tests/core/test_config.py` (missing-secret + production-secret cases) |

**Evidence section:**
- Test magic link received (timestamp): _____
- Test Slack webhook fired (channel/timestamp): _____
- Missing-secret error screenshot path: _____

---

## Section 3 — Database & migrations

| # | Check | Status |
|---|---|---|
| 3.1 🔴 | Production DB provisioned (PostgreSQL 15+) with `pg_trgm` extension enabled | ☐ |
| 3.2 🔴 | `alembic upgrade head` on production DB completes without errors | ☐ |
| 3.3 🔴 | `alembic downgrade -1 && alembic upgrade head` round-trips cleanly on staging/clone of prod | ☐ |
| 3.4 🔴 | Automated daily backup configured, verified by restore-test into staging | ☐ |
| 3.5 🔴 | Backup retention policy documented (minimum 7 daily + 4 weekly) | ☐ |
| 3.6 🔴 | DB connection pool sized appropriately for VPS capacity (no `pool_size=100` on 2GB RAM) | ☐ |
| 3.7 🟡 | Slow query log enabled, baseline captured | ☐ |
| 3.8 🔴 | StatCan catalog sync has run at least once on production DB (≥6,000 cubes in `cube_catalog`) | ☐ |

**Evidence section:**
- Migration run timestamp: _____
- Restore-test date and target env: _____
- Catalog sync count: _____

---

## Section 4 — Tech debt blockers

Per `OPERATOR_AUTOMATION_ROADMAP.md` §2.2 decision: blockers cleared before launch, other DEBT entries handled opportunistically.

| # | Check | Status |
|---|---|---|
| 4.1 🔴 | DEBT-008 — startup secrets validation (see §2.1 above) | ✅ pre-existing — DEBT-008 resolved 2026-04-12 (Pre-deploy Hardening); validator in `backend/src/core/config.py` + tests in `backend/tests/core/test_config.py` |
| 4.2 🔴 | DEBT-020 — CMHC and Tasks routers unmounted (they back dead code, confuse operators) | ✅ pre-existing — `backend/src/main.py` includes active routers only; `backend/src/api/routers/cmhc.py` and `backend/src/api/routers/tasks.py` absent |
| 4.3 🔴 | DEBT-016 — `docs/architecture/ARCHITECTURE.md` LLM Gate references removed or clearly marked `[REMOVED]` | ✅ pre-existing — DEBT-016 resolved 2026-04-12; `docs/architecture/ARCHITECTURE.md` removed and `docs/ARCHITECTURE.md` contains no LLM Gate references |
| 4.4 🔴 | DEBT-019 — ARCHITECTURE.md flow diagram no longer shows LLM Gate in critical path | ✅ pre-existing — DEBT-019 resolved 2026-04-12; `docs/ARCHITECTURE.md` flow is Data Sources → ETL Pipeline → Cube Catalog → Data Workbench → Visual Engine → Publication |
| 4.5 🟡 | DEBT-007 — `services/ai/*` + `models/llm_request.py` marked `# BACKLOG:` or deleted | ✅ pre-existing — DEBT-007 resolved 2026-04-12; `backend/src/services/ai/` and `backend/src/models/llm_request.py` are deleted |
| 4.6 🟡 | Tech debt tempcleanup bug (noted in userMemories recent_updates) — temp_cleanup.py excludes keys referenced by pending jobs | ☐ |

Other active DEBT entries (not blockers, handled post-launch or during idle time):
- DEBT-010, DEBT-015, DEBT-022, and any new entries from Stage 4

---

## Section 5 — i18n completeness

Per user confirmation 2026-04-23: "we have almost finished" i18n. Verify completion.

| # | Check | Status |
|---|---|---|
| 5.1 🔴 | Phase 0 glossary finalized — `I18N_GLOSSARY.md` committed with founder sign-off | ☐ |
| 5.2 🔴 | Next.js Phase 1 — all admin routes (`/admin/*`) pass `messages/en.json` and `messages/ru.json` coverage check (no hardcoded EN strings in JSX) | ☐ |
| 5.3 🔴 | Flutter Phase 3 — all routes pass ARB coverage check (`flutter gen-l10n` succeeds, no missing keys) | ☐ |
| 5.4 🔴 | Language switcher works runtime in Next.js (cookie persistence) | ☐ |
| 5.5 🔴 | Language switcher works runtime in Flutter (SharedPreferences persistence) | ☐ |
| 5.6 🔴 | Cyrillic rendering verified in Flutter — test string "Инфляция, ВВП, Занятость" renders correctly, no tofu/squares | ☐ |
| 5.7 🔴 | Cyrillic rendering verified in Next.js — same test string in editor and admin | ☐ |
| 5.8 🟡 | Russian translations spot-checked by founder — no obvious machine-translation artifacts in high-visibility strings (buttons, headers, error messages) | ☐ |
| 5.9 🔴 | Locale-dependent formatting verified: numbers (1 234,56 in RU vs 1,234.56 in EN), dates (23.04.2026 vs 2026-04-23) | ☐ |

**Post-launch commitment:** every new PR that adds UI text must include entries in both locale files (`en.json`+`ru.json` or `en.arb`+`ru.arb`). Enforced via roadmap implementation prompts.

---

## Section 6 — Lead funnel end-to-end

This is the revenue pipeline. Every step must be verified.

| # | Check | Status |
|---|---|---|
| 6.1 🔴 | Public gallery loads at `summa.vision/` with at least 1 graphic visible | ☐ |
| 6.2 🔴 | Lead form (email capture) renders with Turnstile challenge | ☐ |
| 6.3 🔴 | Turnstile pass → email captured → magic link generated → email delivered (verified with real inbox, not log) | ☐ |
| 6.4 🔴 | Magic link click → token validated → presigned S3 URL returned → high-res PNG downloads | ☐ |
| 6.5 🔴 | Magic link reuse: second click on same token rejected (single-use enforced) | ☐ |
| 6.6 🔴 | Magic link expiry: token older than configured TTL rejected | ☐ |
| 6.7 🔴 | Rate limit: 4th lead submission from same IP within 1 minute blocked | ☐ |
| 6.8 🔴 | Resend magic link: 2nd request within 2 min blocked | ☐ |
| 6.9 🔴 | B2B lead (e.g. `test@<corporate-domain>.com`) triggers Slack notification | ☐ |
| 6.10 🔴 | B2C lead (e.g. `test@gmail.com`) does NOT trigger Slack, only logged | ☐ |
| 6.11 🔴 | ESP sync: `Lead.esp_synced` flips to `True` after successful ESP call | ☐ |
| 6.12 🔴 | ESP failure mode: simulated 500 from ESP → `esp_sync_failed_permanent` flag set after retry budget exhausted | ☐ |
| 6.13 🟡 | Download analytics: successful download increments appropriate counter | ☐ |

**Evidence section:**
- Test email inbox: _____
- Slack channel observed: _____
- Rate limit test timestamp: _____

---

## Section 7 — Performance & limits

| # | Check | Status |
|---|---|---|
| 7.1 🔴 | Public gallery Lighthouse score ≥ 90 on mobile (Performance) | ☐ |
| 7.2 🔴 | Gallery first contentful paint < 1.5s on 4G simulation | ☐ |
| 7.3 🟡 | Editor loads in < 3s on production | ☐ |
| 7.4 🔴 | R15 hard caps verified: API endpoints refuse requests exceeding documented limits (preview >100 rows, transform output size, etc.) | ☐ |
| 7.5 🟡 | CDN cache hit ratio > 80% for gallery PNGs after warmup | ☐ |
| 7.6 🔴 | S3 costs projection for 30 days based on expected traffic < $X ceiling (founder decides X) | ☐ |

---

## Section 8 — Security review

| # | Check | Status |
|---|---|---|
| 8.1 🔴 | No secrets committed to git — audit with `git log --all --full-history -p` | grep for common patterns (api_key, secret, password, token with `=`) | ☐ |
| 8.2 🔴 | All `/admin/*` endpoints return 401/403 for unauthenticated requests | ☐ |
| 8.3 🔴 | CORS policy on API: only `summa.vision` origin allowed (not `*`) | ☐ |
| 8.4 🔴 | No debug/verbose error messages leak stack traces to public responses | ☐ |
| 8.5 🔴 | SQL injection: parametrized queries everywhere (spot-check top 5 endpoints) | ☐ |
| 8.6 🟡 | CSP headers configured on Next.js responses | ☐ |
| 8.7 🟡 | HSTS header set, preload-eligible | ☐ |
| 8.8 🔴 | Presigned S3 URLs: private bucket is NOT publicly readable (verified by direct URL access with no signature → denied) | ☐ |

---

## Section 9 — Operational readiness

| # | Check | Status |
|---|---|---|
| 9.1 🔴 | APScheduler daily StatCan sync runs at 09:15 EST on production, confirmed via AuditEvent log | ☐ |
| 9.2 🔴 | Failed job alerting: a deliberately failed job triggers observable notification (Slack or log) | ☐ |
| 9.3 🟡 | Zombie job detection: job stuck in RUNNING > N minutes is flagged | ☐ |
| 9.4 🔴 | Log retention: structlog JSON output captured by host (file or journald), rotation configured | ☐ |
| 9.5 🟡 | Observability MVP: server logs accessible from founder workstation via SSH in < 10 seconds | ☐ |
| 9.6 🔴 | Rollback plan documented: if deploy breaks production, steps to revert to previous container image | ☐ |
| 9.7 🔴 | Founder has SSH access to production VPS with 2FA (or equivalent secured access) | ☐ |

---

## Section 10 — Launch batch readiness

Cross-reference: launch content batch is scoped in `OPERATOR_AUTOMATION_ROADMAP.md` §5 "Stage C — Launch batch & onboarding". Content selection is founder's call and is NOT gated by this checklist — but the delivery mechanics ARE.

| # | Check | Status |
|---|---|---|
| 10.1 🔴 | At least 1 graphic published to production DB with `status = PUBLISHED` | ☐ |
| 10.2 🔴 | Published graphic renders on public gallery with correct PNG, title, download button | ☐ |
| 10.3 🔴 | Published graphic's high-res PNG accessible only via lead-funnel (direct S3 access denied) | ☐ |
| 10.4 🟡 | 3 Golden Example drafts exist with `TUTORIAL:` prefix (from roadmap Phase 1.2) | ☐ |
| 10.5 🟡 | UTM attribution verified: test lead submitted via `?utm_content=<test_lineage>` logs correctly | ☐ |

---

## Section 11 — Post-launch monitoring plan

Not a gate — a commitment. Document what will be watched in first 72 hours.

| # | Commitment |
|---|---|
| 11.1 | Founder checks production logs at least twice on launch day |
| 11.2 | First 72h: any 500-series API error investigated within 4h |
| 11.3 | First 7 days: lead-funnel conversion reviewed daily (leads / unique visitors) |
| 11.4 | First 30 days: weekly review of roadmap Phase 3 planning — operators' actual pain points inform binding design |

---

## Final sign-off

Launch cutover authorized when:

- All 🔴 items are ✅
- All 🟡 items are ✅ OR have documented mitigation plan
- Founder manually signs below

```
Launch authorized by: __________________
Date: __________________
DNS cutover executed: __________________
```

---

## Revision log

| Date | Change | Reason |
|---|---|---|
| 2026-04-23 | Initial version | Derived from Stage 4 production polish work + operator automation roadmap |
| 2026-04-26 | §4.1-4.6 + §2.1+2.12 audit-and-sync | Section §4 audited against current code + DEBT Resolved table: DEBT-008/007/016/019/020 verified and checklist statuses synced to ✅ with evidence; §4.6 remains ☐ because pending-job exclusion exists but current test file has 4 tests (<5 required by this checklist text). §2.1 + §2.12 verified via Settings `@model_validator` + tests. Items §2.2-§2.11 intentionally left ☐ for founder-only runtime/env launch verification. No code changes in this PR. |
