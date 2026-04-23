"""Fix DPD Classic FR (id=13) tarifs to match Shopify "Livraison sur lieu de travail".

Replaces all existing price rules on carrier 13 with the exact Shopify tranches.
Idempotent: wipes existing rules, recreates from TARGETS.

Source: Shopify "Livraison sur lieu de travail" (DPD CLASSIC) — screenshot 2026-04-23.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _client import execute, create, unlink

CARRIER_ID = 13

# (max_weight_kg, price_eur) — None = catch-all (Shopify "Aucune limite")
TARGETS = [
    (10, 10.90),
    (20, 12.90),
    (30, 15.90),
    (40, 26.90),
    (50, 28.90),
    (60, 30.90),
    (9999, 49.90),  # catch-all 60+ (Shopify: no limit)
]


def main():
    carrier = execute(
        "delivery.carrier", "read", [[CARRIER_ID], ["name", "price_rule_ids"]]
    )[0]
    print(f"Carrier: {carrier['name']} (id={CARRIER_ID})")
    existing = carrier["price_rule_ids"]
    if existing:
        print(f"Deleting {len(existing)} existing rules: {existing}")
        unlink("delivery.price.rule", existing)

    for max_w, price in TARGETS:
        rid = create(
            "delivery.price.rule",
            {
                "carrier_id": CARRIER_ID,
                "variable": "weight",
                "operator": "<=",
                "max_value": float(max_w),
                "list_base_price": price,
                "list_price": 0.0,
                "variable_factor": "weight",
            },
        )
        label = f"<={max_w}kg" if max_w < 9999 else "60+ kg (catch-all)"
        print(f"  + rule_id={rid}  {label}  = {price}€")


if __name__ == "__main__":
    main()
