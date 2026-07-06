"""Etape 3b : completer MYVO/OUT/00196 avec serum + bain (deja que le shampoing).

Odoo a auto-cree la livraison avec le seul shampoing (35). On ajoute les moves
serum (1) et bain (1) lies a leurs lignes SO, puis on confirme + reserve.
Laisse le BL pret a valider (par Yoann).
"""
from _client import execute, search_read, create

PID = 214          # MYVO/OUT/00196
GROUP = 113
SRC, DEST = 28, 5

# (SOL id, product id, qte) a ajouter
AJOUTS = [
    (2031, 2375, 1.0),  # serum-finition-ultime-50-ml
    (2032, 2306, 1.0),  # bain-miraculeux-50-ml
]

# produits deja presents ?
present = {m["product_id"][0] for m in
           search_read("stock.move", [("picking_id", "=", PID)], ["product_id"])}
uoms = {p["id"]: p["uom_id"][0] for p in
        search_read("product.product", [("id", "in", [a[1] for a in AJOUTS])], ["uom_id"])}

for sol_id, prod, qty in AJOUTS:
    if prod in present:
        print(f"  produit {prod} deja present, saute.")
        continue
    pname = search_read("product.product", [("id", "=", prod)], ["display_name"])[0]["display_name"]
    mv = create("stock.move", {
        "name": pname, "product_id": prod, "product_uom_qty": qty,
        "product_uom": uoms[prod], "location_id": SRC, "location_dest_id": DEST,
        "picking_id": PID, "group_id": GROUP, "sale_line_id": sol_id,
    })
    print(f"  + move {mv} : {pname[:40]:40} qty={qty}")

# confirmer les nouveaux moves + reserver tout
execute("stock.picking", "action_confirm", [[PID]])
execute("stock.picking", "action_assign", [[PID]])

# etat final
p = search_read("stock.picking", [("id", "=", PID)], ["name", "state"])[0]
print(f"\n=== {p['name']} (id={PID}) state={p['state']} ===")
moves = search_read("stock.move", [("picking_id", "=", PID)],
                    ["product_id", "product_uom_qty", "quantity", "state"])
for m in moves:
    flag = "" if m["quantity"] >= m["product_uom_qty"] else "  <-- non reserve entierement"
    print(f"  {m['product_id'][1][:40]:40} | demande={m['product_uom_qty']} reserve={m['quantity']} | {m['state']}{flag}")
mls = search_read("stock.move.line", [("picking_id", "=", PID)],
                  ["product_id", "quantity", "lot_id"])
print("  -- move lines --")
for ml in mls:
    print(f"    {ml['product_id'][1][:40]:40} | qty={ml['quantity']} | lot={ml.get('lot_id')}")
