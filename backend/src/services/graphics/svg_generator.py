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
from src.services.graphics.schemas import ChartConfig

# ---------------------------------------------------------------------------
# StatCan column mapping
# ---------------------------------------------------------------------------
# DataFetchService (A-5) produces DataFrames with these columns.
# The chart generator maps them to Plotly trace axes.

STATCAN_DATE_COL = "REF_DATE"
STATCAN_VALUE_COL = "VALUE"
STATCAN_VALUE_SCALED_COL = "VALUE_SCALED"  # After scalar normalization
STATCAN_GEO_COL = "GEO"

# Size presets for distribution channels
SIZE_PRESETS: dict[str, tuple[int, int]] = {
    "instagram": (1080, 1080),
    "twitter": (1200, 628),
    "reddit": (1200, 900),
    "square": (1080, 1080),
    "wide": (1920, 1080),
}

# ---------------------------------------------------------------------------
# Size preset constants (width, height) in pixels (Legacy)
# ---------------------------------------------------------------------------

SIZE_INSTAGRAM: tuple[int, int] = SIZE_PRESETS["instagram"]
SIZE_TWITTER: tuple[int, int] = SIZE_PRESETS["twitter"]
SIZE_REDDIT: tuple[int, int] = SIZE_PRESETS["reddit"]

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
# DataFrame abstraction helpers (work with both Polars and Pandas)
# ---------------------------------------------------------------------------

def _get_columns(df: object) -> list[str]:
    """Get column names from Polars or Pandas DataFrame."""
    if hasattr(df, "columns"):
        return list(df.columns)
    return []


def _get_column_values(df: object, col: str) -> list:
    """Extract column values as a Python list."""
    if hasattr(df, "to_series"):
        # Polars
        return df[col].to_list()
    elif hasattr(df, "iloc"):
        # Pandas
        return df[col].tolist()
    return list(df[col])


def _get_unique_values(df: object, col: str) -> list:
    """Get unique values from a column."""
    if hasattr(df, "to_series"):
        # Polars
        return df[col].unique().sort().to_list()
    elif hasattr(df, "iloc"):
        # Pandas
        return sorted(df[col].unique().tolist())
    return list(set(df[col]))


def _filter_df(df: object, col: str, value: object) -> object:
    """Filter DataFrame to rows where col == value."""
    try:
        import polars as pl
        if isinstance(df, pl.DataFrame):
            return df.filter(pl.col(col) == value)
    except ImportError:
        pass

    # Pandas fallback
    if hasattr(df, "iloc"):
        return df[df[col] == value]

    return df


def _pick_value_col(df: object) -> str:
    """Pick the best value column from available columns.

    Prefers VALUE_SCALED (normalized) over raw VALUE.
    """
    columns = _get_columns(df)
    if STATCAN_VALUE_SCALED_COL in columns:
        return STATCAN_VALUE_SCALED_COL
    if STATCAN_VALUE_COL in columns:
        return STATCAN_VALUE_COL
    # Fallback: first numeric-looking column
    for col in columns:
        if col.upper() in ("VALUE", "VALUES", "AMOUNT", "RATE"):
            return col
    raise ValueError(
        f"Cannot determine value column. Available: {columns}. "
        f"Pass value_col explicitly."
    )


def _parse_statcan_dates(
    date_series: list[str] | list[object],
) -> list[datetime]:
    """Parse StatCan date strings to datetime objects.

    Handles formats:
        "2024-01-01" → datetime(2024, 1, 1)
        "2024-01"    → datetime(2024, 1, 1)
        "2024"       → datetime(2024, 1, 1)

    Also handles Polars Date/Datetime objects that may come
    from read_parquet.
    """
    from datetime import datetime, date

    parsed = []
    for d in date_series:
        if isinstance(d, datetime):
            parsed.append(d)
        elif isinstance(d, date):
            parsed.append(datetime(d.year, d.month, d.day))
        elif isinstance(d, str):
            for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
                try:
                    parsed.append(datetime.strptime(d, fmt))
                    break
                except ValueError:
                    continue
            else:
                # Last resort: try pandas-style
                parsed.append(datetime(int(d[:4]), 1, 1))
        else:
            # Polars datetime might be a Python datetime already
            parsed.append(d)
    return parsed


def _downsample(
    x: list,
    y: list,
    max_points: int = 500,
) -> tuple[list, list]:
    """Downsample data if it exceeds max_points (R15).

    Uses simple every-nth-point strategy. For production, could
    use LTTB (Largest Triangle Three Buckets) algorithm.

    Args:
        x: X-axis values.
        y: Y-axis values.
        max_points: Maximum number of data points.

    Returns:
        Downsampled (x, y) tuple.
    """
    if len(x) <= max_points:
        return x, y

    step = len(x) / max_points
    indices = [int(i * step) for i in range(max_points)]
    # Always include last point
    if indices[-1] != len(x) - 1:
        indices[-1] = len(x) - 1

    return [x[i] for i in indices], [y[i] for i in indices]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _generate_chart_svg_legacy(
    df: pd.DataFrame,
    chart_type: ChartType,
    size: tuple[int, int] = SIZE_INSTAGRAM,
) -> bytes:
    """Generate a transparent-background SVG chart from *df*. (Legacy support)"""
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


def generate_chart_svg(
    df: object,  # Polars DataFrame or Pandas DataFrame
    chart_type: str | ChartType = "line",
    size: tuple[int, int] | str = (1200, 900),
    config: ChartConfig | None = None,
    value_col: str | None = None,
    date_col: str | None = None,
    geo_col: str | None = None,
    max_points: int = 500,
) -> bytes:
    """Generate a transparent-background SVG chart from a DataFrame.

    Accepts both Polars and Pandas DataFrames. For Polars DataFrames,
    converts to lists internally (chart libraries need plain Python types).
    Also accepts legacy two-column Pandas DataFrames with a ChartType enum.

    Args:
        df: Input DataFrame with StatCan-shaped columns.
        chart_type: One of "line", "bar", "scatter", "area",
            "stacked_bar", "heatmap", or a ChartType enum.
        size: Tuple (width, height) in pixels, or preset name
            ("instagram", "twitter", "reddit").
        config: Visual configuration. Uses defaults if None.
        value_col: Override value column (default: VALUE_SCALED or VALUE).
        date_col: Override date column (default: REF_DATE).
        geo_col: Override geography column (default: GEO).
        max_points: Downsample threshold (R15, default 500).

    Returns:
        SVG bytes (starts with ``<svg``).
    """
    # Legacy support
    if isinstance(chart_type, ChartType) or isinstance(df, pd.DataFrame) and _get_columns(df) and _get_columns(df)[0] != STATCAN_DATE_COL and len(_get_columns(df)) <= 5 and not (STATCAN_DATE_COL in _get_columns(df)):
        ct = chart_type if isinstance(chart_type, ChartType) else ChartType(chart_type.upper())
        s = size if isinstance(size, tuple) else SIZE_PRESETS.get(size.lower(), SIZE_INSTAGRAM)
        return _generate_chart_svg_legacy(df, ct, s)

    if config is None:
        config = ChartConfig()

    # Resolve size preset
    if isinstance(size, str):
        size = SIZE_PRESETS.get(size.lower(), (1200, 900))

    width, height = size

    # --- Extract data from DataFrame ---
    _date_col = date_col or STATCAN_DATE_COL
    _value_col = value_col or _pick_value_col(df)
    _geo_col = geo_col or STATCAN_GEO_COL

    columns = _get_columns(df)

    if _date_col not in columns:
        raise ValueError(f"Date column '{_date_col}' not found. Available: {columns}")
    if _value_col not in columns:
        raise ValueError(f"Value column '{_value_col}' not found. Available: {columns}")

    # --- Extract series per geography ---
    traces = []
    geo_groups = _get_unique_values(df, _geo_col) if _geo_col in columns else [None]

    for i, geo in enumerate(geo_groups):
        if geo is not None:
            subset = _filter_df(df, _geo_col, geo)
        else:
            subset = df

        x_raw = _get_column_values(subset, _date_col)
        y_raw = _get_column_values(subset, _value_col)

        # Parse dates
        x_parsed = _parse_statcan_dates(x_raw)

        # Convert y to float, handling None/null
        y_parsed = [float(v) if v is not None else None for v in y_raw]

        # Downsample if needed (R15)
        x_final, y_final = _downsample(x_parsed, y_parsed, max_points)

        color = config.color_palette[i % len(config.color_palette)]
        name = str(geo) if geo is not None else "Value"

        ct_str = chart_type.lower() if isinstance(chart_type, str) else chart_type.name.lower()

        if ct_str == "bar":
            traces.append(go.Bar(x=x_final, y=y_final, name=name,
                                 marker_color=color))
        elif ct_str == "stacked_bar":
            traces.append(go.Bar(x=x_final, y=y_final, name=name,
                                 marker_color=color))
        elif ct_str == "scatter":
            traces.append(go.Scatter(x=x_final, y=y_final, name=name,
                                     mode="markers", marker_color=color))
        elif ct_str == "area":
            traces.append(go.Scatter(x=x_final, y=y_final, name=name,
                                     fill="tozeroy", line_color=color))
        elif ct_str == "heatmap":
            traces.append(go.Heatmap(x=x_final, y=y_final, z=[y_final],
                                     colorscale=[[0, "#000000"], [1, color]]))
        else:  # line (default)
            traces.append(go.Scatter(x=x_final, y=y_final, name=name,
                                     mode="lines", line_color=color))

    # --- Layout ---
    layout = go.Layout(
        title=dict(text=config.title, font=dict(color="white", size=24)),
        xaxis=dict(
            title=config.x_label,
            showgrid=config.show_grid,
            color="white",
            gridcolor="rgba(255,255,255,0.1)",
        ),
        yaxis=dict(
            title=config.y_label,
            showgrid=config.show_grid,
            color="white",
            gridcolor="rgba(255,255,255,0.1)",
        ),
        paper_bgcolor="rgba(0,0,0,0)" if config.transparent_bg else "#141414",
        plot_bgcolor="rgba(0,0,0,0)" if config.transparent_bg else "#1a1a2e",
        font=dict(color="white"),
        showlegend=config.show_legend and len(traces) > 1,
        width=width,
        height=height,
        margin=dict(l=60, r=30, t=60, b=50),
    )

    ct_str = chart_type.lower() if isinstance(chart_type, str) else chart_type.name.lower()
    if ct_str == "stacked_bar":
        layout.barmode = "stack"

    fig = go.Figure(data=traces, layout=layout)

    # --- Export as SVG ---
    svg_bytes: bytes = pio.to_image(fig, format="svg", width=width, height=height)

    return svg_bytes
