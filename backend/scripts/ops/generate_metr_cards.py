"""Generate signal card data JSON files for Theme #2 METR.

Usage:
    cd backend && python -m scripts.ops.generate_metr_cards

Outputs:
    backend/data/theme2_cards/hero_kpi.json
    backend/data/theme2_cards/waterfall.json
    backend/data/theme2_cards/ranked_bars.json
    backend/data/theme2_cards/slope.json
    backend/data/theme2_cards/metr_curves_full.json
"""

from __future__ import annotations

import json
from pathlib import Path

from src.services.metr.card_data import generate_all_cards
from src.services.metr.engine import (
    FamilyType,
    Province,
    generate_curve,
)

# Pre-defined scenarios for the full interactive calculator
SCENARIOS = [
    {
        "label": "Single parent, 2 kids u6",
        "province": Province.ON,
        "family_type": FamilyType.SINGLE_PARENT,
        "n_children": 2,
        "children_under_6": 2,
    },
    {
        "label": "Single, no kids",
        "province": Province.ON,
        "family_type": FamilyType.SINGLE,
        "n_children": 0,
        "children_under_6": 0,
    },
    {
        "label": "Couple, 2 kids u6",
        "province": Province.ON,
        "family_type": FamilyType.COUPLE,
        "n_children": 2,
        "children_under_6": 2,
    },
    {
        "label": "Single parent, 1 kid u6",
        "province": Province.ON,
        "family_type": FamilyType.SINGLE_PARENT,
        "n_children": 1,
        "children_under_6": 1,
    },
]


def main() -> None:
    output_dir = Path(__file__).resolve().parent.parent.parent / "data" / "theme2_cards"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate signal card data
    cards = generate_all_cards()
    for card in cards:
        filename = f"{card['card_type']}.json"
        (output_dir / filename).write_text(json.dumps(card, indent=2))
        print(f"  {filename}")

    # Generate full curve data for the interactive calculator
    full_curves: dict[str, list[dict]] = {}
    for scenario in SCENARIOS:
        label = scenario["label"]
        curve = generate_curve(
            province=scenario["province"],
            family_type=scenario["family_type"],
            n_children=scenario["n_children"],
            children_under_6=scenario["children_under_6"],
        )
        full_curves[label] = [
            {"gross": p.gross, "net": p.net, "metr": p.metr, "zone": p.zone}
            for p in curve
        ]
    (output_dir / "metr_curves_full.json").write_text(json.dumps(full_curves, indent=2))
    print("  metr_curves_full.json")

    print(f"\nAll files written to {output_dir}")


if __name__ == "__main__":
    main()
