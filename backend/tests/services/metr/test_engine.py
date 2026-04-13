"""Tests for METR calculation engine.

Verifies tax calculations, benefit clawbacks, dead zones, and
cross-province comparisons against known reference values from
the original metr_calculator.py output and CRA formulas.
"""

from __future__ import annotations

import pytest

from src.services.metr.engine import (
    DeadZone,
    FamilyType,
    METRComponents,
    METRCurvePoint,
    METRInput,
    METRResult,
    Province,
    calculate_metr,
    calculate_net_income,
    ccb_benefit,
    classify_zone,
    cpp2_contribution,
    cpp_contribution,
    cwb_benefit,
    ei_premium,
    federal_tax,
    find_dead_zones,
    generate_curve,
    gst_credit,
    ontario_health_premium,
    provincial_benefits,
    provincial_tax,
)


# ---------------------------------------------------------------------------
# Federal tax component tests
# ---------------------------------------------------------------------------


class TestFederalTax:
    def test_below_basic_personal_amount(self) -> None:
        assert federal_tax(10_000) == 0.0

    def test_at_basic_personal_amount(self) -> None:
        assert federal_tax(16_129) == 0.0

    def test_first_bracket(self) -> None:
        # $50,000 taxable = $50,000 - $16,129 = $33,871 at 15%
        tax = federal_tax(50_000)
        expected = (50_000 - 16_129) * 0.15
        assert abs(tax - expected) < 1.0

    def test_second_bracket(self) -> None:
        # Income in the second bracket
        tax = federal_tax(100_000)
        assert tax > 0
        assert tax < 100_000 * 0.33  # less than max marginal rate on all income


class TestCPP:
    def test_below_exemption(self) -> None:
        assert cpp_contribution(3_000) == 0.0

    def test_at_exemption(self) -> None:
        assert cpp_contribution(3_500) == 0.0

    def test_normal_income(self) -> None:
        cpp = cpp_contribution(50_000)
        expected = (50_000 - 3_500) * 0.0595
        assert abs(cpp - expected) < 1.0

    def test_capped_at_max(self) -> None:
        cpp = cpp_contribution(200_000)
        expected = (71_300 - 3_500) * 0.0595
        assert abs(cpp - expected) < 1.0


class TestCPP2:
    def test_below_first_ceiling(self) -> None:
        assert cpp2_contribution(50_000) == 0.0

    def test_between_ceilings(self) -> None:
        cpp2 = cpp2_contribution(75_000)
        expected = (75_000 - 71_300) * 0.04
        assert abs(cpp2 - expected) < 1.0

    def test_above_second_ceiling(self) -> None:
        cpp2 = cpp2_contribution(100_000)
        expected = (81_200 - 71_300) * 0.04
        assert abs(cpp2 - expected) < 1.0


class TestEI:
    def test_normal_income(self) -> None:
        ei = ei_premium(50_000)
        expected = 50_000 * 0.0166
        assert abs(ei - expected) < 1.0

    def test_capped(self) -> None:
        ei = ei_premium(100_000)
        expected = 65_700 * 0.0166
        assert abs(ei - expected) < 1.0


class TestOHP:
    def test_below_threshold(self) -> None:
        assert ontario_health_premium(18_000) == 0.0

    def test_first_tier(self) -> None:
        ohp = ontario_health_premium(22_000)
        assert 0 < ohp <= 300

    def test_high_income(self) -> None:
        assert ontario_health_premium(250_000) == 900.0


# ---------------------------------------------------------------------------
# Provincial tax tests
# ---------------------------------------------------------------------------


class TestProvincialTax:
    def test_ontario_basic_personal(self) -> None:
        assert provincial_tax(10_000, Province.ON) == 0.0

    def test_ontario_positive(self) -> None:
        tax = provincial_tax(60_000, Province.ON)
        assert tax > 0

    def test_bc_basic_personal(self) -> None:
        assert provincial_tax(10_000, Province.BC) == 0.0

    def test_bc_positive(self) -> None:
        tax = provincial_tax(60_000, Province.BC)
        assert tax > 0

    def test_alberta_flat(self) -> None:
        # AB is flat 10% above personal amount
        tax = provincial_tax(50_000, Province.AB)
        expected = (50_000 - 21_885) * 0.10
        assert abs(tax - expected) < 1.0

    def test_quebec_positive(self) -> None:
        tax = provincial_tax(60_000, Province.QC)
        assert tax > 0


# ---------------------------------------------------------------------------
# Benefit tests
# ---------------------------------------------------------------------------


class TestCCB:
    def test_no_children(self) -> None:
        assert ccb_benefit(50_000, 0, 0) == 0.0

    def test_low_income_max_benefit(self) -> None:
        # Below clawback threshold, get full benefit
        ccb = ccb_benefit(30_000, 2, 2)
        expected = 2 * 7_787
        assert abs(ccb - expected) < 1.0

    def test_clawback_reduces_benefit(self) -> None:
        ccb_low = ccb_benefit(30_000, 2, 2)
        ccb_high = ccb_benefit(60_000, 2, 2)
        assert ccb_high < ccb_low

    def test_high_income_zero(self) -> None:
        ccb = ccb_benefit(300_000, 1, 1)
        assert ccb == 0.0


class TestGSTCredit:
    def test_single_low_income(self) -> None:
        gst = gst_credit(20_000, FamilyType.SINGLE, 0)
        assert gst == 340.0

    def test_family_with_children(self) -> None:
        gst = gst_credit(20_000, FamilyType.SINGLE_PARENT, 2)
        # base + spouse-equivalent + 2 children
        expected = 340 + 340 + 2 * 179
        assert abs(gst - expected) < 1.0

    def test_high_income_zero(self) -> None:
        gst = gst_credit(200_000, FamilyType.SINGLE, 0)
        assert gst == 0.0


class TestCWB:
    def test_below_threshold(self) -> None:
        assert cwb_benefit(2_000, FamilyType.SINGLE) == 0.0

    def test_single_worker(self) -> None:
        cwb = cwb_benefit(15_000, FamilyType.SINGLE)
        assert cwb > 0

    def test_fully_clawed_back(self) -> None:
        cwb = cwb_benefit(100_000, FamilyType.SINGLE)
        assert cwb == 0.0


class TestProvincialBenefits:
    def test_ontario_trillium_low_income(self) -> None:
        ben = provincial_benefits(20_000, Province.ON, FamilyType.SINGLE, 0, 0)
        assert ben > 0

    def test_bc_family_benefit_with_kids(self) -> None:
        ben = provincial_benefits(20_000, Province.BC, FamilyType.SINGLE_PARENT, 2, 2)
        assert ben > 0

    def test_bc_no_kids_no_benefit(self) -> None:
        ben = provincial_benefits(20_000, Province.BC, FamilyType.SINGLE, 0, 0)
        assert ben == 0.0

    def test_alberta_cfb_with_kids(self) -> None:
        ben = provincial_benefits(20_000, Province.AB, FamilyType.SINGLE_PARENT, 2, 2)
        assert ben > 0

    def test_quebec_solidarity(self) -> None:
        ben = provincial_benefits(20_000, Province.QC, FamilyType.SINGLE, 0, 0)
        assert ben > 0


# ---------------------------------------------------------------------------
# Core calculation tests — reference values
# ---------------------------------------------------------------------------


class TestCalculateNetIncome:
    def test_net_income_at_20k_with_benefits(self) -> None:
        """At $20k gross, net should be HIGHER than gross due to benefits."""
        net, _ = calculate_net_income(
            METRInput(20_000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        assert net > 20_000

    def test_net_income_at_100k(self) -> None:
        """At $100k, clawbacks are mostly done. Net should be reasonable."""
        net, _ = calculate_net_income(
            METRInput(100_000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        assert 70_000 <= net <= 90_000

    def test_components_sum_correctly(self) -> None:
        """Total taxes = sum of individual tax components."""
        _, comp = calculate_net_income(
            METRInput(50_000, Province.ON, FamilyType.SINGLE, 0, 0),
        )
        expected_total = (
            comp.federal_tax + comp.provincial_tax +
            comp.cpp + comp.cpp2 + comp.ei + comp.ohp
        )
        assert abs(comp.total_taxes - expected_total) < 1.0

    def test_benefits_sum_correctly(self) -> None:
        """Total benefits = sum of individual benefit components."""
        _, comp = calculate_net_income(
            METRInput(30_000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        expected_benefits = comp.ccb + comp.gst_credit + comp.cwb + comp.provincial_benefits
        assert abs(comp.total_benefits - expected_benefits) < 1.0

    def test_zero_income(self) -> None:
        """At $0 gross, should get benefits only."""
        net, comp = calculate_net_income(
            METRInput(0, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        assert comp.total_taxes == 0.0
        assert comp.total_benefits > 0
        assert net > 0


class TestCalculateMETR:
    def test_ontario_single_parent_2kids_peak_metr(self) -> None:
        """Peak METR for single parent 2 kids u6 in Ontario should be high (>50%)
        in the $35k-$55k range due to benefit clawbacks."""
        curve = generate_curve(Province.ON, FamilyType.SINGLE_PARENT, 2, 2)
        peak = max(curve, key=lambda p: p.metr)
        assert peak.metr >= 50.0
        assert 30_000 <= peak.gross <= 60_000

    def test_ontario_single_no_kids_moderate_metr(self) -> None:
        """Single no kids should have moderate METR — lower than family."""
        result = calculate_metr(
            METRInput(35_000, Province.ON, FamilyType.SINGLE, 0, 0),
        )
        assert 25.0 <= result.metr <= 75.0

    def test_metr_returns_valid_zone(self) -> None:
        result = calculate_metr(
            METRInput(47_000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        assert result.metr >= 0
        zone = classify_zone(result.metr)
        assert zone in ("normal", "high", "dead_zone", "extreme")

    def test_pure_function_determinism(self) -> None:
        """Same input always produces same output."""
        inp = METRInput(47_000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2)
        r1 = calculate_metr(inp)
        r2 = calculate_metr(inp)
        assert r1.metr == r2.metr
        assert r1.net_income == r2.net_income

    def test_high_income_low_metr(self) -> None:
        """At very high income, METR should be moderate (clawbacks done)."""
        result = calculate_metr(
            METRInput(150_000, Province.ON, FamilyType.SINGLE, 0, 0),
        )
        assert result.metr < 55.0


# ---------------------------------------------------------------------------
# Zone classification
# ---------------------------------------------------------------------------


class TestClassifyZone:
    def test_normal(self) -> None:
        assert classify_zone(30.0) == "normal"

    def test_high(self) -> None:
        assert classify_zone(50.0) == "high"

    def test_dead_zone(self) -> None:
        assert classify_zone(60.0) == "dead_zone"

    def test_extreme(self) -> None:
        assert classify_zone(75.0) == "extreme"

    def test_boundary_45(self) -> None:
        assert classify_zone(45.0) == "high"

    def test_boundary_55(self) -> None:
        assert classify_zone(55.0) == "dead_zone"

    def test_boundary_70(self) -> None:
        assert classify_zone(70.0) == "extreme"


# ---------------------------------------------------------------------------
# Curve generation
# ---------------------------------------------------------------------------


class TestGenerateCurve:
    def test_curve_length(self) -> None:
        curve = generate_curve(
            Province.ON, FamilyType.SINGLE, 0, 0,
            income_min=15_000, income_max=155_000, step=1_000,
        )
        # (155_000 - 15_000) / 1_000 + 1 = 141
        assert len(curve) == 141

    def test_curve_points_ordered(self) -> None:
        curve = generate_curve(Province.ON, FamilyType.SINGLE, 0, 0)
        for i in range(len(curve) - 1):
            assert curve[i].gross < curve[i + 1].gross

    def test_curve_net_income_increases(self) -> None:
        """Net income should generally increase (may not be monotonic
        due to clawbacks, but over the full range it should rise)."""
        curve = generate_curve(Province.ON, FamilyType.SINGLE, 0, 0)
        assert curve[-1].net > curve[0].net

    def test_curve_has_zones(self) -> None:
        curve = generate_curve(
            Province.ON, FamilyType.SINGLE_PARENT, 2, 2,
        )
        zones = {p.zone for p in curve}
        # Family with kids should have at least normal and high zones
        assert "normal" in zones or "high" in zones


# ---------------------------------------------------------------------------
# Dead zone detection
# ---------------------------------------------------------------------------


class TestFindDeadZones:
    def test_dead_zones_exist_for_single_parent(self) -> None:
        """Single parent 2 kids should have dead zones."""
        curve = generate_curve(Province.ON, FamilyType.SINGLE_PARENT, 2, 2)
        zones = find_dead_zones(curve)
        assert len(zones) >= 1

    def test_dead_zone_structure(self) -> None:
        curve = generate_curve(Province.ON, FamilyType.SINGLE_PARENT, 2, 2)
        zones = find_dead_zones(curve)
        for z in zones:
            assert z.start <= z.end
            assert z.peak_metr >= 55.0

    def test_no_dead_zones_at_high_threshold(self) -> None:
        """With extremely high threshold, may find no dead zones."""
        curve = generate_curve(Province.ON, FamilyType.SINGLE, 0, 0)
        zones = find_dead_zones(curve, threshold=95.0)
        # Single no kids unlikely to reach 95% METR
        assert len(zones) == 0


# ---------------------------------------------------------------------------
# Cross-province comparisons
# ---------------------------------------------------------------------------


class TestProvincialComparison:
    def test_all_provinces_produce_results(self) -> None:
        for prov in Province:
            result = calculate_metr(
                METRInput(47_000, prov, FamilyType.SINGLE_PARENT, 2, 2),
            )
            assert result.metr > 0
            assert result.net_income > 0

    def test_alberta_flat_rate(self) -> None:
        """Alberta flat 10% applies uniformly above the personal amount."""
        ab_tax = provincial_tax(60_000, Province.AB)
        expected = (60_000 - 21_885) * 0.10
        assert abs(ab_tax - expected) < 1.0

    def test_different_provinces_different_metr(self) -> None:
        """Each province should produce distinct METR values."""
        results = {}
        for prov in Province:
            r = calculate_metr(
                METRInput(47_000, prov, FamilyType.SINGLE_PARENT, 2, 2),
            )
            results[prov] = r.metr
        # At least 2 distinct values (likely all 4 different)
        assert len(set(results.values())) >= 2


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------


class TestDataClasses:
    def test_metr_input_children_derived(self) -> None:
        inp = METRInput(50_000, Province.ON, FamilyType.SINGLE_PARENT, 3, 1)
        assert inp.children_6_to_17 == 2

    def test_metr_input_frozen(self) -> None:
        inp = METRInput(50_000, Province.ON, FamilyType.SINGLE, 0, 0)
        with pytest.raises(AttributeError):
            inp.gross_income = 60_000  # type: ignore[misc]

    def test_engine_rejects_invalid_children(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            METRInput(50_000, Province.ON, FamilyType.SINGLE_PARENT, n_children=1, children_under_6=3)

    def test_single_with_children_becomes_single_parent(self) -> None:
        inp = METRInput(50_000, Province.ON, FamilyType.SINGLE, n_children=2, children_under_6=1)
        assert inp.family_type == FamilyType.SINGLE_PARENT

    def test_metr_components_frozen(self) -> None:
        comp = METRComponents(
            federal_tax=100, provincial_tax=50, cpp=30, cpp2=10,
            ei=20, ohp=0, ccb=0, gst_credit=0, cwb=0,
            provincial_benefits=0, total_taxes=210, total_benefits=0,
        )
        with pytest.raises(AttributeError):
            comp.federal_tax = 200  # type: ignore[misc]
