"""Slack notification service for lead alerts (D-3, PR-37/38).

Sends formatted Slack messages via incoming webhook for high-value
leads (B2B, education). Failures are logged but never propagated —
Slack is non-critical infrastructure.

Follows ARCH-DPEN-001: ``httpx.AsyncClient`` and ``Settings`` injected
via constructor.
"""

from __future__ import annotations

import time

import httpx
import structlog

from src.core.config import Settings

logger = structlog.get_logger(module="slack_notifier")


class SlackNotifierService:
    """Sends Slack alerts for new leads via incoming webhook.

    Attributes:
        webhook_url: The Slack incoming webhook URL.
        _http_client: Injected async HTTP client.
        _sent_keys: In-memory dedupe cache mapping dedupe_key → timestamp.
    """

    _DEDUPE_TTL_SECONDS: float = 300.0  # 5 minutes

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self.webhook_url: str = settings.SLACK_WEBHOOK_URL
        self._http_client = http_client
        self._sent_keys: dict[str, float] = {}
        self._startup_warned: bool = False

    async def notify_lead(
        self,
        email: str,
        category: str,
        company_domain: str | None,
        context: dict | None = None,
        dedupe_key: str | None = None,
    ) -> bool:
        """Send a Slack notification for a new lead.

        Args:
            email: The lead's email address.
            category: Lead category (``b2b``, ``education``, ``isp``, ``b2c``).
            company_domain: Extracted domain for B2B/education leads.
            context: Optional extra context (budget, message, etc.).
            dedupe_key: If provided, prevents duplicate messages for the
                same key within a 5-minute window.

        Returns:
            ``True`` if the message was sent successfully, ``False`` otherwise.
        """
        if not self.webhook_url:
            if not self._startup_warned:
                logger.warning("slack_webhook_not_configured")
                self._startup_warned = True
            return False

        # Dedupe check
        if dedupe_key is not None:
            now = time.monotonic()
            self._prune_expired_keys(now)
            if dedupe_key in self._sent_keys:
                logger.debug("slack_dedupe_skipped", dedupe_key=dedupe_key)
                return True
            self._sent_keys[dedupe_key] = now

        tag = "[B2B LEAD]" if category == "b2b" else f"[{category.upper()}]"

        # Build detail lines
        lines = [
            f"*New {category.upper()} Lead*",
            f"\u2022 Email: {email}",
        ]
        if company_domain:
            lines.append(f"\u2022 Domain: {company_domain}")
        lines.append(f"\u2022 Category: {category}")

        if context:
            for key, value in context.items():
                lines.append(f"\u2022 {key.replace('_', ' ').title()}: {value}")

        payload = {
            "text": f"{tag} {email}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n".join(lines),
                    },
                },
            ],
        }

        try:
            resp = await self._http_client.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info("slack_notification_sent", email=email, category=category)
            return True
        except Exception:
            logger.warning(
                "slack_notification_failed",
                email=email,
                category=category,
                exc_info=True,
            )
            return False

    def _prune_expired_keys(self, now: float) -> None:
        """Remove dedupe keys older than the TTL."""
        cutoff = now - self._DEDUPE_TTL_SECONDS
        expired = [k for k, ts in self._sent_keys.items() if ts < cutoff]
        for k in expired:
            del self._sent_keys[k]
