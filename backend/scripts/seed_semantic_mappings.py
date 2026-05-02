"""Phase 3.1a + 3.1ab: Seed SemanticMapping rows from YAML.

Usage::

    cd backend
    python scripts/seed_semantic_mappings.py <yaml_path> [<yaml_path> ...]
    python scripts/seed_semantic_mappings.py --skip-validation <yaml_path>

Idempotent: re-running the same YAML is a no-op (no version bump, no DB
write) thanks to ``SemanticMappingRepository.upsert_by_key``
change-detection.

Commit granularity: each YAML file is committed independently. If multiple
files are passed and an earlier file succeeds before a later one fails,
already-committed mappings remain. For all-or-nothing across multiple
files, pass them in a single YAML or wrap in a transaction at the call
site.

Phase 3.1ab default: each row goes through
:class:`SemanticMappingService.upsert_validated`, which fetches cube
metadata from :class:`StatCanMetadataCacheService` (priming cache on miss
via the StatCan WDS API) and rejects rows whose ``dimension_filters`` do
not match the cached cube. ``--skip-validation`` reverts to the 3.1a
direct-repo path for offline / dev workflows; a structlog warning is
emitted whenever the flag is used.

When validation is on, each mapping row must include a top-level
``product_id`` key (StatCan numeric ID) — the row's ``cube_id`` alone is a
semantic identifier and does not uniquely select cube metadata.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
import yaml

from src.core.database import get_session_factory
from src.core.rate_limit import AsyncTokenBucket
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.semantic_mapping import SemanticMappingCreate
from src.services.semantic_mappings.service import SemanticMappingService
from src.services.statcan.client import StatCanClient
from src.services.statcan.maintenance import StatCanMaintenanceGuard
from src.services.statcan.metadata_cache import StatCanMetadataCacheService

logger: structlog.stdlib.BoundLogger = structlog.get_logger(
    module="scripts.seed_semantic_mappings",
)


async def _seed_one_file_skip_validation(path: Path) -> None:
    """Phase 3.1a direct-repo path. Used only with --skip-validation."""
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "mappings" not in data:
        raise ValueError(f"{path}: expected top-level 'mappings' key")

    factory = get_session_factory()
    async with factory() as session:
        repo = SemanticMappingRepository(session)

        for raw in data["mappings"]:
            # product_id is a validation-only sibling key; pop it before
            # constructing the pydantic payload (which forbids extras).
            raw = {k: v for k, v in raw.items() if k != "product_id"}
            payload = SemanticMappingCreate(**raw)
            mapping, was_created = await repo.upsert_by_key(
                payload, updated_by="seed"
            )
            verb = "created" if was_created else "updated"
            print(
                f"  {verb}: {payload.cube_id} / {payload.semantic_key}  "
                f"(v{mapping.version})"
            )

        await session.commit()


async def _seed_one_file_validated(
    path: Path, service: SemanticMappingService
) -> None:
    """Phase 3.1ab validated path. Each row is checked against the cache."""
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "mappings" not in data:
        raise ValueError(f"{path}: expected top-level 'mappings' key")

    for raw in data["mappings"]:
        product_id = raw.get("product_id")
        if product_id is None:
            raise ValueError(
                f"{path}: row {raw.get('semantic_key')!r} is missing "
                f"'product_id' (required when validation is on; pass "
                f"--skip-validation to bypass)."
            )

        # Validate the SemanticMapping shape via pydantic, then forward
        # the flat fields the service expects.
        payload = SemanticMappingCreate(
            **{k: v for k, v in raw.items() if k != "product_id"}
        )
        mapping = await service.upsert_validated(
            cube_id=payload.cube_id,
            product_id=int(product_id),
            semantic_key=payload.semantic_key,
            label=payload.label,
            description=payload.description,
            config=payload.config.model_dump(),
            is_active=payload.is_active,
            updated_by="seed",
        )
        print(
            f"  upserted: {payload.cube_id} / {payload.semantic_key}  "
            f"(v{mapping.version})"
        )


async def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed SemanticMapping rows from YAML."
    )
    parser.add_argument("yaml_paths", nargs="+", type=Path)
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help=(
            "Skip cache-driven validation and call the repository directly "
            "(3.1a path). Use only for offline / dev workflows where the "
            "StatCan WDS endpoint is unreachable."
        ),
    )
    args = parser.parse_args()

    for path in args.yaml_paths:
        if not path.is_file():
            print(f"ERROR: {path} does not exist", file=sys.stderr)
            return 1

    if args.skip_validation:
        logger.warning(
            "seed.skip_validation_enabled",
            message=(
                "Validation skipped via --skip-validation flag. "
                "Use only for offline dev."
            ),
        )
        for path in args.yaml_paths:
            print(f"Seeding from {path} ...")
            await _seed_one_file_skip_validation(path)
        print("Done.")
        return 0

    factory = get_session_factory()
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = StatCanClient(
            http_client,
            StatCanMaintenanceGuard(),
            AsyncTokenBucket(),
        )
        cache = StatCanMetadataCacheService(
            session_factory=factory,
            client=client,
            clock=lambda: datetime.now(timezone.utc),
            logger=structlog.get_logger(module="statcan.metadata_cache"),
        )
        service = SemanticMappingService(
            session_factory=factory,
            repository_factory=SemanticMappingRepository,
            metadata_cache=cache,
            logger=structlog.get_logger(module="semantic_mappings.service"),
        )
        for path in args.yaml_paths:
            print(f"Seeding from {path} ...")
            await _seed_one_file_validated(path, service)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
