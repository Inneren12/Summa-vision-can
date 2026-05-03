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


# ---------------------------------------------------------------------------
# Resolve namespace — emitted by admin resolve router (Phase 3.1c)
# ---------------------------------------------------------------------------
#
# Convention divergence (intentional): the wire values below are
# UPPER_SNAKE_CASE, NOT the lowercase dot.namespace convention used by
# the auth namespace above. This preserves verbatim the error_code
# string already shipped by ``admin_semantic_mappings.py`` (which uses
# the literal ``"MAPPING_NOT_FOUND"`` for the same condition). Recon
# §3 explicitly locks this: REUSE the existing wire value rather than
# introducing a parallel ``mapping.not_found`` form that would force
# a frontend i18n-key migration. Phase 3.2 (DEBT-030 envelope work)
# may re-unify the convention; until then the resolve router emits
# the same upper-case token as 3.1b to keep the i18n key registry
# stable.

MAPPING_NOT_FOUND = "MAPPING_NOT_FOUND"
"""Active semantic mapping not found for resolve lookup (404)."""

RESOLVE_CACHE_MISS = "RESOLVE_CACHE_MISS"
"""No cached value available for the requested lookup after auto-prime
+ re-query (recon §C2 terminal step, 404)."""

RESOLVE_INVALID_FILTERS = "RESOLVE_INVALID_FILTERS"
"""Filter set parse / mapping-shape validation failed (400)."""
