"""Tests for LeadScoringService (D-3, PR-35).

Validates pure domain classification logic against all category paths
and edge cases.
"""

from __future__ import annotations

import pytest

from src.services.crm.scoring import LeadScore, LeadScoringService


@pytest.fixture()
def scorer() -> LeadScoringService:
    return LeadScoringService()


class TestLeadScoring:
    def test_gmail_returns_b2c(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("me@gmail.com")
        assert result == LeadScore(is_b2b=False, company_domain=None, category="b2c")

    def test_rogers_returns_isp(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("john@rogers.com")
        assert result.category == "isp"
        assert result.is_b2b is False
        assert result.company_domain is None

    def test_utoronto_returns_education(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("sarah@utoronto.ca")
        assert result.category == "education"
        assert result.is_b2b is False
        assert result.company_domain == "utoronto.ca"

    def test_tdbank_returns_b2b(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("ceo@tdbank.ca")
        assert result == LeadScore(is_b2b=True, company_domain="tdbank.ca", category="b2b")

    def test_edu_domain_returns_education(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("prof@mit.edu")
        assert result.category == "education"
        assert result.is_b2b is False
        assert result.company_domain == "mit.edu"

    def test_college_pattern_match(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("admin@college-ontario.ca")
        assert result.category == "education"
        assert result.company_domain == "college-ontario.ca"

    def test_unknown_ca_domain_returns_b2b(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("info@unknowncompany.ca")
        assert result.category == "b2b"
        assert result.is_b2b is True
        assert result.company_domain == "unknowncompany.ca"

    def test_priority_edu_over_isp(self, scorer: LeadScoringService) -> None:
        """If a domain somehow matches both ISP and .edu rules, education wins."""
        result = scorer.score_lead("user@something.edu")
        assert result.category == "education"

    def test_case_insensitive(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("CEO@TDBANK.CA")
        assert result == LeadScore(is_b2b=True, company_domain="tdbank.ca", category="b2b")

    def test_invalid_email_format(self, scorer: LeadScoringService) -> None:
        with pytest.raises(ValueError, match="Invalid email format"):
            scorer.score_lead("no-at-sign")


class TestLeadScoringEdgeCases:
    def test_all_free_domains(self, scorer: LeadScoringService) -> None:
        """Every free email domain should return b2c."""
        for domain in LeadScoringService.FREE_EMAIL_DOMAINS:
            result = scorer.score_lead(f"user@{domain}")
            assert result.category == "b2c", f"Expected b2c for {domain}"

    def test_all_isp_domains(self, scorer: LeadScoringService) -> None:
        """Every ISP domain should return isp."""
        for domain in LeadScoringService.ISP_DOMAINS:
            result = scorer.score_lead(f"user@{domain}")
            assert result.category == "isp", f"Expected isp for {domain}"

    def test_all_university_domains(self, scorer: LeadScoringService) -> None:
        """Every university domain should return education."""
        for domain in LeadScoringService.UNIVERSITY_DOMAINS:
            result = scorer.score_lead(f"user@{domain}")
            assert result.category == "education", f"Expected education for {domain}"

    def test_academy_ca_pattern(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("info@academy-arts.ca")
        assert result.category == "education"

    def test_institut_ca_pattern(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("admin@institut-national.ca")
        assert result.category == "education"

    def test_school_ca_pattern(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("teacher@school-board.ca")
        assert result.category == "education"

    def test_uni_ca_pattern(self, scorer: LeadScoringService) -> None:
        result = scorer.score_lead("student@uni-northbay.ca")
        assert result.category == "education"
