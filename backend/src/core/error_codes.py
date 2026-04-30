"""Wire-format error codes emitted by the backend.

These are the dot-separated string codes that appear in the API response
envelope (`detail.error_code`). Frontend uses an explicit dictionary
(`frontend-public/src/lib/api/errorCodes.ts`) to map these to i18n keys.

Naming convention: lowercase, dot-separated, namespace-prefixed.
Example: `auth.missing_api_key`, `publication.precondition_failed`.

Python constants are UPPER_SNAKE; their values are lowercase dot codes.
This separates Python module discipline (constants) from wire format.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Auth namespace — emitted by AuthMiddleware (DEBT-034)
# ---------------------------------------------------------------------------

AUTH_NOT_CONFIGURED = "auth.not_configured"
"""Admin API key environment variable is unset or empty."""

AUTH_MISSING_API_KEY = "auth.missing_api_key"
"""Request to admin namespace did not include X-API-KEY header."""

AUTH_INVALID_API_KEY = "auth.invalid_api_key"
"""X-API-KEY header value did not match configured admin key."""

AUTH_ADMIN_RATE_LIMITED = "auth.admin_rate_limited"
"""Per-key rate limit exceeded for admin namespace."""
