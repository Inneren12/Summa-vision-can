"""Tests for the AI image client (Visual Engine — PR-18).

Validates the mock ``AIImageClient`` produces correctly-sized PNG
backgrounds with the expected gradient and neon noise characteristics.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from src.services.graphics.ai_image_client import AIImageClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> AIImageClient:
    """Create a fresh ``AIImageClient`` instance."""
    return AIImageClient()


# ---------------------------------------------------------------------------
# Core behaviour tests
# ---------------------------------------------------------------------------


async def test_generate_background_returns_png_bytes(
    client: AIImageClient,
) -> None:
    """Output must be ``bytes`` that decode as a valid PNG."""
    result = await client.generate_background(
        prompt="test background", size=(200, 100)
    )
    assert isinstance(result, bytes)
    # PNG magic bytes
    assert result[:8] == b"\x89PNG\r\n\x1a\n"


async def test_generate_background_exact_size(
    client: AIImageClient,
) -> None:
    """Output image must match the requested (width, height) exactly."""
    for w, h in [(1080, 1080), (1200, 628), (800, 600), (50, 50)]:
        result = await client.generate_background(
            prompt="size test", size=(w, h)
        )
        img = Image.open(io.BytesIO(result))
        assert img.size == (w, h), f"Expected ({w}, {h}), got {img.size}"


async def test_generate_background_rgba_mode(
    client: AIImageClient,
) -> None:
    """Generated PNG must be in RGBA mode for compositing."""
    result = await client.generate_background(
        prompt="mode test", size=(100, 100)
    )
    img = Image.open(io.BytesIO(result))
    assert img.mode == "RGBA"


async def test_generate_background_gradient_colours(
    client: AIImageClient,
) -> None:
    """Top-left pixel should be near #1a1a2e, bottom-left near #16213e."""
    result = await client.generate_background(
        prompt="gradient test", size=(100, 100)
    )
    img = Image.open(io.BytesIO(result))
    pixels = img.load()

    # Top-left — expect close to (0x1a, 0x1a, 0x2e, 255)
    top_r, top_g, top_b, top_a = pixels[0, 0]
    assert abs(top_r - 0x1A) <= 2
    assert abs(top_g - 0x1A) <= 2
    assert abs(top_b - 0x2E) <= 2
    assert top_a == 255

    # Bottom-left — expect close to (0x16, 0x21, 0x3e, 255)
    bot_r, bot_g, bot_b, bot_a = pixels[0, 99]
    assert abs(bot_r - 0x16) <= 2
    assert abs(bot_g - 0x21) <= 2
    assert abs(bot_b - 0x3E) <= 2
    assert bot_a == 255


async def test_generate_background_deterministic_noise(
    client: AIImageClient,
) -> None:
    """Two calls with same size should produce identical images (seeded RNG)."""
    a = await client.generate_background(prompt="p1", size=(100, 100))
    b = await client.generate_background(prompt="p2", size=(100, 100))
    assert a == b


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


async def test_generate_background_logs_info(
    client: AIImageClient,
) -> None:
    """Must log ``ai_image.mock_generated`` with size and prompt_preview."""
    with patch(
        "src.services.graphics.ai_image_client.logger"
    ) as mock_logger:
        await client.generate_background(
            prompt="A beautiful Canadian housing market visual",
            size=(1080, 1080),
        )
        mock_logger.info.assert_called_once_with(
            "ai_image.mock_generated",
            size=(1080, 1080),
            prompt_preview="A beautiful Canadian housing market visual"[:50],
        )


async def test_generate_background_prompt_preview_truncated(
    client: AIImageClient,
) -> None:
    """Prompt preview in log must be truncated to 50 chars."""
    long_prompt = "x" * 200
    with patch(
        "src.services.graphics.ai_image_client.logger"
    ) as mock_logger:
        await client.generate_background(prompt=long_prompt, size=(50, 50))
        call_kwargs = mock_logger.info.call_args
        assert call_kwargs[1]["prompt_preview"] == "x" * 50


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_generate_background_minimum_size(
    client: AIImageClient,
) -> None:
    """1×1 pixel image should not crash."""
    result = await client.generate_background(prompt="tiny", size=(1, 1))
    img = Image.open(io.BytesIO(result))
    assert img.size == (1, 1)


async def test_generate_background_empty_prompt(
    client: AIImageClient,
) -> None:
    """Empty prompt string should not crash."""
    result = await client.generate_background(prompt="", size=(50, 50))
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (50, 50)


# ---------------------------------------------------------------------------
# DI structure test
# ---------------------------------------------------------------------------


def test_ai_image_client_constructor_no_args() -> None:
    """AIImageClient must be constructable with no arguments."""
    client = AIImageClient()
    assert client is not None
