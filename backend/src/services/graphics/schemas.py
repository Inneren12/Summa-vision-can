"""Chart configuration and enums for SVG generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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


class ChartConfig(BaseModel):
    """Configuration for chart rendering.

    Controls visual appearance of the generated SVG chart.
    All fields have sensible defaults for StatCan data visualization.
    """

    title: str = ""
    x_label: str = ""
    y_label: str = ""
    show_legend: bool = True
    color_palette: list[str] = Field(
        default_factory=lambda: [
            "#00FF88",  # neon green
            "#00AAFF",  # neon blue
            "#FF6644",  # coral
            "#FFAA00",  # amber
            "#AA44FF",  # purple
            "#FF44AA",  # pink
        ]
    )
    transparent_bg: bool = True
    show_grid: bool = False
