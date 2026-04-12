"""Email service interface (D-0a).

Defines the abstract contract for sending transactional emails.
Concrete implementations (e.g. SES, SMTP, console) are injected
via dependency injection (ARCH-DPEN-001).
"""

from __future__ import annotations

import abc


class EmailServiceInterface(abc.ABC):
    """Abstract email sending contract."""

    @abc.abstractmethod
    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
    ) -> None:
        """Send a transactional email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML content of the email.

        Raises:
            EmailSendError: If the email could not be sent.
        """


class ConsoleEmailService(EmailServiceInterface):
    """Dev/test implementation that logs emails to stdout."""

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html_body: str,
    ) -> None:
        """Print email details to console instead of sending."""
        import structlog

        logger = structlog.get_logger()
        logger.info(
            "email_sent_console",
            to=to,
            subject=subject,
            body_length=len(html_body),
        )
