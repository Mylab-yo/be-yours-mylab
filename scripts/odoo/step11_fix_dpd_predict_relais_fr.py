"""Fix DPD Predict FR (id=12) and Point Relais FR (id=11) tarifs to match Shopify.

Source: Shopify screenshots 2026-04-23.
Same approach as step10_fix_dpd_classic_fr.py: wipe existing rules, recreate clean.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _client import execute, create, unlink

CARRIERS = {
    12: {
        "label": "DPD Predict FR",
        "tranches": [
            (10, 14.50),
            (20, 16.90),
            (30, 22.90),
            (40, 39.90),
            (50, 45.90),
            (9999, 59.90),  # catch-all 50+
        ],
    },
    11: {
        "label": "DPD Point Relais FR",
        "tranches": [
            (1, 6.00),
            (2, 6.50),
            (5, 7.50),
            (10, 10.50),
            (15, 12.50),
            (20, 14.50),
            (9999, 29.90),  # catch-all 20+
        ],
    },
}


def main():
    for carrier_id, cfg in CARRIERS.items():
        carrier = execute(
            "delivery.carrier", "read",
            [[carrier_id], ["name", "price_rule_ids"]],
        )[0]
        print(f"\n=== {cfg['label']} — {carrier['name']} (id={carrier_id}) ===")
        if carrier["price_rule_ids"]:
            print(f"Deleting {len(carrier['price_rule_ids'])} existing rules")
            unlink("delivery.price.rule", carrier["price_rule_ids"])

        for max_w, price in cfg["tranches"]:
            rid = create(
                "delivery.price.rule",
                {
                    "carrier_id": carrier_id,
                    "variable": "weight",
                    "operator": "<=",
                    "max_value": float(max_w),
                    "list_base_price": price,
                    "list_price": 0.0,
                    "variable_factor": "weight",
                },
            )
            label = f"<={max_w}kg" if max_w < 9999 else "catch-all (aucune limite)"
            print(f"  + rule_id={rid}  {label}  = {price}€")


if __name__ == "__main__":
    main()
