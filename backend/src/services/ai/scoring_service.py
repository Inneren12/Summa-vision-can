"""Brief Generation Service — AI scoring pipeline orchestrator.

Wires together ``LLMInterface``, ``PromptLoader``, and
``PublicationRepository`` to score StatCan datasets for virality and
persist high-scoring results as DRAFT publications.

Architecture notes:
    * All dependencies arrive via constructor injection (ARCH-DPEN-001).
    * ``AIServiceError`` for any single dataset is caught and logged —
      one failure never aborts the entire batch (fault-tolerant).
    * ``structlog`` is used for all logging (structured JSON).
"""

from __future__ import annotations

import hashlib

import structlog

from src.core.exceptions import AIServiceError
from src.core.prompt_loader import PromptLoader
from src.models.publication import Publication, PublicationStatus
from src.repositories.publication_repository import PublicationRepository
from src.services.ai.llm_interface import LLMInterface
from src.services.ai.schemas import ContentBrief
from src.services.statcan.schemas import CubeMetadataResponse

logger = structlog.get_logger(module="scoring_service")


class BriefGenerationService:
    """Score StatCan datasets for virality and persist top results.

    This service is the core business-logic glue for Phase 2.  It:

    1. Renders a journalist prompt for each incoming dataset.
    2. Sends the prompt to the LLM via ``LLMInterface.generate_structured``.
    3. Filters results using a configurable ``virality_threshold``.
    4. Persists qualifying briefs as ``DRAFT`` publications.

    Args:
        llm: Provider-agnostic LLM client.
        prompt_loader: Prompt template renderer.
        publication_repo: Repository for persisting publications.
        virality_threshold: Minimum ``virality_score`` to persist a
            dataset (default ``7.0``).
    """

    def __init__(
        self,
        *,
        llm: LLMInterface,
        prompt_loader: PromptLoader,
        publication_repo: PublicationRepository,
        virality_threshold: float = 7.0,
    ) -> None:
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._publication_repo = publication_repo
        self._virality_threshold = virality_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def score_datasets(
        self,
        datasets: list[CubeMetadataResponse],
    ) -> list[Publication]:
        """Score a batch of StatCan datasets and persist qualifying ones.

        For each dataset the service:

        1. Builds a ``data_hash`` from cube ID + reference period.
        2. Renders the ``journalist`` prompt template.
        3. Calls the LLM for a structured ``ContentBrief``.
        4. Persists datasets scoring ≥ ``virality_threshold`` as DRAFT
           publications; skips (with DEBUG log) those below.

        If the LLM raises ``AIServiceError`` for a single dataset, the
        error is logged and processing continues with the next dataset.

        Args:
            datasets: List of ``CubeMetadataResponse`` metadata objects.

        Returns:
            List of newly created ``Publication`` objects (only those
            that passed the virality threshold).
        """
        persisted: list[Publication] = []
        errors: int = 0

        for dataset in datasets:
            cube_id = str(dataset.product_id)
            release_date = (
                dataset.cube_end_date.isoformat()
                if dataset.cube_end_date
                else "unknown"
            )

            try:
                publication = await self._process_single(
                    dataset=dataset,
                    cube_id=cube_id,
                    release_date=release_date,
                )
            except AIServiceError as exc:
                errors += 1
                logger.error(
                    "scoring.llm_error",
                    cube_id=cube_id,
                    error=str(exc),
                    error_code=exc.error_code,
                )
                continue

            if publication is not None:
                persisted.append(publication)

        logger.info(
            "scoring.batch_complete",
            total=len(datasets),
            persisted=len(persisted),
            skipped=len(datasets) - len(persisted) - errors,
            errors=errors,
        )

        return persisted

    async def score_single(
        self,
        dataset: CubeMetadataResponse,
    ) -> Publication | None:
        """Score a single dataset — convenience wrapper.

        Args:
            dataset: A single ``CubeMetadataResponse`` metadata object.

        Returns:
            The created ``Publication`` if the score meets the threshold,
            or ``None`` if it was below threshold or the LLM call failed.
        """
        results = await self.score_datasets([dataset])
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _process_single(
        self,
        *,
        dataset: CubeMetadataResponse,
        cube_id: str,
        release_date: str,
    ) -> Publication | None:
        """Process a single dataset through the scoring pipeline.

        Args:
            dataset: The cube metadata.
            cube_id: Stringified product ID (for logging / hashing).
            release_date: ISO-formatted end date (for hashing / prompt).

        Returns:
            A ``Publication`` if persisted, ``None`` if below threshold.

        Raises:
            AIServiceError: Propagated from the LLM call.
        """
        # 1. Build data_hash for cache invalidation
        data_hash = hashlib.sha256(
            f"{cube_id}:{release_date}".encode()
        ).hexdigest()

        # 2. Render the journalist prompt
        prompt = self._prompt_loader.render(
            "journalist",
            dataset_title=dataset.cube_title_en,
            dataset_description=dataset.survey_en or dataset.cube_title_en,
            reference_date=release_date,
        )

        # 3. Call the LLM
        content_brief: ContentBrief = await self._llm.generate_structured(  # type: ignore[assignment]
            prompt,
            ContentBrief,
            data_hash=data_hash,
        )

        # 4. Threshold check
        if content_brief.virality_score < self._virality_threshold:
            logger.debug(
                "scoring.below_threshold",
                cube_id=cube_id,
                virality_score=content_brief.virality_score,
                threshold=self._virality_threshold,
            )
            return None

        # 5. Persist as DRAFT publication
        publication = await self._publication_repo.create(
            headline=content_brief.headline,
            chart_type=content_brief.chart_type.value,
            virality_score=content_brief.virality_score,
            s3_key_lowres=None,
            s3_key_highres=None,
            status=PublicationStatus.DRAFT,
        )

        logger.info(
            "scoring.publication_created",
            cube_id=cube_id,
            publication_id=publication.id,
            virality_score=content_brief.virality_score,
            headline=content_brief.headline,
        )

        return publication
