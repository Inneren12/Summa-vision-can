import pytest
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.exceptions import DataSourceError
from src.schemas.job_payloads import CatalogSyncPayload, CubeFetchPayload
from src.services.jobs.handlers import handle_catalog_sync, handle_cube_fetch


async def test_catalog_sync_handler_requires_http_client() -> None:
    """Handler raises RuntimeError when app_state has no http_client (ARCH-DPEN-001)."""
    payload = CatalogSyncPayload()
    app_state = SimpleNamespace()  # no statcan_client, no http_client

    with pytest.raises(RuntimeError, match="ARCH-DPEN-001"):
        await handle_catalog_sync(payload, app_state=app_state)


async def test_cube_fetch_handler_requires_http_client() -> None:
    """Handler raises RuntimeError when app_state has no http_client (ARCH-DPEN-001)."""
    from unittest.mock import patch, AsyncMock
    import contextlib

    payload = CubeFetchPayload(product_id="14-10-0127")
    app_state = SimpleNamespace(storage=None)  # no statcan_client, no http_client

    mock_repo = AsyncMock()
    mock_cube = AsyncMock()
    mock_cube.frequency = "monthly"
    mock_repo.get_by_product_id.return_value = mock_cube

    @contextlib.asynccontextmanager
    async def mock_factory():
        yield AsyncMock()

    with patch("src.core.database.get_session_factory", return_value=lambda: mock_factory()), \
         patch("src.repositories.cube_catalog_repository.CubeCatalogRepository.get_by_product_id", return_value=mock_cube):
        with pytest.raises(RuntimeError, match="ARCH-DPEN-001"):
            await handle_cube_fetch(payload, app_state=app_state)


@pytest.mark.asyncio
async def test_handle_cube_fetch_fails_when_cube_not_in_catalog(db_session: AsyncSession) -> None:
    """Handler raises CUBE_NOT_FOUND when catalog has no matching cube."""
    # Since handle_cube_fetch calls get_session_factory(), we need to mock it
    # or rely on the test database. We'll use the test db_session.
    from unittest.mock import patch

    payload = CubeFetchPayload(product_id="99-99-9999")
    app_state = SimpleNamespace(storage=None, statcan_client=None)

    # Mock get_session_factory and CubeCatalogRepository to avoid DB needs
    import contextlib
    @contextlib.asynccontextmanager
    async def mock_factory():
        yield db_session

    from unittest.mock import AsyncMock

    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_by_product_id.return_value = None

    # CubeCatalogRepository is imported locally in handle_cube_fetch, we can't easily patch it that way.
    # Instead, let's just insert it into the test DB or we patch src.repositories.cube_catalog_repository.CubeCatalogRepository
    with patch("src.core.database.get_session_factory", return_value=lambda: mock_factory()), \
         patch("src.repositories.cube_catalog_repository.CubeCatalogRepository.get_by_product_id", return_value=None):
        with pytest.raises(DataSourceError) as exc_info:
            await handle_cube_fetch(payload, app_state=app_state)

    assert exc_info.value.error_code == "CUBE_NOT_FOUND"
