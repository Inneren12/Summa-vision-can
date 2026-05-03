"""Phase 3.1c — Resolve service package.

Hosts the read-side service that fronts ``StatCanValueCacheService.get_cached``
for the singular admin resolve endpoint
(``GET /api/v1/admin/resolve/{cube_id}/{semantic_key}``).

See ``docs/recon/phase-3-1c-recon.md`` (and the addendum) for the full
contract; this package implements the locks recorded there (L1, L2,
R1-R3, C1-C3, F-fix-3 missing-observation contract).
"""
