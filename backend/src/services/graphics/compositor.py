"""Image compositor — merges AI background + SVG chart into final PNG.

This module is the second layer of the Visual Engine pipeline:

1. ``svg_generator.generate_chart_svg()`` produces a transparent SVG chart.
2. ``ai_image_client.AIImageClient.generate_background()`` produces a BG PNG.
3. **This module** composites them into a single publication-ready PNG with
   an optional semi-transparent watermark.

The primary entry point is :func:`composite_image`.

Architecture notes:
    * Pure function (ARCH-PURA-001) — no HTTP, no database, no file I/O
      beyond in-memory image operations.
    * Uses ``Pillow`` for raster operations and ``CairoSVG`` for
      SVG-to-PNG rasterisation.
    * ``CairoSVG`` is imported lazily to avoid hard dependency on the
      native ``cairo`` C library at module import time. This allows the
      rest of the graphics package to be imported even when cairo is not
      installed (e.g. local Windows development without GTK).
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont


def _svg2png(
    bytestring: bytes,
    output_width: int,
    output_height: int,
    dpi: int,
) -> bytes:
    """Rasterise SVG bytes to PNG via CairoSVG (lazy import).

    Args:
        bytestring: Raw SVG document.
        output_width: Target width in pixels.
        output_height: Target height in pixels.
        dpi: Rendering DPI.

    Returns:
        PNG-encoded image as ``bytes``.

    Raises:
        ImportError: If ``cairosvg`` (or the native cairo lib) is missing.
    """
    import cairosvg  # lazy import — native cairo may not be installed

    result: bytes = cairosvg.svg2png(
        bytestring=bytestring,
        output_width=output_width,
        output_height=output_height,
        dpi=dpi,
    )
    return result


def composite_image(
    bg_bytes: bytes,
    svg_bytes: bytes,
    *,
    dpi: int = 150,
    watermark: bool = True,
    watermark_text: str = "summa.vision",
) -> bytes:
    """Composite an SVG chart over a background image into a final PNG.

    Parameters
    ----------
    bg_bytes:
        PNG-encoded background image (from ``AIImageClient``).
    svg_bytes:
        SVG chart (from ``generate_chart_svg``).
    dpi:
        Rendering DPI for SVG rasterisation.  At 150 DPI the output
        matches the background pixel dimensions; at 300 DPI the
        output is doubled (for B2B high-res).
    watermark:
        Whether to add a semi-transparent watermark in the bottom-right
        corner of the final image.
    watermark_text:
        Text content for the watermark.

    Returns
    -------
    bytes
        PNG-encoded composite image ready for publication.

    Raises
    ------
    ValueError
        If *bg_bytes* or *svg_bytes* cannot be decoded.
    """
    # 1. Decode background
    bg = Image.open(io.BytesIO(bg_bytes))
    if bg.mode != "RGBA":
        bg = bg.convert("RGBA")

    # 2. Determine target size from background
    target_w, target_h = bg.size

    # 3. Rasterise SVG to PNG at target dimensions
    svg_png_bytes = _svg2png(
        bytestring=svg_bytes,
        output_width=target_w,
        output_height=target_h,
        dpi=dpi,
    )
    svg_layer = Image.open(io.BytesIO(svg_png_bytes))
    if svg_layer.mode != "RGBA":
        svg_layer = svg_layer.convert("RGBA")

    # 4. Resize background if needed (shouldn't normally happen, but guard)
    if bg.size != (target_w, target_h):
        bg = bg.resize((target_w, target_h), Image.LANCZOS)

    # 5. Composite — SVG layer on top of background
    result = Image.alpha_composite(bg, svg_layer)

    # 6. Watermark (optional)
    if watermark:
        result = _apply_watermark(result, watermark_text)

    # 7. Save to PNG bytes
    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    return buffer.getvalue()


def _apply_watermark(img: Image.Image, text: str) -> Image.Image:
    """Add a semi-transparent text watermark to the bottom-right corner.

    Args:
        img: The RGBA image to watermark.
        text: Watermark string.

    Returns:
        A new image with the watermark applied.
    """
    # Create a transparent overlay for the watermark
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = ImageFont.load_default()

    # Determine text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Position: 12px padding from bottom-right
    padding = 12
    x = img.width - text_w - padding
    y = img.height - text_h - padding

    # Semi-transparent white
    draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)

    return Image.alpha_composite(img, overlay)
