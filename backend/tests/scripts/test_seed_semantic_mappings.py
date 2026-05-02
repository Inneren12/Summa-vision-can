"""Phase 3.1ab: seed CLI test.

Asserts that ``--skip-validation`` reverts to the direct-repo path and
emits a structlog warning, while bypassing
:meth:`SemanticMappingService.upsert_validated`. The validated default
path is exercised end-to-end in the integration test
(``tests/integration/test_semantic_mapping_service_integration.py``)
where the StatCan client is mocked but everything else is real.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts import seed_semantic_mappings
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)


_YAML_BODY = """\
mappings:
  - cube_id: "18-10-0004"
    semantic_key: "cpi.canada.all_items.index"
    label: "CPI — Canada, all-items"
    description: "headline"
    config:
      dimension_filters:
        Geography: "Canada"
        Products: "All-items"
      measure: "Value"
      unit: "index"
      frequency: "monthly"
      supported_metrics:
        - current_value
      default_geo: "Canada"
    is_active: true
"""


@pytest.fixture()
def yaml_file(tmp_path: Path) -> Path:
    p = tmp_path / "cpi.yaml"
    p.write_text(_YAML_BODY, encoding="utf-8")
    return p


@pytest.mark.asyncio
async def test_seed_cli_skip_validation_flag_uses_direct_repo_path(
    yaml_file, async_engine, monkeypatch
):
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    monkeypatch.setattr(
        seed_semantic_mappings, "get_session_factory", lambda: factory
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "seed_semantic_mappings.py",
            "--skip-validation",
            str(yaml_file),
        ],
    )

    spy_upsert_validated = AsyncMock()
    warning_calls: list[tuple[str, dict]] = []

    def _fake_warning(event: str, **kwargs) -> None:
        warning_calls.append((event, kwargs))

    monkeypatch.setattr(
        seed_semantic_mappings.logger, "warning", _fake_warning
    )

    with patch.object(
        seed_semantic_mappings.SemanticMappingService,
        "upsert_validated",
        spy_upsert_validated,
    ):
        rc = await seed_semantic_mappings._main()

    assert rc == 0
    spy_upsert_validated.assert_not_called()
    # Structlog warning emitted at least once with the documented event name.
    assert any(
        event == "seed.skip_validation_enabled" for event, _ in warning_calls
    ), warning_calls

    # And the direct-repo path actually persisted the row.
    async with factory() as session:
        repo = SemanticMappingRepository(session)
        fetched = await repo.get_by_key(
            "18-10-0004", "cpi.canada.all_items.index"
        )
    assert fetched is not None
    assert fetched.label == "CPI — Canada, all-items"
