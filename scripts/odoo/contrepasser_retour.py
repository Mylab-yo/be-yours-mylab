"""Contre-passe UN retour en trop (IN/00020|21|22) : re-sort le stock des lots bidons.

Usage : python contrepasser_retour.py <picking_id>
- Cree le retour-du-retour (OUT) via le wizard (copie les sale_line_id)
- Force les lots BIDONS (149 shampoing / 150 serum / 151 bain) sur la sortie
  pour vider les lots poubelles et NE PAS toucher le vrai stock
- Valide. Resultat : livre remonte vers 0, lot bidon -> 0
"""
import sys
from _client import execute, search_read

PID = int(sys.argv[1])
LOT_BIDON = {2401: 149, 2375: 150, 2306: 151}  # produit -> lot poubelle

# garde
GUARD = [155, 212, 213, 214, 217, 218, 219]
cur = sorted(p["id"] for p in search_read("stock.picking",
    ["|", ("group_id", "=", 113), ("origin", "in",
     ["S00562", "Retour de MYVO/OUT/00138", "Retour de MYVO/OUT/00195"])], ["id"]))
# on autorise l'apparition des OUT de contre-passe (ids > 219)
if any(i not in cur for i in GUARD):
    raise SystemExit(f"Garde: pickings attendus manquants. Actuel={cur}")

src = search_read("stock.picking", [("id", "=", PID)], ["name", "state"])[0]
print(f"Contre-passe de {src['name']} (state={src['state']})")
if src["state"] != "done":
    raise SystemExit("  source pas done -> STOP")

ctx = {"active_id": PID, "active_ids": [PID], "active_model": "stock.picking"}
# quantites recues d'origine
orig = {m["product_id"][0]: m["quantity"] for m in
        search_read("stock.move", [("picking_id", "=", PID)], ["product_id", "quantity"])}

# 1. wizard
wiz = execute("stock.return.picking", "create", [{"picking_id": PID}], {"context": ctx})
w = execute("stock.return.picking", "read", [[wiz], ["product_return_moves"]], {"context": ctx})[0]
rms = execute("stock.return.picking.line", "read",
              [w["product_return_moves"], ["product_id", "move_id"]], {"context": ctx})
for r in rms:
    prod = r["product_id"][0]
    execute("stock.return.picking.line", "write",
            [[r["id"]], {"quantity": orig[prod], "to_refund": True}], {"context": ctx})
res = execute("stock.return.picking", "action_create_returns", [[wiz]], {"context": ctx})
OUT = res["res_id"]
o = search_read("stock.picking", [("id", "=", OUT)], ["name", "state", "location_id", "location_dest_id"])[0]
print(f"  -> sortie creee {o['name']} (id={OUT}) {o['location_id'][1]}->{o['location_dest_id'][1]}")

# 2. forcer les lots bidons sur la sortie
execute("stock.picking", "action_assign", [[OUT]])
for mv in search_read("stock.move", [("picking_id", "=", OUT)],
                      ["id", "product_id", "product_uom_qty", "location_id", "location_dest_id"]):
    prod = mv["product_id"][0]
    lot = LOT_BIDON[prod]
    mls = search_read("stock.move.line", [("move_id", "=", mv["id"])], ["id"])
    if mls:
        execute("stock.move.line", "write",
                [[m["id"] for m in mls], {"lot_id": lot, "quantity": mv["product_uom_qty"]}])
    else:
        execute("stock.move.line", "create", [{
            "move_id": mv["id"], "picking_id": OUT, "product_id": prod,
            "location_id": mv["location_id"][0], "location_dest_id": mv["location_dest_id"][0],
            "lot_id": lot, "quantity": mv["product_uom_qty"],
        }])
    print(f"    lot {lot} force sur {mv['product_id'][1][:35]} qty={mv['product_uom_qty']}")

# 3. valider
r2 = execute("stock.picking", "button_validate", [[OUT]])
print(f"  button_validate -> {r2}")
after = search_read("stock.picking", [("id", "=", OUT)], ["name", "state"])[0]
print(f"  {after['name']} state={after['state']}")

# 4. verif livre SO
print("\n  SO S00562 livre apres cette contre-passe :")
for l in search_read("sale.order.line", [("order_id", "=", 529), ("product_id", "!=", False)],
                     ["product_id", "product_uom_qty", "qty_delivered"]):
    print(f"    {l['product_id'][1][:38]:38} cmd={l['product_uom_qty']} livr={l['qty_delivered']}")
