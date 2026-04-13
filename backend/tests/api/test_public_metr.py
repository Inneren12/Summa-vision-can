"""Tests for METR public API endpoints.

Tests exercise:
1. Calculate endpoint — returns METR with components.
2. Curve endpoint — returns full curve with dead zones.
3. Compare endpoint — returns provincial comparison.
4. Input validation — invalid params return 422.
5. Rate limiting — excess requests return 429.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.public_metr import router


# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


# ---------------------------------------------------------------------------
# Calculate endpoint
# ---------------------------------------------------------------------------


class TestCalculateEndpoint:
    def test_returns_200(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 47000, "province": "ON",
                    "family_type": "single_parent", "n_children": 2,
                    "children_under_6": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "metr" in data
        assert "components" in data
        assert "zone" in data
        assert "keep_per_dollar" in data

    def test_zone_classification(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 47000, "province": "ON",
                    "family_type": "single_parent", "n_children": 2,
                    "children_under_6": 2},
        )
        data = resp.json()
        assert data["zone"] in ("normal", "high", "dead_zone", "extreme")

    def test_components_present(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000},
        )
        assert resp.status_code == 200
        comp = resp.json()["components"]
        expected_keys = {
            "federal_tax", "provincial_tax", "cpp", "cpp2", "ei",
            "ohp", "ccb", "gst_credit", "cwb", "provincial_benefits",
        }
        assert expected_keys == set(comp.keys())

    def test_default_params(self) -> None:
        """Default province=ON, family_type=single, 0 children."""
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gross_income"] == 50000

    def test_keep_per_dollar(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000},
        )
        data = resp.json()
        expected_keep = round(1 - data["metr"] / 100, 3)
        assert abs(data["keep_per_dollar"] - expected_keep) < 0.01

    def test_all_provinces(self) -> None:
        for prov in ("ON", "BC", "AB", "QC"):
            resp = client.get(
                "/api/v1/public/metr/calculate",
                params={"income": 50000, "province": prov},
            )
            assert resp.status_code == 200, f"Failed for {prov}"


# ---------------------------------------------------------------------------
# Curve endpoint
# ---------------------------------------------------------------------------


class TestCurveEndpoint:
    def test_returns_curve(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/curve",
            params={"province": "ON", "family_type": "single_parent",
                    "n_children": 2, "children_under_6": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["curve"]) > 100
        assert "dead_zones" in data
        assert "peak" in data
        assert "annotations" in data

    def test_curve_points_structure(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/curve",
            params={"province": "ON", "step": 5000},
        )
        data = resp.json()
        point = data["curve"][0]
        assert "gross" in point
        assert "net" in point
        assert "metr" in point
        assert "zone" in point

    def test_custom_range(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/curve",
            params={"income_min": 20000, "income_max": 80000, "step": 2000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["curve"][0]["gross"] == 20000
        assert data["curve"][-1]["gross"] == 80000

    def test_dead_zones_for_family(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/curve",
            params={"province": "ON", "family_type": "single_parent",
                    "n_children": 2, "children_under_6": 2},
        )
        data = resp.json()
        assert len(data["dead_zones"]) >= 1

    def test_peak_present(self) -> None:
        resp = client.get("/api/v1/public/metr/curve")
        data = resp.json()
        assert "gross" in data["peak"]
        assert "metr" in data["peak"]


# ---------------------------------------------------------------------------
# Compare endpoint
# ---------------------------------------------------------------------------


class TestCompareEndpoint:
    def test_returns_4_provinces(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/compare",
            params={"income": 47000, "family_type": "single_parent",
                    "n_children": 2, "children_under_6": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["provinces"]) == 4

    def test_sorted_by_metr_descending(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/compare",
            params={"income": 47000},
        )
        data = resp.json()
        metrs = [p["metr"] for p in data["provinces"]]
        assert metrs == sorted(metrs, reverse=True)

    def test_each_province_has_fields(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/compare",
            params={"income": 50000},
        )
        data = resp.json()
        for p in data["provinces"]:
            assert "province" in p
            assert "metr" in p
            assert "zone" in p

    def test_all_four_province_codes(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/compare",
            params={"income": 50000},
        )
        data = resp.json()
        codes = {p["province"] for p in data["provinces"]}
        assert codes == {"ON", "BC", "AB", "QC"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_negative_income_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": -5000},
        )
        assert resp.status_code == 422

    def test_income_too_high_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 600000},
        )
        assert resp.status_code == 422

    def test_invalid_province_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000, "province": "XX"},
        )
        assert resp.status_code == 422

    def test_invalid_family_type_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000, "family_type": "invalid"},
        )
        assert resp.status_code == 422

    def test_too_many_children_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000, "n_children": 10},
        )
        assert resp.status_code == 422

    def test_compare_income_too_low_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/compare",
            params={"income": 5000},
        )
        assert resp.status_code == 422

    def test_curve_step_too_small_returns_422(self) -> None:
        resp = client.get(
            "/api/v1/public/metr/curve",
            params={"step": 100},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_rate_limit_enforced(self) -> None:
        """After 60 requests, subsequent ones should be rate-limited."""
        # Reset any existing limiter state by importing and resetting
        from src.api.routers.public_metr import _metr_limiter
        _metr_limiter.reset()

        for i in range(60):
            resp = client.get(
                "/api/v1/public/metr/calculate",
                params={"income": 50000},
            )
            assert resp.status_code == 200, f"Request {i+1} failed unexpectedly"

        # 61st request should be rate-limited
        resp = client.get(
            "/api/v1/public/metr/calculate",
            params={"income": 50000},
        )
        assert resp.status_code == 429

        # Clean up
        _metr_limiter.reset()
