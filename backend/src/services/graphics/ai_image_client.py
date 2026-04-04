"""Mock AI image background generator.

Produces synthetic dark-gradient PNG backgrounds for infographic
compositing.  The current implementation is a **mock** — it generates
a deterministic gradient image locally instead of calling an external
AI image API.

Architecture notes:
    * Dependencies arrive via constructor injection (ARCH-DPEN-001).
      The constructor is intentionally empty now, but the class structure
      allows injecting a real HTTP client later.
    * ``structlog`` is used for all logging (structured JSON).

# TODO: replace with real AI image API (Stable Diffusion / DALL-E / Imagen)
"""

from __future__ import annotations

import io
import random

import structlog
from PIL import Image, ImageDraw

logger = structlog.get_logger(module="ai_image_client")


class AIImageClient:
    """Client for generating AI-powered background images.

    Currently returns a **mock** gradient with subtle neon noise.
    The constructor accepts no arguments today, but the DI-ready
    structure (ARCH-DPEN-001) allows future injection of an HTTP
    client, API key provider, or retry policy.

    Example::

        client = AIImageClient()
        bg_png = await client.generate_background(
            prompt="Canadian housing data visualization background",
            size=(1080, 1080),
        )
    """

    def __init__(self) -> None:
        """Initialise the AI image client.

        # TODO: replace with real AI image API (Stable Diffusion / DALL-E / Imagen)
        # Future signature:
        #   def __init__(self, *, http_client: httpx.AsyncClient, api_key: str) -> None:
        """

    async def generate_background(
        self,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        """Generate a background image for infographic compositing.

        The mock implementation produces a vertical dark gradient
        (``#1a1a2e`` → ``#16213e``) with subtle neon noise pixels
        scattered across the surface for visual realism.

        Args:
            prompt: Text description of the desired background.
                Currently only logged (not used for generation).
            size: ``(width, height)`` in pixels for the output image.

        Returns:
            PNG-encoded image as ``bytes`` with dimensions exactly
            matching *size*.
        """
        width, height = size

        # Create base gradient image (#1a1a2e → #16213e, top to bottom)
        img = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(img)

        # Gradient colours
        r1, g1, b1 = 0x1A, 0x1A, 0x2E  # #1a1a2e (top)
        r2, g2, b2 = 0x16, 0x21, 0x3E  # #16213e (bottom)

        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (width - 1, y)], fill=(r, g, b, 255))

        # Add subtle neon noise for realism
        rng = random.Random(42)  # deterministic seed for reproducibility
        neon_colors = [
            (0, 255, 148),   # neon green
            (0, 212, 255),   # neon blue
            (255, 0, 110),   # neon pink
        ]
        noise_count = max(1, (width * height) // 500)
        pixels = img.load()
        for _ in range(noise_count):
            nx = rng.randint(0, width - 1)
            ny = rng.randint(0, height - 1)
            nr, ng, nb = rng.choice(neon_colors)
            # Very low alpha so the noise is subtle
            pixels[nx, ny] = (nr, ng, nb, rng.randint(8, 25))

        # Encode to PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

        logger.info(
            "ai_image.mock_generated",
            size=size,
            prompt_preview=prompt[:50],
        )

        return png_bytes
