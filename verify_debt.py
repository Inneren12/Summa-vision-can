#!/usr/bin/env python3
"""DEBT.md structural validator.

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


def validate(path: Path) -> list[str]:
    """Validate DEBT.md structure. Returns list of errors."""
    if not path.exists():
        return [f"DEBT.md not found at {path}"]

    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    # 1. No speculative language in descriptions
    spec_pattern = re.compile(
        r"(?i)\b(may be|might be|possibly|perhaps|could be)\b"
    )
    for i, line in enumerate(content.splitlines(), 1):
        if line.startswith("- **Description"):
            if spec_pattern.search(line):
                errors.append(
                    f"Line {i}: speculative language in Description"
                )

    # 2. Count entries vs required fields
    entry_count = len(re.findall(r"^### DEBT-", content, re.MULTILINE))
    if entry_count == 0:
        return errors  # No entries to validate

    required = [
        "Source", "Added", "Severity", "Category",
        "Status", "Description", "Impact", "Resolution", "Target",
    ]
    for field in required:
        field_count = len(
            re.findall(rf"\*\*{field}:\*\*", content)
        )
        if field_count < entry_count:
            errors.append(
                f"Only {field_count}/{entry_count} entries have "
                f"'{field}' field"
            )

    # 3. No duplicate IDs
    ids = re.findall(r"^### (DEBT-\d+)", content, re.MULTILINE)
    seen: set[str] = set()
    for debt_id in ids:
        if debt_id in seen:
            errors.append(f"Duplicate ID: {debt_id}")
        seen.add(debt_id)

    return errors


if __name__ == "__main__":
    debt_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("DEBT.md")
    errors = validate(debt_path)

    if errors:
        print(f"DEBT.md validation FAILED ({len(errors)} errors):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"DEBT.md validation PASSED ({len(re.findall(r'^### DEBT-', debt_path.read_text(), re.MULTILINE))} entries)")
        sys.exit(0)