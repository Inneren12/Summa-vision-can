"""Tests for the Summa Vision API health endpoint."""

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_health_returns_200() -> None:
    """GET /api/health should return 200 with status and timestamp."""
    response = client.get("/api/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_health_cors_headers() -> None:
    """GET /api/health with an Origin header should return CORS allow-origin."""
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
