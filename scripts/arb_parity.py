#!/usr/bin/env python3
"""ARB parity verification for Summa Vision admin app.

Verifies EN/RU ARB files have matching keys, placeholder parity, and
metadata consistency.

Usage: python3 scripts/arb_parity.py [--strict-metadata] [--json] \
                                      [--en PATH] [--ru PATH]

Exit codes:
  0 - clean
  1 - drift
  2 - error
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load_arb(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: ARB file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(2)


def placeholders(value) -> set:
    if not isinstance(value, str):
        return set()
    return set(re.findall(r"\{(\w+)\}", value))


def check_parity(en: dict, ru: dict, strict_metadata: bool) -> dict:
    en_keys = {k for k in en if not k.startswith("@")}
    ru_keys = {k for k in ru if not k.startswith("@")}

    findings = {
        "en_count": len(en_keys),
        "ru_count": len(ru_keys),
        "missing_in_ru": sorted(en_keys - ru_keys),
        "missing_in_en": sorted(ru_keys - en_keys),
        "placeholder_mismatches": [],
        "metadata_mismatches": [],
        "ru_metadata_count": sum(
            1 for k in ru if k.startswith("@") and not k.startswith("@@")
        ),
    }

    for k in sorted(en_keys & ru_keys):
        en_ph = placeholders(en[k])
        ru_ph = placeholders(ru[k])
        if en_ph != ru_ph:
            findings["placeholder_mismatches"].append({
                "key": k,
                "en": sorted(en_ph),
                "ru": sorted(ru_ph),
            })

    for k in sorted(en_keys):
        meta = en.get(f"@{k}", {})
        if not isinstance(meta, dict):
            continue
        declared_raw = meta.get("placeholders", {})
        if not isinstance(declared_raw, dict):
            continue
        declared = set(declared_raw.keys())
        actual = placeholders(en[k])
        if declared != actual:
            findings["metadata_mismatches"].append({
                "key": k,
                "declared": sorted(declared),
                "actual": sorted(actual),
            })

    has_drift = bool(
        findings["missing_in_ru"]
        or findings["missing_in_en"]
        or findings["placeholder_mismatches"]
        or findings["metadata_mismatches"]
        or (strict_metadata and findings["ru_metadata_count"] > 0)
    )
    findings["status"] = "drift" if has_drift else "clean"
    return findings


def _placeholder_key_count(en: dict) -> int:
    return sum(
        1
        for k in en
        if not k.startswith("@") and placeholders(en[k])
    )


def format_human(findings: dict, en: dict, strict_metadata: bool) -> str:
    lines = []
    if findings["status"] == "clean":
        lines.append("=== ARB parity check: PASS ===")
        lines.append(f"EN keys: {findings['en_count']}")
        lines.append(f"RU keys: {findings['ru_count']}")
        ph_count = _placeholder_key_count(en)
        lines.append(
            f"Placeholder parity: clean ({ph_count} keys with placeholders)"
        )
        lines.append("Metadata consistency: clean")
        if strict_metadata:
            lines.append(
                f"RU metadata entries: {findings['ru_metadata_count']} (strict mode allows 0)"
            )
        return "\n".join(lines)

    lines.append("=== ARB parity check: DRIFT ===")
    lines.append(f"EN keys: {findings['en_count']}")
    lines.append(f"RU keys: {findings['ru_count']}")
    lines.append(f"Missing in RU: {findings['missing_in_ru']}")
    lines.append(f"Missing in EN: {findings['missing_in_en']}")
    lines.append(
        f"Placeholder mismatches: {findings['placeholder_mismatches']}"
    )
    lines.append(f"Metadata mismatches: {findings['metadata_mismatches']}")
    if strict_metadata:
        lines.append(
            f"RU metadata entries (strict mode): {findings['ru_metadata_count']}"
        )
    lines.append("")
    lines.append("Exit code: 1")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Verify ARB key parity for Summa Vision admin.",
    )
    parser.add_argument(
        "--en",
        default="frontend/lib/l10n/app_en.arb",
        help="Path to EN ARB file",
    )
    parser.add_argument(
        "--ru",
        default="frontend/lib/l10n/app_ru.arb",
        help="Path to RU ARB file",
    )
    parser.add_argument(
        "--strict-metadata",
        action="store_true",
        help="Also fail if RU has unexpected @<key> metadata",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    args = parser.parse_args()

    en_path = Path(args.en)
    ru_path = Path(args.ru)
    en = load_arb(en_path)
    ru = load_arb(ru_path)

    findings = check_parity(en, ru, args.strict_metadata)

    if args.json_output:
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    else:
        print(format_human(findings, en, args.strict_metadata))

    sys.exit(1 if findings["status"] == "drift" else 0)


if __name__ == "__main__":
    main()
