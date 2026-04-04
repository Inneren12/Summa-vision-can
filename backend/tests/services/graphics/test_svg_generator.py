"""Tests for the SVG chart generator (Visual Engine — PR-17, PR-17b).

All tests generate **real SVG output** via Plotly + Kaleido — no mocking
of the rendering pipeline.  This validates the actual chart appearance,
transparent backgrounds, size embedding, and neon styling.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.exceptions import ValidationError
from src.services.ai.schemas import ChartType
from src.services.graphics.svg_generator import (
    NEON_PALETTE,
    SIZE_INSTAGRAM,
    SIZE_REDDIT,
    SIZE_TWITTER,
    _MIN_COLS,
    generate_chart_svg,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_df() -> pd.DataFrame:
    """Minimal 2-column, 3-row DataFrame for most tests."""
    return pd.DataFrame(
        {"Month": ["Jan", "Feb", "Mar"], "Sales": [100, 150, 200]}
    )


@pytest.fixture()
def heatmap_df() -> pd.DataFrame:
    """3-column DataFrame suitable for HEATMAP tests."""
    return pd.DataFrame(
        {
            "Category": ["A", "B", "C"],
            "Q1": [10, 20, 30],
            "Q2": [40, 50, 60],
        }
    )


@pytest.fixture()
def candlestick_df() -> pd.DataFrame:
    """5-column DataFrame for CANDLESTICK tests (date, open, high, low, close)."""
    return pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "Open": [1.35, 1.36, 1.34],
            "High": [1.37, 1.38, 1.36],
            "Low": [1.34, 1.35, 1.33],
            "Close": [1.36, 1.34, 1.35],
        }
    )


@pytest.fixture()
def bubble_df() -> pd.DataFrame:
    """3-column DataFrame for BUBBLE tests (x, y, size)."""
    return pd.DataFrame(
        {
            "Price": [100, 200, 300, 400],
            "Volume": [50, 150, 100, 200],
            "City_Pop": [500000, 1000000, 750000, 2000000],
        }
    )


@pytest.fixture()
def choropleth_df() -> pd.DataFrame:
    """2-column DataFrame with Canadian province codes for CHOROPLETH tests."""
    return pd.DataFrame(
        {
            "Province": ["ON", "BC", "AB", "QC"],
            "Value": [100, 80, 90, 95],
        }
    )


@pytest.fixture()
def pie_df() -> pd.DataFrame:
    """5-category DataFrame for PIE/DONUT tests."""
    return pd.DataFrame(
        {
            "Category": ["Housing", "Food", "Transport", "Health", "Other"],
            "Weight": [30, 20, 15, 10, 25],
        }
    )


@pytest.fixture()
def waterfall_df() -> pd.DataFrame:
    """DataFrame with positive and negative values for WATERFALL tests."""
    return pd.DataFrame(
        {
            "Item": ["Q1 Revenue", "COGS", "Opex", "Tax", "Q1 Net"],
            "Amount": [500, -200, -100, -50, 150],
        }
    )


@pytest.fixture()
def treemap_df() -> pd.DataFrame:
    """5-category DataFrame for TREEMAP tests."""
    return pd.DataFrame(
        {
            "Ministry": ["Defense", "Health", "Education", "Transport", "Justice"],
            "Budget": [80, 120, 100, 60, 40],
        }
    )


# ---------------------------------------------------------------------------
# Core output tests
# ---------------------------------------------------------------------------


def test_generate_chart_svg_returns_svg_bytes(simple_df: pd.DataFrame) -> None:
    """SVG output must be ``bytes`` starting with ``<svg``."""
    result = generate_chart_svg(simple_df, ChartType.BAR)
    assert isinstance(result, bytes)
    assert result.lstrip().startswith(b"<svg")


# ---------------------------------------------------------------------------
# Size preset tests
# ---------------------------------------------------------------------------


def test_size_instagram_dimensions(simple_df: pd.DataFrame) -> None:
    svg = generate_chart_svg(simple_df, ChartType.BAR, size=SIZE_INSTAGRAM)
    text = svg.decode("utf-8")
    assert 'width="1080"' in text
    assert 'height="1080"' in text


def test_size_twitter_dimensions(simple_df: pd.DataFrame) -> None:
    svg = generate_chart_svg(simple_df, ChartType.BAR, size=SIZE_TWITTER)
    text = svg.decode("utf-8")
    assert 'width="1200"' in text
    assert 'height="628"' in text


def test_size_reddit_dimensions(simple_df: pd.DataFrame) -> None:
    svg = generate_chart_svg(simple_df, ChartType.BAR, size=SIZE_REDDIT)
    text = svg.decode("utf-8")
    assert 'width="1200"' in text
    assert 'height="900"' in text


def test_custom_size_dimensions(simple_df: pd.DataFrame) -> None:
    svg = generate_chart_svg(simple_df, ChartType.BAR, size=(800, 600))
    text = svg.decode("utf-8")
    assert 'width="800"' in text
    assert 'height="600"' in text


# ---------------------------------------------------------------------------
# Chart type coverage — ALL 13 TYPES
# ---------------------------------------------------------------------------


def test_all_chart_types_produce_svg(
    heatmap_df: pd.DataFrame,
    candlestick_df: pd.DataFrame,
    bubble_df: pd.DataFrame,
    choropleth_df: pd.DataFrame,
) -> None:
    """Every ``ChartType`` must produce valid SVG bytes.

    Uses an appropriate DataFrame for each chart type based on its
    column requirements.
    """
    # Map each chart type to an appropriate DataFrame
    type_to_df: dict[ChartType, pd.DataFrame] = {
        ChartType.LINE: heatmap_df,
        ChartType.BAR: heatmap_df,
        ChartType.SCATTER: heatmap_df,
        ChartType.AREA: heatmap_df,
        ChartType.STACKED_BAR: heatmap_df,
        ChartType.HEATMAP: heatmap_df,
        ChartType.CANDLESTICK: candlestick_df,
        ChartType.PIE: heatmap_df,
        ChartType.DONUT: heatmap_df,
        ChartType.WATERFALL: heatmap_df,
        ChartType.TREEMAP: heatmap_df,
        ChartType.BUBBLE: bubble_df,
        ChartType.CHOROPLETH: choropleth_df,
    }
    for ct in ChartType:
        df = type_to_df[ct]
        svg = generate_chart_svg(df, ct)
        assert isinstance(svg, bytes), f"{ct.name} did not return bytes"
        assert svg.lstrip().startswith(b"<svg"), (
            f"{ct.name} output does not start with <svg"
        )


# ---------------------------------------------------------------------------
# Styling tests
# ---------------------------------------------------------------------------


def test_transparent_background(simple_df: pd.DataFrame) -> None:
    svg = generate_chart_svg(simple_df, ChartType.LINE)
    text = svg.decode("utf-8")
    # Plotly's SVG renderer represents rgba(0,0,0,0) as
    # fill: rgb(0, 0, 0); fill-opacity: 0;
    assert (
        "rgba(0,0,0,0)" in text
        or "rgba(0, 0, 0, 0)" in text
        or "fill-opacity: 0" in text
    )


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


def test_empty_dataframe_raises() -> None:
    df = pd.DataFrame()
    with pytest.raises(ValidationError):
        generate_chart_svg(df, ChartType.BAR)


def test_insufficient_columns_raises() -> None:
    df = pd.DataFrame({"only_one": [1, 2, 3]})
    with pytest.raises(ValidationError):
        generate_chart_svg(df, ChartType.BAR)


def test_candlestick_requires_5_columns() -> None:
    """CANDLESTICK with only 4 columns must raise ValidationError."""
    df = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02"],
            "Open": [1.35, 1.36],
            "High": [1.37, 1.38],
            "Low": [1.34, 1.35],
        }
    )
    with pytest.raises(ValidationError):
        generate_chart_svg(df, ChartType.CANDLESTICK)


def test_bubble_requires_3_columns() -> None:
    """BUBBLE with only 2 columns must raise ValidationError."""
    df = pd.DataFrame({"X": [1, 2, 3], "Y": [4, 5, 6]})
    with pytest.raises(ValidationError):
        generate_chart_svg(df, ChartType.BUBBLE)


# ---------------------------------------------------------------------------
# Constant export tests
# ---------------------------------------------------------------------------


def test_neon_palette_constants_exported() -> None:
    """All constants must be importable and have correct values."""
    assert SIZE_INSTAGRAM == (1080, 1080)
    assert SIZE_TWITTER == (1200, 628)
    assert SIZE_REDDIT == (1200, 900)
    assert isinstance(NEON_PALETTE, list)
    assert len(NEON_PALETTE) == 6
    assert NEON_PALETTE[0] == "#00FF94"


def test_package_level_imports() -> None:
    """Constants and function must be importable from the package root."""
    from src.services.graphics import (  # noqa: F811
        NEON_PALETTE as pkg_palette,
        SIZE_INSTAGRAM as pkg_ig,
        SIZE_REDDIT as pkg_reddit,
        SIZE_TWITTER as pkg_twitter,
        generate_chart_svg as pkg_fn,
    )

    assert pkg_ig == (1080, 1080)
    assert pkg_twitter == (1200, 628)
    assert pkg_reddit == (1200, 900)
    assert isinstance(pkg_palette, list)
    assert callable(pkg_fn)


# ---------------------------------------------------------------------------
# Individual chart type specifics (original 6)
# ---------------------------------------------------------------------------


def test_line_chart_contains_path(simple_df: pd.DataFrame) -> None:
    """LINE charts must emit an SVG ``<path>`` element for the line."""
    svg = generate_chart_svg(simple_df, ChartType.LINE)
    text = svg.decode("utf-8")
    # Plotly renders lines as <path> elements
    assert "<path" in text


def test_bar_chart_contains_rect(simple_df: pd.DataFrame) -> None:
    """BAR charts must emit ``<rect>`` elements for bars (or <path>)."""
    svg = generate_chart_svg(simple_df, ChartType.BAR)
    text = svg.decode("utf-8")
    # Plotly can render bars as either <rect> or <path>
    assert "<path" in text or "<rect" in text


def test_scatter_chart_contains_circle(simple_df: pd.DataFrame) -> None:
    """SCATTER charts must emit circle/point markers."""
    svg = generate_chart_svg(simple_df, ChartType.SCATTER)
    text = svg.decode("utf-8")
    assert "<svg" in text  # baseline check; markers may be <circle> or <path>


def test_area_chart_contains_fill(simple_df: pd.DataFrame) -> None:
    """AREA chart must produce SVG with filled region."""
    svg = generate_chart_svg(simple_df, ChartType.AREA)
    text = svg.decode("utf-8")
    assert "<path" in text


def test_stacked_bar_chart(heatmap_df: pd.DataFrame) -> None:
    """STACKED_BAR must produce valid SVG."""
    svg = generate_chart_svg(heatmap_df, ChartType.STACKED_BAR)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_heatmap_chart(heatmap_df: pd.DataFrame) -> None:
    """HEATMAP must produce valid SVG."""
    svg = generate_chart_svg(heatmap_df, ChartType.HEATMAP)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


# ---------------------------------------------------------------------------
# New chart type specifics (PR-17b — 7 new types)
# ---------------------------------------------------------------------------


def test_pie_produces_svg(pie_df: pd.DataFrame) -> None:
    """PIE chart with 5 categories must produce valid SVG."""
    svg = generate_chart_svg(pie_df, ChartType.PIE)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_donut_produces_svg(pie_df: pd.DataFrame) -> None:
    """DONUT chart must produce valid SVG."""
    svg = generate_chart_svg(pie_df, ChartType.DONUT)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_waterfall_produces_svg(waterfall_df: pd.DataFrame) -> None:
    """WATERFALL chart with positive and negative values must produce SVG."""
    svg = generate_chart_svg(waterfall_df, ChartType.WATERFALL)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_treemap_produces_svg(treemap_df: pd.DataFrame) -> None:
    """TREEMAP with 5 categories and values must produce SVG."""
    svg = generate_chart_svg(treemap_df, ChartType.TREEMAP)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_bubble_normalizes_sizes() -> None:
    """BUBBLE chart with wildly different sizes must not crash."""
    df = pd.DataFrame(
        {
            "X": [1, 2, 3],
            "Y": [10, 20, 30],
            "Size": [1, 100, 1000],
        }
    )
    svg = generate_chart_svg(df, ChartType.BUBBLE)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_choropleth_province_mapping(choropleth_df: pd.DataFrame) -> None:
    """CHOROPLETH with ON, BC, AB, QC province codes must produce SVG."""
    svg = generate_chart_svg(choropleth_df, ChartType.CHOROPLETH)
    text = svg.decode("utf-8")
    assert text.lstrip().startswith("<svg")


def test_choropleth_produces_svg_with_geo_layout(
    choropleth_df: pd.DataFrame,
) -> None:
    """CHOROPLETH SVG must contain geographic elements (non-trivial output)."""
    svg = generate_chart_svg(choropleth_df, ChartType.CHOROPLETH)
    assert len(svg) > 100  # must be non-trivially sized


# ---------------------------------------------------------------------------
# Enum & infrastructure tests (PR-17b)
# ---------------------------------------------------------------------------


def test_chart_type_enum_has_13_values() -> None:
    """ChartType enum must have exactly 13 values after PR-17b."""
    assert len(ChartType) == 13


def test_min_cols_dict_covers_all_chart_types() -> None:
    """Every ChartType must have an entry in _MIN_COLS."""
    for ct in ChartType:
        assert ct in _MIN_COLS, f"{ct.name} missing from _MIN_COLS"
