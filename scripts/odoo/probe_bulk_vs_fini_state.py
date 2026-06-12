"""Etat vrac (2518) vs fini (2403) + existe-t-il une nomenclature (BoM) vrac->fini ?"""
from _client import search_read

for vid, label in [(2518, "Bulk shampoing volume (vrac, kg)"),
                   (2403, "shampoing volume 200ml (fini, u.)")]:
    p = search_read("product.product", [("id", "=", vid)],
                    ["name", "qty_available", "uom_id"])
    print(f"=== {label} -> {p[0]['name']}: {p[0]['qty_available']} {p[0]['uom_id'][1]}")

# BoM eventuel pour le fini
boms = search_read("mrp.bom", [("product_tmpl_id", "=", 2357)],
                   ["id", "product_qty", "bom_line_ids", "type"])
print("\n=== mrp.bom pour shampoing volume 200ml (tmpl 2357) ===")
print(" ", boms if boms else "AUCUNE nomenclature")
if boms:
    lines = search_read("mrp.bom.line", [("bom_id", "=", boms[0]["id"])],
                        ["product_id", "product_qty", "product_uom_id"])
    for l in lines:
        print(f"    consomme: {l['product_id']} x {l['product_qty']} {l['product_uom_id'][1]}")
