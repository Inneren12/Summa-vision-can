"""METR Calculation Engine — Summa Vision Theme #2.

Computes Marginal Effective Tax Rates across the income spectrum for
Canadian workers. Components: Federal income tax, CPP/CPP2, EI,
provincial income tax, CCB, GST/HST Credit, CWB, provincial benefits
(OTB, BCF, ACFB, QC solidarity credit).

All functions are **pure** (ARCH-PURA-001) — no I/O, no DB, no network.
Tax parameters are 2025 values. Sources: CRA, C.D. Howe Institute, PBO.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class Province(str, Enum):
    ON = "ON"
    BC = "BC"
    AB = "AB"
    QC = "QC"


class FamilyType(str, Enum):
    SINGLE = "single"
    SINGLE_PARENT = "single_parent"
    COUPLE = "couple"


@dataclass(frozen=True)
class METRInput:
    gross_income: int
    province: Province
    family_type: FamilyType
    n_children: int = 0
    children_under_6: int = 0

    @property
    def children_6_to_17(self) -> int:
        return self.n_children - self.children_under_6


@dataclass(frozen=True)
class METRComponents:
    federal_tax: float
    provincial_tax: float
    cpp: float
    cpp2: float
    ei: float
    ohp: float  # Ontario Health Premium (ON only, 0 elsewhere)
    ccb: float  # Canada Child Benefit received
    gst_credit: float  # GST/HST Credit received
    cwb: float  # Canada Workers Benefit received
    provincial_benefits: float  # OTB (ON) / BCF (BC) / ACFB (AB) / QC
    total_taxes: float
    total_benefits: float


@dataclass(frozen=True)
class METRResult:
    gross_income: int
    net_income: int
    metr: float  # percentage 0–100+
    components: METRComponents


@dataclass(frozen=True)
class METRCurvePoint:
    gross: int
    net: int
    metr: float
    zone: str  # "normal" | "high" | "dead_zone" | "extreme"


@dataclass(frozen=True)
class DeadZone:
    start: int
    end: int
    peak_metr: float


# ---------------------------------------------------------------------------
# 2025 Federal Tax Parameters
# ---------------------------------------------------------------------------

# Federal tax brackets (2025)
_FED_BRACKETS: list[tuple[float, float]] = [
    (57_375, 0.15),
    (57_375, 0.205),   # 57,375 to 114,750
    (63_025, 0.26),    # 114,750 to 177,775
    (75_414, 0.29),    # 177,775 to 253,189
    (float("inf"), 0.33),  # above 253,189
]

_FED_BASIC_PERSONAL = 16_129

# CPP 2025
_CPP_RATE = 0.0595
_CPP_EXEMPTION = 3_500
_CPP_MAX_PENSIONABLE = 71_300
_CPP_MAX_CONTRIBUTION = (_CPP_MAX_PENSIONABLE - _CPP_EXEMPTION) * _CPP_RATE  # ~4,034.10

# CPP2 2025 (second ceiling)
_CPP2_RATE = 0.04
_CPP2_CEILING = 81_200
_CPP2_MAX_CONTRIBUTION = (_CPP2_CEILING - _CPP_MAX_PENSIONABLE) * _CPP2_RATE  # ~396.00

# EI 2025
_EI_RATE = 0.0166
_EI_MAX_INSURABLE = 65_700
_EI_MAX_CONTRIBUTION = _EI_MAX_INSURABLE * _EI_RATE  # ~1,090.62

# CCB 2025 (Canada Child Benefit)
_CCB_MAX_UNDER_6 = 7_787
_CCB_MAX_6_TO_17 = 6_570
_CCB_CLAWBACK_THRESHOLD = 36_502
_CCB_CLAWBACK_RATE_1_CHILD = 0.07
_CCB_CLAWBACK_RATE_2_PLUS = 0.135  # for the under-6 portion
_CCB_CLAWBACK_RATE_2_PLUS_6_17 = 0.057  # additional rate for 6-17 portion

# GST/HST Credit 2025
_GST_CREDIT_BASE = 340  # per adult
_GST_CREDIT_SPOUSE = 340
_GST_CREDIT_CHILD = 179
_GST_THRESHOLD = 44_530
_GST_CLAWBACK_RATE = 0.05

# Canada Workers Benefit (CWB) 2025 — single
_CWB_SINGLE_RATE = 0.27
_CWB_SINGLE_THRESHOLD = 3_000
_CWB_SINGLE_MAX = 1_590
_CWB_SINGLE_CLAWBACK_START = 24_975
_CWB_SINGLE_CLAWBACK_RATE = 0.15

# CWB — family
_CWB_FAMILY_RATE = 0.27
_CWB_FAMILY_THRESHOLD = 3_000
_CWB_FAMILY_MAX = 2_730
_CWB_FAMILY_CLAWBACK_START = 28_494
_CWB_FAMILY_CLAWBACK_RATE = 0.15


# ---------------------------------------------------------------------------
# Provincial Tax Parameters (2025)
# ---------------------------------------------------------------------------

# Ontario brackets
_ON_BRACKETS: list[tuple[float, float]] = [
    (52_886, 0.0505),
    (52_878, 0.0915),   # 52,886 to 105,764
    (44_236, 0.1116),   # 105,764 to 150,000
    (70_000, 0.1216),   # 150,000 to 220,000
    (float("inf"), 0.1316),  # above 220,000
]
_ON_BASIC_PERSONAL = 11_865
# Ontario surtax
_ON_SURTAX_THRESHOLD_1 = 5_315
_ON_SURTAX_RATE_1 = 0.20
_ON_SURTAX_THRESHOLD_2 = 6_802
_ON_SURTAX_RATE_2 = 0.36

# Ontario Health Premium (OHP) — progressive, not a surtax
_OHP_BRACKETS: list[tuple[float, float, float, float]] = [
    # (threshold, rate, base_premium, rate_on_excess)
    (20_000, 0, 0, 0),
    (25_000, 0, 0, 0.06),       # $0 + 6% of amount over $20,000 (max $300)
    (36_000, 300, 300, 0.06),    # $300 + 6% of amount over $25,000 (max $450)
    (38_500, 450, 450, 0.25),    # $450 + 25% of amount over $36,000 (max $600)
    (48_000, 600, 600, 0.25),    # $600 + 25% of amount over $38,500 (max $750)
    (72_000, 750, 750, 0.25),    # $750 + 25% of amount over $48,000 (max $900)
    (200_000, 900, 900, 0),      # $900 flat
    (float("inf"), 900, 900, 0),
]

# BC brackets
_BC_BRACKETS: list[tuple[float, float]] = [
    (47_937, 0.0506),
    (47_938, 0.0770),   # 47,937 to 95,875
    (13_825, 0.1050),   # 95,875 to 109,700
    (24_930, 0.1229),   # 109,700 to 134,630
    (46_592, 0.1470),   # 134,630 to 181,222
    (66_218, 0.1680),   # 181,222 to 247,440
    (float("inf"), 0.2050),  # above 247,440
]
_BC_BASIC_PERSONAL = 12_580

# Alberta — flat 10%
_AB_RATE = 0.10
_AB_BASIC_PERSONAL = 21_885

# Quebec brackets (simplified — separate filing not modelled)
_QC_BRACKETS: list[tuple[float, float]] = [
    (51_780, 0.14),
    (51_780, 0.19),    # 51,780 to 103,560
    (18_940, 0.24),    # 103,560 to 122,500
    (float("inf"), 0.2575),  # above 122,500
]
_QC_BASIC_PERSONAL = 18_056

# Ontario Trillium Benefit (OTB) — simplified as sales tax + energy + property
_OTB_MAX_SINGLE = 1_013  # combined max for low-income single
_OTB_MAX_FAMILY = 1_213  # combined max for family
_OTB_CLAWBACK_THRESHOLD = 32_864
_OTB_CLAWBACK_RATE = 0.04

# BC Family Benefit (BCF) — per child
_BCF_PER_CHILD = 2_188
_BCF_CLAWBACK_THRESHOLD = 25_506
_BCF_CLAWBACK_RATE_1 = 0.0132  # 1 child
_BCF_CLAWBACK_RATE_2 = 0.0264  # 2+ children

# Alberta Child and Family Benefit (ACFB) — per child
_ACFB_PER_CHILD = 1_330  # base amount per child (up to 4)
_ACFB_WORKING_SUPPLEMENT = 764  # per family
_ACFB_CLAWBACK_THRESHOLD = 27_024
_ACFB_CLAWBACK_RATE = 0.04

# Quebec — Solidarity Tax Credit (simplified)
_QC_SOLIDARITY_BASE = 1_032  # housing + sales tax components
_QC_SOLIDARITY_CLAWBACK_THRESHOLD = 39_710
_QC_SOLIDARITY_CLAWBACK_RATE = 0.06


# ---------------------------------------------------------------------------
# Tax Calculation — Pure Functions
# ---------------------------------------------------------------------------


def _apply_brackets(taxable_income: float, brackets: list[tuple[float, float]]) -> float:
    """Apply progressive tax brackets to taxable income."""
    tax = 0.0
    remaining = taxable_income
    for width, rate in brackets:
        if remaining <= 0:
            break
        taxed = min(remaining, width)
        tax += taxed * rate
        remaining -= taxed
    return tax


def federal_tax(gross_income: int) -> float:
    """Calculate federal income tax for 2025."""
    taxable = max(0, gross_income - _FED_BASIC_PERSONAL)
    return _apply_brackets(taxable, _FED_BRACKETS)


def cpp_contribution(gross_income: int) -> float:
    """Calculate CPP employee contribution for 2025."""
    pensionable = max(0, min(gross_income, _CPP_MAX_PENSIONABLE) - _CPP_EXEMPTION)
    return pensionable * _CPP_RATE


def cpp2_contribution(gross_income: int) -> float:
    """Calculate CPP2 (second ceiling) employee contribution for 2025."""
    if gross_income <= _CPP_MAX_PENSIONABLE:
        return 0.0
    earnings = min(gross_income, _CPP2_CEILING) - _CPP_MAX_PENSIONABLE
    return earnings * _CPP2_RATE


def ei_premium(gross_income: int) -> float:
    """Calculate EI employee premium for 2025."""
    insurable = min(gross_income, _EI_MAX_INSURABLE)
    return insurable * _EI_RATE


def ontario_health_premium(gross_income: int) -> float:
    """Calculate Ontario Health Premium for 2025."""
    if gross_income <= 20_000:
        return 0.0
    if gross_income <= 25_000:
        return min(300, (gross_income - 20_000) * 0.06)
    if gross_income <= 36_000:
        return min(450, 300 + (gross_income - 25_000) * 0.06)
    if gross_income <= 38_500:
        return min(600, 450 + (gross_income - 36_000) * 0.25)
    if gross_income <= 48_000:
        return min(750, 600 + (gross_income - 38_500) * 0.25)
    if gross_income <= 72_000:
        return min(900, 750 + (gross_income - 48_000) * 0.25)
    if gross_income <= 200_000:
        return 900.0
    return 900.0


def provincial_tax(gross_income: int, province: Province) -> float:
    """Calculate provincial income tax for 2025."""
    if province == Province.ON:
        taxable = max(0, gross_income - _ON_BASIC_PERSONAL)
        base_tax = _apply_brackets(taxable, _ON_BRACKETS)
        # Ontario surtax
        surtax = 0.0
        if base_tax > _ON_SURTAX_THRESHOLD_1:
            surtax += (base_tax - _ON_SURTAX_THRESHOLD_1) * _ON_SURTAX_RATE_1
        if base_tax > _ON_SURTAX_THRESHOLD_2:
            surtax += (base_tax - _ON_SURTAX_THRESHOLD_2) * _ON_SURTAX_RATE_2
        return base_tax + surtax

    if province == Province.BC:
        taxable = max(0, gross_income - _BC_BASIC_PERSONAL)
        return _apply_brackets(taxable, _BC_BRACKETS)

    if province == Province.AB:
        taxable = max(0, gross_income - _AB_BASIC_PERSONAL)
        return taxable * _AB_RATE

    if province == Province.QC:
        taxable = max(0, gross_income - _QC_BASIC_PERSONAL)
        return _apply_brackets(taxable, _QC_BRACKETS)

    return 0.0


def ccb_benefit(
    adjusted_family_income: int,
    n_children: int,
    children_under_6: int,
) -> float:
    """Calculate Canada Child Benefit for 2025.

    CCB is based on adjusted family net income (AFNI). For simplicity,
    we use gross employment income as a proxy for AFNI.
    """
    if n_children == 0:
        return 0.0

    children_6_to_17 = n_children - children_under_6

    max_benefit = (children_under_6 * _CCB_MAX_UNDER_6) + (children_6_to_17 * _CCB_MAX_6_TO_17)

    if adjusted_family_income <= _CCB_CLAWBACK_THRESHOLD:
        return max_benefit

    excess = adjusted_family_income - _CCB_CLAWBACK_THRESHOLD

    if n_children == 1:
        clawback = excess * _CCB_CLAWBACK_RATE_1_CHILD
    else:
        # Two-tier clawback for 2+ children
        clawback = excess * _CCB_CLAWBACK_RATE_2_PLUS

    return max(0.0, max_benefit - clawback)


def gst_credit(
    adjusted_income: int,
    family_type: FamilyType,
    n_children: int,
) -> float:
    """Calculate GST/HST Credit for 2025 (annual amount)."""
    amount = _GST_CREDIT_BASE  # for the individual

    if family_type in (FamilyType.COUPLE, FamilyType.SINGLE_PARENT):
        amount += _GST_CREDIT_SPOUSE

    amount += n_children * _GST_CREDIT_CHILD

    if adjusted_income <= _GST_THRESHOLD:
        return amount

    clawback = (adjusted_income - _GST_THRESHOLD) * _GST_CLAWBACK_RATE
    return max(0.0, amount - clawback)


def cwb_benefit(
    gross_income: int,
    family_type: FamilyType,
) -> float:
    """Calculate Canada Workers Benefit for 2025."""
    if gross_income < 3_000:
        return 0.0

    is_family = family_type in (FamilyType.COUPLE, FamilyType.SINGLE_PARENT)

    if is_family:
        benefit = min(
            _CWB_FAMILY_MAX,
            (gross_income - _CWB_FAMILY_THRESHOLD) * _CWB_FAMILY_RATE,
        )
        if gross_income > _CWB_FAMILY_CLAWBACK_START:
            benefit -= (gross_income - _CWB_FAMILY_CLAWBACK_START) * _CWB_FAMILY_CLAWBACK_RATE
    else:
        benefit = min(
            _CWB_SINGLE_MAX,
            (gross_income - _CWB_SINGLE_THRESHOLD) * _CWB_SINGLE_RATE,
        )
        if gross_income > _CWB_SINGLE_CLAWBACK_START:
            benefit -= (gross_income - _CWB_SINGLE_CLAWBACK_START) * _CWB_SINGLE_CLAWBACK_RATE

    return max(0.0, benefit)


def provincial_benefits(
    gross_income: int,
    province: Province,
    family_type: FamilyType,
    n_children: int,
    children_under_6: int,
) -> float:
    """Calculate province-specific benefits for 2025."""
    if province == Province.ON:
        return _ontario_trillium(gross_income, family_type)
    if province == Province.BC:
        return _bc_family_benefit(gross_income, n_children)
    if province == Province.AB:
        return _alberta_cfb(gross_income, n_children)
    if province == Province.QC:
        return _qc_solidarity(gross_income, family_type)
    return 0.0


def _ontario_trillium(gross_income: int, family_type: FamilyType) -> float:
    """Ontario Trillium Benefit (OTB) — sales tax + energy + property components."""
    is_family = family_type in (FamilyType.COUPLE, FamilyType.SINGLE_PARENT)
    max_benefit = _OTB_MAX_FAMILY if is_family else _OTB_MAX_SINGLE

    if gross_income <= _OTB_CLAWBACK_THRESHOLD:
        return max_benefit

    clawback = (gross_income - _OTB_CLAWBACK_THRESHOLD) * _OTB_CLAWBACK_RATE
    return max(0.0, max_benefit - clawback)


def _bc_family_benefit(gross_income: int, n_children: int) -> float:
    """BC Family Benefit — per-child amount with income clawback."""
    if n_children == 0:
        return 0.0

    max_benefit = n_children * _BCF_PER_CHILD

    if gross_income <= _BCF_CLAWBACK_THRESHOLD:
        return max_benefit

    excess = gross_income - _BCF_CLAWBACK_THRESHOLD
    rate = _BCF_CLAWBACK_RATE_1 if n_children == 1 else _BCF_CLAWBACK_RATE_2
    clawback = excess * rate
    return max(0.0, max_benefit - clawback)


def _alberta_cfb(gross_income: int, n_children: int) -> float:
    """Alberta Child and Family Benefit (ACFB) — per-child + working supplement."""
    if n_children == 0:
        return 0.0

    max_benefit = min(n_children, 4) * _ACFB_PER_CHILD + _ACFB_WORKING_SUPPLEMENT

    if gross_income <= _ACFB_CLAWBACK_THRESHOLD:
        return max_benefit

    clawback = (gross_income - _ACFB_CLAWBACK_THRESHOLD) * _ACFB_CLAWBACK_RATE
    return max(0.0, max_benefit - clawback)


def _qc_solidarity(gross_income: int, family_type: FamilyType) -> float:
    """Quebec Solidarity Tax Credit (simplified)."""
    is_family = family_type in (FamilyType.COUPLE, FamilyType.SINGLE_PARENT)
    max_benefit = _QC_SOLIDARITY_BASE * (1.5 if is_family else 1.0)

    if gross_income <= _QC_SOLIDARITY_CLAWBACK_THRESHOLD:
        return max_benefit

    clawback = (gross_income - _QC_SOLIDARITY_CLAWBACK_THRESHOLD) * _QC_SOLIDARITY_CLAWBACK_RATE
    return max(0.0, max_benefit - clawback)


# ---------------------------------------------------------------------------
# Core Calculation Functions
# ---------------------------------------------------------------------------


def calculate_net_income(inp: METRInput) -> tuple[int, METRComponents]:
    """Calculate net income and component breakdown for given input.

    Pure function (ARCH-PURA-001). Returns (net_income, components).
    """
    # Taxes & contributions
    fed = federal_tax(inp.gross_income)
    prov = provincial_tax(inp.gross_income, inp.province)
    cpp = cpp_contribution(inp.gross_income)
    cpp2 = cpp2_contribution(inp.gross_income)
    ei = ei_premium(inp.gross_income)
    ohp = ontario_health_premium(inp.gross_income) if inp.province == Province.ON else 0.0

    total_taxes = fed + prov + cpp + cpp2 + ei + ohp

    # Benefits
    ccb = ccb_benefit(inp.gross_income, inp.n_children, inp.children_under_6)
    gst = gst_credit(inp.gross_income, inp.family_type, inp.n_children)
    cwb = cwb_benefit(inp.gross_income, inp.family_type)
    prov_ben = provincial_benefits(
        inp.gross_income, inp.province, inp.family_type,
        inp.n_children, inp.children_under_6,
    )

    total_benefits = ccb + gst + cwb + prov_ben

    net = round(inp.gross_income - total_taxes + total_benefits)

    components = METRComponents(
        federal_tax=round(fed, 2),
        provincial_tax=round(prov, 2),
        cpp=round(cpp, 2),
        cpp2=round(cpp2, 2),
        ei=round(ei, 2),
        ohp=round(ohp, 2),
        ccb=round(ccb, 2),
        gst_credit=round(gst, 2),
        cwb=round(cwb, 2),
        provincial_benefits=round(prov_ben, 2),
        total_taxes=round(total_taxes, 2),
        total_benefits=round(total_benefits, 2),
    )

    return net, components


def calculate_metr(inp: METRInput, delta: int = 1000) -> METRResult:
    """Calculate METR at a given income point.

    METR = 1 - (change in net income / change in gross income)
    Uses a forward-difference of ``delta`` dollars.

    Pure function (ARCH-PURA-001).
    """
    net_base, components = calculate_net_income(inp)

    inp_plus = METRInput(
        gross_income=inp.gross_income + delta,
        province=inp.province,
        family_type=inp.family_type,
        n_children=inp.n_children,
        children_under_6=inp.children_under_6,
    )
    net_plus, _ = calculate_net_income(inp_plus)

    net_change = net_plus - net_base
    metr = round((1 - net_change / delta) * 100, 1)

    return METRResult(
        gross_income=inp.gross_income,
        net_income=net_base,
        metr=metr,
        components=components,
    )


def classify_zone(metr: float) -> str:
    """Classify METR value into zone for visualization."""
    if metr >= 70:
        return "extreme"
    if metr >= 55:
        return "dead_zone"
    if metr >= 45:
        return "high"
    return "normal"


def generate_curve(
    province: Province,
    family_type: FamilyType,
    n_children: int,
    children_under_6: int,
    income_min: int = 15_000,
    income_max: int = 155_000,
    step: int = 1_000,
) -> list[METRCurvePoint]:
    """Generate full METR curve across income range.

    Pure function (ARCH-PURA-001).
    """
    points: list[METRCurvePoint] = []
    for income in range(income_min, income_max + 1, step):
        result = calculate_metr(
            METRInput(income, province, family_type, n_children, children_under_6),
        )
        points.append(
            METRCurvePoint(
                gross=income,
                net=result.net_income,
                metr=result.metr,
                zone=classify_zone(result.metr),
            )
        )
    return points


def find_dead_zones(
    curve: list[METRCurvePoint],
    threshold: float = 55.0,
) -> list[DeadZone]:
    """Find contiguous income ranges where METR exceeds threshold.

    Pure function (ARCH-PURA-001).
    """
    zones: list[DeadZone] = []
    in_zone = False
    start = 0
    peak = 0.0

    for point in curve:
        if point.metr >= threshold:
            if not in_zone:
                in_zone = True
                start = point.gross
                peak = point.metr
            else:
                peak = max(peak, point.metr)
        else:
            if in_zone:
                zones.append(DeadZone(start=start, end=prev_gross, peak_metr=peak))
                in_zone = False
        prev_gross = point.gross

    # Close final zone if curve ends inside one
    if in_zone:
        zones.append(DeadZone(start=start, end=curve[-1].gross, peak_metr=peak))

    return zones
