"""Unit tests for ``derive_clone_slug`` (Phase 2.2.0.5)."""
from __future__ import annotations

import pytest

from src.services.publications.exceptions import PublicationSlugGenerationError
from src.services.publications.lineage import derive_clone_slug


class TestDeriveCloneSlug:
    """Locked semantics (Phase 2.2.0.5 design): clone slug is built from
    the headline AS-IS. The ``_COPY_PREFIX`` ("Copy of ") is NOT stripped;
    a clone with headline "Copy of XYZ" gets slug "copy-of-xyz".
    """

    def test_basic_clone_headline(self):
        # "Copy of " prefix is preserved in the slug.
        assert derive_clone_slug("Copy of XYZ") == "copy-of-xyz"

    def test_no_prefix(self):
        assert derive_clone_slug("XYZ here") == "xyz-here"

    def test_chained_clone_keeps_all_prefixes(self):
        # Clone-of-clone: every "Copy of " prefix is preserved.
        assert (
            derive_clone_slug("Copy of Copy of XYZ")
            == "copy-of-copy-of-xyz"
        )

    def test_empty_headline_raises(self):
        with pytest.raises(PublicationSlugGenerationError):
            derive_clone_slug("")

    def test_none_headline_raises(self):
        with pytest.raises(PublicationSlugGenerationError):
            derive_clone_slug(None)  # type: ignore[arg-type]

    def test_collision_with_existing(self):
        # When "xyz-here" already exists, clone falls back to "-2".
        assert (
            derive_clone_slug("XYZ here", existing_slugs={"xyz-here"})
            == "xyz-here-2"
        )
