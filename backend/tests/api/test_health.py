"""Unit tests for the ``GET /api/health`` endpoint."""

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.core.config import Settings, get_settings
from src.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _override_settings() -> Settings:
    """Return a deterministic ``Settings`` instance for test isolation."""
    return Settings(app_name="Test App", debug=True, cors_origins="*")


app.dependency_overrides[get_settings] = _override_settings
client = TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health_returns_200() -> None:
    """``GET /api/health`` should respond with HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_status_ok() -> None:
    """The JSON body must contain ``"status": "ok"``."""
    data: dict[str, str] = client.get("/api/health").json()
    assert data["status"] == "ok"


def test_health_timestamp_is_valid_iso() -> None:
    """The ``timestamp`` field must be a valid ISO-8601 datetime string."""
    data: dict[str, str] = client.get("/api/health").json()
    ts = data["timestamp"]
    # Will raise ValueError if the format is not ISO-8601
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None, "timestamp must be timezone-aware"


def test_health_timestamp_is_recent() -> None:
    """The ``timestamp`` should be very close to *now* (within 5 seconds)."""
    before = datetime.now(timezone.utc)
    data: dict[str, str] = client.get("/api/health").json()
    after = datetime.now(timezone.utc)

    ts = datetime.fromisoformat(data["timestamp"])
    assert before <= ts <= after


def test_health_cors_headers() -> None:
    """An ``Origin`` header in the request should trigger CORS response headers."""
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is not None


def test_health_response_keys() -> None:
    """The response must contain exactly ``status`` and ``timestamp`` keys."""
    data: dict[str, str] = client.get("/api/health").json()
    assert set(data.keys()) == {"status", "timestamp"}


def test_health_with_frozen_time() -> None:
    """Verify the exact timestamp value when ``datetime.now`` is mocked."""
    frozen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch("src.api.routers.health.datetime") as mock_dt:
        mock_dt.now.return_value = frozen
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        data: dict[str, str] = client.get("/api/health").json()

    assert data["timestamp"] == frozen.isoformat()


def test_get_settings_returns_settings_instance() -> None:
    """``get_settings()`` must return a ``Settings`` instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_is_cached() -> None:
    """Successive calls to ``get_settings()`` must return the same object."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_defaults() -> None:
    """Default ``Settings`` should carry the expected values."""
    settings = Settings(_env_file=None)
    assert settings.app_name == "Summa Vision API"
    assert settings.debug is False
    assert settings.cors_origins == "*"
