"""Phase 3.1ab + 3.1b: ``SemanticMappingService``.

Wraps :class:`SemanticMappingRepository` with cache-driven validation. The
3.1b admin save endpoint goes through :meth:`SemanticMappingService.upsert_validated`;
the repository's ``upsert_by_key`` is no longer called directly from request
handlers in 3.1b.

Architecture notes
------------------
* **R6 — short-lived sessions:** the service holds an
  ``async_sessionmaker`` factory and opens one session per call.
* **ARCH-DPEN-001 — DI:** session factory, repository factory, metadata
  cache and logger are all injected via ``__init__``.
* **Exception re-wrap:** cache-layer errors are caught and rethrown as
  :class:`MetadataValidationError` family for a uniform admin/UI contract.
* **3.1b additions:** optimistic concurrency via ``if_match_version``,
  list/get/soft-delete admin operations, and validate-all-then-decide
  bulk upsert (``upsert_many_validated``) used by the seed CLI.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

import structlog
from sqlalchemy import func, select
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
    BulkUpsertItem,
    BulkUpsertItemResult,
    BulkUpsertResult,
    BulkValidationError,
    CubeNotInCacheError,
    DimensionMismatchError,
    MappingNotFoundError,
    MemberMismatchError,
    MetadataValidationError,
    VersionConflictError,
)
from src.services.semantic_mappings.validation import (
    ValidationResult,
    validate_mapping_against_cache,
)
from src.services.statcan.metadata_cache import (
    CubeMetadataCacheEntry,
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

    # ------------------------------------------------------------------
    # Validation helpers (pure path used by both single + bulk upsert)
    # ------------------------------------------------------------------

    async def _fetch_cache_entry(
        self, *, cube_id: str, product_id: int
    ) -> CubeMetadataCacheEntry:
        try:
            return await self._metadata_cache.get_or_fetch(cube_id, product_id)
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

    def _raise_for_validation_result(
        self, *, cube_id: str, semantic_key: str, result: ValidationResult
    ) -> None:
        if result.is_valid:
            return
        self._logger.info(
            "semantic_mapping.validation_failed",
            cube_id=cube_id,
            semantic_key=semantic_key,
            error_count=len(result.errors),
            error_codes=[e.error_code for e in result.errors],
        )
        error_codes = {e.error_code for e in result.errors}
        if "CUBE_PRODUCT_MISMATCH" in error_codes:
            raise MetadataValidationError(
                result=result, cube_id=cube_id, error_code="CUBE_PRODUCT_MISMATCH"
            )
        if "DIMENSION_NOT_FOUND" in error_codes:
            raise DimensionMismatchError(
                result=result, cube_id=cube_id, error_code="DIMENSION_NOT_FOUND"
            )
        if "MEMBER_NOT_FOUND" in error_codes:
            raise MemberMismatchError(
                result=result, cube_id=cube_id, error_code="MEMBER_NOT_FOUND"
            )
        raise MetadataValidationError(result=result, cube_id=cube_id)

    # ------------------------------------------------------------------
    # Single-row upsert (admin endpoint)
    # ------------------------------------------------------------------

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
        if_match_version: int | None = None,
    ) -> tuple[SemanticMapping, bool]:
        """Validate against the cache, then upsert through the repository.

        Returns ``(mapping, was_created)`` so callers (admin endpoint) can
        distinguish 201 vs 200.

        Raises:
            pydantic.ValidationError: ``config`` does not satisfy
                :class:`SemanticMappingConfig`. Raised BEFORE any cache
                fetch — bad shape never triggers a StatCan call.
            VersionConflictError: ``if_match_version`` mismatch with the
                existing row's ``version``.
            CubeNotInCacheError / DimensionMismatchError / MemberMismatchError /
            MetadataValidationError: per existing 3.1ab semantics.
        """
        # 1. Pydantic config validation FIRST.
        config_model = SemanticMappingConfig.model_validate(config)
        dimension_filters = config_model.dimension_filters or {}

        # 2. Cache fetch (auto-prime).
        cache_entry = await self._fetch_cache_entry(
            cube_id=cube_id, product_id=product_id
        )

        # 3. Pure validation against cache.
        result = validate_mapping_against_cache(
            cube_id=cube_id,
            product_id=product_id,
            dimension_filters=dimension_filters,
            cache_entry=cache_entry,
        )
        self._raise_for_validation_result(
            cube_id=cube_id, semantic_key=semantic_key, result=result
        )

        # 4. Persist with optimistic concurrency check inside the session.
        payload = SemanticMappingCreate(
            cube_id=cube_id,
            semantic_key=semantic_key,
            label=label,
            description=description,
            config=config_model,
            is_active=is_active,
        )
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            existing = await repo.get_by_key(cube_id, semantic_key)
            if (
                existing is not None
                and if_match_version is not None
                and existing.version != if_match_version
            ):
                raise VersionConflictError(
                    cube_id=cube_id,
                    semantic_key=semantic_key,
                    expected_version=if_match_version,
                    actual_version=existing.version,
                )
            mapping, was_created = await repo.upsert_by_key(
                payload, updated_by=updated_by
            )
            await session.commit()
            # Refresh so the (server-side) ``updated_at`` value is materialized
            # on the instance before the session closes; otherwise downstream
            # serialization hits DetachedInstanceError on lazy-loaded columns.
            await session.refresh(mapping)
            session.expunge(mapping)
            return mapping, was_created

    # ------------------------------------------------------------------
    # Read / list / soft-delete (admin endpoints)
    # ------------------------------------------------------------------

    async def list_mappings(
        self,
        *,
        cube_id: str | None = None,
        semantic_key: str | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[SemanticMapping], int]:
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            return await repo.list(
                cube_id=cube_id,
                semantic_key=semantic_key,
                is_active=is_active,
                limit=limit,
                offset=offset,
            )

    async def get_mapping(self, id: int) -> SemanticMapping:
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            mapping = await repo.get_by_id(id)
            if mapping is None:
                raise MappingNotFoundError(mapping_id=id)
            session.expunge(mapping)
            return mapping

    async def soft_delete(self, id: int) -> SemanticMapping:
        """Idempotent: returns row regardless of prior is_active state.

        Raises :class:`MappingNotFoundError` only if the row genuinely
        does not exist.
        """
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            mapping = await repo.soft_delete(id)
            if mapping is None:
                raise MappingNotFoundError(mapping_id=id)
            await session.commit()
            await session.refresh(mapping)
            session.expunge(mapping)
            return mapping

    # ------------------------------------------------------------------
    # Bulk validated upsert (seed CLI; no admin HTTP endpoint in 3.1b)
    # ------------------------------------------------------------------

    async def upsert_many_validated(
        self, items: list[BulkUpsertItem]
    ) -> BulkUpsertResult:
        """Validate-all-then-decide atomic bulk upsert.

        Flow:
            1. For each item: fetch cache entry (auto-prime, may hit
               StatCan). Cache fetches happen PRE-session. If ANY item
               raises :class:`CubeNotInCacheError`, the whole batch fails
               immediately (matching the locked semantics — no partial
               persist).
            2. For each item: validate via the pure validator. Per-item
               validity is collected; we do NOT short-circuit on the
               first failure so the operator sees the full picture.
            3. If ANY item invalid, raise :class:`BulkValidationError`
               with per-item results — NO rows persisted.
            4. Else open ONE session, persist all items, commit once.
        """
        if not items:
            return BulkUpsertResult(items=[], created_count=0, updated_count=0)

        # Shape-validate all configs FIRST. Any pydantic.ValidationError
        # surfaces before we contact StatCan.
        config_models: list[SemanticMappingConfig] = []
        for item in items:
            config_models.append(SemanticMappingConfig.model_validate(item.config))

        # 1. Pre-session cache fetches (whole batch fails on any miss).
        cache_entries: list[CubeMetadataCacheEntry] = []
        for item in items:
            entry = await self._fetch_cache_entry(
                cube_id=item.cube_id, product_id=item.product_id
            )
            cache_entries.append(entry)

        # 2. Per-item pure validation.
        per_item_results: list[BulkUpsertItemResult] = []
        any_invalid = False
        for item, config_model, cache_entry in zip(
            items, config_models, cache_entries, strict=True
        ):
            result = validate_mapping_against_cache(
                cube_id=item.cube_id,
                product_id=item.product_id,
                dimension_filters=config_model.dimension_filters or {},
                cache_entry=cache_entry,
            )
            if result.is_valid:
                per_item_results.append(
                    BulkUpsertItemResult(
                        cube_id=item.cube_id,
                        semantic_key=item.semantic_key,
                        is_valid=True,
                        error_code=None,
                        message=None,
                    )
                )
            else:
                any_invalid = True
                first = result.errors[0]
                per_item_results.append(
                    BulkUpsertItemResult(
                        cube_id=item.cube_id,
                        semantic_key=item.semantic_key,
                        is_valid=False,
                        error_code=first.error_code,
                        message=first.message,
                        details={
                            "errors": [
                                {
                                    "error_code": e.error_code,
                                    "dimension_name": e.dimension_name,
                                    "member_name": e.member_name,
                                    "message": e.message,
                                }
                                for e in result.errors
                            ],
                        },
                    )
                )

        if any_invalid:
            raise BulkValidationError(per_item_results)

        # 3. Single-session, single-commit persist.
        created_count = 0
        updated_count = 0
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            for item, config_model in zip(items, config_models, strict=True):
                # Optimistic concurrency check, if requested.
                if item.if_match_version is not None:
                    existing = await repo.get_by_key(
                        item.cube_id, item.semantic_key
                    )
                    if (
                        existing is not None
                        and existing.version != item.if_match_version
                    ):
                        # No rows persisted — session will roll back on raise.
                        await session.rollback()
                        raise VersionConflictError(
                            cube_id=item.cube_id,
                            semantic_key=item.semantic_key,
                            expected_version=item.if_match_version,
                            actual_version=existing.version,
                        )
                payload = SemanticMappingCreate(
                    cube_id=item.cube_id,
                    semantic_key=item.semantic_key,
                    label=item.label,
                    description=item.description,
                    config=config_model,
                    is_active=item.is_active,
                )
                _, was_created = await repo.upsert_by_key(
                    payload, updated_by="seed"
                )
                if was_created:
                    created_count += 1
                else:
                    updated_count += 1
            await session.commit()

        return BulkUpsertResult(
            items=per_item_results,
            created_count=created_count,
            updated_count=updated_count,
        )
