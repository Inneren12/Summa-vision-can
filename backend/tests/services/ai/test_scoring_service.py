"""Unit tests for BriefGenerationService.

Tests cover:
    - Batch scoring with multiple datasets (above/below threshold).
    - Single dataset scoring (convenience wrapper).
    - AIServiceError tolerance (one failure does not abort the batch).
    - Threshold configuration.
    - Correct field mapping to PublicationRepository.create().
    - Structured logging output.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import AIServiceError
from src.models.publication import Publication, PublicationStatus
from src.services.ai.schemas import ChartType, ContentBrief
from src.services.ai.scoring_service import BriefGenerationService
from src.services.statcan.schemas import CubeMetadataResponse, DimensionSchema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_dataset(
    product_id: int = 1234,
    title: str = "Consumer Price Index",
    end_date: datetime | None = None,
    survey_en: str | None = "Monthly survey",
) -> CubeMetadataResponse:
    """Create a minimal ``CubeMetadataResponse`` for testing."""
    return CubeMetadataResponse(
        product_id=product_id,
        cube_title_en=title,
        cube_title_fr="Titre FR",
        cube_start_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        cube_end_date=end_date or datetime(2024, 6, 1, tzinfo=timezone.utc),
        frequency_code=1,
        scalar_factor_code=0,
        dimension=[
            DimensionSchema(
                dimension_name_en="Geography",
                dimension_name_fr="Géographie",
                dimension_position_id=1,
                has_uom=False,
            )
        ],
        survey_en=survey_en,
    )


def _make_brief(
    virality_score: float = 8.5,
    headline: str = "CPI hits record high",
    chart_type: ChartType = ChartType.BAR,
) -> ContentBrief:
    """Create a ``ContentBrief`` with sensible defaults."""
    return ContentBrief(
        virality_score=virality_score,
        headline=headline,
        bg_prompt="A dramatic Canadian skyline at sunset",
        chart_type=chart_type,
        reasoning="High interest in inflation data",
    )


def _make_publication(
    pub_id: int = 1,
    headline: str = "CPI hits record high",
    chart_type: str = "BAR",
    virality_score: float = 8.5,
) -> Publication:
    """Create a mock ``Publication`` object."""
    pub = Publication(
        headline=headline,
        chart_type=chart_type,
        virality_score=virality_score,
        s3_key_lowres=None,
        s3_key_highres=None,
        status=PublicationStatus.DRAFT,
    )
    pub.id = pub_id
    return pub


@pytest.fixture()
def mock_llm() -> AsyncMock:
    """LLM that returns a high-scoring ContentBrief by default."""
    llm = AsyncMock()
    llm.generate_structured = AsyncMock(return_value=_make_brief())
    return llm


@pytest.fixture()
def mock_prompt_loader() -> MagicMock:
    """PromptLoader that returns a canned prompt string."""
    loader = MagicMock()
    loader.render = MagicMock(return_value="rendered prompt text")
    return loader


@pytest.fixture()
def mock_publication_repo() -> AsyncMock:
    """PublicationRepository that returns a mock Publication on create."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=_make_publication())
    return repo


@pytest.fixture()
def service(
    mock_llm: AsyncMock,
    mock_prompt_loader: MagicMock,
    mock_publication_repo: AsyncMock,
) -> BriefGenerationService:
    """BriefGenerationService wired with mock dependencies."""
    return BriefGenerationService(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        publication_repo=mock_publication_repo,
        virality_threshold=7.0,
    )


# ---------------------------------------------------------------------------
# Tests: score_datasets — happy path
# ---------------------------------------------------------------------------


class TestScoreDatasetsHappyPath:
    """Tests for the batch scoring method under normal conditions."""

    @pytest.mark.asyncio()
    async def test_single_dataset_above_threshold_persists(
        self,
        service: BriefGenerationService,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """A dataset scoring above threshold should be persisted."""
        datasets = [_make_dataset()]
        results = await service.score_datasets(datasets)

        assert len(results) == 1
        mock_publication_repo.create.assert_called_once()

    @pytest.mark.asyncio()
    async def test_create_called_with_correct_fields(
        self,
        service: BriefGenerationService,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """Verify field mapping from ContentBrief → publication_repo.create."""
        datasets = [_make_dataset()]
        await service.score_datasets(datasets)

        call_kwargs = mock_publication_repo.create.call_args.kwargs
        assert call_kwargs["headline"] == "CPI hits record high"
        assert call_kwargs["chart_type"] == "BAR"
        assert call_kwargs["virality_score"] == 8.5
        assert call_kwargs["s3_key_lowres"] is None
        assert call_kwargs["s3_key_highres"] is None
        assert call_kwargs["status"] == PublicationStatus.DRAFT

    @pytest.mark.asyncio()
    async def test_multiple_datasets_all_above_threshold(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """All datasets scoring above threshold should be persisted."""
        datasets = [
            _make_dataset(product_id=1),
            _make_dataset(product_id=2),
            _make_dataset(product_id=3),
        ]

        # Return distinct publications for each call
        mock_publication_repo.create = AsyncMock(
            side_effect=[
                _make_publication(pub_id=1),
                _make_publication(pub_id=2),
                _make_publication(pub_id=3),
            ]
        )

        results = await service.score_datasets(datasets)
        assert len(results) == 3
        assert mock_publication_repo.create.call_count == 3


# ---------------------------------------------------------------------------
# Tests: score_datasets — below threshold
# ---------------------------------------------------------------------------


class TestScoreDatasetsBelowThreshold:
    """Tests for datasets that score below the virality threshold."""

    @pytest.mark.asyncio()
    async def test_below_threshold_not_persisted(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """A dataset scoring below threshold should NOT be persisted."""
        mock_llm.generate_structured = AsyncMock(
            return_value=_make_brief(virality_score=5.0)
        )
        datasets = [_make_dataset()]

        results = await service.score_datasets(datasets)

        assert len(results) == 0
        mock_publication_repo.create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_mixed_above_and_below_threshold(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """Only datasets above threshold should be persisted."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=[
                _make_brief(virality_score=9.0),  # above
                _make_brief(virality_score=3.0),  # below
                _make_brief(virality_score=7.5),  # above
            ]
        )
        mock_publication_repo.create = AsyncMock(
            side_effect=[
                _make_publication(pub_id=1),
                _make_publication(pub_id=2),
            ]
        )

        datasets = [
            _make_dataset(product_id=1),
            _make_dataset(product_id=2),
            _make_dataset(product_id=3),
        ]

        results = await service.score_datasets(datasets)

        assert len(results) == 2
        assert mock_publication_repo.create.call_count == 2

    @pytest.mark.asyncio()
    async def test_exactly_at_threshold_is_persisted(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """A score exactly equal to threshold SHOULD be persisted (>= check)."""
        mock_llm.generate_structured = AsyncMock(
            return_value=_make_brief(virality_score=7.0)
        )

        results = await service.score_datasets([_make_dataset()])

        assert len(results) == 1
        mock_publication_repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: AIServiceError handling
# ---------------------------------------------------------------------------


class TestScoreDatasetsErrorHandling:
    """Tests for fault-tolerant error handling."""

    @pytest.mark.asyncio()
    async def test_ai_error_skips_dataset_continues_batch(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """An AIServiceError for one dataset should not abort the batch."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=[
                AIServiceError(message="API failure", error_code="AI_API_ERROR"),
                _make_brief(virality_score=8.0),
            ]
        )

        datasets = [
            _make_dataset(product_id=1),
            _make_dataset(product_id=2),
        ]

        results = await service.score_datasets(datasets)

        assert len(results) == 1
        assert mock_publication_repo.create.call_count == 1

    @pytest.mark.asyncio()
    async def test_all_datasets_fail_returns_empty(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """If all LLM calls fail, return an empty list."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=AIServiceError(
                message="API down", error_code="AI_API_ERROR"
            )
        )

        datasets = [_make_dataset(product_id=1), _make_dataset(product_id=2)]

        results = await service.score_datasets(datasets)

        assert results == []
        mock_publication_repo.create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_ai_error_logs_with_cube_id(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
    ) -> None:
        """Verify that AIServiceError is logged with the cube ID."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=AIServiceError(
                message="timeout", error_code="AI_TIMEOUT"
            )
        )

        with patch("src.services.ai.scoring_service.logger") as mock_logger:
            await service.score_datasets([_make_dataset(product_id=9999)])

            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args
            assert call_kwargs.args[0] == "scoring.llm_error"
            assert call_kwargs.kwargs["cube_id"] == "9999"


# ---------------------------------------------------------------------------
# Tests: score_single
# ---------------------------------------------------------------------------


class TestScoreSingle:
    """Tests for the single-dataset convenience wrapper."""

    @pytest.mark.asyncio()
    async def test_returns_publication_when_above_threshold(
        self,
        service: BriefGenerationService,
    ) -> None:
        """score_single returns a Publication if above threshold."""
        result = await service.score_single(_make_dataset())

        assert result is not None
        assert isinstance(result, Publication)

    @pytest.mark.asyncio()
    async def test_returns_none_when_below_threshold(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
    ) -> None:
        """score_single returns None if below threshold."""
        mock_llm.generate_structured = AsyncMock(
            return_value=_make_brief(virality_score=2.0)
        )

        result = await service.score_single(_make_dataset())

        assert result is None

    @pytest.mark.asyncio()
    async def test_returns_none_on_ai_error(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
    ) -> None:
        """score_single returns None if the LLM call fails."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=AIServiceError(message="fail")
        )

        result = await service.score_single(_make_dataset())

        assert result is None


# ---------------------------------------------------------------------------
# Tests: prompt rendering & data hash
# ---------------------------------------------------------------------------


class TestPromptAndHash:
    """Tests for correct prompt rendering and data hash construction."""

    @pytest.mark.asyncio()
    async def test_prompt_rendered_with_correct_kwargs(
        self,
        service: BriefGenerationService,
        mock_prompt_loader: MagicMock,
    ) -> None:
        """Verify PromptLoader.render() is called with expected arguments."""
        dataset = _make_dataset(
            title="Housing Starts",
            survey_en="National housing survey",
        )
        await service.score_datasets([dataset])

        mock_prompt_loader.render.assert_called_once_with(
            "journalist",
            dataset_title="Housing Starts",
            dataset_description="National housing survey",
            reference_date="2024-06-01T00:00:00+00:00",
        )

    @pytest.mark.asyncio()
    async def test_data_hash_passed_to_llm(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
    ) -> None:
        """Verify data_hash is correctly computed and passed to the LLM."""
        dataset = _make_dataset(product_id=5678)
        release_date = dataset.cube_end_date.isoformat()  # type: ignore[union-attr]
        expected_hash = hashlib.sha256(
            f"5678:{release_date}".encode()
        ).hexdigest()

        await service.score_datasets([dataset])

        call_kwargs = mock_llm.generate_structured.call_args.kwargs
        assert call_kwargs["data_hash"] == expected_hash

    @pytest.mark.asyncio()
    async def test_missing_survey_en_uses_title_as_description(
        self,
        service: BriefGenerationService,
        mock_prompt_loader: MagicMock,
    ) -> None:
        """When survey_en is None, cube_title_en is used as description."""
        dataset = _make_dataset(
            title="GDP by Industry",
            survey_en=None,
        )
        await service.score_datasets([dataset])

        call_kwargs = mock_prompt_loader.render.call_args.kwargs
        assert call_kwargs["dataset_description"] == "GDP by Industry"

    @pytest.mark.asyncio()
    async def test_missing_end_date_uses_unknown(
        self,
        service: BriefGenerationService,
        mock_prompt_loader: MagicMock,
        mock_llm: AsyncMock,
    ) -> None:
        """When cube_end_date is None, 'unknown' is used for reference_date."""
        dataset = _make_dataset()
        # Override cube_end_date to None via a new instance
        dataset = CubeMetadataResponse(
            product_id=1234,
            cube_title_en="Test",
            cube_title_fr="Test FR",
            cube_end_date=None,
            frequency_code=1,
            scalar_factor_code=0,
            dimension=[
                DimensionSchema(
                    dimension_name_en="Geo",
                    dimension_name_fr="Géo",
                    dimension_position_id=1,
                    has_uom=False,
                )
            ],
        )

        await service.score_datasets([dataset])

        call_kwargs = mock_prompt_loader.render.call_args.kwargs
        assert call_kwargs["reference_date"] == "unknown"


# ---------------------------------------------------------------------------
# Tests: configurable threshold
# ---------------------------------------------------------------------------


class TestConfigurableThreshold:
    """Tests for threshold configuration at construction time."""

    @pytest.mark.asyncio()
    async def test_custom_lower_threshold(
        self,
        mock_llm: AsyncMock,
        mock_prompt_loader: MagicMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """A lower threshold should persist more datasets."""
        service = BriefGenerationService(
            llm=mock_llm,
            prompt_loader=mock_prompt_loader,
            publication_repo=mock_publication_repo,
            virality_threshold=3.0,
        )
        mock_llm.generate_structured = AsyncMock(
            return_value=_make_brief(virality_score=4.0)
        )

        results = await service.score_datasets([_make_dataset()])

        assert len(results) == 1

    @pytest.mark.asyncio()
    async def test_custom_higher_threshold(
        self,
        mock_llm: AsyncMock,
        mock_prompt_loader: MagicMock,
        mock_publication_repo: AsyncMock,
    ) -> None:
        """A higher threshold should filter more datasets."""
        service = BriefGenerationService(
            llm=mock_llm,
            prompt_loader=mock_prompt_loader,
            publication_repo=mock_publication_repo,
            virality_threshold=9.0,
        )
        mock_llm.generate_structured = AsyncMock(
            return_value=_make_brief(virality_score=8.5)
        )

        results = await service.score_datasets([_make_dataset()])

        assert len(results) == 0


# ---------------------------------------------------------------------------
# Tests: structlog summary
# ---------------------------------------------------------------------------


class TestLogging:
    """Tests for structured logging output."""

    @pytest.mark.asyncio()
    async def test_batch_complete_summary_logged(
        self,
        service: BriefGenerationService,
        mock_llm: AsyncMock,
    ) -> None:
        """Verify the batch-complete summary is logged with correct counts."""
        mock_llm.generate_structured = AsyncMock(
            side_effect=[
                _make_brief(virality_score=9.0),
                _make_brief(virality_score=3.0),
                AIServiceError(message="fail"),
            ]
        )

        datasets = [
            _make_dataset(product_id=1),
            _make_dataset(product_id=2),
            _make_dataset(product_id=3),
        ]

        with patch("src.services.ai.scoring_service.logger") as mock_logger:
            await service.score_datasets(datasets)

            # Find the batch_complete call
            info_calls = [
                c
                for c in mock_logger.info.call_args_list
                if c.args[0] == "scoring.batch_complete"
            ]
            assert len(info_calls) == 1
            kwargs = info_calls[0].kwargs
            assert kwargs["total"] == 3
            assert kwargs["persisted"] == 1
            assert kwargs["skipped"] == 1
            assert kwargs["errors"] == 1

    @pytest.mark.asyncio()
    async def test_empty_batch_logs_zeros(
        self,
        service: BriefGenerationService,
    ) -> None:
        """An empty dataset list should log a summary with all zeros."""
        with patch("src.services.ai.scoring_service.logger") as mock_logger:
            results = await service.score_datasets([])

            assert results == []
            mock_logger.info.assert_called_once_with(
                "scoring.batch_complete",
                total=0,
                persisted=0,
                skipped=0,
                errors=0,
            )
