"""B2B lead scoring service (D-3, PR-35).

Pure domain classification — no I/O, no async, no database calls.
Complies with ARCH-PURA-001: data processing is a pure function.

Priority rules (order matters):
    1. Domain ends with ``.edu`` → education.
    2. Domain is in ``UNIVERSITY_DOMAINS`` → education.
    3. Domain ends with ``.ca`` AND contains ``uni|college|school|academy|institut`` → education.
    4. Domain is in ``ISP_DOMAINS`` → isp.
    5. Domain is in ``FREE_EMAIL_DOMAINS`` → b2c.
    6. Everything else → b2b.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LeadScore(BaseModel):
    """Result of classifying a lead by email domain."""

    is_b2b: bool
    company_domain: str | None
    category: Literal["b2b", "education", "isp", "b2c"]


class LeadScoringService:
    """Classifies leads by email domain.

    All class-level constants are ``frozenset`` for O(1) lookups.
    The single public method ``score_lead`` is pure and synchronous.
    """

    FREE_EMAIL_DOMAINS: frozenset[str] = frozenset({
        "gmail.com", "yahoo.com", "yahoo.ca", "outlook.com", "hotmail.com",
        "hotmail.ca", "protonmail.com", "protonmail.ch", "icloud.com",
        "mail.com", "aol.com", "zoho.com", "yandex.com", "gmx.com",
        "live.com", "live.ca", "msn.com",
    })

    ISP_DOMAINS: frozenset[str] = frozenset({
        "shaw.ca", "rogers.com", "bell.net", "bell.ca", "telus.net",
        "videotron.ca", "sasktel.net", "eastlink.ca", "cogeco.ca",
        "tbaytel.net", "northwestel.net", "mts.net", "sympatico.ca",
    })

    UNIVERSITY_DOMAINS: frozenset[str] = frozenset({
        "utoronto.ca", "ubc.ca", "mcgill.ca", "uwaterloo.ca", "ualberta.ca",
        "queensu.ca", "sfu.ca", "yorku.ca", "ucalgary.ca", "uottawa.ca",
        "dal.ca", "uvic.ca", "usask.ca", "umanitoba.ca", "concordia.ca",
        "wlu.ca", "torontomu.ca", "carleton.ca", "uoguelph.ca", "unb.ca",
    })

    _EDUCATION_KEYWORDS: tuple[str, ...] = (
        "uni", "college", "school", "academy", "institut",
    )

    def score_lead(self, email: str) -> LeadScore:
        """Classify a lead by email domain.

        Args:
            email: The lead's email address.

        Returns:
            A ``LeadScore`` with ``is_b2b``, ``company_domain``, and ``category``.

        Raises:
            ValueError: If *email* does not contain an ``@`` character.
        """
        if "@" not in email:
            raise ValueError(f"Invalid email format: {email!r}")

        domain = email.split("@")[1].lower()

        # --- Priority 1: .edu TLD ---
        if domain.endswith(".edu"):
            return LeadScore(is_b2b=False, company_domain=domain, category="education")

        # --- Priority 2: Known university domains ---
        if domain in self.UNIVERSITY_DOMAINS:
            return LeadScore(is_b2b=False, company_domain=domain, category="education")

        # --- Priority 3: .ca + education keyword ---
        if domain.endswith(".ca") and any(kw in domain for kw in self._EDUCATION_KEYWORDS):
            return LeadScore(is_b2b=False, company_domain=domain, category="education")

        # --- Priority 4: ISP domains ---
        if domain in self.ISP_DOMAINS:
            return LeadScore(is_b2b=False, company_domain=None, category="isp")

        # --- Priority 5: Free email domains ---
        if domain in self.FREE_EMAIL_DOMAINS:
            return LeadScore(is_b2b=False, company_domain=None, category="b2c")

        # --- Priority 6: Everything else is B2B ---
        return LeadScore(is_b2b=True, company_domain=domain, category="b2b")
