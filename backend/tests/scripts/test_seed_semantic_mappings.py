"""Phase 3.1ab + 3.1b: seed CLI tests.

Three scenarios:
* ``--skip-validation`` reverts to the direct-repo path and emits a
  structlog warning, while bypassing
  :meth:`SemanticMappingService.upsert_many_validated`.
* Default (validated) path constructs a ``SemanticMappingService`` and
  forwards the YAML batch to ``upsert_many_validated`` with the expected
  per-item shape (smoke test against CLI ↔ service signature drift).
* File-atomic regression: when the bulk service raises
  :class:`BulkValidationError`, NO rows from that file are persisted.

The validated default path is also exercised end-to-end in
``tests/integration/test_semantic_mapping_service_integration.py`` where
the StatCan client is mocked but everything else is real.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


_YAML_BODY_WITH_PRODUCT_ID = """\
mappings:
  - cube_id: "18-10-0004"
    product_id: 18100004
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

    spy_upsert_many_validated = AsyncMock()
    warning_calls: list[tuple[str, dict]] = []

    def _fake_warning(event: str, **kwargs) -> None:
        warning_calls.append((event, kwargs))

    monkeypatch.setattr(
        seed_semantic_mappings.logger, "warning", _fake_warning
    )

    with patch.object(
        seed_semantic_mappings.SemanticMappingService,
        "upsert_many_validated",
        spy_upsert_many_validated,
    ):
        rc = await seed_semantic_mappings._main()

    assert rc == 0
    spy_upsert_many_validated.assert_not_called()
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


@pytest.mark.asyncio
async def test_seed_cli_default_path_calls_upsert_many_validated(
    tmp_path: Path, async_engine, monkeypatch
):
    """Phase 3.1b: the default (validated) path constructs a
    ``SemanticMappingService`` and forwards the YAML batch to
    ``upsert_many_validated`` (NOT the per-row ``upsert_validated``).
    Catches CLI ↔ service signature drift.
    """
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(
        seed_semantic_mappings, "get_session_factory", lambda: factory
    )

    yaml_path = tmp_path / "cpi.yaml"
    yaml_path.write_text(_YAML_BODY_WITH_PRODUCT_ID, encoding="utf-8")

    captured_init: list[dict] = []
    captured_batches: list[list] = []

    class _FakeSemanticMappingService:
        def __init__(self, **kwargs) -> None:
            captured_init.append(kwargs)

        async def upsert_many_validated(self, items):
            captured_batches.append(list(items))
            return SimpleNamespace(
                items=list(items),
                created_count=len(items),
                updated_count=0,
            )

        async def upsert_validated(self, **kwargs):  # pragma: no cover
            raise AssertionError(
                "Phase 3.1b CLI must NOT call per-row upsert_validated"
            )

    monkeypatch.setattr(
        seed_semantic_mappings,
        "SemanticMappingService",
        _FakeSemanticMappingService,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["seed_semantic_mappings.py", str(yaml_path)],
    )

    rc = await seed_semantic_mappings._main()

    assert rc == 0
    assert len(captured_init) == 1
    init_kwargs = captured_init[0]
    assert set(init_kwargs.keys()) == {
        "session_factory",
        "repository_factory",
        "metadata_cache",
        "logger",
    }

    # One bulk call carrying the single YAML row.
    assert len(captured_batches) == 1
    batch = captured_batches[0]
    assert len(batch) == 1
    item = batch[0]
    assert item.cube_id == "18-10-0004"
    assert item.product_id == 18100004
    assert item.semantic_key == "cpi.canada.all_items.index"
    assert item.label == "CPI — Canada, all-items"
    assert item.is_active is True
    assert item.config["dimension_filters"] == {
        "Geography": "Canada",
        "Products": "All-items",
    }


@pytest.mark.asyncio
async def test_seed_cli_default_path_is_file_atomic_on_bulk_validation_error(
    tmp_path: Path, async_engine, monkeypatch
):
    """Phase 3.1b regression: when ``upsert_many_validated`` raises
    :class:`BulkValidationError`, the CLI surfaces the error and persists
    NO rows from that file.
    """
    from src.services.semantic_mappings.exceptions import (
        BulkUpsertItemResult,
        BulkValidationError,
    )

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(
        seed_semantic_mappings, "get_session_factory", lambda: factory
    )
    yaml_path = tmp_path / "cpi.yaml"
    yaml_path.write_text(_YAML_BODY_WITH_PRODUCT_ID, encoding="utf-8")

    class _FailingService:
        def __init__(self, **kwargs) -> None:
            pass

        async def upsert_many_validated(self, items):
            raise BulkValidationError(
                [
                    BulkUpsertItemResult(
                        cube_id=i.cube_id,
                        semantic_key=i.semantic_key,
                        is_valid=False,
                        error_code="MEMBER_NOT_FOUND",
                        message="member missing",
                    )
                    for i in items
                ]
            )

    monkeypatch.setattr(
        seed_semantic_mappings, "SemanticMappingService", _FailingService
    )
    monkeypatch.setattr(
        "sys.argv", ["seed_semantic_mappings.py", str(yaml_path)]
    )

    with pytest.raises(BulkValidationError):
        await seed_semantic_mappings._main()

    async with factory() as session:
        repo = SemanticMappingRepository(session)
        fetched = await repo.get_by_key(
            "18-10-0004", "cpi.canada.all_items.index"
        )
    assert fetched is None
