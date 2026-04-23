"""Extend max_weight on DPD FR carriers to match new Shopify tranches.

max_weight limits carrier visibility in the sale-order shipping dialog.
Old values (1/30/30 kg) prevented display for orders above the old max.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _client import execute, write

# (id, new_max_weight_kg)
UPDATES = [
    (11, 20.0),   # Point Relais : DPD PR limite physique 20kg, Shopify catch-all 29.90€
    (12, 9999.0), # Predict       : Shopify "Aucune limite"
    (13, 9999.0), # Classic       : Shopify "Aucune limite"
]

for cid, max_w in UPDATES:
    c = execute("delivery.carrier","read",[[cid],["name","max_weight"]])[0]
    print(f"id={cid} {c['name']}  max_weight: {c['max_weight']} -> {max_w}")
    write("delivery.carrier",[cid],{"max_weight": max_w})

print("Done.")
