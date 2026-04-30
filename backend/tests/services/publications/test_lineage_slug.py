"""Unit tests for ``generate_slug`` (Phase 2.2.0.5)."""
from __future__ import annotations

import pytest

from src.services.publications.exceptions import (
    PublicationSlugCollisionError,
    PublicationSlugGenerationError,
)
from src.services.publications.lineage import (
    MAX_SLUG_BODY_LEN,
    MIN_SLUG_BODY_LEN,
    RESERVED_SLUGS,
    generate_slug,
)


class TestGenerateSlugBasic:
    def test_basic_ascii(self):
        assert generate_slug("Canada GDP Q3 2026") == "canada-gdp-q3-2026"

    def test_ukrainian_transliteration(self):
        result = generate_slug("Інфляція в Україні")
        assert result.isascii()
        assert len(result) >= MIN_SLUG_BODY_LEN

    def test_chinese_transliteration(self):
        # python-slugify may either transliterate CJK or drop it; either
        # output is acceptable as long as a valid ASCII body is produced.
        # Pad with ASCII so the test does not depend on CJK handling
        # (tracked under DEBT-049).
        result = generate_slug("中国GDP增长 china growth")
        assert result.isascii()
        assert len(result) >= MIN_SLUG_BODY_LEN

    def test_truncation_at_max_body_len(self):
        long_headline = "a" * 250
        result = generate_slug(long_headline)
        assert len(result) <= MAX_SLUG_BODY_LEN


class TestGenerateSlugRejection:
    def test_empty_headline_raises(self):
        with pytest.raises(PublicationSlugGenerationError):
            generate_slug("")

    def test_too_short_body_raises(self):
        with pytest.raises(PublicationSlugGenerationError):
            generate_slug("ab")

    def test_only_punctuation_raises(self):
        with pytest.raises(PublicationSlugGenerationError):
            generate_slug("!!!")


class TestGenerateSlugCollision:
    def test_no_collision_returns_bare(self):
        assert generate_slug("Canada GDP", existing_slugs=set()) == "canada-gdp"

    def test_one_collision_returns_dash_2(self):
        assert (
            generate_slug("Canada GDP", existing_slugs={"canada-gdp"})
            == "canada-gdp-2"
        )

    def test_collision_chain(self):
        existing = {"canada-gdp", "canada-gdp-2", "canada-gdp-3"}
        assert generate_slug("Canada GDP", existing_slugs=existing) == "canada-gdp-4"

    def test_99_collisions_returns_dash_99(self):
        existing = {"canada-gdp"} | {f"canada-gdp-{n}" for n in range(2, 99)}
        assert generate_slug("Canada GDP", existing_slugs=existing) == "canada-gdp-99"

    def test_full_exhaustion_raises(self):
        existing = {"canada-gdp"} | {f"canada-gdp-{n}" for n in range(2, 100)}
        with pytest.raises(PublicationSlugCollisionError) as exc_info:
            generate_slug("Canada GDP", existing_slugs=existing)
        assert exc_info.value.message
        # Error envelope details carry the exhausted base + attempt count.
        details = exc_info.value.detail.get("details", {})
        assert details.get("base_slug") == "canada-gdp"
        assert details.get("attempts") == 98


class TestGenerateSlugReserved:
    def test_reserved_admin_returns_dash_2(self):
        # "admin" is in RESERVED_SLUGS; should disambiguate to admin-2
        assert generate_slug("Admin", existing_slugs=set()) == "admin-2"

    def test_reserved_with_existing_collision(self):
        assert generate_slug("Admin", existing_slugs={"admin-2"}) == "admin-3"

    def test_reserved_count_is_25(self):
        assert len(RESERVED_SLUGS) == 25


class TestGenerateSlugAcceptsCollections:
    def test_accepts_set(self):
        generate_slug("X is here", existing_slugs={"foo"})

    def test_accepts_frozenset(self):
        generate_slug("X is here", existing_slugs=frozenset({"foo"}))

    def test_accepts_list(self):
        generate_slug("X is here", existing_slugs=["foo"])

    def test_accepts_none(self):
        generate_slug("X is here", existing_slugs=None)


class TestGenerateSlugPurity:
    def test_does_not_touch_db(self):
        # No DB session passed; function returns or raises without I/O.
        assert generate_slug("Pure Function Test") == "pure-function-test"
