"""Annule l'OF dejaunisseur bloque (MYVO/MO/00025, to_close, rien produit) faute de
flacons 200 libres (free_qty=0). Libere les composants reserves. Reversible : on
recreera l'OF quand les flacons seront reapprovisionnes.
"""
import _client as odoo

mo = odoo.search_read("mrp.production", [("name", "=", "MYVO/MO/00025")],
                      ["id", "state", "qty_produced"])[0]
print(f"Avant : OF {mo['id']} state={mo['state']} qty_produced={mo['qty_produced']}")

if mo["state"] != "cancel" and mo["qty_produced"] == 0:
    odoo.execute("mrp.production", "action_cancel", [[mo["id"]]])

st = odoo.search_read("mrp.production", [("id", "=", mo["id"])], ["state"])[0]
print(f"Apres : state={st['state']}")

# Verif liberation flacon + recap stock finis
p = odoo.execute("product.product", "read", [[2552], ["free_qty", "qty_available"]])[0]
print(f"\nFLACON-PLA-200 : free_qty={p['free_qty']:g} qty_available={p['qty_available']:g}")

print("\n=== Stock finis shampoing 200ml apres conditionnement ===")
FINIS = {2401: "purifiant", 2396: "nourrissant", 2377: "gel douche", 2390: "dejaunisseur"}
for p in sorted(odoo.search_read("product.product", [("id", "in", list(FINIS))],
                                 ["id", "qty_available"]), key=lambda x: x["id"]):
    print(f"  {FINIS[p['id']]:<14} {p['qty_available']:g} u.")
