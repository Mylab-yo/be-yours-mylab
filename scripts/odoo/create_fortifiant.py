# -*- coding: utf-8 -*-
"""Create FORTIFIANT products + degressive pl3 tiers. Idempotent."""
from _client import execute, search_read

TAX_SALE = 103       # TVA 20% G
TAX_PURCHASE = 68
UOM = 1              # Units
PL = 3              # TARIFS DEGRESSIFS MYLAB
COMPANY = 3
CUR = 125           # EUR

PRODUCTS = [
    dict(key="shampoing-fortifiant-200-ml",  name="shampoing fortifiant 200ml",
         categ=13, weight=0.25, list_price=8.00,
         tiers=[(6,8.00),(12,7.60),(24,7.20),(48,6.40),(96,5.70)]),
    dict(key="shampoing-fortifiant-500-ml",  name="shampoing fortifiant 500ml",
         categ=19, weight=0.60, list_price=16.90,
         tiers=[(6,16.90),(14,15.20),(28,14.35),(42,13.50),(54,12.15)]),
    dict(key="shampoing-fortifiant-1000-ml", name="shampoing fortifiant 1000ml",
         categ=18, weight=1.10, list_price=27.90,
         tiers=[]),  # only base price defined in source table
    dict(key="serum-fortifiant-50-ml",       name="serum fortifiant 50ml",
         categ=16, weight=0.12, list_price=12.50,
         tiers=[(6,12.50),(12,11.85),(24,11.20),(48,10.00),(96,8.95),
                (192,8.25),(384,7.90),(500,7.45)]),
]

# detect is_storable field availability (Odoo 18)
fg = execute("product.template", "fields_get", [["is_storable"]], {"attributes": ["type"]})
HAS_IS_STORABLE = "is_storable" in fg
print("is_storable field present:", HAS_IS_STORABLE)

for p in PRODUCTS:
    base_vals = {
        "name": p["name"], "default_code": p["key"], "type": "consu",
        "categ_id": p["categ"], "list_price": p["list_price"], "weight": p["weight"],
        "uom_id": UOM, "uom_po_id": UOM,
        "taxes_id": [(6, 0, [TAX_SALE])], "supplier_taxes_id": [(6, 0, [TAX_PURCHASE])],
        "sale_ok": True, "purchase_ok": True,
    }
    if HAS_IS_STORABLE:
        base_vals["is_storable"] = True

    existing = search_read("product.template", [("default_code", "=", p["key"])],
                           ["id", "product_variant_id"])
    if existing:
        tid = existing[0]["id"]
        execute("product.template", "write", [[tid], base_vals])
        print(f"\nUPDATED tmpl {tid}: {p['name']}")
    else:
        tid = execute("product.template", "create", [base_vals])
        print(f"\nCREATED tmpl {tid}: {p['name']}")

    var = search_read("product.template", [("id", "=", tid)], ["product_variant_id"])
    vid = var[0]["product_variant_id"][0]

    # idempotent tiers: wipe existing pl3 items for this tmpl, recreate
    old = execute("product.pricelist.item", "search",
                  [[("pricelist_id", "=", PL), ("product_tmpl_id", "=", tid)]])
    if old:
        execute("product.pricelist.item", "unlink", [old])
        print(f"  cleared {len(old)} old pl3 item(s)")

    for qty, price in p["tiers"]:
        execute("product.pricelist.item", "create", [{
            "pricelist_id": PL, "company_id": COMPANY, "currency_id": CUR,
            "product_tmpl_id": tid, "product_id": vid,
            "applied_on": "0_product_variant", "compute_price": "fixed",
            "base": "list_price", "min_quantity": qty, "fixed_price": price,
        }])
    print(f"  variant {vid} | list_price {p['list_price']} | {len(p['tiers'])} tier(s) created")

print("\nDONE.")
