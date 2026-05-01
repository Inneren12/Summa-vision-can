"""Pydantic V2 schemas for Statistics Canada WDS API responses.

Maps camelCase JSON keys from the StatCan API to snake_case Python
attributes and coerces loose types (e.g. string-encoded integers) so
that downstream Pandas pipelines receive clean, validated data.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class StatCanBaseModel(BaseModel):
    """Base model for all Statistics Canada WDS API responses."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        strict=False,
        frozen=True,
    )


class ChangedCubeResponse(StatCanBaseModel):
    """A single entry returned by the getChangedCubeList endpoint."""

    product_id: int
    cube_title_en: str
    cube_title_fr: str
    release_time: datetime
    frequency_code: int
    survey_en: Optional[str] = None
    survey_fr: Optional[str] = None
    subject_code: Optional[str] = None


class MemberSchema(StatCanBaseModel):
    """A single member within a StatCan cube dimension.

    Phase 3.1aa: needed by the metadata cache so that the validator
    (3.1ab) can verify that mapping ``dimension_filters`` reference
    real members of the cube.
    """

    member_id: int
    member_name_en: str
    member_name_fr: str


class DimensionSchema(StatCanBaseModel):
    """A single dimension within a cube's metadata."""

    dimension_name_en: str
    dimension_name_fr: str
    dimension_position_id: int
    has_uom: bool

    # Phase 3.1aa: members are additive — older callers (e.g. the
    # ETL service's ``fetch_todays_releases`` flow) do not require
    # them, so the default empty list keeps existing tests green.
    members: List[MemberSchema] = Field(default_factory=list, alias="member")


class CubeMetadataResponse(StatCanBaseModel):
    """Full metadata envelope returned by the getCubeMetadata endpoint."""

    product_id: int
    cube_title_en: str
    cube_title_fr: str
    cube_start_date: Optional[datetime] = None
    cube_end_date: Optional[datetime] = None
    frequency_code: int

    # CRITICAL FIELD: Required for multiplying "thousands/millions" values.
    # StatCan sometimes returns this as a string — the validator below
    # coerces it to int before Pydantic performs its own type check.
    scalar_factor_code: int

    @field_validator("scalar_factor_code", mode="before")
    @classmethod
    def _coerce_scalar_factor_code(cls, value: object) -> int:
        """Coerce string representations of integers to ``int``.

        The Statistics Canada API occasionally returns
        ``scalarFactorCode`` as a JSON string (e.g. ``"3"``) instead
        of a native integer.  This validator ensures the value is
        always an ``int`` before it reaches the rest of the model.

        Raises
        ------
        ValueError
            If *value* is a string that cannot be converted to ``int``.
        """
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"scalar_factor_code must be an integer or a "
                    f"numeric string, got {value!r}"
                ) from exc
        # Let Pydantic handle any other type (float, None, etc.)
        return int(value)  # type: ignore[arg-type]

    member_uom_code: Optional[int] = None

    # Needs explicit alias since StatCan uses 'dimension' for the list array
    dimensions: List[DimensionSchema] = Field(..., alias="dimension")

    subject_code: Optional[str] = None
    survey_en: Optional[str] = None
    survey_fr: Optional[str] = None
    corrections_en: Optional[str] = None
    corrections_fr: Optional[str] = None
