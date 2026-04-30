"""Schema-level tests for the publication slug field (Phase 2.2.0.5)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.publication import (
    PublicationCreate,
    PublicationPublicResponse,
    PublicationResponse,
    PublicationUpdate,
)


class TestPublicationCreateRejectsSlug:
    def test_create_rejects_slug_field(self):
        with pytest.raises(ValidationError):
            PublicationCreate(
                headline="Test",
                chart_type="bar",
                slug="forbidden",  # extra="forbid"
            )


class TestPublicationUpdateRejectsSlug:
    def test_update_rejects_slug_field(self):
        with pytest.raises(ValidationError):
            PublicationUpdate(slug="forbidden")  # extra="forbid"


class TestPublicationResponseIncludesSlug:
    def test_slug_field_present(self):
        assert "slug" in PublicationResponse.model_fields


class TestPublicationPublicResponseIncludesSlug:
    def test_slug_field_present(self):
        assert "slug" in PublicationPublicResponse.model_fields

    def test_lineage_key_not_in_public_response(self):
        # Phase 2.2.0 decision: ``lineage_key`` is admin-internal and must
        # NOT leak through the public surface. ``slug`` IS public (URL
        # identity); ``lineage_key`` is analytics-internal.
        assert "lineage_key" not in PublicationPublicResponse.model_fields
