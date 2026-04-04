# Module: Graphics Services

**Package:** `backend.src.services.graphics`
**Purpose:** SVG chart generation, AI background generation, and image compositing for the Visual Engine. Produces publication-ready PNG infographics from pandas DataFrames.

## Package Structure

```
services/graphics/
├── __init__.py           ← Re-exports constants, generate_chart_svg, AIImageClient, composite_image
├── svg_generator.py      ← Pure function: DataFrame → SVG bytes
├── ai_image_client.py    ← Mock AI image background generator
└── compositor.py         ← BG + SVG → publication-ready PNG
```

## Constants

### Size Presets

| Constant | Value | Target Platform |
|----------|-------|-----------------|
| `SIZE_INSTAGRAM` | `(1080, 1080)` | Instagram feed post |
| `SIZE_TWITTER` | `(1200, 628)` | Twitter/X card |
| `SIZE_REDDIT` | `(1200, 900)` | Reddit post |

All presets are module-level `tuple[int, int]` constants exported from both `svg_generator.py` and the package `__init__.py`.

### Neon Brand Palette

```python
NEON_PALETTE: list[str] = [
    "#00FF94",  # neon green
    "#00D4FF",  # neon blue
    "#FF006E",  # neon pink
    "#FFB700",  # neon yellow
    "#7B2FFF",  # neon purple
    "#FF4500",  # neon orange
]
```

Used as colour sequence for all chart traces. Single-series charts use `NEON_PALETTE[0]` (neon green). Multi-series charts (STACKED_BAR) cycle through the palette.

## Classes

### `AIImageClient` (ai_image_client.py) — ✅ Complete (Mock)

Mock AI background image generator. Produces synthetic dark-gradient PNGs with neon noise for infographic compositing.

```python
class AIImageClient:
    def __init__(self) -> None: ...

    async def generate_background(
        self,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes: ...
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Text description of desired background (logged, not used for generation in mock) |
| `size` | `tuple[int, int]` | `(width, height)` in pixels — output matches exactly |

**Returns:** `bytes` — PNG-encoded RGBA image.

**Mock behaviour:**
- Vertical dark gradient: `#1a1a2e` (top) → `#16213e` (bottom)
- Subtle neon noise pixels (deterministic seed=42 for reproducibility)
- Logs `ai_image.mock_generated` with `size` and `prompt_preview` (first 50 chars)

**Architecture:**
- Constructor is intentionally empty (ARCH-DPEN-001). Future versions will inject HTTP client, API key, etc.
- `# TODO: replace with real AI image API (Stable Diffusion / DALL-E / Imagen)`

## Functions

### `generate_chart_svg` (svg_generator.py) — ✅ Complete

Primary entry point. Pure function (ARCH-PURA-001).

```python
def generate_chart_svg(
    df: pd.DataFrame,
    chart_type: ChartType,
    size: tuple[int, int] = SIZE_INSTAGRAM,
) -> bytes:
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `df` | `pd.DataFrame` | — | Two-column minimum. Col 0 = X axis, Col 1+ = Y axis / values |
| `chart_type` | `ChartType` | — | One of 13 enum values from `services.ai.schemas` |
| `size` | `tuple[int, int]` | `SIZE_INSTAGRAM` | `(width, height)` in pixels |

**Returns:** `bytes` — Raw SVG document (UTF-8). Starts with `b'<svg'` after stripping whitespace.

**Raises:** `ValidationError` (from `src.core.exceptions`) if `df` is empty or has fewer than 2 columns.

### `composite_image` (compositor.py) — ✅ Complete

Composites an SVG chart over a background image into a final publication-ready PNG.

```python
def composite_image(
    bg_bytes: bytes,
    svg_bytes: bytes,
    *,
    dpi: int = 150,
    watermark: bool = True,
    watermark_text: str = "summa.vision",
) -> bytes:
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bg_bytes` | `bytes` | — | PNG-encoded background (from `AIImageClient`) |
| `svg_bytes` | `bytes` | — | SVG chart (from `generate_chart_svg`) |
| `dpi` | `int` | `150` | Rendering DPI for SVG rasterisation |
| `watermark` | `bool` | `True` | Add semi-transparent watermark |
| `watermark_text` | `str` | `"summa.vision"` | Watermark text |

**Returns:** `bytes` — PNG-encoded composite image.

**Pipeline (order of operations):**

1. Decode `bg_bytes` → Pillow RGBA image
2. Determine target size from background `(bg.width, bg.height)`
3. Rasterise SVG via `cairosvg.svg2png(output_width=target_w, output_height=target_h, dpi=dpi)`
4. Resize background if it doesn't match target (safety guard)
5. Alpha-composite SVG layer over background
6. Apply watermark (if enabled): semi-transparent white `(255, 255, 255, 128)`, 12px padding, `ImageFont.load_default()`
7. Save to PNG bytes

**DPI behaviour:**

| DPI | SIZE_INSTAGRAM bg | Output PNG |
|-----|-------------------|------------|
| 150 | 1080×1080 | 1080×1080 |
| 300 | 2160×2160 | 2160×2160 |

The output always matches the background dimensions. For high-res B2B output, provide a larger background.

### Supported ChartType Mappings

| ChartType | Plotly Trace | Details |
|-----------|-------------|---------|
| `LINE` | `go.Scatter(mode='lines')` | Single line, `NEON_PALETTE[0]` colour |
| `BAR` | `go.Bar` | Vertical bars, `NEON_PALETTE[0]` marker colour |
| `SCATTER` | `go.Scatter(mode='markers')` | Point markers, `NEON_PALETTE[0]` |
| `AREA` | `go.Scatter(mode='lines', fill='tozeroy')` | Filled area below line |
| `STACKED_BAR` | `go.Bar` + `barmode='stack'` | Stacks all numeric columns (col 1+). Cycles through `NEON_PALETTE` |
| `HEATMAP` | `go.Heatmap` | Col 0 = y-labels, remaining cols = x-labels + z-values. Custom neon colourscale |
| `CANDLESTICK` | `go.Candlestick` | OHLC data (currency rates, indices). `NEON_PALETTE[0]` increasing, `NEON_PALETTE[2]` decreasing |
| `PIE` | `go.Pie` | Proportional data (e.g. CPI composition). Cycles through `NEON_PALETTE` |
| `DONUT` | `go.Pie` with `hole=0.4` | Like PIE but with central hole |
| `WATERFALL` | `go.Waterfall` | YoY changes (GDP, budget). Green for increase, pink for decrease |
| `TREEMAP` | `go.Treemap` | Flat hierarchical data (budget by ministry). Cycles through `NEON_PALETTE` |
| `BUBBLE` | `go.Scatter(mode='markers')` | Scatter with sized markers. Sizes normalised to 10–60px range |
| `CHOROPLETH` | `go.Choropleth` | Canadian province map. Province codes (ON, BC, etc.) mapped to `CAN-XX` Plotly IDs |

### DataFrame Shape Requirements

| ChartType | Minimum Columns | Column Layout |
|-----------|----------------|---------------|
| `LINE`, `BAR`, `SCATTER`, `AREA` | 2 | Col 0 = X labels, Col 1 = Y values |
| `STACKED_BAR` | 2 | Col 0 = X labels, Col 1+ = Y series (stacked) |
| `HEATMAP` | 2 | Col 0 = Y labels, Col 1+ = X labels with Z values |
| `CANDLESTICK` | 5 | Col 0 = date/label, Col 1 = Open, Col 2 = High, Col 3 = Low, Col 4 = Close |
| `PIE`, `DONUT` | 2 | Col 0 = labels, Col 1 = values |
| `WATERFALL` | 2 | Col 0 = labels, Col 1 = values (positive = growth, negative = decline) |
| `TREEMAP` | 2 | Col 0 = labels (names), Col 1 = values (size) |
| `BUBBLE` | 3 | Col 0 = X axis, Col 1 = Y axis, Col 2 = bubble size |
| `CHOROPLETH` | 2 | Col 0 = province code (ON, BC, AB, QC, etc.), Col 1 = values |

## Styling Rules

Every chart generated by this module applies the following layout:

| Property | Value | Purpose |
|----------|-------|---------|
| `paper_bgcolor` | `rgba(0,0,0,0)` | Transparent outer background |
| `plot_bgcolor` | `rgba(0,0,0,0)` | Transparent plot area |
| `showgrid` | `False` (both axes) | Clean, minimal look |
| `showline` | `False` (both axes) | No axis lines |
| `zeroline` | `False` (both axes) | No zero reference line |
| `font.family` | `Arial, sans-serif` | Brand font |
| `font.color` | `#FFFFFF` | White text for dark backgrounds |
| `font.size` | `14` | Readable at social media scale |
| `legend.font.color` | `#FFFFFF` | White legend text |
| `legend.title.text` | `""` | No legend title |
| `margin` | `l=40, r=40, t=40, b=40` | Tight margins |

## Dependencies

| This module uses | This module is used by |
|------------------|----------------------|
| `plotly` (graph_objects, io) | `compositor.py` (SVG input) |
| `kaleido` (SVG export engine) | — |
| `Pillow` (raster image operations) | — |
| `CairoSVG` (SVG→PNG rasterisation) | — |
| `pandas` (DataFrame input) | — |
| `structlog` (logging in AIImageClient) | — |
| `src.core.exceptions` (ValidationError) | — |
| `src.services.ai.schemas` (ChartType) | — |

> [!IMPORTANT]
> `CairoSVG` requires the native `cairo` C library. On Linux/CI this is typically available (`libcairo2`). On Windows, install via GTK3 runtime. The lazy import in `compositor.py` prevents import-time failures when cairo is not installed.

> [!IMPORTANT]
> This module is **completely decoupled** from all AI services (`llm_interface`, `scoring_service`, etc.). It only imports `ChartType` from `schemas.py` as a shared enum.

## Architecture Rules Enforced

- **ARCH-PURA-001**: `generate_chart_svg` and `composite_image` are pure functions — no HTTP, no database, no file I/O (except in-memory operations).
- **ARCH-DPEN-001**: `AIImageClient` uses constructor injection. No global state. Mock implementation keeps the constructor empty but DI-ready.
- No bare `except:` — only `ValidationError` is raised explicitly.
- Strict type hints, `mypy`-compliant.
- No `Any` type annotations.

## Example Usage

```python
import asyncio
import pandas as pd
from src.services.ai.schemas import ChartType
from src.services.graphics import (
    AIImageClient,
    composite_image,
    generate_chart_svg,
    SIZE_TWITTER,
)

async def main():
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr"],
        "Revenue": [12000, 15500, 18200, 21000],
    })

    # 1. Generate SVG chart
    svg_bytes = generate_chart_svg(df, ChartType.BAR, size=SIZE_TWITTER)

    # 2. Generate AI background
    client = AIImageClient()
    bg_bytes = await client.generate_background(
        prompt="Canadian housing data visualization",
        size=SIZE_TWITTER,
    )

    # 3. Composite into final PNG
    png_bytes = composite_image(bg_bytes, svg_bytes, dpi=150)

    # png_bytes is ready for publication / S3 upload
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

asyncio.run(main())
```

---

## Maintenance

This file MUST be updated in the same PR that changes the described functionality.
If you add/modify/remove a class, module, rule, or test — update this doc in the same commit.
