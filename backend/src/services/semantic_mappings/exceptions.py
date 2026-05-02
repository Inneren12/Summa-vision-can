"""Exception hierarchy for SemanticMapping validation.

Raised by :class:`src.services.semantic_mappings.service.SemanticMappingService`
when validation against the StatCan metadata cache fails. The 3.1b admin save
endpoint will catch :class:`MetadataValidationError` (and subclasses) and
render the configured ``error_code`` in the DEBT-030 envelope.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

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
