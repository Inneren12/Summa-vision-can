#!/usr/bin/env python3
"""DEBT.md structural validator.

Parses each ### DEBT-NNN block individually and validates that
every entry has all 9 required fields. Also checks for speculative
language and duplicate IDs.

Usage:
    python verify_debt.py          # from repo root
    python verify_debt.py DEBT.md  # explicit path

Exit code 0 = all checks passed.
Exit code 1 = validation errors found.

Runs in CI: .github/workflows/backend.yml
"""

import re
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "Source",
    "Added",
    "Severity",
    "Category",
    "Status",
    "Description",
    "Impact",
    "Resolution",
    "Target",
]

SPECULATIVE_PATTERN = re.compile(
    r"\b(may be|might be|possibly|perhaps|could be)\b", re.IGNORECASE
)

# Fields where speculative language is not allowed
NO_SPECULATION_FIELDS = {"Description", "Impact"}


def parse_entries(content: str) -> list[tuple[str, str]]:
    """Split DEBT.md into (entry_id, entry_text) tuples.

    Each entry starts with ### DEBT-NNN and ends before the next
    ### DEBT- or end of Active Debt section.
    """
    entries: list[tuple[str, str]] = []
    # Split on ### DEBT- headers
    parts = re.split(r"(?=^### DEBT-\d+)", content, flags=re.MULTILINE)

    for part in parts:
        match = re.match(r"^### (DEBT-\d+)", part)
        if match:
            entries.append((match.group(1), part))

    return entries


def validate_entry(entry_id: str, entry_text: str) -> list[str]:
    """Validate a single DEBT entry block. Returns list of errors."""
    errors: list[str] = []

    # Check all required fields are present in THIS entry
    for field in REQUIRED_FIELDS:
        pattern = rf"\*\*{field}:\*\*"
        if not re.search(pattern, entry_text):
            errors.append(f"{entry_id}: missing required field '{field}'")

    # Check for speculative language in Description and Impact
    for field in NO_SPECULATION_FIELDS:
        # Extract field value (everything after **Field:** until next **Field:** or end)
        field_match = re.search(
            rf"\*\*{field}:\*\*\s*(.*?)(?=\n- \*\*|\n###|\Z)",
            entry_text,
            re.DOTALL,
        )
        if field_match:
            field_value = field_match.group(1)
            if SPECULATIVE_PATTERN.search(field_value):
                errors.append(
                    f"{entry_id}: speculative language in '{field}' field"
                )

    return errors


def validate(path: Path) -> list[str]:
    """Validate DEBT.md structure. Returns list of errors."""
    if not path.exists():
        return [f"DEBT.md not found at {path}"]

    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    # Parse entries
    entries = parse_entries(content)

    if not entries:
        # No entries is valid — debt might be empty
        return errors

    # Validate each entry individually
    for entry_id, entry_text in entries:
        errors.extend(validate_entry(entry_id, entry_text))

    # Check for duplicate IDs
    ids = [eid for eid, _ in entries]
    seen: set[str] = set()
    for debt_id in ids:
        if debt_id in seen:
            errors.append(f"Duplicate ID: {debt_id}")
        seen.add(debt_id)

    return errors


if __name__ == "__main__":
    debt_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("DEBT.md")
    errors = validate(debt_path)

    # Count entries for summary
    content = debt_path.read_text(encoding="utf-8") if debt_path.exists() else ""
    entry_count = len(re.findall(r"^### DEBT-", content, re.MULTILINE))

    if errors:
        print(f"DEBT.md validation FAILED ({len(errors)} errors, {entry_count} entries):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"DEBT.md validation PASSED ({entry_count} entries, {len(REQUIRED_FIELDS)} fields each)")
        sys.exit(0)