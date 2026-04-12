"""ESP (Email Service Provider) client for subscriber management (D-3, PR-34/49).

Defines the ``ESPSubscriberInterface`` ABC and the ``BeehiivClient``
implementation. Transactional emails (download links) are handled by
``EmailServiceInterface`` — this module manages *subscriber list* operations.

Follows ARCH-DPEN-001: ``httpx.AsyncClient`` and settings injected via
constructor.
"""

from __future__ import annotations

import abc

import httpx
import structlog

from src.core.config import Settings
from src.core.exceptions import ESPPermanentError, ESPTransientError

logger = structlog.get_logger(module="esp_client")


class ESPSubscriberInterface(abc.ABC):
    """Abstract contract for ESP subscriber operations."""

    @abc.abstractmethod
    async def add_subscriber(self, email: str, metadata: dict | None = None) -> None:
        """Add a subscriber to the ESP list.

        Raises:
            ESPPermanentError: On 4xx client errors.
            ESPTransientError: On 5xx server errors or timeouts.
        """

    @abc.abstractmethod
    async def add_tag(self, email: str, tag: str) -> None:
        """Add a tag to an existing subscriber.

        Raises:
            ESPPermanentError: On 4xx client errors.
            ESPTransientError: On 5xx server errors or timeouts.
        """


class BeehiivClient(ESPSubscriberInterface):
    """Beehiiv ESP client implementation.

    Attributes:
        _http_client: Injected async HTTP client.
        _api_key: Beehiiv API key.
        _publication_id: Beehiiv publication ID.
    """

    _BASE_URL = "https://api.beehiiv.com/v2"

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        publication_id: str,
    ) -> None:
        self._http_client = http_client
        self._api_key = api_key
        self._publication_id = publication_id

    @classmethod
    def from_settings(
        cls, http_client: httpx.AsyncClient, settings: Settings
    ) -> BeehiivClient:
        """Factory that reads credentials from Settings."""
        return cls(
            http_client=http_client,
            api_key=settings.BEEHIIV_API_KEY,
            publication_id=settings.BEEHIIV_PUBLICATION_ID,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def add_subscriber(self, email: str, metadata: dict | None = None) -> None:
        """POST a new subscriber to Beehiiv."""
        url = f"{self._BASE_URL}/publications/{self._publication_id}/subscriptions"
        payload: dict = {
            "email": email,
            "reactivate_existing": True,
            "send_welcome_email": False,
        }
        if metadata:
            payload["custom_fields"] = [
                {"name": k, "value": str(v)} for k, v in metadata.items()
            ]

        await self._request("POST", url, json=payload)
        logger.info("esp_subscriber_added", email=email)

    async def add_tag(self, email: str, tag: str) -> None:
        """POST a tag to an existing Beehiiv subscriber."""
        url = f"{self._BASE_URL}/publications/{self._publication_id}/subscriptions/tags"
        payload = {"email": email, "tag": tag}

        await self._request("POST", url, json=payload)
        logger.info("esp_tag_added", email=email, tag=tag)

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        """Execute an HTTP request with ESP-specific error handling."""
        try:
            resp = await self._http_client.request(
                method,
                url,
                headers=self._headers,
                timeout=15.0,
                **kwargs,
            )
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise ESPTransientError(
                status_code=0,
                detail=f"ESP request failed: {exc}",
            ) from exc

        if 400 <= resp.status_code < 500:
            raise ESPPermanentError(
                status_code=resp.status_code,
                detail=f"ESP client error: {resp.text}",
            )

        if resp.status_code >= 500:
            raise ESPTransientError(
                status_code=resp.status_code,
                detail=f"ESP server error: {resp.text}",
            )

        return resp
