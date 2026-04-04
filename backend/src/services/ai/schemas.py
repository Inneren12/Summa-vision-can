"""Pydantic V2 schemas for the AI scoring pipeline.

Defines ``ContentBrief`` — the structured output format returned by the
LLM Gate when evaluating a Statistics Canada dataset for virality — and
``ChartType``, the enum of supported chart visualisations.

These models are passed as the ``schema`` argument to
:meth:`GeminiClient.generate_structured` so that Gemini responses are
validated and typed at the boundary.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ChartType(str, Enum):
    """Supported chart types for infographic generation.

    Each value maps to a Plotly trace type used by the Visual Engine
    (PR-17, PR-17b).
    """

    LINE = "LINE"
    BAR = "BAR"
    SCATTER = "SCATTER"
    AREA = "AREA"
    STACKED_BAR = "STACKED_BAR"
    HEATMAP = "HEATMAP"
    CANDLESTICK = "CANDLESTICK"
    PIE = "PIE"
    DONUT = "DONUT"
    WATERFALL = "WATERFALL"
    TREEMAP = "TREEMAP"
    BUBBLE = "BUBBLE"
    CHOROPLETH = "CHOROPLETH"


class ContentBrief(BaseModel):
    """Structured LLM output for dataset virality assessment.

    Frozen model — instances are immutable once created.

    Attributes:
        virality_score: Score from 1.0 to 10.0 indicating viral potential.
        headline: Punchy social media headline (max 280 chars).
        bg_prompt: Detailed AI image generation prompt for the background.
        chart_type: Recommended chart type from :class:`ChartType`.
        reasoning: Optional LLM reasoning for debugging (ignored in
            production flows).
    """

    model_config = ConfigDict(frozen=True)

    virality_score: float = Field(
        ge=1.0,
        le=10.0,
        description="Virality score from 1.0 (low) to 10.0 (high).",
    )
    headline: str = Field(
        min_length=1,
        max_length=280,
        description="Suggested social media headline.",
    )
    bg_prompt: str = Field(
        min_length=1,
        description="AI image generation prompt for the background.",
    )
    chart_type: ChartType = Field(
        description="Recommended chart type for the infographic.",
    )
    reasoning: str | None = Field(
        default=None,
        description="Optional LLM reasoning (useful for debugging).",
    )
