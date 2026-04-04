"""Plotly-based SVG chart generator for the Visual Engine.

Produces transparent-background, neon-styled SVG charts from a pandas
DataFrame and a :class:`ChartType` enum value.  This module is a **pure
function** (ARCH-PURA-001) — no HTTP, no database, no file I/O beyond
the in-memory SVG serialisation performed by Plotly/Kaleido.

Supported chart types
---------------------
- ``LINE``        → ``go.Scatter(mode='lines')``
- ``BAR``         → ``go.Bar``
- ``SCATTER``     → ``go.Scatter(mode='markers')``
- ``AREA``        → ``go.Scatter(mode='lines', fill='tozeroy')``
- ``STACKED_BAR`` → ``go.Bar`` with ``barmode='stack'``
- ``HEATMAP``     → ``go.Heatmap``
- ``CANDLESTICK`` → ``go.Candlestick``
- ``PIE``         → ``go.Pie``
- ``DONUT``       → ``go.Pie`` with ``hole=0.4``
- ``WATERFALL``   → ``go.Waterfall``
- ``TREEMAP``     → ``go.Treemap``
- ``BUBBLE``      → ``go.Scatter(mode='markers')`` with sized markers
- ``CHOROPLETH``  → ``go.Choropleth`` (Canada provinces)

Example
-------
::

    import pandas as pd
    from src.services.ai.schemas import ChartType
    from src.services.graphics.svg_generator import generate_chart_svg, SIZE_TWITTER

    df = pd.DataFrame({"Month": ["Jan", "Feb", "Mar"], "Sales": [100, 150, 200]})
    svg_bytes = generate_chart_svg(df, ChartType.BAR, size=SIZE_TWITTER)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src.core.exceptions import ValidationError
from src.services.ai.schemas import ChartType

# ---------------------------------------------------------------------------
# Size preset constants (width, height) in pixels
# ---------------------------------------------------------------------------

SIZE_INSTAGRAM: tuple[int, int] = (1080, 1080)
SIZE_TWITTER: tuple[int, int] = (1200, 628)
SIZE_REDDIT: tuple[int, int] = (1200, 900)

# ---------------------------------------------------------------------------
# Neon brand colour palette
# ---------------------------------------------------------------------------

NEON_PALETTE: list[str] = [
    "#00FF94",  # neon green
    "#00D4FF",  # neon blue
    "#FF006E",  # neon pink
    "#FFB700",  # neon yellow
    "#7B2FFF",  # neon purple
    "#FF4500",  # neon orange
]

# ---------------------------------------------------------------------------
# Shared layout helpers (private)
# ---------------------------------------------------------------------------


def _base_layout(size: tuple[int, int]) -> go.Layout:
    """Return a Plotly ``Layout`` with the neon/transparent house style."""
    width, height = size
    return go.Layout(
        width=width,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color="#FFFFFF", size=14),
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(title=dict(text=""), font=dict(color="#FFFFFF")),
        xaxis=dict(showgrid=False, showline=False, zeroline=False),
        yaxis=dict(showgrid=False, showline=False, zeroline=False),
    )


def _validate_dataframe(df: pd.DataFrame, min_cols: int = 2) -> None:
    """Raise :class:`ValidationError` if *df* is empty or too narrow."""
    if df.empty:
        raise ValidationError(
            message="DataFrame is empty — cannot generate chart.",
            error_code="CHART_EMPTY_DF",
        )
    if len(df.columns) < min_cols:
        raise ValidationError(
            message=(
                f"DataFrame has {len(df.columns)} column(s); "
                f"at least {min_cols} are required."
            ),
            error_code="CHART_INSUFFICIENT_COLUMNS",
        )


# ---------------------------------------------------------------------------
# Trace builders (one per ChartType)
# ---------------------------------------------------------------------------


def _build_line(df: pd.DataFrame) -> list[go.Scatter]:
    x = df.iloc[:, 0]
    y = df.iloc[:, 1]
    return [
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color=NEON_PALETTE[0]),
        )
    ]


def _build_bar(df: pd.DataFrame) -> list[go.Bar]:
    x = df.iloc[:, 0]
    y = df.iloc[:, 1]
    return [go.Bar(x=x, y=y, marker_color=NEON_PALETTE[0])]


def _build_scatter(df: pd.DataFrame) -> list[go.Scatter]:
    x = df.iloc[:, 0]
    y = df.iloc[:, 1]
    return [
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker=dict(color=NEON_PALETTE[0]),
        )
    ]


def _build_area(df: pd.DataFrame) -> list[go.Scatter]:
    x = df.iloc[:, 0]
    y = df.iloc[:, 1]
    return [
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            fill="tozeroy",
            line=dict(color=NEON_PALETTE[0]),
            fillcolor=NEON_PALETTE[0],
        )
    ]


def _build_stacked_bar(df: pd.DataFrame) -> list[go.Bar]:
    x = df.iloc[:, 0]
    numeric_cols = df.columns[1:]
    traces: list[go.Bar] = []
    for idx, col in enumerate(numeric_cols):
        traces.append(
            go.Bar(
                x=x,
                y=df[col],
                name=str(col),
                marker_color=NEON_PALETTE[idx % len(NEON_PALETTE)],
            )
        )
    return traces


def _build_heatmap(df: pd.DataFrame) -> list[go.Heatmap]:
    y_labels = df.iloc[:, 0].astype(str).tolist()
    z_data = df.iloc[:, 1:].values.tolist()
    x_labels = [str(c) for c in df.columns[1:]]
    return [
        go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            colorscale=[
                [0.0, NEON_PALETTE[2]],   # neon pink
                [0.5, NEON_PALETTE[4]],   # neon purple
                [1.0, NEON_PALETTE[0]],   # neon green
            ],
        )
    ]


def _build_candlestick(df: pd.DataFrame) -> list[go.Candlestick]:
    """Build a candlestick chart (OHLC data — currency rates, indices)."""
    return [go.Candlestick(
        x=df.iloc[:, 0],
        open=df.iloc[:, 1],
        high=df.iloc[:, 2],
        low=df.iloc[:, 3],
        close=df.iloc[:, 4],
        increasing_line_color=NEON_PALETTE[0],
        decreasing_line_color=NEON_PALETTE[2],
    )]


def _build_pie(df: pd.DataFrame) -> list[go.Pie]:
    """Build a pie chart (proportional data — e.g. CPI composition)."""
    return [go.Pie(
        labels=df.iloc[:, 0],
        values=df.iloc[:, 1],
        marker=dict(colors=NEON_PALETTE),
        textfont=dict(color="#FFFFFF"),
    )]


def _build_donut(df: pd.DataFrame) -> list[go.Pie]:
    """Build a donut chart (pie with central hole)."""
    return [go.Pie(
        labels=df.iloc[:, 0],
        values=df.iloc[:, 1],
        hole=0.4,
        marker=dict(colors=NEON_PALETTE),
        textfont=dict(color="#FFFFFF"),
    )]


def _build_waterfall(df: pd.DataFrame) -> list[go.Waterfall]:
    """Build a waterfall chart (YoY changes — GDP, budget)."""
    values = df.iloc[:, 1].tolist()
    measures = ["relative"] * len(values)
    return [go.Waterfall(
        x=df.iloc[:, 0],
        y=values,
        measure=measures,
        increasing=dict(marker=dict(color=NEON_PALETTE[0])),
        decreasing=dict(marker=dict(color=NEON_PALETTE[2])),
        connector=dict(line=dict(color=NEON_PALETTE[1], width=1)),
        textfont=dict(color="#FFFFFF"),
    )]


def _build_treemap(df: pd.DataFrame) -> list[go.Treemap]:
    """Build a flat treemap (hierarchical data — budget by ministry)."""
    labels = df.iloc[:, 0].astype(str).tolist()
    values = df.iloc[:, 1].tolist()
    return [go.Treemap(
        labels=labels,
        values=values,
        parents=[""] * len(labels),
        marker=dict(
            colors=NEON_PALETTE * (len(labels) // len(NEON_PALETTE) + 1),
            colorscale=None,
        ),
        textfont=dict(color="#FFFFFF"),
    )]


def _build_bubble(df: pd.DataFrame) -> list[go.Scatter]:
    """Build a bubble chart (scatter with sized markers)."""
    sizes = df.iloc[:, 2].tolist()
    min_s, max_s = min(sizes), max(sizes)
    if max_s > min_s:
        norm = [10 + 50 * (s - min_s) / (max_s - min_s) for s in sizes]
    else:
        norm = [30] * len(sizes)
    return [go.Scatter(
        x=df.iloc[:, 0],
        y=df.iloc[:, 1],
        mode="markers",
        marker=dict(
            size=norm,
            color=NEON_PALETTE[0],
            opacity=0.8,
            line=dict(width=1, color=NEON_PALETTE[1]),
        ),
    )]


def _build_choropleth(df: pd.DataFrame) -> list[go.Choropleth]:
    """Build a choropleth map of Canadian provinces."""
    province_map = {
        "ON": "CAN-ON", "BC": "CAN-BC", "AB": "CAN-AB", "QC": "CAN-QC",
        "MB": "CAN-MB", "SK": "CAN-SK", "NS": "CAN-NS", "NB": "CAN-NB",
        "NL": "CAN-NL", "PE": "CAN-PE", "YT": "CAN-YT", "NT": "CAN-NT",
        "NU": "CAN-NU",
    }
    locations = [
        province_map.get(str(code).upper(), str(code))
        for code in df.iloc[:, 0]
    ]
    return [go.Choropleth(
        locations=locations,
        z=df.iloc[:, 1],
        locationmode="geojson-id",
        colorscale=[
            [0.0, NEON_PALETTE[2]],
            [0.5, NEON_PALETTE[4]],
            [1.0, NEON_PALETTE[0]],
        ],
        colorbar=dict(
            title=dict(text="", font=dict(color="#FFFFFF")),
            tickfont=dict(color="#FFFFFF"),
        ),
        marker=dict(line=dict(color="#141414", width=0.5)),
    )]


# ---------------------------------------------------------------------------
# Minimum column counts per chart type
# ---------------------------------------------------------------------------

_MIN_COLS: dict[ChartType, int] = {
    ChartType.LINE: 2,
    ChartType.BAR: 2,
    ChartType.SCATTER: 2,
    ChartType.AREA: 2,
    ChartType.STACKED_BAR: 2,
    ChartType.HEATMAP: 2,
    ChartType.CANDLESTICK: 5,
    ChartType.PIE: 2,
    ChartType.DONUT: 2,
    ChartType.WATERFALL: 2,
    ChartType.TREEMAP: 2,
    ChartType.BUBBLE: 3,
    ChartType.CHOROPLETH: 2,
}

# Map from ChartType → builder
_TRACE_BUILDERS: dict[
    ChartType,
    type[None],  # placeholder for type annotation — see assignment below
] = {}  # type: ignore[assignment]

# We populate at module level; mypy can't infer the union of return types
# so we use a plain dict and dispatch at runtime.
_BUILDERS = {
    ChartType.LINE: _build_line,
    ChartType.BAR: _build_bar,
    ChartType.SCATTER: _build_scatter,
    ChartType.AREA: _build_area,
    ChartType.STACKED_BAR: _build_stacked_bar,
    ChartType.HEATMAP: _build_heatmap,
    ChartType.CANDLESTICK: _build_candlestick,
    ChartType.PIE: _build_pie,
    ChartType.DONUT: _build_donut,
    ChartType.WATERFALL: _build_waterfall,
    ChartType.TREEMAP: _build_treemap,
    ChartType.BUBBLE: _build_bubble,
    ChartType.CHOROPLETH: _build_choropleth,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_chart_svg(
    df: pd.DataFrame,
    chart_type: ChartType,
    size: tuple[int, int] = SIZE_INSTAGRAM,
) -> bytes:
    """Generate a transparent-background SVG chart from *df*.

    Parameters
    ----------
    df:
        Two-column DataFrame.  Column 0 = X axis (labels/dates),
        column 1 = Y axis (numeric values).  For ``STACKED_BAR`` and
        ``HEATMAP``, additional numeric columns are supported.
    chart_type:
        One of the thirteen :class:`ChartType` enum values.
    size:
        ``(width, height)`` in pixels.  Defaults to :data:`SIZE_INSTAGRAM`.

    Returns
    -------
    bytes
        Raw SVG document encoded as UTF-8.  Starts with ``b'<svg'``
        (after stripping leading whitespace).

    Raises
    ------
    ValidationError
        If *df* is empty or has fewer than 2 columns.
    """
    _validate_dataframe(df, min_cols=_MIN_COLS[chart_type])

    builder = _BUILDERS[chart_type]
    traces = builder(df)

    layout = _base_layout(size)

    # Stacked bar requires barmode on the layout
    if chart_type is ChartType.STACKED_BAR:
        layout.barmode = "stack"  # type: ignore[attr-defined]

    # Choropleth requires geo settings for Canada
    if chart_type is ChartType.CHOROPLETH:
        layout.geo = dict(  # type: ignore[attr-defined]
            scope="north america",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#444444",
            showland=True,
            landcolor="#1a1a2e",
            showocean=True,
            oceancolor="#0d0d1a",
            showcountries=True,
            countrycolor="#333333",
            bgcolor="rgba(0,0,0,0)",
            projection=dict(type="mercator"),
            center=dict(lat=60, lon=-96),
            lataxis=dict(range=[41, 84]),
            lonaxis=dict(range=[-141, -52]),
        )

    fig = go.Figure(data=traces, layout=layout)

    # Render to SVG bytes via kaleido
    svg_bytes: bytes = pio.to_image(fig, format="svg")

    return svg_bytes
