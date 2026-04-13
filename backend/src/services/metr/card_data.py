"""Signal card data generator for Theme #2 METR.

Generates the 4 signal card datasets as Python dicts. These are
serialized to JSON by the CLI script and consumed by the SVG chart
generator to produce social-media-ready card images.

All functions are pure (ARCH-PURA-001) — they call only the engine's
pure calculation functions.
"""

from __future__ import annotations

from src.services.metr.engine import (
    FamilyType,
    METRInput,
    Province,
    calculate_metr,
    calculate_net_income,
    classify_zone,
    generate_curve,
)


def generate_card_1_hero_kpi() -> dict:
    """Card 1: Hero KPI + mini METR curve.

    Headline: 'Earn $1 More. Keep 22c.'
    Hero KPI: peak METR for single parent 2 kids (ON).
    Mini chart: METR curve simplified to ~30 points.
    """
    curve = generate_curve(Province.ON, FamilyType.SINGLE_PARENT, 2, 2, step=5000)
    peak = max(curve, key=lambda p: p.metr)
    keep_cents = round((1 - peak.metr / 100) * 100)

    return {
        "card_type": "hero_kpi",
        "eyebrow": "TAXATION",
        "headline": f"Earn $1 More. Keep {keep_cents}\u00a2.",
        "subheadline": "Ontario single parent, 2 children under 6",
        "hero_kpi": {"value": f"{peak.metr}%", "label": "Peak Marginal Tax Rate"},
        "peak_income": peak.gross,
        "mini_chart": [{"gross": p.gross, "metr": p.metr} for p in curve],
        "source": "Summa Vision calculation from CRA formulas, 2025 tax year",
        "size": [1200, 900],
    }


def generate_card_2_waterfall() -> dict:
    """Card 2: Waterfall — Where does your $10k raise go?

    Shows decomposition of a $45k -> $55k raise for single parent 2 kids.
    """
    net_45, comp_45 = calculate_net_income(
        METRInput(45000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
    )
    net_55, comp_55 = calculate_net_income(
        METRInput(55000, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
    )

    delta_fed = comp_55.federal_tax - comp_45.federal_tax
    delta_prov = comp_55.provincial_tax - comp_45.provincial_tax
    delta_cpp = (comp_55.cpp + comp_55.cpp2) - (comp_45.cpp + comp_45.cpp2)
    delta_ei = comp_55.ei - comp_45.ei
    delta_ccb = comp_55.ccb - comp_45.ccb
    delta_cwb = comp_55.cwb - comp_45.cwb
    delta_prov_ben = comp_55.provincial_benefits - comp_45.provincial_benefits
    real_gain = net_55 - net_45

    return {
        "card_type": "waterfall",
        "eyebrow": "THE RAISE TRAP",
        "headline": "Where Does Your $10,000 Raise Go?",
        "subheadline": "Ontario, single parent, 2 kids \u2014 earning $45k \u2192 $55k",
        "steps": [
            {"label": "Gross Raise", "value": 10000, "type": "start"},
            {"label": "Federal Tax", "value": -abs(round(delta_fed)), "type": "loss"},
            {"label": "Provincial Tax", "value": -abs(round(delta_prov)), "type": "loss"},
            {"label": "CPP/EI", "value": -abs(round(delta_cpp + delta_ei)), "type": "loss"},
            {"label": "CCB Lost", "value": round(delta_ccb), "type": "loss"},
            {"label": "CWB Lost", "value": round(delta_cwb), "type": "loss"},
            {"label": "Prov Benefits Lost", "value": round(delta_prov_ben), "type": "loss"},
            {"label": "Real Gain", "value": round(real_gain), "type": "end"},
        ],
        "source": "Summa Vision calculation from CRA formulas, 2025 tax year",
        "size": [1200, 900],
    }


def generate_card_3_provincial_bars() -> dict:
    """Card 3: Horizontal ranked bars — Provincial METR comparison.

    At $47k income, single parent 2 kids.
    """
    income = 47000
    province_names = {
        "ON": "Ontario",
        "BC": "British Columbia",
        "AB": "Alberta",
        "QC": "Quebec",
    }
    provinces_data = []
    for prov in Province:
        result = calculate_metr(
            METRInput(income, prov, FamilyType.SINGLE_PARENT, 2, 2),
        )
        provinces_data.append({
            "province": prov.value,
            "province_name": province_names[prov.value],
            "metr": result.metr,
            "zone": classify_zone(result.metr),
        })

    provinces_data.sort(key=lambda x: x["metr"], reverse=True)

    return {
        "card_type": "ranked_bars",
        "eyebrow": "PROVINCIAL COMPARISON",
        "headline": "Which Province Punishes Your Raise Most?",
        "subheadline": f"METR at ${income:,} \u2014 single parent, 2 children",
        "bars": provinces_data,
        "source": "Summa Vision calculation from CRA + provincial formulas, 2025",
        "size": [1200, 900],
    }


def generate_card_4_slope() -> dict:
    """Card 4: Slope chart — Gross vs Net, $45k -> $55k.

    Shows the disparity between gross income increase and net income increase
    across three $10k raise scenarios.
    """
    scenarios = [
        ("$45k \u2192 $55k", 45000, 55000),
        ("$55k \u2192 $65k", 55000, 65000),
        ("$85k \u2192 $95k", 85000, 95000),
    ]
    slopes = []
    for label, start, end in scenarios:
        net_start, _ = calculate_net_income(
            METRInput(start, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        net_end, _ = calculate_net_income(
            METRInput(end, Province.ON, FamilyType.SINGLE_PARENT, 2, 2),
        )
        slopes.append({
            "label": label,
            "gross_start": start,
            "gross_end": end,
            "net_start": round(net_start),
            "net_end": round(net_end),
            "gross_delta": end - start,
            "net_delta": round(net_end - net_start),
            "effective_rate": round(
                (1 - (net_end - net_start) / (end - start)) * 100, 1,
            ),
        })

    return {
        "card_type": "slope",
        "eyebrow": "THE DEAD ZONE",
        "headline": "A $10k Raise \u2014 What You Actually Keep",
        "subheadline": "Ontario, single parent, 2 children under 6",
        "slopes": slopes,
        "source": "Summa Vision calculation from CRA formulas, 2025 tax year",
        "size": [1200, 900],
    }


def generate_all_cards() -> list[dict]:
    """Generate all 4 signal card datasets."""
    return [
        generate_card_1_hero_kpi(),
        generate_card_2_waterfall(),
        generate_card_3_provincial_bars(),
        generate_card_4_slope(),
    ]
