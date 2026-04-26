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

import json
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Workflow states mirror the frontend ``WorkflowState`` union in
# ``frontend-public/src/components/editor/types.ts``. Kept in-sync by
# review; frontend owns shape validation of nested history/comment
# entries via ``assertCanonicalDocumentV2Shape``.
WorkflowState = Literal[
    "draft", "in_review", "approved", "exported", "published"
]


# ---------------------------------------------------------------------------
# Visual configuration
# ---------------------------------------------------------------------------


class BrandingConfig(BaseModel):
    """Typed branding block for :class:`VisualConfig`.

    Replaces the loose ``dict`` previously accepted under
    ``VisualConfig.branding`` so the editor contract is fully typed.

    Attributes:
        show_top_accent: Whether to render the top accent stripe.
        show_corner_mark: Whether to render the corner brand mark.
        accent_color: Hex colour used for the brand accent
            (default ``"#FBBF24"``).
    """

    show_top_accent: bool = True
    show_corner_mark: bool = True
    accent_color: str = "#FBBF24"


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
        branding: Typed :class:`BrandingConfig` block with accent flags
            and colour.
    """

    layout: str = "single_stat"
    palette: str = "housing"
    background: str = "gradient_warm"
    size: str = "instagram"
    custom_primary: Optional[str] = None
    branding: BrandingConfig = Field(default_factory=BrandingConfig)


# ---------------------------------------------------------------------------
# Review subtree
# ---------------------------------------------------------------------------


class ReviewPayload(BaseModel):
    """Mirror of the frontend ``CanonicalDocument.review`` subtree.

    Stored verbatim as JSON in ``Publication.review``. The top-level
    shape (``workflow``, ``history``, ``comments``) is validated here;
    nested history and comment elements are accepted as raw dicts
    because the frontend's ``assertCanonicalDocumentV2Shape`` owns the
    deep-shape contract and evolves faster than the backend needs to.

    Adding ``extra='forbid'`` mirrors :class:`PublicationUpdate` — an
    unknown top-level key (e.g. ``"workflows"``) is a likely typo and
    must fail loudly rather than silently be persisted and lost.
    """

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowState
    history: list[dict[str, Any]] = Field(default_factory=list)
    comments: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("history", "comments", mode="before")
    @classmethod
    def _coerce_none_to_list(cls, v: Any) -> Any:
        """Treat ``None`` as an empty list for parity with the frontend."""
        return v if v is not None else []


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
    review: Optional[ReviewPayload] = None
    # Opaque full-canonical-document JSON string. See DEBT-026 resolution:
    # backend stores verbatim, frontend owns shape validation. Typed as
    # ``str`` (not ``dict`` or a nested model) so Pydantic does not parse
    # or re-serialise it; the column is opaque at this layer.
    document_state: Optional[str] = None
    virality_score: Optional[float] = None
    source_product_id: Optional[str] = Field(None, max_length=100)


class PublicationUpdate(BaseModel):
    """Request body for ``PATCH /api/v1/admin/publications/{id}``.

    PATCH semantics:

    * Field omitted from request body → not changed.
    * Field explicitly set to ``null`` → cleared (column set to ``None``
      in the database).
    * Field set to a value → updated.

    To drive these semantics the router calls
    ``model.model_dump(exclude_unset=True)`` — only keys the client
    actually sent end up in the update dict; a key with value ``None``
    means "clear this field".

    ``extra='forbid'`` rejects unknown fields with HTTP 422 to prevent
    silent typos (e.g. ``"eybrow"`` instead of ``"eyebrow"``).
    """

    model_config = ConfigDict(extra="forbid")

    headline: Optional[str] = Field(None, min_length=1, max_length=500)
    chart_type: Optional[str] = Field(None, min_length=1, max_length=50)
    eyebrow: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    source_text: Optional[str] = Field(None, max_length=500)
    footnote: Optional[str] = None
    visual_config: Optional[VisualConfig] = None
    review: Optional[ReviewPayload] = None
    # Opaque full-canonical-document JSON string — see DEBT-026 resolution.
    # Unlike ``review`` (parsed for workflow-sync logic), ``document_state``
    # is never inspected by the backend: frontend serialises the whole
    # ``CanonicalDocument`` as a JSON string on the wire, the backend
    # persists it verbatim, and ``exclude_unset=True`` gives the usual
    # PATCH semantics (omitted = unchanged, explicit null = cleared).
    document_state: Optional[str] = None
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
        review: Parsed review subtree (workflow / history / comments,
            admin-only). ``None`` when the row has no review payload.
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
    review: Optional[ReviewPayload] = None
    # Opaque full-canonical-document JSON string (DEBT-026 resolution).
    # Passed straight through from the ``publications.document_state``
    # Text column to the wire without parsing — the frontend rehydrates
    # with ``JSON.parse`` + ``validateImportStrict``.
    document_state: Optional[str] = None
    virality_score: Optional[float] = None
    status: str
    cdn_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    cloned_from_publication_id: Optional[int] = None

    @field_validator("review", mode="before")
    @classmethod
    def _parse_review_json(cls, v: Any) -> Any:
        """Parse the stored JSON string into a dict before validation.

        ``Publication.review`` is a Text column holding a JSON string;
        Pydantic would otherwise reject it as "not a dict". Parse early
        so :class:`ReviewPayload` validation runs on the structured form.
        ``None`` and dicts are passed through unchanged.
        """
        if isinstance(v, str):
            return json.loads(v)
        return v


# ``review`` is deliberately absent from :class:`PublicationPublicResponse`
# below. Workflow state, audit history and review comments are
# admin-only editorial data and MUST NOT leak through the public
# gallery endpoint. Adding a field here also requires extending the
# public schema — do NOT do that for review; add a new admin-only
# response shape instead.
class PublicationPublicResponse(BaseModel):
    """Public gallery response — same shape as :class:`PublicationResponse`
    but with ``visual_config`` deliberately omitted.

    The editor's layer configuration is admin-only and must NOT be
    exposed on the public surface. ``preview_url`` is a short-lived
    presigned URL for the low-resolution thumbnail populated by the
    public gallery endpoint at serialization time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    headline: str
    chart_type: str
    eyebrow: Optional[str] = None
    description: Optional[str] = None
    source_text: Optional[str] = None
    footnote: Optional[str] = None
    virality_score: Optional[float] = None
    preview_url: Optional[str] = None
    status: str = "PUBLISHED"
    cdn_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    cloned_from_publication_id: Optional[int] = None
