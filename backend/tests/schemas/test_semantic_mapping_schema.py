"""Phase 3.1a: SemanticMapping schema tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.semantic_mapping import (
    SemanticMappingConfig,
    SemanticMappingCreate,
)


class TestSemanticMappingConfig:
    def test_valid_config_round_trips(self):
        c = SemanticMappingConfig(
            dimension_filters={"Geography": "Canada"},
            measure="Value",
            unit="index",
            frequency="monthly",
        )
        d = c.model_dump()
        c2 = SemanticMappingConfig.model_validate(d)
        assert c2.frequency == "monthly"

    def test_invalid_frequency_rejected(self):
        with pytest.raises(ValidationError):
            SemanticMappingConfig(
                dimension_filters={},
                measure="Value",
                unit="index",
                frequency="weekly",  # not in Literal
            )

    def test_invalid_metric_rejected(self):
        with pytest.raises(ValidationError):
            SemanticMappingConfig(
                dimension_filters={},
                measure="Value",
                unit="index",
                frequency="monthly",
                supported_metrics=[
                    "current_value",
                    "ytd_average",  # not supported
                ],
            )

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            SemanticMappingConfig(
                dimension_filters={},
                measure="Value",
                unit="index",
                frequency="monthly",
                rogue_field="x",
            )


class TestSemanticMappingCreate:
    def _valid_config(self) -> SemanticMappingConfig:
        return SemanticMappingConfig(
            dimension_filters={"Geography": "Canada"},
            measure="Value",
            unit="index",
            frequency="monthly",
        )

    def test_semantic_key_pattern_accepts_dotted(self):
        c = SemanticMappingCreate(
            cube_id="18-10-0004",
            semantic_key="cpi.canada.all_items.index",
            label="x",
            config=self._valid_config(),
        )
        assert c.semantic_key == "cpi.canada.all_items.index"

    def test_semantic_key_pattern_rejects_uppercase(self):
        with pytest.raises(ValidationError):
            SemanticMappingCreate(
                cube_id="18-10-0004",
                semantic_key="CPI.Canada",  # uppercase forbidden
                label="x",
                config=self._valid_config(),
            )

    def test_semantic_key_pattern_rejects_spaces(self):
        with pytest.raises(ValidationError):
            SemanticMappingCreate(
                cube_id="18-10-0004",
                semantic_key="cpi canada",  # space forbidden
                label="x",
                config=self._valid_config(),
            )
