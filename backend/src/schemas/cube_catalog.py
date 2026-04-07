"""Pydantic schemas for CubeCatalog operations."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class CubeCatalogCreate(BaseModel):
    """Input schema for creating/upserting a cube catalog entry.

    Used by CatalogSyncService to pass parsed StatCan API data
    to the repository.
    """

    product_id: str
    cube_id_statcan: int
    title_en: str
    title_fr: str | None = None
    subject_code: str
    subject_en: str
    survey_en: str | None = None
    frequency: str
    start_date: date | None = None
    end_date: date | None = None
    archive_status: bool = False


class CubeCatalogResponse(BaseModel):
    """Output schema for API responses."""

    id: int
    product_id: str
    cube_id_statcan: int
    title_en: str
    title_fr: str | None = None
    subject_code: str
    subject_en: str
    survey_en: str | None = None
    frequency: str
    start_date: date | None = None
    end_date: date | None = None
    archive_status: bool
    last_synced_at: datetime | None = None

    model_config = {"from_attributes": True}


class CubeSearchResult(BaseModel):
    """Lightweight search result for the search endpoint."""

    product_id: str
    cube_id_statcan: int
    title_en: str
    subject_en: str
    frequency: str

    model_config = {"from_attributes": True}
