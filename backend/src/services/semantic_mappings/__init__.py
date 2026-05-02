"""Phase 3.1ab: SemanticMapping validator + service.

Wraps :class:`src.repositories.semantic_mapping_repository.SemanticMappingRepository`
with name-based validation against
:class:`src.services.statcan.metadata_cache.StatCanMetadataCacheService`.

Validation is name-based (founder lock 1, 2026-05-01): the mapping's
``config.dimension_filters`` is a ``dict[str, str]`` of dimension name → member
name pairs. The validator compares EN names (case-fold + strip) against the
cached cube metadata. Resolved numeric IDs are populated in the
:class:`ValidationResult` for forward consumers.
"""
