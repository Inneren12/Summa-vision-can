"""DEBT.md structural validator.

Usage:
    python verify_debt.py

Future: wire into CI via .github/workflows/backend.yml
    or as a pre-commit hook.
"""
import re

with open("DEBT.md", "r") as f:
    content = f.read()

# We ignore the headers that contain instructions on not using speculative language
# So we only search the content that comes after the "## Active Debt" separator
body_content = content.split("## Active Debt", 1)[-1]
assert not re.search(r"(?i)\b(may be|might|possibly|perhaps|could be)\b", body_content), "Found speculative language"
headers = len(re.findall(r"### DEBT-", content))
added = len(re.findall(r"Added:", content))
assert headers == added, f"Headers ({headers}) != Added ({added})"

status = len(re.findall(r"Status:", content))
assert headers == status, f"Headers ({headers}) != Status ({status})"

ids = re.findall(r"### (DEBT-\d+)", content)
assert len(ids) == len(set(ids)), "Duplicate IDs found"

errors = []
# Check that every entry has all required fields
required_fields = ["Source:", "Added:", "Severity:", "Category:", "Status:",
                   "Description:", "Impact:", "Resolution:", "Target:"]

entry_count = len(re.findall(r"^### DEBT-", content, re.MULTILINE))

for field in required_fields:
    # Alternative: count by the bold markdown pattern
    actual = len(re.findall(rf"\*\*{re.escape(field.rstrip(':'))}:\*\*", content))
    if actual < entry_count:
        errors.append(
            f"Only {actual}/{entry_count} entries have '{field.rstrip(':')}' field"
        )

if errors:
    print("Validation failed:")
    for err in errors:
        print(f" - {err}")
    exit(1)

print("All validations passed!")
