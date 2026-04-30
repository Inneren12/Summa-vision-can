"""Schema-level tests for the publication slug field (Phase 2.2.0.5)."""
from __future__ import annotations

from datetime import datetime, timezone

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


def _response_payload(**overrides) -> dict:
    base = {
        "id": "1",
        "headline": "Test",
        "chart_type": "bar",
        "status": "DRAFT",
        "lineage_key": "01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c",
        "created_at": datetime(2026, 4, 30, tzinfo=timezone.utc),
        "slug": "canada-gdp-q3-2026",
    }
    base.update(overrides)
    return base


def _public_response_payload(**overrides) -> dict:
    base = {
        "id": 1,
        "headline": "Test",
        "chart_type": "bar",
        "status": "PUBLISHED",
        "created_at": datetime(2026, 4, 30, tzinfo=timezone.utc),
        "slug": "canada-gdp-q3-2026",
    }
    base.update(overrides)
    return base


class TestPublicationResponseIncludesSlug:
    def test_slug_field_present(self):
        assert "slug" in PublicationResponse.model_fields

    def test_slug_field_serializes_correctly(self):
        response = PublicationResponse.model_validate(_response_payload())
        assert response.slug == "canada-gdp-q3-2026"

        dumped = response.model_dump()
        assert dumped["slug"] == "canada-gdp-q3-2026"

    def test_slug_accepts_none_pre_not_null_migration(self):
        """TRANSITIONAL: this test asserts the nullable response schema state
        that exists between Chunk 4.5 (DB+ORM tighten) and Part B (router+schema
        tighten). DELETE THIS TEST when Part B lands and slug becomes
        ``slug: str`` (non-optional) in PublicationResponse / PublicationPublicResponse.

        Tracked in DEBT-049 follow-ups.
        """
        # Pre-Chunk-4.5 the column is nullable; the response schema must
        # tolerate ``None`` until the NOT NULL migration ships.
        response = PublicationResponse.model_validate(
            _response_payload(slug=None)
        )
        assert response.slug is None


class TestPublicationPublicResponseIncludesSlug:
    def test_slug_field_present(self):
        assert "slug" in PublicationPublicResponse.model_fields

    def test_slug_field_serializes_correctly(self):
        response = PublicationPublicResponse.model_validate(
            _public_response_payload()
        )
        assert response.slug == "canada-gdp-q3-2026"

        dumped = response.model_dump()
        assert dumped["slug"] == "canada-gdp-q3-2026"

    def test_lineage_key_not_in_public_response(self):
        # Phase 2.2.0 decision: ``lineage_key`` is admin-internal and must
        # NOT leak through the public surface. ``slug`` IS public (URL
        # identity); ``lineage_key`` is analytics-internal.
        assert "lineage_key" not in PublicationPublicResponse.model_fields

    def test_lineage_key_omitted_from_dump(self):
        # Defence-in-depth: even if ``lineage_key`` is passed in, the
        # serialized output of ``PublicationPublicResponse`` does not
        # carry it (extra fields are dropped, not echoed back).
        response = PublicationPublicResponse.model_validate(
            _public_response_payload()
        )
        assert "lineage_key" not in response.model_dump()
