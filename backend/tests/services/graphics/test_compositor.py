"""Tests for the image compositor (Visual Engine — PR-18).

Validates that ``composite_image`` correctly merges a background PNG
and an SVG chart layer into a final publication-ready PNG, with
optional watermarking and correct pixel dimensions.

Since the native ``cairo`` C library may not be installed on all dev
machines (especially Windows), we mock ``cairosvg.svg2png`` to return
a synthetic PNG of the correct size.  This isolates the Pillow
compositing logic (which is the primary concern of this module).
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

from src.services.graphics.compositor import composite_image, _apply_watermark


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_solid_png(
    width: int,
    height: int,
    colour: tuple[int, int, int, int] = (26, 26, 46, 255),
) -> bytes:
    """Create a solid-colour RGBA PNG of the given dimensions."""
    img = Image.new("RGBA", (width, height), colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_solid_rgb_png(
    width: int,
    height: int,
    colour: tuple[int, int, int] = (26, 26, 46),
) -> bytes:
    """Create a solid-colour RGB (no alpha) PNG."""
    img = Image.new("RGB", (width, height), colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_svg_layer_png(
    width: int,
    height: int,
) -> bytes:
    """Create a semi-transparent green-rectangle PNG to simulate rasterised SVG."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Green rectangle — clamped to image bounds
    x0 = min(10, width - 1)
    y0 = min(10, height - 1)
    x1 = min(110, width - 1)
    y1 = min(110, height - 1)
    if x1 >= x0 and y1 >= y0:
        draw.rectangle([(x0, y0), (x1, y1)], fill=(0, 255, 148, 204))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_minimal_svg(width: int = 1080, height: int = 1080) -> bytes:
    """Create a minimal SVG — actual rendering is mocked."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect x="10" y="10" width="100" height="100" '
        f'fill="#00FF94" opacity="0.8"/>'
        f"</svg>"
    )
    return svg.encode("utf-8")


def _mock_svg2png(
    bytestring: bytes,
    output_width: int,
    output_height: int,
    dpi: int,
) -> bytes:
    """Mock replacement for ``_svg2png`` that returns a synthetic PNG."""
    return _make_svg_layer_png(output_width, output_height)


# ---------------------------------------------------------------------------
# Auto-mock fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_svg2png():
    """Patch ``_svg2png`` for all compositor tests (no native cairo needed)."""
    with patch(
        "src.services.graphics.compositor._svg2png",
        side_effect=_mock_svg2png,
    ):
        yield


# ---------------------------------------------------------------------------
# Core compositing tests
# ---------------------------------------------------------------------------


def test_composite_returns_png_bytes() -> None:
    """Output must be valid PNG bytes."""
    bg = _make_solid_png(200, 200)
    svg = _make_minimal_svg(200, 200)
    result = composite_image(bg, svg)
    assert isinstance(result, bytes)
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


def test_composite_output_dimensions_match_background() -> None:
    """Output image dimensions must match the background size."""
    for w, h in [(1080, 1080), (1200, 628), (800, 600)]:
        bg = _make_solid_png(w, h)
        svg = _make_minimal_svg(w, h)
        result = composite_image(bg, svg)
        img = Image.open(io.BytesIO(result))
        assert img.size == (w, h), f"Expected ({w}, {h}), got {img.size}"


def test_composite_rgba_output() -> None:
    """Output must be RGBA mode."""
    bg = _make_solid_png(100, 100)
    svg = _make_minimal_svg(100, 100)
    result = composite_image(bg, svg)
    img = Image.open(io.BytesIO(result))
    assert img.mode == "RGBA"


def test_composite_rgb_background_converted() -> None:
    """An RGB (no alpha) background must be auto-converted to RGBA."""
    bg = _make_solid_rgb_png(100, 100)
    svg = _make_minimal_svg(100, 100)
    result = composite_image(bg, svg)
    img = Image.open(io.BytesIO(result))
    assert img.size == (100, 100)
    assert img.mode == "RGBA"


# ---------------------------------------------------------------------------
# SVG overlay validation
# ---------------------------------------------------------------------------


def test_composite_svg_overlay_modifies_pixels() -> None:
    """The SVG layer should visibly change pixels vs. the raw background."""
    bg = _make_solid_png(200, 200, (0, 0, 0, 255))
    svg = _make_minimal_svg(200, 200)
    result = composite_image(bg, svg, watermark=False)
    img = Image.open(io.BytesIO(result))

    # The green rect in the mocked SVG layer is at (10, 10) → (110, 110)
    # So the pixel at (50, 50) should NOT be pure black
    result_pixel = img.getpixel((50, 50))
    assert result_pixel != (0, 0, 0, 255), (
        "SVG overlay did not modify pixels"
    )


# ---------------------------------------------------------------------------
# Watermark tests
# ---------------------------------------------------------------------------


def test_composite_with_watermark_default() -> None:
    """Default watermark=True should produce a valid PNG."""
    bg = _make_solid_png(300, 300)
    svg = _make_minimal_svg(300, 300)
    result = composite_image(bg, svg, watermark=True)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (300, 300)


def test_composite_without_watermark() -> None:
    """watermark=False should still produce a valid PNG."""
    bg = _make_solid_png(300, 300)
    svg = _make_minimal_svg(300, 300)
    result = composite_image(bg, svg, watermark=False)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (300, 300)


def test_composite_watermark_modifies_bottom_right() -> None:
    """With watermark=True, image should differ from no-watermark version."""
    bg = _make_solid_png(300, 300, (26, 26, 46, 255))
    svg = _make_minimal_svg(300, 300)

    with_wm = composite_image(bg, svg, watermark=True)
    without_wm = composite_image(bg, svg, watermark=False)

    # The two images should not be identical
    assert with_wm != without_wm


def test_composite_custom_watermark_text() -> None:
    """Custom watermark text should produce a different image than default."""
    bg = _make_solid_png(300, 300, (0, 0, 0, 255))
    svg = _make_minimal_svg(300, 300)

    default_wm = composite_image(bg, svg, watermark_text="summa.vision")
    custom_wm = composite_image(bg, svg, watermark_text="custom.text")

    # Different watermark text should produce different images
    assert default_wm != custom_wm


# ---------------------------------------------------------------------------
# DPI tests
# ---------------------------------------------------------------------------


def test_composite_dpi_default_150() -> None:
    """At default DPI=150, output matches background dimensions."""
    bg = _make_solid_png(1080, 1080)
    svg = _make_minimal_svg(1080, 1080)
    result = composite_image(bg, svg, dpi=150)
    img = Image.open(io.BytesIO(result))
    assert img.size == (1080, 1080)


def test_composite_dpi_300() -> None:
    """At DPI=300, output still matches background dimensions.

    (SVG is rasterised to match bg size regardless of DPI.)
    """
    bg = _make_solid_png(1080, 1080)
    svg = _make_minimal_svg(1080, 1080)
    result = composite_image(bg, svg, dpi=300)
    img = Image.open(io.BytesIO(result))
    assert img.size == (1080, 1080)


# ---------------------------------------------------------------------------
# _apply_watermark unit tests
# ---------------------------------------------------------------------------


def test_apply_watermark_returns_rgba() -> None:
    """``_apply_watermark`` must return an RGBA image."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 255))
    result = _apply_watermark(img, "test")
    assert result.mode == "RGBA"
    assert result.size == (200, 200)


def test_apply_watermark_changes_pixels() -> None:
    """Watermark text should modify at least some pixels."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 255))
    original_bytes = img.tobytes()
    result = _apply_watermark(img, "summa.vision")
    assert result.tobytes() != original_bytes


# ---------------------------------------------------------------------------
# Package-level export tests
# ---------------------------------------------------------------------------


def test_package_exports_compositor() -> None:
    """composite_image and AIImageClient must be importable from package root."""
    from src.services.graphics import AIImageClient as PkgClient
    from src.services.graphics import composite_image as pkg_fn

    assert callable(pkg_fn)
    assert PkgClient is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_composite_small_image() -> None:
    """Tiny images (e.g. 10×10) should not crash."""
    bg = _make_solid_png(10, 10)
    svg = _make_minimal_svg(10, 10)
    result = composite_image(bg, svg, watermark=False)
    img = Image.open(io.BytesIO(result))
    assert img.size == (10, 10)


def test_composite_watermark_on_small_image() -> None:
    """Watermark on a very small image should not crash."""
    bg = _make_solid_png(20, 20)
    svg = _make_minimal_svg(20, 20)
    result = composite_image(bg, svg, watermark=True)
    img = Image.open(io.BytesIO(result))
    assert img.size == (20, 20)


def test_composite_svg2png_called_with_correct_args() -> None:
    """``_svg2png`` must be called with bg dimensions and requested DPI."""
    bg = _make_solid_png(500, 300)
    svg = _make_minimal_svg(500, 300)

    with patch(
        "src.services.graphics.compositor._svg2png",
        side_effect=_mock_svg2png,
    ) as mock_fn:
        composite_image(bg, svg, dpi=200, watermark=False)
        mock_fn.assert_called_once_with(
            bytestring=svg,
            output_width=500,
            output_height=300,
            dpi=200,
        )
