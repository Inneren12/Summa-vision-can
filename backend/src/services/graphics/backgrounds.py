import io
import math
import random
from enum import Enum
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter


class BackgroundCategory(str, Enum):
    """Categories for background generation, mapping to specific brand accents."""

    HOUSING = "HOUSING"
    INFLATION = "INFLATION"
    EMPLOYMENT = "EMPLOYMENT"
    TRADE = "TRADE"
    ENERGY = "ENERGY"
    DEMOGRAPHICS = "DEMOGRAPHICS"


class BackgroundGenerator:
    """Programmatic generator for template backgrounds."""

    # Base dark theme color
    BASE_COLOR = (20, 20, 20)  # #141414

    # Accent color palettes per category (Neon brand colors)
    PALETTES = {
        BackgroundCategory.HOUSING: (0, 229, 255),      # Neon Cyan
        BackgroundCategory.INFLATION: (255, 107, 53),   # Neon Red/Orange
        BackgroundCategory.EMPLOYMENT: (57, 255, 20),   # Neon Green
        BackgroundCategory.TRADE: (191, 64, 191),       # Neon Purple
        BackgroundCategory.ENERGY: (255, 215, 0),       # Neon Yellow
        BackgroundCategory.DEMOGRAPHICS: (65, 105, 225) # Neon Blue
    }

    @staticmethod
    def _create_variant_1(
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        accent: tuple[int, int, int]
    ) -> None:
        """Variant 1: Radial gradient from bottom-center."""
        center_x = width // 2
        center_y = int(height * 1.2)  # Source is below the image
        max_radius = int(math.hypot(width / 2, height) * 1.5)

        for radius in range(max_radius, 0, -5):
            # Intensity drops off non-linearly, keeping top third dark
            distance_ratio = radius / max_radius
            intensity = int((1 - distance_ratio)**3 * 60)  # max intensity 60

            if intensity <= 0:
                continue

            color = (
                int(BackgroundGenerator.BASE_COLOR[0] + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * (intensity / 255)),
                int(BackgroundGenerator.BASE_COLOR[1] + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * (intensity / 255)),
                int(BackgroundGenerator.BASE_COLOR[2] + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * (intensity / 255))
            )
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                fill=color
            )

    @staticmethod
    def _create_variant_2(
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        accent: tuple[int, int, int]
    ) -> None:
        """Variant 2: Diagonal gradient (bottom-left to top-right)."""
        # We want the top third to be mostly base color.
        # So gradient effectively stops around y = height // 3.

        for y in range(height):
            for x in range(width):
                # Calculate distance from bottom-left corner
                # We want it to quickly fade as it goes up
                y_factor = (height - y) / (height * 0.66) # 0 at bottom, 1 at 1/3 from top

                if y_factor > 1.0:
                    continue # Keep top pure base

                x_factor = x / width # 0 at left, 1 at right

                # Combine factors, strongest at bottom-left
                intensity_ratio = max(0.0, 1.0 - math.sqrt(x_factor**2 + y_factor**2))

                intensity = int(intensity_ratio**2 * 70)

                if intensity > 0:
                    color = (
                        int(BackgroundGenerator.BASE_COLOR[0] + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * (intensity / 255)),
                        int(BackgroundGenerator.BASE_COLOR[1] + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * (intensity / 255)),
                        int(BackgroundGenerator.BASE_COLOR[2] + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * (intensity / 255))
                    )
                    draw.point((x, y), fill=color)

    @staticmethod
    def _create_variant_3(
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        accent: tuple[int, int, int]
    ) -> None:
        """Variant 3: Horizontal bands with subtle noise/texture in lower two thirds."""
        # Top third remains pure base
        start_y = height // 3

        # Draw some subtle horizontal bands
        num_bands = 5
        band_height = (height - start_y) // num_bands

        for i in range(num_bands):
            y1 = start_y + i * band_height
            y2 = y1 + band_height

            # Vary intensity per band
            intensity = int((i / num_bands) * 50) + 10

            color = (
                int(BackgroundGenerator.BASE_COLOR[0] + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * (intensity / 255)),
                int(BackgroundGenerator.BASE_COLOR[1] + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * (intensity / 255)),
                int(BackgroundGenerator.BASE_COLOR[2] + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * (intensity / 255))
            )

            draw.rectangle([0, y1, width, y2], fill=color)

        # Add some "noise" pixels in the lower 2/3
        # Seed pseudo-random deterministically so output is same for same size/variant/category
        # Note: the function should be pure, so we instantiate a local PRNG
        rng = random.Random(width + height * 3)
        for _ in range(int(width * height * 0.05)): # 5% noise
            x = rng.randint(0, width - 1)
            y = rng.randint(start_y, height - 1)
            noise_val = rng.randint(-15, 15)

            # Get current pixel roughly
            curr_y_ratio = (y - start_y) / (height - start_y)
            curr_intensity = int(curr_y_ratio * 50) + 10

            r = min(255, max(0, BackgroundGenerator.BASE_COLOR[0] + int((accent[0] - BackgroundGenerator.BASE_COLOR[0]) * (curr_intensity / 255)) + noise_val))
            g = min(255, max(0, BackgroundGenerator.BASE_COLOR[1] + int((accent[1] - BackgroundGenerator.BASE_COLOR[1]) * (curr_intensity / 255)) + noise_val))
            b = min(255, max(0, BackgroundGenerator.BASE_COLOR[2] + int((accent[2] - BackgroundGenerator.BASE_COLOR[2]) * (curr_intensity / 255)) + noise_val))

            draw.point((x, y), fill=(r, g, b))

@lru_cache(maxsize=36)
def get_background(category: BackgroundCategory, size: tuple[int, int], variant: int = 1) -> bytes:
    """
    Generate a template background image as PNG bytes.

    Args:
        category: The BackgroundCategory defining the accent color.
        size: A tuple of (width, height) in pixels.
        variant: An integer 1, 2, or 3 representing the visual style.

    Returns:
        Bytes of the generated PNG image.

    Raises:
        ValueError: If variant is not 1, 2, or 3.
        TypeError: If category is not a BackgroundCategory.
    """
    if not isinstance(category, BackgroundCategory):
        raise TypeError(f"Invalid category type: {type(category)}. Must be BackgroundCategory.")

    if variant not in [1, 2, 3]:
        raise ValueError(f"Invalid variant: {variant}. Must be 1, 2, or 3.")

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid size: {size}. Width and height must be positive.")

    # Create base image
    img = Image.new("RGB", size, color=BackgroundGenerator.BASE_COLOR)
    draw = ImageDraw.Draw(img)

    accent_color = BackgroundGenerator.PALETTES[category]

    if variant == 1:
        BackgroundGenerator._create_variant_1(draw, width, height, accent_color)
    elif variant == 2:
        BackgroundGenerator._create_variant_2(draw, width, height, accent_color)
    elif variant == 3:
        BackgroundGenerator._create_variant_3(draw, width, height, accent_color)

    # Optional: subtle overall blur to smooth out gradients, except variant 3 which has noise
    if variant in [1, 2]:
        img = img.filter(ImageFilter.GaussianBlur(radius=2))

    # Save to bytes
    byte_io = io.BytesIO()
    img.save(byte_io, format="PNG")
    return byte_io.getvalue()
