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
