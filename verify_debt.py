import re

with open("DEBT.md", "r") as f:
    content = f.read()

assert not re.search(r"(?i)may be|might|possibly|perhaps|could be", content), "Found speculative language"
headers = len(re.findall(r"### DEBT-", content))
added = len(re.findall(r"Added:", content))
assert headers == added, f"Headers ({headers}) != Added ({added})"

status = len(re.findall(r"Status:", content))
assert headers == status, f"Headers ({headers}) != Status ({status})"

ids = re.findall(r"### (DEBT-\d+)", content)
assert len(ids) == len(set(ids)), "Duplicate IDs found"

print("All validations passed!")
