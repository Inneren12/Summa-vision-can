"""Tests for ContentBrief and ChartType (PR-15)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.services.ai.schemas import ChartType, ContentBrief


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_PAYLOAD: dict[str, object] = {
    "virality_score": 7.5,
    "headline": "Canadian housing prices surge 12% in Q4",
    "bg_prompt": "A dramatic Canadian skyline at sunset with housing cranes",
    "chart_type": "BAR",
    "reasoning": "Housing is top concern for Canadians in 2025.",
}


# ---------------------------------------------------------------------------
# ChartType enum
# ---------------------------------------------------------------------------


class TestChartType:
    """Tests for the ChartType string enum."""

    def test_all_thirteen_values_exist(self) -> None:
        """Assert all 13 required chart types are defined."""
        expected = {
            "LINE", "BAR", "SCATTER", "AREA", "STACKED_BAR", "HEATMAP",
            "CANDLESTICK", "PIE", "DONUT", "WATERFALL", "TREEMAP",
            "BUBBLE", "CHOROPLETH",
        }
        actual = {member.value for member in ChartType}
        assert actual == expected

    def test_value_based_lookup(self) -> None:
        """ChartType('LINE') should return ChartType.LINE."""
        assert ChartType("LINE") is ChartType.LINE

    def test_value_based_lookup_all(self) -> None:
        """Every string value should resolve to the correct member."""
        for member in ChartType:
            assert ChartType(member.value) is member

    def test_invalid_value_raises(self) -> None:
        """An unknown string should raise ValueError."""
        with pytest.raises(ValueError):
            ChartType("SPARKLINE")


# ---------------------------------------------------------------------------
# ContentBrief — valid cases
# ---------------------------------------------------------------------------


class TestContentBriefValid:
    """Tests for valid ContentBrief instantiation."""

    def test_valid_payload_creates_model(self) -> None:
        """A fully valid payload should instantiate without error."""
        brief = ContentBrief(**VALID_PAYLOAD)  # type: ignore[arg-type]
        assert brief.virality_score == 7.5
        assert brief.headline == "Canadian housing prices surge 12% in Q4"
        assert brief.chart_type is ChartType.BAR
        assert brief.reasoning == "Housing is top concern for Canadians in 2025."

    def test_reasoning_defaults_to_none(self) -> None:
        """reasoning is optional and should default to None."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "reasoning"}
        brief = ContentBrief(**payload)  # type: ignore[arg-type]
        assert brief.reasoning is None

    def test_boundary_virality_score_min(self) -> None:
        """virality_score of exactly 1.0 should pass."""
        payload = {**VALID_PAYLOAD, "virality_score": 1.0}
        brief = ContentBrief(**payload)  # type: ignore[arg-type]
        assert brief.virality_score == 1.0

    def test_boundary_virality_score_max(self) -> None:
        """virality_score of exactly 10.0 should pass."""
        payload = {**VALID_PAYLOAD, "virality_score": 10.0}
        brief = ContentBrief(**payload)  # type: ignore[arg-type]
        assert brief.virality_score == 10.0

    def test_headline_at_max_length(self) -> None:
        """A headline of exactly 280 characters should pass."""
        payload = {**VALID_PAYLOAD, "headline": "A" * 280}
        brief = ContentBrief(**payload)  # type: ignore[arg-type]
        assert len(brief.headline) == 280

    def test_all_chart_types_accepted(self) -> None:
        """Each ChartType value should be accepted by ContentBrief."""
        for ct in ChartType:
            payload = {**VALID_PAYLOAD, "chart_type": ct.value}
            brief = ContentBrief(**payload)  # type: ignore[arg-type]
            assert brief.chart_type is ct


# ---------------------------------------------------------------------------
# ContentBrief — validation errors
# ---------------------------------------------------------------------------


class TestContentBriefValidation:
    """Tests for ContentBrief validation error paths."""

    def test_virality_score_below_min_raises(self) -> None:
        """virality_score < 1.0 should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "virality_score": 0.5}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_virality_score_above_max_raises(self) -> None:
        """virality_score > 10.0 should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "virality_score": 10.1}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_empty_headline_raises(self) -> None:
        """An empty headline should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "headline": ""}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_headline_too_long_raises(self) -> None:
        """A headline over 280 characters should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "headline": "A" * 281}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_empty_bg_prompt_raises(self) -> None:
        """An empty bg_prompt should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "bg_prompt": ""}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_invalid_chart_type_raises(self) -> None:
        """An invalid chart_type string should raise ValidationError."""
        payload = {**VALID_PAYLOAD, "chart_type": "SPARKLINE"}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_missing_virality_score_raises(self) -> None:
        """Missing virality_score should raise ValidationError."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "virality_score"}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]

    def test_missing_headline_raises(self) -> None:
        """Missing headline should raise ValidationError."""
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "headline"}
        with pytest.raises(ValidationError):
            ContentBrief(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ContentBrief — immutability
# ---------------------------------------------------------------------------


class TestContentBriefImmutability:
    """Tests that ContentBrief is frozen (immutable)."""

    def test_assignment_raises(self) -> None:
        """Assigning a field after creation should raise ValidationError."""
        brief = ContentBrief(**VALID_PAYLOAD)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            brief.virality_score = 5.0  # type: ignore[misc]

    def test_assignment_headline_raises(self) -> None:
        """Assigning headline after creation should raise ValidationError."""
        brief = ContentBrief(**VALID_PAYLOAD)  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            brief.headline = "New headline"  # type: ignore[misc]
