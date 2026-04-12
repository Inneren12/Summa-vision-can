"""Cloudflare Turnstile CAPTCHA validator (D-0b).

Validates Turnstile response tokens against the Cloudflare siteverify API.
Injected into endpoints via dependency injection (ARCH-DPEN-001).
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileValidator:
    """Validates Cloudflare Turnstile CAPTCHA tokens.

    Args:
        secret_key: The Turnstile secret key from Cloudflare dashboard.
        http_client: Injected async HTTP client (ARCH-DPEN-001).
    """

    def __init__(self, secret_key: str, http_client: httpx.AsyncClient) -> None:
        self._secret_key = secret_key
        self._http_client = http_client

    async def validate(self, token: str, client_ip: str | None = None) -> bool:
        """Validate a Turnstile response token.

        Args:
            token: The turnstile response token from the client.
            client_ip: Optional client IP for additional validation.

        Returns:
            True if the token is valid, False otherwise.
        """
        payload: dict[str, str] = {
            "secret": self._secret_key,
            "response": token,
        }
        if client_ip:
            payload["remoteip"] = client_ip

        try:
            resp = await self._http_client.post(
                TURNSTILE_VERIFY_URL,
                data=payload,
                timeout=10.0,
            )
            result = resp.json()
            success: bool = result.get("success", False)

            if not success:
                logger.warning(
                    "turnstile_validation_failed",
                    error_codes=result.get("error-codes", []),
                )

            return success
        except httpx.HTTPError:
            logger.warning("turnstile_request_failed", exc_info=True)
            return False
