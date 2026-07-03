"""Probe LECTURE SEULE : ou est stocke le vrac aujourd'hui (emplacement conventionnel) ?

Regarde les quants internes des 4 vrac + la destination par defaut du picking type
manufacturing MYVO, pour router l'entree des OF au bon emplacement.
"""
import _client as odoo

BULK = {2519: "purifiant", 2514: "nourrissant", 2521: "gel douche", 2545: "dejaunisseur"}

quants = odoo.search_read(
    "stock.quant",
    [("product_id", "in", list(BULK)), ("location_id.usage", "=", "internal")],
    ["product_id", "location_id", "quantity", "lot_id"],
)
print("=== Quants internes existants (vrac) ===")
if not quants:
    print("  (aucun quant interne)")
for q in quants:
    lot = q["lot_id"][1] if q.get("lot_id") else "-"
    print(f"  {q['product_id'][1]:<40} loc={q['location_id'][1]:<20} qty={q['quantity']:g} lot={lot}")

# Destination par defaut des OF confirmes (move_finished)
print("\n=== Destination move_finished des OF 18-21 (par defaut) ===")
mos = odoo.search_read("mrp.production", [("id", "in", [18, 19, 20, 21])],
                       ["name", "product_id", "location_dest_id", "move_finished_ids"])
for mo in mos:
    dest = mo["location_dest_id"][1] if mo.get("location_dest_id") else "?"
    mfs = odoo.search_read("stock.move", [("id", "in", mo["move_finished_ids"])],
                           ["location_dest_id", "product_id"])
    for mf in mfs:
        mfdest = mf["location_dest_id"][1] if mf.get("location_dest_id") else "?"
        print(f"  {mo['name']} {mo['product_id'][1]:<40} OF.dest={dest} move_finished.dest={mfdest}")
