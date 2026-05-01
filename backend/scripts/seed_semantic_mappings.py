"""Phase 3.1a: Seed SemanticMapping rows from YAML.

Usage::

    cd backend
    python scripts/seed_semantic_mappings.py <yaml_path> [<yaml_path> ...]

Idempotent: re-running the same YAML is a no-op (no version bump, no DB
write) thanks to ``SemanticMappingRepository.upsert_by_key``
change-detection.

Commit granularity: each YAML file is committed independently. If multiple
files are passed and an earlier file succeeds before a later one fails,
already-committed mappings remain. For all-or-nothing across multiple
files, pass them in a single YAML or wrap in a transaction at the call
site.

Phase 3.1a explicitly does NOT validate cube_id existence or dimension
correctness here. Validation hooks in once SemanticMappingValidator
ships in 3.1ab. Until then, manually review YAML before seeding.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

from src.core.database import get_session_factory
from src.repositories.semantic_mapping_repository import (
    SemanticMappingRepository,
)
from src.schemas.semantic_mapping import SemanticMappingCreate


async def _seed_one_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "mappings" not in data:
        raise ValueError(f"{path}: expected top-level 'mappings' key")

    factory = get_session_factory()
    async with factory() as session:
        repo = SemanticMappingRepository(session)

        for raw in data["mappings"]:
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


async def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed SemanticMapping rows from YAML."
    )
    parser.add_argument("yaml_paths", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.yaml_paths:
        if not path.is_file():
            print(f"ERROR: {path} does not exist", file=sys.stderr)
            return 1
        print(f"Seeding from {path} ...")
        await _seed_one_file(path)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
