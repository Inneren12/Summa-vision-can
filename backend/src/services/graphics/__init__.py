"""Graphics services — SVG chart generation, image compositing, and AI backgrounds.

This package provides the Visual Engine's rendering pipeline:

* :func:`svg_generator.generate_chart_svg` — DataFrame → transparent SVG
* :class:`ai_image_client.AIImageClient` — AI-generated backgrounds (mock)
* :func:`compositor.composite_image` — BG + SVG → publication-ready PNG

Note: ``composite_image`` depends on CairoSVG which requires the native
cairo C library.  It is imported eagerly here; if cairo is not installed,
import this package from the specific sub-module instead::

    from src.services.graphics.svg_generator import generate_chart_svg
"""

from src.services.graphics.ai_image_client import AIImageClient
from src.services.graphics.backgrounds import BackgroundCategory, get_background
from src.services.graphics.compositor import composite_image
from src.services.graphics.svg_generator import (
    NEON_PALETTE,
    SIZE_INSTAGRAM,
    SIZE_REDDIT,
    SIZE_TWITTER,
    generate_chart_svg,
)

__all__ = [
    "AIImageClient",
    "BackgroundCategory",
    "NEON_PALETTE",
    "SIZE_INSTAGRAM",
    "SIZE_REDDIT",
    "SIZE_TWITTER",
    "composite_image",
    "generate_chart_svg",
    "get_background",
]
