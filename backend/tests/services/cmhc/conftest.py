"""Shared pytest fixtures for CMHC service tests.

Provides static HTML strings mimicking CMHC portal output, mock storage
implementations, and pre-configured parser instances.
"""

from __future__ import annotations

import pytest

from src.core.storage import StorageInterface
from src.services.cmhc.parser import CMHCParser


# ---------------------------------------------------------------------------
# Static HTML fixtures
# ---------------------------------------------------------------------------

VALID_CMHC_HTML: str = """\
<!DOCTYPE html>
<html lang="en">
<head><title>CMHC Housing Data</title></head>
<body>
<div class="data-container">
  <h1>Housing Market Data – Toronto</h1>
  <table class="data-table" id="housing-data">
    <thead>
      <tr>
        <th>Geography</th>
        <th>Year</th>
        <th>Starts</th>
        <th>Completions</th>
        <th>Under Construction</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Toronto CMA</td>
        <td>2024</td>
        <td>42150</td>
        <td>38200</td>
        <td>97500</td>
      </tr>
      <tr>
        <td>Toronto CMA</td>
        <td>2023</td>
        <td>48300</td>
        <td>36100</td>
        <td>101200</td>
      </tr>
      <tr>
        <td>Toronto CMA</td>
        <td>2022</td>
        <td>43800</td>
        <td>33900</td>
        <td>98700</td>
      </tr>
    </tbody>
  </table>
</div>
</body>
</html>
"""

VALID_CMHC_HTML_MULTIPLE_TABLES: str = """\
<!DOCTYPE html>
<html lang="en">
<head><title>CMHC Multi-Table</title></head>
<body>
  <table id="navigation"><thead><tr><th>Nav</th></tr></thead><tbody><tr><td>Link</td></tr></tbody></table>
  <table id="data">
    <thead>
      <tr><th>City</th><th>Population</th></tr>
    </thead>
    <tbody>
      <tr><td>Toronto</td><td>2930000</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

HTML_MISSING_TABLE: str = """\
<!DOCTYPE html>
<html lang="en">
<head><title>CMHC – Error</title></head>
<body>
<div class="error">
  <h1>Access Denied</h1>
  <p>Please complete the CAPTCHA challenge.</p>
</div>
</body>
</html>
"""

HTML_TABLE_NO_THEAD: str = """\
<!DOCTYPE html>
<html lang="en">
<head><title>CMHC – Broken Table</title></head>
<body>
<table>
  <tr><td>Row without header</td><td>123</td></tr>
</table>
</body>
</html>
"""

HTML_EMPTY_TABLE: str = """\
<!DOCTYPE html>
<html lang="en">
<head><title>CMHC – Empty</title></head>
<body>
<table>
  <thead><tr><th>Col A</th><th>Col B</th></tr></thead>
  <tbody></tbody>
</table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Mock storage
# ---------------------------------------------------------------------------


class MockStorage(StorageInterface):
    """In-memory storage backend for testing.

    Records all uploads so tests can assert on call history.
    """

    def __init__(self) -> None:
        self.uploaded_csv: dict[str, str] = {}
        self.uploaded_raw: dict[str, str | bytes] = {}

    async def upload_dataframe_as_csv(
        self, df: "import('pandas').DataFrame", path: str  # noqa: F821
    ) -> None:
        import pandas as pd

        self.uploaded_csv[path] = df.to_csv(index=False)

    async def upload_raw(
        self, data: str | bytes, path: str, content_type: str = "text/html"
    ) -> None:
        self.uploaded_raw[path] = data

    async def download_csv(self, path: str) -> "import('pandas').DataFrame":  # noqa: F821
        import pandas as pd
        import io

        if path not in self.uploaded_csv:
            raise FileNotFoundError(f"Mock: {path}")
        return pd.read_csv(io.StringIO(self.uploaded_csv[path]))

    async def list_objects(self, prefix: str) -> list[str]:
        return sorted(
            k for k in {**self.uploaded_csv, **self.uploaded_raw} if k.startswith(prefix)
        )

    async def generate_presigned_url(self, path: str, ttl: int = 3600) -> str:
        return f"mock://presigned/{path}?ttl={ttl}"


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def parser() -> CMHCParser:
    """Return a fresh ``CMHCParser`` instance."""
    return CMHCParser()


@pytest.fixture()
def mock_storage() -> MockStorage:
    """Return a fresh ``MockStorage`` instance."""
    return MockStorage()
