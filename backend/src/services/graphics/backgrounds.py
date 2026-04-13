"""Programmatic generator for template backgrounds.

Generates dark-themed backgrounds with neon brand accents.
All background generation happens programmatically in-memory via Pillow,
strictly complying with ARCH-PURA-001 (Pure Data Transformations)
with no file I/O or external network calls.
"""

import io
import math
import random
from enum import Enum

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

    # Max allowed dimension to avoid excessive RAM allocation
    MAX_DIMENSION = 4096

    # Accent color palettes per category (Design System v3.2 data semantic tokens)
    # These exact RGB tuples are mixed with the BASE_COLOR
    # during gradient and noise calculation to theme the image.
    PALETTES = {
        BackgroundCategory.HOUSING: (34, 211, 238),  # --data-housing #22D3EE
        BackgroundCategory.INFLATION: (249, 115, 22),  # --data-monopoly #F97316
        BackgroundCategory.EMPLOYMENT: (16, 185, 129),  # --data-positive #10B981
        BackgroundCategory.TRADE: (167, 139, 250),  # --data-society #A78BFA
        BackgroundCategory.ENERGY: (251, 191, 36),  # --accent #FBBF24
        BackgroundCategory.DEMOGRAPHICS: (59, 130, 246),  # --data-gov #3B82F6
    }

    @staticmethod
    def _create_variant_1(
        draw: ImageDraw.ImageDraw, width: int, height: int, accent: tuple[int, int, int]
    ) -> None:
        """Variant 1: Radial gradient from bottom-center."""
        center_x = width // 2
        center_y = int(height * 1.2)  # Source is below the image
        max_radius = int(math.hypot(width / 2, height) * 1.5)

        for radius in range(max_radius, 0, -5):
            # Intensity drops off non-linearly, keeping top third dark
            distance_ratio = radius / max_radius
            intensity = int((1 - distance_ratio) ** 3 * 60)  # max intensity 60

            if intensity <= 0:
                continue

            ratio = intensity / 255
            r = int(
                BackgroundGenerator.BASE_COLOR[0]
                + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * ratio
            )
            g = int(
                BackgroundGenerator.BASE_COLOR[1]
                + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * ratio
            )
            b = int(
                BackgroundGenerator.BASE_COLOR[2]
                + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * ratio
            )

            draw.ellipse(
                (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ),
                fill=(r, g, b),
            )

    @staticmethod
    def _create_variant_2(
        img: Image.Image, width: int, height: int, accent: tuple[int, int, int]
    ) -> None:
        """Variant 2: Diagonal gradient (bottom-left to top-right)."""
        # Create a tiny version (e.g. 1/8th scale) to draw shapes extremely fast
        # Note: Must ensure small dimensions are at least 1
        sw = max(1, width // 8)
        sh = max(1, height // 8)

        small_img = Image.new("RGB", (sw, sh), color=BackgroundGenerator.BASE_COLOR)
        small_draw = ImageDraw.Draw(small_img)

        # Draw concentric thick lines from bottom-left corner
        # This will create a diagonal gradient effect when scaled up
        max_dist = int(
            math.hypot(sw, sh) * 0.8
        )  # Stop before the top right (negative space)

        # Step determines band thickness
        step = max(1, max_dist // 10)

        for radius in range(max_dist, 0, -step):
            # Intensity drops off towards top right
            distance_ratio = radius / max_dist
            intensity_ratio = max(0.0, 1.0 - distance_ratio)
            intensity = int(intensity_ratio**2 * 70)

            if intensity > 0:
                ratio = intensity / 255
                r = int(
                    BackgroundGenerator.BASE_COLOR[0]
                    + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * ratio
                )
                g = int(
                    BackgroundGenerator.BASE_COLOR[1]
                    + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * ratio
                )
                b = int(
                    BackgroundGenerator.BASE_COLOR[2]
                    + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * ratio
                )

                # Draw thick circles originating from bottom-left (0, sh)
                # Pillow coords: bbox [x0, y0, x1, y1]
                small_draw.ellipse(
                    [-radius, sh - radius, radius, sh + radius], fill=(r, g, b)
                )

        # Resize small image back to original dimensions using smooth scaling
        scaled_img = small_img.resize(
            (width, height), resample=Image.Resampling.LANCZOS
        )

        # Paste the smooth gradient back into the original image
        img.paste(scaled_img, (0, 0))

    @staticmethod
    def _create_variant_3(
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        accent: tuple[int, int, int],
        category: BackgroundCategory,
        variant: int,
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
            ratio = intensity / 255

            r = int(
                BackgroundGenerator.BASE_COLOR[0]
                + (accent[0] - BackgroundGenerator.BASE_COLOR[0]) * ratio
            )
            g = int(
                BackgroundGenerator.BASE_COLOR[1]
                + (accent[1] - BackgroundGenerator.BASE_COLOR[1]) * ratio
            )
            b = int(
                BackgroundGenerator.BASE_COLOR[2]
                + (accent[2] - BackgroundGenerator.BASE_COLOR[2]) * ratio
            )

            draw.rectangle([0, y1, width, y2], fill=(r, g, b))

        # Add some "noise" pixels in the lower 2/3
        # Seed pseudo-random deterministically so output is same for same size/variant/category
        # Note: the function should be pure, so we instantiate a local PRNG
        seed = hash((category.value, variant, width, height))
        rng = random.Random(seed)
        for _ in range(int(width * height * 0.05)):  # 5% noise
            x = rng.randint(0, width - 1)
            y = rng.randint(start_y, height - 1)
            noise_val = rng.randint(-15, 15)

            # Get current pixel roughly
            curr_y_ratio = (y - start_y) / (height - start_y)
            curr_intensity = int(curr_y_ratio * 50) + 10
            ratio = curr_intensity / 255

            r = min(
                255,
                max(
                    0,
                    BackgroundGenerator.BASE_COLOR[0]
                    + int((accent[0] - BackgroundGenerator.BASE_COLOR[0]) * ratio)
                    + noise_val,
                ),
            )
            g = min(
                255,
                max(
                    0,
                    BackgroundGenerator.BASE_COLOR[1]
                    + int((accent[1] - BackgroundGenerator.BASE_COLOR[1]) * ratio)
                    + noise_val,
                ),
            )
            b = min(
                255,
                max(
                    0,
                    BackgroundGenerator.BASE_COLOR[2]
                    + int((accent[2] - BackgroundGenerator.BASE_COLOR[2]) * ratio)
                    + noise_val,
                ),
            )

            draw.point((x, y), fill=(r, g, b))


def get_background(
    category: BackgroundCategory, size: tuple[int, int], variant: int = 1
) -> bytes:
    """
    Generate a template background image as PNG bytes.

    Args:
        category: The BackgroundCategory defining the accent color.
        size: A tuple of (width, height) in pixels.
              Should typically match standard presets like SIZE_INSTAGRAM (1080, 1080),
              SIZE_TWITTER (1200, 628), or SIZE_REDDIT (1200, 900).
        variant: An integer 1, 2, or 3 representing the visual style.

    Returns:
        Bytes of the generated PNG image.

    Raises:
        ValueError: If variant is not 1, 2, or 3.
        TypeError: If category is not a BackgroundCategory.
    """
    if not isinstance(category, BackgroundCategory):
        raise TypeError(
            f"Invalid category type: {type(category)}. Must be BackgroundCategory."
        )

    if variant not in [1, 2, 3]:
        raise ValueError(f"Invalid variant: {variant}. Must be 1, 2, or 3.")

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid size: {size}. Width and height must be positive.")
    if (
        width > BackgroundGenerator.MAX_DIMENSION
        or height > BackgroundGenerator.MAX_DIMENSION
    ):
        raise ValueError(
            f"Image dimensions must not exceed {BackgroundGenerator.MAX_DIMENSION}px. Got ({width}, {height})."
        )

    # Create base image
    img = Image.new("RGB", size, color=BackgroundGenerator.BASE_COLOR)
    draw = ImageDraw.Draw(img)

    accent_color = BackgroundGenerator.PALETTES[category]

    if variant == 1:
        BackgroundGenerator._create_variant_1(draw, width, height, accent_color)
    elif variant == 2:
        BackgroundGenerator._create_variant_2(img, width, height, accent_color)
    elif variant == 3:
        BackgroundGenerator._create_variant_3(
            draw, width, height, accent_color, category, variant
        )

    # Optional: subtle overall blur to smooth out gradients, except variant 3 which has noise
    if variant in [1, 2]:
        img = img.filter(ImageFilter.GaussianBlur(radius=2))

    # Save to bytes
    byte_io = io.BytesIO()
    img.save(byte_io, format="PNG")
    return byte_io.getvalue()
