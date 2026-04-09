import io
import pytest
from PIL import Image
from src.services.graphics.backgrounds import BackgroundCategory, get_background, BackgroundGenerator
from src.services.graphics.svg_generator import SIZE_INSTAGRAM, SIZE_TWITTER, SIZE_REDDIT

def test_backgrounds_valid_png_bytes():
    """Test each of the 6 categories returns valid PNG bytes."""
    for category in BackgroundCategory:
        bg_bytes = get_background(category, (100, 100), variant=1)
        assert isinstance(bg_bytes, bytes)
        assert bg_bytes.startswith(b'\x89PNG\r\n\x1a\n')

def test_backgrounds_variants_distinct():
    """Test each of the 3 variants per category produces distinct images."""
    for category in BackgroundCategory:
        bg1 = get_background(category, (100, 100), variant=1)
        bg2 = get_background(category, (100, 100), variant=2)
        bg3 = get_background(category, (100, 100), variant=3)

        assert bg1 != bg2
        assert bg2 != bg3
        assert bg1 != bg3

def test_backgrounds_dimensions():
    """Test dimensions match requested size."""
    size = (1080, 1080)
    bg_bytes = get_background(BackgroundCategory.HOUSING, size, variant=1)

    img = Image.open(io.BytesIO(bg_bytes))
    assert img.size == size

def test_backgrounds_standard_presets():
    """Test with all 3 standard presets."""
    for size in [SIZE_INSTAGRAM, SIZE_TWITTER, SIZE_REDDIT]:
        bg_bytes = get_background(BackgroundCategory.EMPLOYMENT, size, variant=2)
        img = Image.open(io.BytesIO(bg_bytes))
        assert img.size == size
        assert img.format == "PNG"

def test_backgrounds_custom_size():
    """Test with a custom non-standard size like (800, 600)."""
    size = (800, 600)
    bg_bytes = get_background(BackgroundCategory.TRADE, size, variant=3)
    img = Image.open(io.BytesIO(bg_bytes))
    assert img.size == size
    assert img.format == "PNG"

def test_backgrounds_invalid_variant():
    """Test invalid variant raises ValueError."""
    with pytest.raises(ValueError, match="Invalid variant"):
        get_background(BackgroundCategory.ENERGY, (100, 100), variant=0)

    with pytest.raises(ValueError, match="Invalid variant"):
        get_background(BackgroundCategory.ENERGY, (100, 100), variant=4)

def test_backgrounds_invalid_category():
    """Test invalid category type raises appropriate error."""
    with pytest.raises(TypeError, match="Invalid category type"):
        get_background("NOT_A_CATEGORY", (100, 100), variant=1)  # type: ignore

def test_backgrounds_deterministic_output():
    """Same args produce byte-identical output (true determinism, not cache identity)."""
    result_1 = get_background(BackgroundCategory.HOUSING, (1080, 1080), variant=1)
    result_2 = get_background(BackgroundCategory.HOUSING, (1080, 1080), variant=1)
    assert result_1 == result_2  # byte equality, NOT object identity

def test_backgrounds_upper_third_dark():
    """Test that the upper-third of each background is predominantly dark."""
    for category in BackgroundCategory:
        for variant in [1, 2, 3]:
            # Use a reasonably large size to avoid rounding errors
            size = (300, 300)
            bg_bytes = get_background(category, size, variant=variant)
            img = Image.open(io.BytesIO(bg_bytes))

            # Sample pixels in the upper third
            # Upper third region is y from 0 to 100
            sampled_pixels = 0
            total_r = total_g = total_b = 0

            # Sample every 10th pixel to be fast
            for y in range(0, 100, 10):
                for x in range(0, 300, 10):
                    r, g, b = img.getpixel((x, y))
                    total_r += r
                    total_g += g
                    total_b += b
                    sampled_pixels += 1

            avg_r = total_r / sampled_pixels
            avg_g = total_g / sampled_pixels
            avg_b = total_b / sampled_pixels

            # Assert average RGB is close to #141414 (20, 20, 20) -> check each channel < 40
            assert avg_r < 40, f"Variant {variant} top-third R too bright: {avg_r}"
            assert avg_g < 40, f"Variant {variant} top-third G too bright: {avg_g}"
            assert avg_b < 40, f"Variant {variant} top-third B too bright: {avg_b}"

def test_backgrounds_invalid_size():
    """Test negative dimensions raise ValueError."""
    with pytest.raises(ValueError, match="Invalid size"):
        get_background(BackgroundCategory.ENERGY, (0, 100), variant=1)

    with pytest.raises(ValueError, match="Invalid size"):
        get_background(BackgroundCategory.ENERGY, (100, -100), variant=1)

def test_backgrounds_rejects_oversized():
    """Test that sizes exceeding MAX_DIMENSION raise ValueError."""
    with pytest.raises(ValueError, match="must not exceed"):
        get_background(BackgroundCategory.HOUSING, (5000, 5000))

def test_backgrounds_variant3_differs_by_category():
    """Test that variant 3 with same size but different categories yields different images due to seed differences."""
    bg1 = get_background(BackgroundCategory.HOUSING, (800, 600), variant=3)
    bg2 = get_background(BackgroundCategory.TRADE, (800, 600), variant=3)
    assert bg1 != bg2
