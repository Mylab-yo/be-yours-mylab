"""Probe LECTURE SEULE : stock des composants necessaires au conditionnement flacons.

Conditionner 1 flacon consomme : vrac (0.2/0.5/1 kg) + 1 flacon vide + 1 bouchon.
Sans flacons/bouchons en stock, l'OF de conditionnement ne peut pas etre termine.
"""
import _client as odoo

CODES = ["FLACON-PLA-200", "FLACON-PLA-500", "FLACON-PLA-1000",
         "BOUCHON-24-410", "BOUCHON-28-410"]

prods = odoo.search_read(
    "product.product",
    [("default_code", "in", CODES)],
    ["id", "name", "default_code", "qty_available", "uom_id"],
)
by_code = {p["default_code"]: p for p in prods}

print("=== Stock composants flacons/bouchons ===")
for code in CODES:
    p = by_code.get(code)
    if not p:
        print(f"  {code:<16} INTROUVABLE")
        continue
    print(f"  {code:<16} stock={p['qty_available']:g} {p['uom_id'][1]:<6} (id={p['id']}) {p['name']}")

# Rappel : vrac dispo par gamme (variantes bulk)
print("\n=== Vrac dispo (kg) ===")
BULK = {2519: "purifiant", 2514: "nourrissant", 2521: "gel douche", 2545: "dejaunisseur"}
bp = odoo.search_read("product.product", [("id", "in", list(BULK))],
                      ["id", "name", "qty_available"])
for p in sorted(bp, key=lambda x: x["id"]):
    print(f"  {BULK[p['id']]:<14} {p['qty_available']:g} kg")

# Combien de flacons 200ml theoriques limites par flacons+bouchons dispo
f200 = by_code.get("FLACON-PLA-200", {}).get("qty_available", 0)
b24 = by_code.get("BOUCHON-24-410", {}).get("qty_available", 0)
print(f"\n=> Plafond 200ml (hors vrac) : min(flacons {f200:g}, bouchons24 {b24:g}) "
      f"= {min(f200, b24):g} flacons 200ml conditionnables")
