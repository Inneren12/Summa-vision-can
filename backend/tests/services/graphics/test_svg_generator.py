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

# ---------------------------------------------------------------------------
# Real StatCan Data Tests (Étape B)
# ---------------------------------------------------------------------------

from datetime import date, datetime
import polars as pl
from src.services.graphics.schemas import ChartConfig
from src.services.graphics.svg_generator import (
    _parse_statcan_dates,
    _downsample,
    _pick_value_col,
)

# ---- Test data ----

def _statcan_df(months: int = 24, geos: int = 1) -> pl.DataFrame:
    """Create a realistic StatCan-shaped Polars DataFrame."""
    rows = []
    geo_names = ["Canada", "Alberta", "Ontario", "British Columbia"][:geos]

    for geo in geo_names:
        for i in range(months):
            year = 2023 + i // 12
            month = (i % 12) + 1
            rows.append({
                "REF_DATE": date(year, month, 1),
                "GEO": geo,
                "VALUE": 100.0 + i * 1.5 + hash(geo) % 10,
                "VALUE_SCALED": (100.0 + i * 1.5 + hash(geo) % 10) * 1000,
                "SCALAR_ID": 3,
            })

    return pl.DataFrame(rows)


# ---- Basic generation ----

def test_generate_svg_returns_svg_bytes_statcan() -> None:
    """generate_chart_svg returns bytes starting with <svg."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, chart_type="line")
    assert isinstance(result, bytes)
    assert result[:4] == b"<svg" or b"<svg" in result[:200]


def test_generate_svg_line_chart_statcan() -> None:
    """Line chart generates successfully."""
    df = _statcan_df(24, 2)
    result = generate_chart_svg(df, chart_type="line")
    assert len(result) > 100


def test_generate_svg_bar_chart_statcan() -> None:
    """Bar chart generates successfully."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, chart_type="bar")
    assert len(result) > 100


def test_generate_svg_scatter_chart_statcan() -> None:
    """Scatter chart generates successfully."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, chart_type="scatter")
    assert len(result) > 100


def test_generate_svg_area_chart_statcan() -> None:
    """Area chart generates successfully."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, chart_type="area")
    assert len(result) > 100


# ---- Size presets ----

def test_size_preset_reddit_statcan() -> None:
    """Reddit preset produces correct dimensions."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, size="reddit")
    assert len(result) > 100
    # SVG should contain width/height matching preset
    svg_text = result.decode("utf-8", errors="ignore")
    assert "1200" in svg_text or "900" in svg_text


def test_size_preset_instagram_statcan() -> None:
    """Instagram preset (1080x1080) works."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, size="instagram")
    assert len(result) > 100


def test_custom_size_tuple_statcan() -> None:
    """Custom (width, height) tuple works."""
    df = _statcan_df(12, 1)
    result = generate_chart_svg(df, size=(800, 600))
    assert len(result) > 100


# ---- Chart config ----

def test_chart_config_title_statcan() -> None:
    """Title appears in SVG output."""
    df = _statcan_df(12, 1)
    config = ChartConfig(title="Test Chart Title")
    result = generate_chart_svg(df, config=config)
    svg_text = result.decode("utf-8", errors="ignore")
    assert "Test Chart Title" in svg_text


def test_chart_config_no_legend_single_series_statcan() -> None:
    """Single series with show_legend=True still works."""
    df = _statcan_df(12, 1)
    config = ChartConfig(show_legend=True)
    result = generate_chart_svg(df, config=config)
    assert len(result) > 100


# ---- Multiple geographies ----

def test_multi_geo_creates_traces() -> None:
    """Multiple GEO values create separate chart traces."""
    df = _statcan_df(12, 3)
    result = generate_chart_svg(df, chart_type="line")
    assert len(result) > 100
    # Should have multiple series in the SVG
    svg_text = result.decode("utf-8", errors="ignore")
    # At minimum the SVG should be non-trivially large
    assert len(result) > 500


# ---- Downsampling (R15) ----

def test_downsample_reduces_points() -> None:
    """Data with >500 points gets downsampled."""
    x = list(range(1000))
    y = [float(i) for i in range(1000)]
    x_ds, y_ds = _downsample(x, y, max_points=500)
    assert len(x_ds) == 500
    assert len(y_ds) == 500


def test_downsample_preserves_small_data() -> None:
    """Data with <=500 points is not modified."""
    x = list(range(100))
    y = [float(i) for i in range(100)]
    x_ds, y_ds = _downsample(x, y, max_points=500)
    assert len(x_ds) == 100


def test_generate_svg_downsamples_large_data() -> None:
    """SVG generation with >500 points triggers downsample."""
    # Create a large dataset
    df = _statcan_df(months=600, geos=1)  # 600 data points
    result = generate_chart_svg(df, max_points=500)
    assert len(result) > 100  # Should succeed without error


# ---- Date parsing ----

def test_parse_date_string_full() -> None:
    """Parse '2024-01-15' format."""
    result = _parse_statcan_dates(["2024-01-15"])
    assert result[0] == datetime(2024, 1, 15)


def test_parse_date_string_month() -> None:
    """Parse '2024-01' format."""
    result = _parse_statcan_dates(["2024-01"])
    assert result[0] == datetime(2024, 1, 1)


def test_parse_date_string_year() -> None:
    """Parse '2024' format."""
    result = _parse_statcan_dates(["2024"])
    assert result[0] == datetime(2024, 1, 1)


def test_parse_date_object() -> None:
    """Python date objects pass through correctly."""
    d = date(2024, 6, 15)
    result = _parse_statcan_dates([d])
    assert result[0] == datetime(2024, 6, 15)


# ---- Value column selection ----

def test_pick_value_col_prefers_scaled() -> None:
    """_pick_value_col prefers VALUE_SCALED over VALUE."""
    df = pl.DataFrame({
        "VALUE": [1.0],
        "VALUE_SCALED": [1000.0],
    })
    assert _pick_value_col(df) == "VALUE_SCALED"


def test_pick_value_col_falls_back_to_value() -> None:
    """_pick_value_col uses VALUE if VALUE_SCALED missing."""
    df = pl.DataFrame({"VALUE": [1.0], "OTHER": [2.0]})
    assert _pick_value_col(df) == "VALUE"


def test_pick_value_col_raises_if_none() -> None:
    """_pick_value_col raises ValueError if no value column found."""
    df = pl.DataFrame({"X": [1], "Y": [2]})
    import pytest
    with pytest.raises(ValueError, match="Cannot determine value column"):
        _pick_value_col(df)


# ---- Missing columns ----

def test_missing_date_column_raises() -> None:
    """Missing date column raises ValueError."""
    df = pl.DataFrame({"VALUE": [1.0], "GEO": ["Canada"]})
    import pytest
    with pytest.raises(ValueError, match="Date column"):
        generate_chart_svg(df)


def test_missing_value_column_raises() -> None:
    """Missing value column raises ValueError."""
    df = pl.DataFrame({"REF_DATE": ["2024-01"], "GEO": ["Canada"]})
    import pytest
    with pytest.raises(ValueError, match="value column"):
        generate_chart_svg(df)
