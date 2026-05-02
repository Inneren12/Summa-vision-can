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
from sqlalchemy.exc import IntegrityError
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
    # Atomic upsert helper (Phase 3.1b R2 — eliminates SELECT-then-UPDATE
    # TOCTOU on the version column)
    # ------------------------------------------------------------------

    async def _upsert_atomic(
        self,
        session: AsyncSession,
        repo: SemanticMappingRepository,
        *,
        cube_id: str,
        semantic_key: str,
        label: str,
        description: str | None,
        config_model: SemanticMappingConfig,
        is_active: bool,
        updated_by: str | None,
        if_match_version: int | None,
    ) -> tuple[SemanticMapping, bool]:
        """Atomic upsert primitive used by both single + bulk paths.

        Caller manages the session: opens it, flushes nothing of its own
        between calls, and commits/rolls back when done.

        Concurrency contract:
            * **CREATE branch:** INSERT inside a SAVEPOINT
              (``session.begin_nested``). On UniqueConstraint violation
              the savepoint rolls back automatically and we fall through
              to the UPDATE branch. The outer transaction is preserved
              — bulk callers do not lose their other items.
            * **UPDATE branch:** atomic
              :meth:`SemanticMappingRepository.update_with_version_check`
              (single ``UPDATE ... WHERE version = :expected``). When
              ``if_match_version`` is supplied and the row's current
              version differs, ``rowcount == 0`` and we re-read the
              actual version (a benign read for error context only) and
              raise :class:`VersionConflictError`.
            * ``if_match_version is None`` semantics: last-write-wins.
              The UPDATE uses the row's currently-observed version as
              the ``WHERE`` filter; on rowcount=0 (concurrent writer
              bumped the version) we retry **once** with the freshest
              version. After one failed retry we raise
              ``CONCURRENT_WRITE_RETRY_EXHAUSTED`` rather than spin.

        Returns ``(mapping, was_created)``.
        """
        payload = SemanticMappingCreate(
            cube_id=cube_id,
            semantic_key=semantic_key,
            label=label,
            description=description,
            config=config_model,
            is_active=is_active,
        )

        # ── CREATE branch ────────────────────────────────────────────
        try:
            async with session.begin_nested():
                created = await repo.create(payload, updated_by=updated_by)
            return created, True
        except IntegrityError:
            # Savepoint rolled back; row exists at (cube_id, semantic_key).
            # Outer transaction is intact — bulk caller's prior items
            # remain pending. Fall through to UPDATE.
            pass

        # ── UPDATE branch (atomic version check) ─────────────────────
        existing = await repo.get_by_key(cube_id, semantic_key)
        if existing is None:
            # Row was deleted between INSERT-fail and SELECT. Extremely
            # rare — only possible under a concurrent DELETE racing the
            # caller. Surface as a generic validation error so the admin
            # endpoint maps it to a 400 envelope.
            raise MetadataValidationError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="ROW_VANISHED_DURING_UPSERT",
            )

        config_dict = config_model.model_dump()
        expected = (
            if_match_version
            if if_match_version is not None
            else existing.version
        )
        updated = await repo.update_with_version_check(
            id=existing.id,
            expected_version=expected,
            label=label,
            description=description,
            config=config_dict,
            is_active=is_active,
            updated_by=updated_by,
        )

        if updated is not None:
            return updated, False

        # rowcount == 0 — version did not match.
        if if_match_version is not None:
            current = await repo.get_by_key(cube_id, semantic_key)
            actual_version = current.version if current is not None else -1
            raise VersionConflictError(
                cube_id=cube_id,
                semantic_key=semantic_key,
                expected_version=if_match_version,
                actual_version=actual_version,
            )

        # if_match_version is None: retry once with whatever the version
        # is right now. Documented last-write-wins contract.
        fresh = await repo.get_by_key(cube_id, semantic_key)
        if fresh is None:
            raise MetadataValidationError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="ROW_VANISHED_DURING_UPSERT",
            )
        retried = await repo.update_with_version_check(
            id=fresh.id,
            expected_version=fresh.version,
            label=label,
            description=description,
            config=config_dict,
            is_active=is_active,
            updated_by=updated_by,
        )
        if retried is None:
            raise MetadataValidationError(
                result=ValidationResult(is_valid=False, errors=[]),
                cube_id=cube_id,
                error_code="CONCURRENT_WRITE_RETRY_EXHAUSTED",
            )
        return retried, False

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

        Optimistic concurrency (R2): when ``if_match_version`` is
        provided, the version check happens **inside** the UPDATE
        statement (``WHERE version = :expected``). No SELECT-then-UPDATE
        — eliminates the TOCTOU race where two concurrent writers with
        the same ``if_match_version`` both pass a Python-level check
        and the second silently overwrites the first.

        Raises:
            pydantic.ValidationError: bad ``config`` shape (before cache).
            VersionConflictError: ``if_match_version`` mismatch.
            CubeNotInCacheError / DimensionMismatchError /
            MemberMismatchError / MetadataValidationError: per 3.1ab.
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

        # 4. Atomic persist (single session + commit per call).
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            mapping, was_created = await self._upsert_atomic(
                session,
                repo,
                cube_id=cube_id,
                semantic_key=semantic_key,
                label=label,
                description=description,
                config_model=config_model,
                is_active=is_active,
                updated_by=updated_by,
                if_match_version=if_match_version,
            )
            await session.commit()
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

        # 3. Single-session, single-commit persist via the shared atomic
        #    primitive. Any VersionConflictError raised by an item rolls
        #    back the whole batch (matches Phase 3.1b §A9 lock).
        created_count = 0
        updated_count = 0
        async with self._session_factory() as session:
            repo = self._repository_factory(session)
            for item, config_model in zip(items, config_models, strict=True):
                _, was_created = await self._upsert_atomic(
                    session,
                    repo,
                    cube_id=item.cube_id,
                    semantic_key=item.semantic_key,
                    label=item.label,
                    description=item.description,
                    config_model=config_model,
                    is_active=item.is_active,
                    updated_by="seed",
                    if_match_version=item.if_match_version,
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
