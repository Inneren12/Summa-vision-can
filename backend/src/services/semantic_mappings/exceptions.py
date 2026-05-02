"""Exception hierarchy for SemanticMapping validation.

Raised by :class:`src.services.semantic_mappings.service.SemanticMappingService`
when validation against the StatCan metadata cache fails. The 3.1b admin save
endpoint will catch :class:`MetadataValidationError` (and subclasses) and
render the configured ``error_code`` in the DEBT-030 envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.services.semantic_mappings.validation import ValidationResult


class MetadataValidationError(Exception):
    """Base class for metadata-validation failures.

    Carries the originating :class:`ValidationResult` so the API layer can
    serialize per-error details (``dimension_name``, ``member_name``,
    ``suggested_member_name_en``) into the response envelope.
    """

    def __init__(
        self,
        *,
        result: "ValidationResult",
        cube_id: str,
        error_code: str = "METADATA_VALIDATION_FAILED",
    ) -> None:
        self._result = result
        self._cube_id = cube_id
        self._error_code = error_code
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        if not self._result.errors:
            return (
                f"Metadata validation failed for cube_id={self._cube_id!r}"
            )
        first = self._result.errors[0]
        more = len(self._result.errors) - 1
        suffix = f" ({more} more)" if more > 0 else ""
        return f"{first.message}{suffix}"

    @property
    def result(self) -> "ValidationResult":
        return self._result

    @property
    def cube_id(self) -> str:
        return self._cube_id

    @property
    def error_code(self) -> str:
        return self._error_code


class CubeNotInCacheError(MetadataValidationError):
    """Cache miss + StatCan unavailable, OR StatCan returned no metadata.

    Re-wraps :class:`src.services.statcan.metadata_cache.StatCanUnavailableError`
    and :class:`src.services.statcan.metadata_cache.CubeNotFoundError` for a
    uniform admin/UI contract.
    """


class DimensionMismatchError(MetadataValidationError):
    """One or more ``DIMENSION_NOT_FOUND`` errors in :attr:`result`."""


class MemberMismatchError(MetadataValidationError):
    """One or more ``MEMBER_NOT_FOUND`` errors in :attr:`result`."""


class MappingNotFoundError(Exception):
    """Raised by SemanticMappingService when a row lookup fails (404 path)."""

    def __init__(
        self,
        *,
        mapping_id: int | None = None,
        cube_id: str | None = None,
        semantic_key: str | None = None,
    ) -> None:
        self.mapping_id = mapping_id
        self.cube_id = cube_id
        self.semantic_key = semantic_key
        if mapping_id is not None:
            msg = f"SemanticMapping id={mapping_id} not found"
        else:
            msg = (
                f"SemanticMapping (cube_id={cube_id!r}, "
                f"semantic_key={semantic_key!r}) not found"
            )
        super().__init__(msg)


class VersionConflictError(Exception):
    """Sibling to MetadataValidationError family.

    NOT a subclass of MetadataValidationError — version conflict is a
    precondition failure, not a metadata-content validation failure. The HTTP
    layer handles it distinctly with 412 PRECONDITION_FAILED status.
    """

    error_code = "VERSION_CONFLICT"

    def __init__(
        self,
        *,
        cube_id: str,
        semantic_key: str,
        expected_version: int,
        actual_version: int,
    ) -> None:
        self.cube_id = cube_id
        self.semantic_key = semantic_key
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Version conflict: expected version={expected_version}, "
            f"actual={actual_version} for ({cube_id!r}, {semantic_key!r})"
        )


@dataclass(frozen=True)
class BulkUpsertItem:
    """Per-item input for :meth:`SemanticMappingService.upsert_many_validated`."""

    cube_id: str
    product_id: int
    semantic_key: str
    label: str
    description: str | None
    config: dict
    is_active: bool
    if_match_version: int | None = None


@dataclass(frozen=True)
class BulkUpsertItemResult:
    """Per-item outcome carried by :class:`BulkValidationError`."""

    cube_id: str
    semantic_key: str
    is_valid: bool
    error_code: str | None
    message: str | None
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class BulkUpsertResult:
    """Aggregate outcome of a successful bulk upsert."""

    items: list[BulkUpsertItemResult] = field(default_factory=list)
    created_count: int = 0
    updated_count: int = 0


class BulkValidationError(MetadataValidationError):
    """Raised when at least one item in a bulk batch fails validation.

    Carries per-item results; NO rows persisted when this raises.
    """

    def __init__(self, results: list[BulkUpsertItemResult]) -> None:
        self._results = results
        invalid_count = sum(1 for r in results if not r.is_valid)
        total = len(results)
        from src.services.semantic_mappings.validation import ValidationResult
        super().__init__(
            result=ValidationResult(is_valid=False, errors=[]),
            cube_id="<bulk>",
            error_code="BULK_VALIDATION_FAILED",
        )
        self._summary = f"{invalid_count} of {total} items failed validation"

    def _build_message(self) -> str:
        # Called by parent __init__ before _summary is set; tolerate that.
        return getattr(self, "_summary", "Bulk validation failed")

    @property
    def results(self) -> list[BulkUpsertItemResult]:
        return self._results
