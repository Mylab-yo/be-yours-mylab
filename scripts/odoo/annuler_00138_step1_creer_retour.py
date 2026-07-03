"""Etape 1 : creer le picking de retour (reverse) du BL MYVO/OUT/00138, SANS le valider.

- Cree le wizard stock.return.picking pour le picking 155
- Renseigne la quantite a retourner sur chaque ligne (= qty done du move d'origine)
- Genere le picking de retour (entrant) : les 35+1+1 seront ramenes en stock
- to_refund=True => la livraison SO repasse a 0 (coherent pour re-livrer proprement)
- NE VALIDE PAS : on inspecte d'abord (etape 2 = button_validate)
"""
from _client import execute, search_read

PID = 155  # MYVO/OUT/00138
ctx = {"active_id": PID, "active_ids": [PID], "active_model": "stock.picking"}

pk = search_read("stock.picking", [("id", "=", PID)], ["name", "state"])[0]
if pk["state"] != "done":
    raise SystemExit(f"Attendu done, trouve {pk['state']} -> STOP")

# quantites done des moves d'origine (pour remplir le retour)
moves = search_read("stock.move", [("picking_id", "=", PID)],
                    ["id", "product_id", "quantity"])
qty_by_move = {m["id"]: m["quantity"] for m in moves}
print("Moves d'origine :", {m["product_id"][1][:30]: m["quantity"] for m in moves})

# 1. Wizard
wiz = execute("stock.return.picking", "create", [{"picking_id": PID}], {"context": ctx})
w = execute("stock.return.picking", "read", [[wiz], ["product_return_moves"]], {"context": ctx})[0]
rm_ids = w["product_return_moves"]
rms = execute("stock.return.picking.line", "read",
              [rm_ids, ["product_id", "quantity", "move_id", "to_refund"]], {"context": ctx})

# 2. Renseigner quantity = qty done du move d'origine, to_refund=True
for r in rms:
    orig_move = r["move_id"][0]
    q = qty_by_move.get(orig_move, 0.0)
    execute("stock.return.picking.line", "write",
            [[r["id"]], {"quantity": q, "to_refund": True}], {"context": ctx})
    print(f"  ligne {r['id']} {r['product_id'][1][:35]:35} -> quantity={q} to_refund=True")

# 3. Generer le retour
res = execute("stock.return.picking", "action_create_returns", [[wiz]], {"context": ctx})
print(f"\naction_create_returns -> {res}")

# 4. Retrouver le picking de retour cree
new_pid = None
if isinstance(res, dict):
    new_pid = res.get("res_id") or (res.get("domain") and None)
if not new_pid:
    # fallback : dernier picking entrant cree pour ce partner avec origin=00138
    cand = search_read("stock.picking",
                       [("origin", "=", pk["name"])], ["id", "name", "state"])
    if cand:
        new_pid = max(c["id"] for c in cand)

ret = search_read("stock.picking", [("id", "=", new_pid)],
                  ["id", "name", "state", "origin", "location_id", "location_dest_id"])[0]
print(f"\n=== Retour cree : {ret['name']} (id={ret['id']}) state={ret['state']} ===")
print(f"  {ret['location_id']} -> {ret['location_dest_id']}  origin={ret['origin']}")
rmls = search_read("stock.move.line", [("picking_id", "=", ret["id"])],
                   ["product_id", "quantity", "lot_id", "lot_name"])
for ml in rmls:
    print(f"    {ml['product_id'][1][:40]:40} | qty={ml['quantity']} "
          f"| lot={ml.get('lot_id')}/{ml.get('lot_name')!r}")
print(f"\n>>> RIEN valide, stock inchange. RETURN_PID={ret['id']}  (etape 2 = valider)")
