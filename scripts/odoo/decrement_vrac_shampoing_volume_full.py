"""Décrémente le vrac Bulk shampoing volume (2518) à 0 : rendement réel = tout le vrac
consommé par les 150 u. de shampoing 200ml (la BoM théorique sous-estimait à 30 kg).
Ajustement d'inventaire sur le lot 220A526C dans MYVO/Stock/Bulk."""
from _client import execute, search, search_read

PRODUCT_ID = 2518   # Bulk shampoing volume (product.product)

# État avant
q = search_read("stock.quant",
                [("product_id", "=", PRODUCT_ID), ("location_id.usage", "=", "internal"),
                 ("quantity", ">", 0)],
                ["id", "location_id", "lot_id", "quantity"])
print("=== vrac AVANT ===")
for r in q:
    print(f"  quant {r['id']}: loc={r['location_id']} lot={r['lot_id']} qty={r['quantity']}")

# Mise à 0 de chaque quant vrac en stock
for r in q:
    execute("stock.quant", "write", [[r["id"]], {"inventory_quantity": 0.0}])
    execute("stock.quant", "action_apply_inventory", [[r["id"]]])
    print(f"  -> quant {r['id']} ajusté à 0")

# Vérif
p = search_read("product.product", [("id", "=", PRODUCT_ID)], ["name", "qty_available"])
print(f"\n=== VERIF === {p[0]['name']} qty_available = {p[0]['qty_available']} (attendu 0)")
