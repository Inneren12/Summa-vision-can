# Active Glossary Snapshot

> **Auto-generated** — Do not edit directly. Source: `specs/glossary/*.json`
> Regenerate by running: `resolve_glossary.sh` or manually from JSON sources.

---

## Global Terms

| Term | Full Name | Definition |
|------|-----------|------------|
| **ETL** | Extract, Transform, Load | The process of extracting raw data from external APIs, transforming it via schema validation and scalar factor normalization, and loading results to S3 or local DB. |
| **Scalar Factor** | Metric Multiplier | A base-10 exponent multiplier that must be applied to raw StatCan response values (e.g., x1000 for 'thousands'). |
| **SSOT** | Single Source of Truth | The single authoritative data source for a given piece of information. |
| **DI** | Dependency Injection | Design pattern where classes receive their dependencies from external sources rather than creating them internally. |
| **AC** | Acceptance Criteria | A set of verifiable conditions that must all be satisfied for a PR to be considered complete. |
| **Maintenance Window** | StatCan Downtime Period | The period from 00:00 to 08:30 EST during which StatCan API is unavailable and no requests should be sent. |
| **Token Bucket** | Rate Limiting Algorithm | An algorithm that controls network traffic by using tokens to represent allowed requests, with tokens refilling at a fixed rate. |

## CMHC Terms

| Term | Full Name | Definition |
|------|-----------|------------|
| **CMHC** | Canada Mortgage and Housing Corporation | Canadian federal crown corporation providing housing data including rental and vacancy statistics. |
| **Stealth Browser** | Anti-Detection Browser Instance | A Playwright browser context configured with playwright-stealth to bypass Cloudflare anti-bot detection. |
| **DOM Parser** | Document Object Model Parser | A component that extracts structured data from raw HTML using BeautifulSoup4, completely decoupled from network I/O. |
| **Exponential Backoff** | Retry Delay Strategy | A retry strategy where wait time doubles after each failed attempt, used when encountering Cloudflare captchas. |

## Phase 3.1aaa Terms (Semantic Value Cache)

| Term | Full Name | Definition |
|------|-----------|------------|
| **Semantic Value Cache** | StatCan Value Cache | Persistent per-period cache of StatCan vectorDataPoint rows keyed by (cube_id, semantic_key, coord, ref_period). Powers the resolve API and decouples user-facing reads from live StatCan availability. |
| **coord** | StatCan Coordinate | A 10-position dot-separated string (e.g. `"1.10.0.0.0.0.0.0.0.0"`) addressing a single cell in a StatCan cube. Slot N corresponds to dimension position N; `0` means "not filtered". |
| **Auto-prime** | Best-Effort Cache Prime | Sync prime of recent periods invoked from the mapping save flow. Per founder lock Q-3 RE-LOCK, failures here MUST NOT propagate — the mapping save proceeds regardless. |
| **source_hash** | Row Content Fingerprint | SHA-256 of the canonical-JSON-encoded value-cache row (excluding all timestamps), used to detect content changes across refreshes without false positives. |
| **period_start** | Generated Period Anchor Date | A Postgres-side STORED GENERATED column derived from `ref_period` via `parse_ref_period_to_date`. Provides date-typed sorting/filtering. NULL on SQLite test fixtures. |
| **ref_period** | StatCan Reference Period | The raw period token returned by the WDS data API (e.g. `"2026-04"`, `"2026-Q3"`, `"2026"`, `"2026-04-15"`). |
