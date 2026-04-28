"""Schema serialization tests for the Phase 2.2.0 ``lineage_key`` field.

Verifies that the Pydantic schemas for the publications API enforce the
post-Phase-2.2.0 contract:

* :class:`PublicationResponse` (admin-facing) exposes ``lineage_key`` as a
  required field — admins must always see the lineage identifier.
* :class:`PublicationCreate` rejects any operator-supplied ``lineage_key``
  via ``extra='forbid'`` so server-side ``generate_lineage_key()`` remains
  the sole authoritative source.
* :class:`PublicationPublicResponse` deliberately does **not** expose
  ``lineage_key`` — the value is admin-only and must never leak through the
  public gallery surface.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.schemas.publication import (
    PublicationCreate,
    PublicationPublicResponse,
    PublicationResponse,
)


_VALID_LINEAGE_KEY = "01923f9e-3c12-7c7e-8b32-1d4f5e6a7b8c"


def _admin_response_payload(**overrides):
    """Build a PublicationResponse-shaped dict with sensible defaults."""
    payload = {
        "id": "1",
        "headline": "test headline",
        "chart_type": "bar",
        "status": "DRAFT",
        "lineage_key": _VALID_LINEAGE_KEY,
        "created_at": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return payload


def test_publication_response_includes_lineage_key() -> None:
    """``lineage_key`` round-trips through PublicationResponse."""
    response = PublicationResponse.model_validate(_admin_response_payload())
    assert response.lineage_key == _VALID_LINEAGE_KEY
    assert "lineage_key" in response.model_dump()


def test_publication_response_rejects_null_lineage_key() -> None:
    """A null lineage_key fails PublicationResponse validation."""
    payload = _admin_response_payload(lineage_key=None)
    with pytest.raises(ValidationError) as exc_info:
        PublicationResponse.model_validate(payload)
    assert "lineage_key" in str(exc_info.value)


def test_publication_create_rejects_lineage_key_in_payload() -> None:
    """PublicationCreate's ``extra='forbid'`` blocks operator-supplied
    ``lineage_key`` (Chunk 3a defence-in-depth, schema-level)."""
    payload = {
        "headline": "test",
        "chart_type": "bar",
        "lineage_key": _VALID_LINEAGE_KEY,
    }
    with pytest.raises(ValidationError) as exc_info:
        PublicationCreate.model_validate(payload)
    error_str = str(exc_info.value)
    assert "lineage_key" in error_str
    assert "extra_forbidden" in error_str or "forbidden" in error_str.lower()


def test_publication_public_response_excludes_lineage_key() -> None:
    """The public-facing schema must not surface ``lineage_key``."""
    payload = {
        "id": 1,
        "headline": "test",
        "chart_type": "bar",
        "created_at": datetime.now(timezone.utc),
    }
    public = PublicationPublicResponse.model_validate(payload)
    dumped = public.model_dump()
    assert "lineage_key" not in dumped
    # Field also absent at the schema definition level — surfaces type
    # errors immediately if a future change adds it without removing this
    # guard.
    assert "lineage_key" not in PublicationPublicResponse.model_fields
