"""Read pricelist id=3 items for the 17 La Tresse products."""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read

PL_ID = 3

VARIANTS = [
    (2396, "shampoing nourrissant 200ml",                24),
    (2399, "shampoing protecteur de couleur 200ml",      12),
    (2357, "masque nourrissant 200ml",                   24),
    (2314, "creme boucles 200ml",                        12),
    (2405, "spray texturisant 200ml",                    12),
    (2390, "shampoing dejaunisseur platine 200ml",       12),
    (2349, "masque dejaunisseur platine 200ml",          12),
    (2384, "shampoing coloristeur blond soleil 200ml",   24),
    (2343, "masque coloristeur blond soleil 200ml",      12),
    (2427, "shampoing nourrissant 1000ml",                8),
    (2444, "masque nourrissant 1000ml",                   6),
    (2429, "shampoing purifiant 1000ml",                  6),
    (2436, "shampoing dejaunisseur platine 1000ml",       6),
    (2452, "masque dejaunisseur platine 1000ml",          4),
    (2431, "shampoing coloristeur blond soleil 1000ml",   2),
    (2447, "masque coloristeur blond soleil 1000ml",      3),
    (2428, "shampoing protecteur de couleur 1000ml",      6),
]

# Probe schema fields
items_one = search_read("product.pricelist.item",
                         [("pricelist_id", "=", PL_ID)],
                         [], limit=1)
print("Schema fields available:", list(items_one[0].keys()) if items_one else "none")
print()

FIELDS = ["id", "applied_on", "product_tmpl_id", "product_id",
          "min_quantity", "compute_price", "fixed_price",
          "percent_price", "price_discount", "price_round",
          "price_min_margin", "price_max_margin", "base", "date_start", "date_end"]

print(f"{'Variant':<55} {'OrderQty':>8} {'Tiers (min_qty→price)'}")
print("-" * 130)
for vid, name, qty in VARIANTS:
    # Pricelist items for this variant: applied_on='0_product_variant' & product_id=vid
    #                                   OR applied_on='1_product' & product_tmpl_id=tmpl
    # Fetch template id first
    items_v = search_read("product.pricelist.item",
                           [("pricelist_id", "=", PL_ID),
                            ("product_id", "=", vid)],
                           FIELDS, limit=20)
    # Try template
    if not items_v:
        # find tmpl
        from _client import execute
        prod = search_read("product.product", [("id", "=", vid)], ["product_tmpl_id"], limit=1)
        tmpl_id = prod[0]["product_tmpl_id"][0]
        items_v = search_read("product.pricelist.item",
                               [("pricelist_id", "=", PL_ID),
                                ("product_tmpl_id", "=", tmpl_id),
                                ("product_id", "=", False)],
                               FIELDS, limit=20)
    # Sort by min_quantity
    items_v.sort(key=lambda x: x.get("min_quantity") or 0)
    tier_strs = []
    matched_price = None
    for it in items_v:
        mq = it.get("min_quantity") or 0
        cp = it.get("compute_price")
        if cp == "fixed":
            p = it.get("fixed_price")
        elif cp == "percentage":
            p = f"-{it.get('percent_price')}%"
        elif cp == "formula":
            p = f"disc={it.get('price_discount')}"
        else:
            p = "?"
        tier_strs.append(f"{int(mq)}->{p}")
        if mq <= qty and cp == "fixed":
            matched_price = p
    tiers = " | ".join(tier_strs) if tier_strs else "NO RULES"
    chosen = f" [chose @{qty}: {matched_price}]" if matched_price is not None else ""
    print(f"{name:<55} {qty:>8}   {tiers}{chosen}")
