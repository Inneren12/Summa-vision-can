#!/usr/bin/env python
"""Batch graphic generation CLI for ops.

Direct service imports — does NOT go through the HTTP API.

Usage examples::

    # Process a JSON manifest of generation configs
    python scripts/ops/generate_batch.py --manifest manifest.json

    # Limit concurrent renders (default: 2)
    python scripts/ops/generate_batch.py --manifest manifest.json --concurrency 4

    # Single generation (no manifest needed)
    python scripts/ops/generate_batch.py \\
        --data-key data/housing_starts.parquet \\
        --chart-type bar \\
        --title "Housing Starts Q1 2026" \\
        --category housing

    # Dry-run: validate manifest without executing
    python scripts/ops/generate_batch.py --manifest manifest.json --dry-run

Manifest format (JSON array)::

    [
        {
            "data_key": "data/housing_starts.parquet",
            "chart_type": "bar",
            "title": "Housing Starts Q1 2026",
            "size": [1080, 1080],
            "category": "housing",
            "source_product_id": "14-10-0127"
        }
    ]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Ensure backend/src is importable when running from backend/
_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch graphic generation — ops CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Manifest mode
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to JSON manifest file with generation configs.",
    )

    # Single-item mode
    parser.add_argument("--data-key", help="S3 key to source Parquet file.")
    parser.add_argument("--chart-type", help='Chart type (e.g. "bar", "line").')
    parser.add_argument("--title", help="Chart headline.")
    parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[1080, 1080],
        metavar=("WIDTH", "HEIGHT"),
        help="Output size in pixels (default: 1080 1080).",
    )
    parser.add_argument(
        "--category",
        default="housing",
        help='Background category (default: "housing").',
    )
    parser.add_argument(
        "--source-product-id",
        default=None,
        help="StatCan product ID for versioning lineage.",
    )

    # Execution options
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Max concurrent render operations (default: 2).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest and print entries without executing.",
    )

    return parser


def _parse_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build the list of generation entries from CLI args."""
    if args.manifest:
        manifest_path: Path = args.manifest
        if not manifest_path.exists():
            print(f"ERROR: Manifest file not found: {manifest_path}", file=sys.stderr)
            sys.exit(1)
        with open(manifest_path) as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            print("ERROR: Manifest must be a JSON array.", file=sys.stderr)
            sys.exit(1)
        return entries

    # Single-item mode
    if not args.data_key:
        print("ERROR: Provide --manifest or --data-key.", file=sys.stderr)
        sys.exit(1)
    if not args.chart_type:
        print("ERROR: --chart-type is required.", file=sys.stderr)
        sys.exit(1)
    if not args.title:
        print("ERROR: --title is required.", file=sys.stderr)
        sys.exit(1)

    return [
        {
            "data_key": args.data_key,
            "chart_type": args.chart_type,
            "title": args.title,
            "size": list(args.size),
            "category": args.category,
            "source_product_id": args.source_product_id,
        }
    ]


def _validate_entry(entry: dict[str, Any], index: int) -> list[str]:
    """Return list of validation errors for a single entry."""
    errors: list[str] = []
    for required in ("data_key", "chart_type", "title"):
        if required not in entry or not entry[required]:
            errors.append(f"  [{index}] Missing required field: {required}")
    size = entry.get("size", [1080, 1080])
    if not isinstance(size, list) or len(size) != 2:
        errors.append(f"  [{index}] 'size' must be a 2-element list, got: {size}")
    return errors


async def _run_batch(
    entries: list[dict[str, Any]],
    concurrency: int,
) -> list[dict[str, Any]]:
    """Execute all generation entries through the pipeline."""
    from src.core.config import get_settings
    from src.core.database import get_engine, get_session_factory
    from src.core.storage import get_storage_manager
    from src.services.graphics.pipeline import GraphicPipeline

    settings = get_settings()
    factory = get_session_factory()
    storage = get_storage_manager()

    pipeline = GraphicPipeline(
        storage=storage,
        session_factory=factory,
        settings=settings,
    )

    render_sem = asyncio.Semaphore(concurrency)
    io_sem = asyncio.Semaphore(concurrency * 5)

    results: list[dict[str, Any]] = []

    for i, entry in enumerate(entries, 1):
        title = entry.get("title", "untitled")
        print(f"[{i}/{len(entries)}] Generating: {title} ...")

        try:
            result = await pipeline.generate(
                data_key=entry["data_key"],
                chart_type=entry["chart_type"],
                title=entry["title"],
                size=tuple(entry.get("size", [1080, 1080])),
                category=entry.get("category", "housing"),
                source_product_id=entry.get("source_product_id"),
                render_sem=render_sem,
                io_sem=io_sem,
            )
            results.append({"index": i, "status": "ok", "result": result.model_dump()})
            print(
                f"  OK  publication_id={result.publication_id} "
                f"version={result.version}"
            )
        except Exception as exc:
            results.append({"index": i, "status": "error", "error": str(exc)})
            print(f"  FAIL  {exc}", file=sys.stderr)

    # Dispose engine
    await get_engine().dispose()

    return results


def main(argv: list[str] | None = None) -> int:
    """Entry point for the batch CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    entries = _parse_entries(args)

    # Validate all entries
    all_errors: list[str] = []
    for idx, entry in enumerate(entries):
        all_errors.extend(_validate_entry(entry, idx))

    if all_errors:
        print("Validation errors:", file=sys.stderr)
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    print(f"Entries: {len(entries)}  Concurrency: {args.concurrency}")

    if args.dry_run:
        for i, entry in enumerate(entries):
            print(f"  [{i}] {entry.get('title', '?')} ({entry.get('chart_type', '?')})")
        print("Dry run complete — no jobs executed.")
        return 0

    results = asyncio.run(_run_batch(entries, args.concurrency))

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    fail_count = len(results) - ok_count
    print(f"\nBatch complete: {ok_count} succeeded, {fail_count} failed")

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
