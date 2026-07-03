"""Probe LECTURE SEULE : tracking/uom/BoM des 4 finis shampoing 200ml a conditionner."""
import _client as odoo

FINIS = {
    2401: ("purifiant 200ml", 16),
    2396: ("nourrissant 200ml", 1),
    2377: ("gel douche 200ml", 22),
    2390: ("dejaunisseur 200ml", 66),
}

prods = odoo.search_read("product.product", [("id", "in", list(FINIS))],
                         ["id", "name", "default_code", "tracking", "uom_id", "qty_available"])
print("=== Finis 200ml ===")
for p in sorted(prods, key=lambda x: x["id"]):
    label, bom = FINIS[p["id"]]
    print(f"[{p['id']}] {p['name']} ({p['default_code']})")
    print(f"    tracking={p['tracking']}  uom={p['uom_id']}  qty_available={p['qty_available']:g}  BoM={bom}")

# Verifier que les BoM consomment bien le bon vrac + composants dispo
print("\n=== BoM (composants) ===")
for vid, (label, bom_id) in FINIS.items():
    lines = odoo.search_read("mrp.bom.line", [("bom_id", "=", bom_id)],
                             ["product_id", "product_qty", "product_uom_id"])
    print(f"  BoM {bom_id} ({label}):")
    for l in lines:
        print(f"      {l['product_qty']:g} {l['product_uom_id'][1]} x {l['product_id'][1]}")
