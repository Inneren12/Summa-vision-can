# Module: CMHC Scraping Pipeline

**Package:** `backend.src.services.cmhc`
**Purpose:** Automated extraction of housing data (rental rates, vacancy rates) from Canada Mortgage and Housing Corporation (CMHC) portal using stealth browser automation, DOM validation, HTML snapshotting, and table parsing.

## Package Structure

```
services/cmhc/
├── __init__.py
├── browser.py         ← Playwright stealth context manager
├── parser.py          ← CMHCParser (BeautifulSoup4 HTML → DataFrame)
└── service.py         ← Extraction pipeline orchestrator
```

## Classes / Functions

### `get_stealth_context(playwright, *, headless, locale, timezone_id, user_agent)` (browser.py) — ✅ Complete
Async function providing a Playwright `BrowserContext` with anti-detection.
- Launches headless Chromium via `playwright.chromium.launch()`.
- Applies `playwright-stealth` patches (spoofs `navigator.webdriver`, fingerprints, User-Agent).
- Configurable: `locale="en-CA"`, `timezone_id="America/Toronto"`, optional `user_agent` override.
- Returns: `BrowserContext` (caller must close it).

### `CMHCParser` (parser.py) — ✅ Complete
Stateless HTML parser, completely decoupled from network I/O.
- `validate_structure(html: str) -> bool` — Checks for expected `<table>` and `<thead>` elements. Returns `False` and logs `CRITICAL` via structlog if the DOM is invalid.
- `parse(html: str) -> pd.DataFrame` — Parses the first `<table>` into a DataFrame using `pd.read_html(flavor="bs4")`. Raises `DataSourceError` on parse failure.
- **ARCH-PURA-001** applies: no HTTP calls, no file I/O inside parser.

### `run_cmhc_extraction_pipeline(city, storage)` (service.py) — ✅ Complete
Async function orchestrating the full CMHC extraction workflow:
1. Builds the target URL from the `city` slug.
2. Opens a stealth browser context, navigates to the page, captures HTML.
3. **Snapshots raw HTML** to storage via `storage.upload_raw()` at `cmhc/snapshots/{date}_{city}.html` BEFORE any parsing (**ARCH-SNAP-001**).
4. Validates DOM structure via `CMHCParser.validate_structure()`.
5. Raises `DataSourceError(error_code="CMHC_STRUCTURE_INVALID")` if validation fails.
6. Parses HTML into DataFrame and returns it.

Parameters:
- `city: str` — City slug (e.g. `"toronto"`).
- `storage: StorageInterface` — Injected storage backend.

Returns: `pd.DataFrame`.

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `playwright` + `playwright-stealth` | `api.routers.cmhc` (via TaskManager) |
| `beautifulsoup4` + `html5lib` | — |
| `core.storage.StorageInterface` | — |
| `core.exceptions.DataSourceError` | — |
| `structlog` | — |
| `pandas` | — |

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
