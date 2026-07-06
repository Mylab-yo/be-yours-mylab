"""Etape 3 : recreer un BL vierge pour S00562 (FEDY) avec les bonnes quantites.

- Deverrouille la SO (verrouillee car payee)
- Ramene la ligne shampoing 48 -> 35 (evite un futur reliquat)
- Cree une nouvelle livraison sortante 35 shampoing + 1 serum + 1 bain,
  liee aux lignes SO, reservee et PRETE A VALIDER (laissee a Yoann)
- Ne re-verrouille PAS la SO (travail en cours + avoir a faire ensuite)
- Ne touche PAS la facture

Idempotent : si un BL brouillon/pret existe deja pour ce groupe, ne recree pas.
"""
from _client import execute, search_read, write, create

SID = 529          # S00562
GROUP = 113        # groupe procurement S00562
PT_OUT = 10        # MYLAB: Bons de livraison (sortant)
SRC = 28           # MYVO/Stock
DEST = 5           # Partners/Customers
PARTNER = 2141     # FEDY BOUTIQUE

# lignes cibles : (SOL id, product id, qte)
CIBLES = [
    (2030, 2401, 35.0),  # shampoing-purifiant-200-ml
    (2031, 2375, 1.0),   # serum-finition-ultime-50-ml
    (2032, 2306, 1.0),   # bain-miraculeux-50-ml
]

# 1. Deverrouiller
so = search_read("sale.order", [("id", "=", SID)], ["name", "locked"])[0]
if so.get("locked"):
    execute("sale.order", "action_unlock", [[SID]])
    print(f"SO {so['name']} deverrouillee.")
else:
    print(f"SO {so['name']} deja deverrouillee.")

# 2. Shampoing 48 -> 35
sol = search_read("sale.order.line", [("id", "=", 2030)], ["product_uom_qty"])[0]
if sol["product_uom_qty"] != 35.0:
    write("sale.order.line", [2030], {"product_uom_qty": 35.0})
    print("Ligne shampoing ramenee a 35.")
else:
    print("Ligne shampoing deja a 35.")

# 3. Anti-doublon : un BL sortant non-termine existe deja pour ce groupe ?
existing = search_read("stock.picking",
                       [("group_id", "=", GROUP), ("picking_type_id", "=", PT_OUT),
                        ("state", "not in", ["done", "cancel"])],
                       ["id", "name", "state"])
if existing:
    print(f"BL sortant deja present : {existing} -> pas de recreation.")
    raise SystemExit(0)

# uom des produits
uoms = {p["id"]: p["uom_id"][0] for p in
        search_read("product.product", [("id", "in", [c[1] for c in CIBLES])], ["uom_id"])}

# 4. Creer le picking
pick = create("stock.picking", {
    "picking_type_id": PT_OUT,
    "partner_id": PARTNER,
    "location_id": SRC,
    "location_dest_id": DEST,
    "origin": "S00562",
    "group_id": GROUP,
})
print(f"\nNouveau picking cree : id={pick}")

# 5. Creer les moves lies aux lignes SO
for sol_id, prod, qty in CIBLES:
    pname = search_read("product.product", [("id", "=", prod)], ["display_name"])[0]["display_name"]
    mv = create("stock.move", {
        "name": pname,
        "product_id": prod,
        "product_uom_qty": qty,
        "product_uom": uoms[prod],
        "location_id": SRC,
        "location_dest_id": DEST,
        "picking_id": pick,
        "group_id": GROUP,
        "sale_line_id": sol_id,
    })
    print(f"  move {mv} : {pname[:40]:40} qty={qty}")

# 6. Confirmer + reserver
execute("stock.picking", "action_confirm", [[pick]])
execute("stock.picking", "action_assign", [[pick]])

# 7. Etat final
p = search_read("stock.picking", [("id", "=", pick)], ["name", "state"])[0]
print(f"\n=== {p['name']} (id={pick}) state={p['state']} ===")
mls = search_read("stock.move.line", [("picking_id", "=", pick)],
                  ["product_id", "quantity", "lot_id"])
for ml in mls:
    print(f"  {ml['product_id'][1][:40]:40} | reserve={ml['quantity']} | lot={ml.get('lot_id')}")
print(f"\n>>> BL vierge PRET. A toi de le valider (verifie lots/quantites avant).")
