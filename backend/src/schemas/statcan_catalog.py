"""Pydantic schemas for StatCan getAllCubesList API response.

Maps camelCase JSON from StatCan API to snake_case Python models.
Used by CatalogSyncService to parse API responses before upserting
into the CubeCatalog table.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class StatCanCubeListItem(BaseModel):
    """A single cube from the StatCan getAllCubesList response."""

    model_config = ConfigDict(populate_by_name=True)

    product_id: str = Field(alias="productId")
    cansim_id: int = Field(alias="cansimId")
    cube_title_en: str = Field(alias="cubeTitleEn")
    cube_title_fr: str | None = Field(default=None, alias="cubeTitleFr")
    subject_code: str = Field(alias="subjectCode")
    subject_en: str = Field(alias="subjectEn")
    survey_en: str | None = Field(default=None, alias="surveyEn")
    frequency_code: int | str = Field(alias="frequencyCode")
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    archived: bool = Field(default=False)


FREQUENCY_MAP: dict[int | str, str] = {
    1: "Annual",
    2: "Biannual",
    4: "Quarterly",
    6: "Monthly",
    7: "Weekly",
    9: "Daily",
    "1": "Annual",
    "2": "Biannual",
    "4": "Quarterly",
    "6": "Monthly",
    "7": "Weekly",
    "9": "Daily",
}
