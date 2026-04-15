"""Pydantic schemas for publication CRUD and gallery rendering.

These schemas are the single source of truth for the editor + gallery
extension. They cover:

* :class:`VisualConfig` — strongly-typed representation of the editor's
  layer configuration (palette, background, layout, branding, custom
  primary colour). Persisted as a JSON string on
  ``Publication.visual_config``.
* :class:`PublicationCreate` — request body for
  ``POST /api/v1/admin/publications``.
* :class:`PublicationUpdate` — request body for
  ``PATCH /api/v1/admin/publications/{id}``.
* :class:`PublicationResponse` — admin-facing response with the full
  editorial + visual payload.
* :class:`PublicationPublicResponse` — public gallery response that
  excludes ``visual_config`` (it is admin-only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Visual configuration
# ---------------------------------------------------------------------------


class VisualConfig(BaseModel):
    """Editor layer configuration.

    Stored as a JSON string in :attr:`Publication.visual_config` —
    application code is responsible for serialising/deserialising via
    ``model_dump_json()`` / ``model_validate_json()``.

    Attributes:
        layout: Layout preset (``single_stat``, ``bar_editorial``,
            ``line_editorial``, ``comparison``).
        palette: Palette identifier (``housing``, ``government``,
            ``energy``, ``society``, ``economy``, ``neutral``).
        background: Background style (``solid_dark``, ``gradient_midnight``,
            ``gradient_warm``, ``gradient_radial``, ``dot_grid``,
            ``line_grid``, ``topo``).
        size: Output canvas preset (``instagram``, ``twitter``, ``reddit``,
            ``linkedin``, ``story``).
        custom_primary: Optional hex colour overriding the palette
            primary, e.g. ``"#22D3EE"``.
        branding: Branding flags & colour. ``show_top_accent`` and
            ``show_corner_mark`` toggle visual brand marks; ``accent_color``
            is the brand accent hex.
    """

    layout: str = "single_stat"
    palette: str = "housing"
    background: str = "gradient_warm"
    size: str = "instagram"
    custom_primary: Optional[str] = None
    branding: dict = Field(
        default_factory=lambda: {
            "show_top_accent": True,
            "show_corner_mark": True,
            "accent_color": "#FBBF24",
        }
    )


# ---------------------------------------------------------------------------
# Create / Update request bodies
# ---------------------------------------------------------------------------


class PublicationCreate(BaseModel):
    """Request body for ``POST /api/v1/admin/publications``.

    All fields except ``headline`` and ``chart_type`` are optional.
    The created publication starts in ``DRAFT`` status.
    """

    headline: str = Field(..., min_length=1, max_length=500)
    chart_type: str = Field(..., min_length=1, max_length=50)
    eyebrow: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    source_text: Optional[str] = Field(None, max_length=500)
    footnote: Optional[str] = None
    visual_config: Optional[VisualConfig] = None
    virality_score: Optional[float] = None
    source_product_id: Optional[str] = Field(None, max_length=100)


class PublicationUpdate(BaseModel):
    """Request body for ``PATCH /api/v1/admin/publications/{id}``.

    All fields are optional; ``None`` means "do not change".
    """

    headline: Optional[str] = Field(None, min_length=1, max_length=500)
    chart_type: Optional[str] = Field(None, min_length=1, max_length=50)
    eyebrow: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    source_text: Optional[str] = Field(None, max_length=500)
    footnote: Optional[str] = None
    visual_config: Optional[VisualConfig] = None
    virality_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PublicationResponse(BaseModel):
    """Admin-facing publication representation.

    Returned by the admin CRUD endpoints. Includes the editor's
    ``visual_config`` (parsed back from JSON when present).

    Attributes:
        id: Publication primary key (string for forward compatibility
            with future UUID migration).
        headline: Short title for the graphic.
        chart_type: Type of chart (``"bar"``, ``"line"``, ``"infographic"``).
        eyebrow: Optional eyebrow / kicker.
        description: Optional gallery card description.
        source_text: Optional source attribution.
        footnote: Optional methodology note.
        visual_config: Parsed editor layer configuration (admin-only).
        virality_score: AI-estimated virality score (0.0 – 1.0).
        status: Lifecycle status (``"DRAFT"`` or ``"PUBLISHED"``).
        cdn_url: Public CDN URL populated by the gallery endpoint.
        created_at: UTC timestamp of record creation.
        updated_at: UTC timestamp of the most recent change.
        published_at: UTC timestamp of last publication transition.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    headline: str
    chart_type: str
    eyebrow: Optional[str] = None
    description: Optional[str] = None
    source_text: Optional[str] = None
    footnote: Optional[str] = None
    visual_config: Optional[VisualConfig] = None
    virality_score: Optional[float] = None
    status: str
    cdn_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class PublicationPublicResponse(BaseModel):
    """Public gallery response — same as :class:`PublicationResponse`
    but with ``visual_config`` deliberately omitted.

    The editor's layer configuration is admin-only and must NOT be
    exposed on the public surface.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    headline: str
    chart_type: str
    eyebrow: Optional[str] = None
    description: Optional[str] = None
    source_text: Optional[str] = None
    footnote: Optional[str] = None
    virality_score: Optional[float] = None
    status: str
    cdn_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
