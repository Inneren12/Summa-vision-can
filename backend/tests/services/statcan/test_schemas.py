"""Unit tests for Statistics Canada Pydantic V2 schemas.

Covers:
- camelCase → snake_case alias mapping for all three models
- Required-field enforcement
- Explicit string-to-int coercion of ``scalarFactorCode``
- Validation errors on genuinely invalid payloads
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.services.statcan.schemas import (
    ChangedCubeResponse,
    CubeMetadataResponse,
    DimensionSchema,
)

# ---------------------------------------------------------------------------
# Shared test fixtures (camelCase, as received from the StatCan WDS API)
# ---------------------------------------------------------------------------

_VALID_CHANGED_CUBE: Dict[str, Any] = {
    "productId": 10100004,
    "cubeTitleEn": "Chartered banks, total claims and liabilities",
    "cubeTitleFr": "Banques à charte, total des créances et passifs",
    "releaseTime": "2025-12-15T08:30:00",
    "frequencyCode": 6,
    "surveyEn": "Monthly Survey of Financial Statistics",
    "surveyFr": "Enquête mensuelle sur les statistiques financières",
    "subjectCode": "36",
}

_VALID_DIMENSION: Dict[str, Any] = {
    "dimensionNameEn": "Geography",
    "dimensionNameFr": "Géographie",
    "dimensionPositionId": 1,
    "hasUom": True,
}

_VALID_CUBE_METADATA: Dict[str, Any] = {
    "productId": 18100004,
    "cubeTitleEn": "Consumer Price Index, monthly",
    "cubeTitleFr": "Indice des prix à la consommation, mensuel",
    "cubeStartDate": "1914-01-01T00:00:00",
    "cubeEndDate": "2025-11-01T00:00:00",
    "frequencyCode": 6,
    "scalarFactorCode": 0,
    "memberUomCode": 257,
    "dimension": [
        {
            "dimensionNameEn": "Geography",
            "dimensionNameFr": "Géographie",
            "dimensionPositionId": 1,
            "hasUom": True,
        },
        {
            "dimensionNameEn": "Products and product groups",
            "dimensionNameFr": "Produits et groupes de produits",
            "dimensionPositionId": 2,
            "hasUom": False,
        },
    ],
    "subjectCode": "18",
    "surveyEn": "Consumer Price Index",
    "surveyFr": "Indice des prix à la consommation",
    "correctionsEn": None,
    "correctionsFr": None,
}


# ===================================================================
# ChangedCubeResponse
# ===================================================================

class TestChangedCubeResponse:
    """Tests for the ChangedCubeResponse schema."""

    def test_valid_payload_maps_to_snake_case(self) -> None:
        """AC-Test 1: camelCase keys are mapped to snake_case attributes."""
        model = ChangedCubeResponse.model_validate(_VALID_CHANGED_CUBE)

        assert model.product_id == 10100004
        assert model.cube_title_en == "Chartered banks, total claims and liabilities"
        assert model.cube_title_fr == "Banques à charte, total des créances et passifs"
        assert model.release_time.year == 2025
        assert model.release_time.month == 12
        assert model.release_time.day == 15
        assert model.frequency_code == 6
        assert model.survey_en == "Monthly Survey of Financial Statistics"
        assert model.survey_fr == "Enquête mensuelle sur les statistiques financières"
        assert model.subject_code == "36"

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields should be None when not provided."""
        minimal: Dict[str, Any] = {
            "productId": 123,
            "cubeTitleEn": "Cube En",
            "cubeTitleFr": "Cube Fr",
            "releaseTime": "2025-01-01T00:00:00",
            "frequencyCode": 1,
        }
        model = ChangedCubeResponse.model_validate(minimal)

        assert model.survey_en is None
        assert model.survey_fr is None
        assert model.subject_code is None

    def test_missing_required_field_triggers_validation_error(self) -> None:
        """Omitting a required field must raise ValidationError."""
        payload = {**_VALID_CHANGED_CUBE}
        del payload["productId"]

        with pytest.raises(ValidationError) as exc_info:
            ChangedCubeResponse.model_validate(payload)

        assert "product_id" in str(exc_info.value) or "productId" in str(
            exc_info.value
        )

    def test_populate_by_snake_case_name(self) -> None:
        """populate_by_name=True allows construction with snake_case keys."""
        model = ChangedCubeResponse.model_validate(
            {
                "product_id": 10100004,
                "cube_title_en": "Title En",
                "cube_title_fr": "Title Fr",
                "release_time": "2025-12-15T08:30:00",
                "frequency_code": 6,
            }
        )
        assert model.product_id == 10100004


# ===================================================================
# DimensionSchema
# ===================================================================

class TestDimensionSchema:
    """Tests for the DimensionSchema schema."""

    def test_valid_payload_maps_to_snake_case(self) -> None:
        """AC-Test 1: camelCase keys are mapped to snake_case attributes."""
        model = DimensionSchema.model_validate(_VALID_DIMENSION)

        assert model.dimension_name_en == "Geography"
        assert model.dimension_name_fr == "Géographie"
        assert model.dimension_position_id == 1
        assert model.has_uom is True

    def test_wrong_type_triggers_validation_error(self) -> None:
        """A non-numeric string for an int field should fail validation."""
        payload = {**_VALID_DIMENSION, "dimensionPositionId": "invalid_integer"}

        with pytest.raises(ValidationError):
            DimensionSchema.model_validate(payload)

    def test_missing_required_field_triggers_validation_error(self) -> None:
        """Omitting a required field must raise ValidationError."""
        payload = {**_VALID_DIMENSION}
        del payload["dimensionNameEn"]

        with pytest.raises(ValidationError):
            DimensionSchema.model_validate(payload)


# ===================================================================
# CubeMetadataResponse
# ===================================================================

class TestCubeMetadataResponse:
    """Tests for the CubeMetadataResponse schema."""

    def test_valid_payload_maps_to_snake_case(self) -> None:
        """AC-Test 1: camelCase keys are mapped to snake_case attributes."""
        model = CubeMetadataResponse.model_validate(_VALID_CUBE_METADATA)

        assert model.product_id == 18100004
        assert model.cube_title_en == "Consumer Price Index, monthly"
        assert model.cube_title_fr == "Indice des prix à la consommation, mensuel"
        assert model.scalar_factor_code == 0
        assert isinstance(model.scalar_factor_code, int)
        assert model.member_uom_code == 257
        assert len(model.dimensions) == 2
        assert model.dimensions[0].dimension_name_en == "Geography"
        assert model.dimensions[1].dimension_name_en == "Products and product groups"
        assert model.subject_code == "18"
        assert model.corrections_en is None

    def test_string_scalar_factor_code_is_coerced_to_int(self) -> None:
        """AC-Test 2: scalarFactorCode="3" must be coerced to int(3).

        The StatCan API sometimes returns string representations of
        integers.  Our field_validator must silently cast them.
        """
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": "3"}
        model = CubeMetadataResponse.model_validate(payload)

        assert model.scalar_factor_code == 3
        assert isinstance(model.scalar_factor_code, int)

    def test_string_zero_scalar_factor_code_is_coerced(self) -> None:
        """Edge case: scalarFactorCode="0" must coerce to int(0)."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": "0"}
        model = CubeMetadataResponse.model_validate(payload)

        assert model.scalar_factor_code == 0
        assert isinstance(model.scalar_factor_code, int)

    def test_negative_string_scalar_factor_code_is_coerced(self) -> None:
        """Edge case: scalarFactorCode="-1" must coerce to int(-1)."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": "-1"}
        model = CubeMetadataResponse.model_validate(payload)

        assert model.scalar_factor_code == -1

    def test_invalid_string_scalar_factor_code_raises_validation_error(self) -> None:
        """AC-Test 3: scalarFactorCode="invalid" must raise ValidationError."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": "invalid"}

        with pytest.raises(ValidationError) as exc_info:
            CubeMetadataResponse.model_validate(payload)

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert any("scalar_factor_code" in str(e) for e in errors)

    def test_non_numeric_string_scalar_factor_code_raises_validation_error(
        self,
    ) -> None:
        """AC-Test 3 variant: scalarFactorCode="not-a-number" raises error."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": "not-a-number"}

        with pytest.raises(ValidationError):
            CubeMetadataResponse.model_validate(payload)

    def test_missing_mandatory_scalar_factor_code_triggers_validation_error(
        self,
    ) -> None:
        """scalar_factor_code is required — omission must fail."""
        payload = {**_VALID_CUBE_METADATA}
        del payload["scalarFactorCode"]

        with pytest.raises(ValidationError) as exc_info:
            CubeMetadataResponse.model_validate(payload)

        assert "scalar_factor_code" in str(exc_info.value) or "scalarFactorCode" in str(
            exc_info.value
        )

    def test_missing_dimensions_triggers_validation_error(self) -> None:
        """dimensions is required — omission must fail."""
        payload = {**_VALID_CUBE_METADATA}
        del payload["dimension"]

        with pytest.raises(ValidationError):
            CubeMetadataResponse.model_validate(payload)

    def test_optional_fields_default_to_none(self) -> None:
        """Optional date/string fields should be None when omitted."""
        minimal: Dict[str, Any] = {
            "productId": 18100004,
            "cubeTitleEn": "CPI",
            "cubeTitleFr": "IPC",
            "frequencyCode": 6,
            "scalarFactorCode": 0,
            "dimension": [
                {
                    "dimensionNameEn": "Geo",
                    "dimensionNameFr": "Géo",
                    "dimensionPositionId": 1,
                    "hasUom": True,
                },
            ],
        }
        model = CubeMetadataResponse.model_validate(minimal)

        assert model.cube_start_date is None
        assert model.cube_end_date is None
        assert model.member_uom_code is None
        assert model.subject_code is None
        assert model.survey_en is None
        assert model.corrections_en is None

    def test_int_scalar_factor_code_passthrough(self) -> None:
        """An already-integer scalarFactorCode should pass through unchanged."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": 5}
        model = CubeMetadataResponse.model_validate(payload)

        assert model.scalar_factor_code == 5
        assert isinstance(model.scalar_factor_code, int)

    def test_float_scalar_factor_code_is_coerced(self) -> None:
        """A float scalarFactorCode (e.g. 3.0) should be coerced to int."""
        payload = {**_VALID_CUBE_METADATA, "scalarFactorCode": 3.0}
        model = CubeMetadataResponse.model_validate(payload)

        assert model.scalar_factor_code == 3
        assert isinstance(model.scalar_factor_code, int)
