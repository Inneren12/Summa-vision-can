"""Pure validation of SemanticMapping config against cached cube metadata.

ARCH-PURA-001: this module's :func:`validate_mapping_against_cache` is a pure
function. No I/O, no clock, no logger, no exceptions raised. Returns
:class:`ValidationResult` only — caller (service layer) decides which exception
subclass to raise based on the error mix.

Founder lock 1 (2026-05-01): validation is name-based, not id-based. The
mapping's ``config.dimension_filters`` is a ``dict[str, str]`` of dimension
``name_en`` → member ``name_en`` pairs. Comparison is case-fold + strip.
Resolved numeric IDs (``dimension_position_id``, ``member_id``) are populated
in the result for downstream consumers (UI, future ID-based migration).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Literal

from src.services.statcan.metadata_cache import CubeMetadataCacheEntry


ErrorCode = Literal[
    "CUBE_PRODUCT_MISMATCH",
    "DIMENSION_NOT_FOUND",
    "MEMBER_NOT_FOUND",
]


@dataclass(frozen=True)
class ValidationError:
    """A single blocking validation problem.

    ``resolved_*`` fields are populated when the cache entry has the
    information available (e.g. dimension matched but member did not — the
    matched dimension's ``position_id`` is recorded).
    """

    error_code: ErrorCode
    dimension_name: str | None
    member_name: str | None
    resolved_dimension_position_id: int | None
    resolved_member_id: int | None
    suggested_member_name_en: str | None
    message: str


@dataclass(frozen=True)
class ResolvedDimensionFilter:
    """A successfully matched (dimension, member) pair with cache IDs."""

    dimension_name: str
    member_name: str
    dimension_position_id: int
    member_id: int


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate validator output. ``is_valid`` ⇔ ``errors`` is empty."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    resolved_filters: list[ResolvedDimensionFilter] = field(default_factory=list)


def _normalize_name(name: str) -> str:
    """Case-fold + strip for name-equality matching. Pure helper."""
    return name.strip().casefold()


def _maybe_fuzzy_suggest(target: str, candidates: list[str]) -> str | None:
    """Best-effort fuzzy hint via :func:`difflib.get_close_matches` (stdlib).

    Returns the closest member name above ``cutoff=0.6``, or ``None``.
    Pure helper. See DEBT-052 for the EN-only limitation.
    """
    matches = get_close_matches(target, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


def validate_mapping_against_cache(
    *,
    cube_id: str,
    product_id: int,
    dimension_filters: dict[str, str],
    cache_entry: CubeMetadataCacheEntry,
) -> ValidationResult:
    """Validate a SemanticMapping's ``dimension_filters`` against cube metadata.

    Args:
        cube_id: Mapping's ``cube_id`` (semantic identifier).
        product_id: Mapping's StatCan numeric ``product_id``.
        dimension_filters: ``dict[str, str]`` from mapping
            ``config.dimension_filters`` — keys are dimension ``name_en``
            values, values are member ``name_en`` values.
        cache_entry: Pre-fetched cache entry. Caller (service layer) is
            responsible for fetching this; the validator is pure.

    Returns:
        :class:`ValidationResult` with ``is_valid`` flag, errors list, and
        resolved filters list. ``is_valid=True`` iff ``errors`` is empty.
        Validation does NOT short-circuit on the first error — all errors
        are collected so the operator sees the full picture.
    """
    errors: list[ValidationError] = []
    resolved: list[ResolvedDimensionFilter] = []

    if cache_entry.product_id != product_id:
        errors.append(
            ValidationError(
                error_code="CUBE_PRODUCT_MISMATCH",
                dimension_name=None,
                member_name=None,
                resolved_dimension_position_id=None,
                resolved_member_id=None,
                suggested_member_name_en=None,
                message=(
                    f"Mapping product_id={product_id} does not match "
                    f"cached product_id={cache_entry.product_id} for "
                    f"cube_id={cube_id!r}"
                ),
            )
        )

    cache_dims = (
        cache_entry.dimensions.get("dimensions", [])
        if isinstance(cache_entry.dimensions, dict)
        else []
    )
    dim_by_normalized_name: dict[str, dict] = {
        _normalize_name(dim["name_en"]): dim for dim in cache_dims
    }

    for dim_name, member_name in dimension_filters.items():
        norm_dim = _normalize_name(dim_name)
        if norm_dim not in dim_by_normalized_name:
            errors.append(
                ValidationError(
                    error_code="DIMENSION_NOT_FOUND",
                    dimension_name=dim_name,
                    member_name=member_name,
                    resolved_dimension_position_id=None,
                    resolved_member_id=None,
                    suggested_member_name_en=None,
                    message=(
                        f"Dimension {dim_name!r} not found in cube {cube_id!r}"
                    ),
                )
            )
            continue

        matched_dim = dim_by_normalized_name[norm_dim]
        members = matched_dim.get("members", [])
        member_by_normalized_name: dict[str, dict] = {
            _normalize_name(m["name_en"]): m for m in members
        }

        norm_member = _normalize_name(member_name)
        if norm_member not in member_by_normalized_name:
            suggested = _maybe_fuzzy_suggest(
                member_name, [m["name_en"] for m in members]
            )
            hint = f" (did you mean {suggested!r}?)" if suggested else ""
            errors.append(
                ValidationError(
                    error_code="MEMBER_NOT_FOUND",
                    dimension_name=dim_name,
                    member_name=member_name,
                    resolved_dimension_position_id=matched_dim.get("position_id"),
                    resolved_member_id=None,
                    suggested_member_name_en=suggested,
                    message=(
                        f"Member {member_name!r} not found in dimension "
                        f"{dim_name!r}{hint}"
                    ),
                )
            )
            continue

        matched_member = member_by_normalized_name[norm_member]
        resolved.append(
            ResolvedDimensionFilter(
                dimension_name=dim_name,
                member_name=member_name,
                dimension_position_id=matched_dim["position_id"],
                member_id=matched_member["member_id"],
            )
        )

    return ValidationResult(
        is_valid=(len(errors) == 0),
        errors=errors,
        resolved_filters=resolved,
    )
