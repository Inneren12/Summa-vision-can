"""Phase 3.1ab: ``SemanticMappingService``.

Wraps :class:`SemanticMappingRepository` with cache-driven validation. The
3.1b admin save endpoint will go through :meth:`SemanticMappingService.upsert_validated`;
the repository's ``upsert_by_key`` is no longer called directly from request
handlers once 3.1b ships.

Architecture notes
------------------
* **R6 — short-lived sessions:** the service holds an
  ``async_sessionmaker`` factory and opens one session per call.
* **ARCH-DPEN-001 — DI:** session factory, repository factory, metadata
  cache and logger are all injected via ``__init__``.
* **Exception re-wrap:** cache-layer errors are caught and rethrown as
  :class:`MetadataValidationError` family for a uniform admin/UI contract.
"""
from __future__ import annotations

from collections.abc import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.semantic_mapping import SemanticMapping
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.semantic_mapping import (
    SemanticMappingConfig,
    SemanticMappingCreate,
)
from src.services.semantic_mappings.exceptions import (
    CubeNotInCacheError,
    DimensionMismatchError,
    MemberMismatchError,
    MetadataValidationError,
)
from src.services.semantic_mappings.validation import (
    ValidationResult,
    validate_mapping_against_cache,
)
from src.services.statcan.metadata_cache import (
    CubeMetadataProductMismatchError,
    CubeNotFoundError,
    StatCanMetadataCacheService,
    StatCanUnavailableError,
)


class SemanticMappingService:
    """Validation-aware façade over :class:`SemanticMappingRepository`."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        repository_factory: Callable[
            [AsyncSession], SemanticMappingRepository
        ],
        metadata_cache: StatCanMetadataCacheService,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._session_factory = session_factory
        self._repository_factory = repository_factory
        self._metadata_cache = metadata_cache
        self._logger = logger

    async def upsert_validated(
        self,
        *,
        cube_id: str,
        product_id: int,
        semantic_key: str,
        label: str,
        description: str | None,
        config: dict,
        is_active: bool,
        updated_by: str | None,
    ) -> SemanticMapping:
        """Validate against the cache, then upsert through the repository.

        Raises:
            CubeNotInCacheError: cache miss + StatCan unreachable, or
                StatCan has no metadata for ``cube_id``.
            MetadataValidationError: cache row's ``product_id`` differs
                from the caller's request, OR the in-mapping ``product_id``
                does not match the cached ``product_id``.
            DimensionMismatchError: at least one ``DIMENSION_NOT_FOUND``.
            MemberMismatchError: at least one ``MEMBER_NOT_FOUND`` (and no
                higher-precedence error class).
        """
        try:
            cache_entry = await self._metadata_cache.get_or_fetch(
                cube_id, product_id
            )
        except StatCanUnavailableError as exc:
            raise CubeNotInCacheError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="CUBE_NOT_IN_CACHE",
            ) from exc
        except CubeNotFoundError as exc:
            raise CubeNotInCacheError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="CUBE_NOT_IN_CACHE",
            ) from exc
        except CubeMetadataProductMismatchError as exc:
            raise MetadataValidationError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="CUBE_PRODUCT_MISMATCH",
            ) from exc

        dimension_filters = config.get("dimension_filters", {}) or {}
        result = validate_mapping_against_cache(
            cube_id=cube_id,
            product_id=product_id,
            dimension_filters=dimension_filters,
            cache_entry=cache_entry,
        )

        if not result.is_valid:
            self._logger.info(
                "semantic_mapping.validation_failed",
                cube_id=cube_id,
                semantic_key=semantic_key,
                error_count=len(result.errors),
                error_codes=[e.error_code for e in result.errors],
            )
            error_codes = {e.error_code for e in result.errors}
            # Precedence: product mismatch ⇒ dimension ⇒ member.
            # Product mismatch invalidates downstream dim/member resolution
            # because we are validating against the wrong cube's metadata.
            if "CUBE_PRODUCT_MISMATCH" in error_codes:
                raise MetadataValidationError(
                    result=result,
                    cube_id=cube_id,
                    error_code="CUBE_PRODUCT_MISMATCH",
                )
            if "DIMENSION_NOT_FOUND" in error_codes:
                raise DimensionMismatchError(
                    result=result,
                    cube_id=cube_id,
                    error_code="DIMENSION_NOT_FOUND",
                )
            if "MEMBER_NOT_FOUND" in error_codes:
                raise MemberMismatchError(
                    result=result,
                    cube_id=cube_id,
                    error_code="MEMBER_NOT_FOUND",
                )
            raise MetadataValidationError(result=result, cube_id=cube_id)

        payload = SemanticMappingCreate(
            cube_id=cube_id,
            semantic_key=semantic_key,
            label=label,
            description=description,
            config=SemanticMappingConfig.model_validate(config),
            is_active=is_active,
        )
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            mapping, _was_created = await repo.upsert_by_key(
                payload, updated_by=updated_by
            )
            await session.commit()
            return mapping
