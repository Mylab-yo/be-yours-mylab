"""Etape 2 : valider le retour MYVO/IN/00018 (id=213).

Le bain miraculeux (produit suivi par lot) a ete expedie sans lot => on assigne
le seul lot existant 190E126C (id 62) sur la ligne de retour, puis on valide.
Ramene 35 shampoing + 1 serum + 1 bain en stock, remet la livraison SO a 0.
"""
from _client import execute, search_read

RET = 213          # MYVO/IN/00018
BAIN = 2306        # bain-miraculeux-50-ml
LOT_BAIN = 62      # 190E126C

r = search_read("stock.picking", [("id", "=", RET)], ["name", "state"])[0]
print(f"Avant : {r['name']} state={r['state']}")
if r["state"] == "done":
    print("  deja valide, on saute la validation.")
elif r["state"] == "cancel":
    raise SystemExit("  annule -> STOP")
else:
    # Assigner le lot au bain sur la ligne de retour
    ml = search_read("stock.move.line",
                     [("picking_id", "=", RET), ("product_id", "=", BAIN)],
                     ["id", "lot_id"])
    if ml and not ml[0].get("lot_id"):
        execute("stock.move.line", "write", [[ml[0]["id"]], {"lot_id": LOT_BAIN}])
        print(f"  lot {LOT_BAIN} assigne a la ligne bain {ml[0]['id']}")

    res = execute("stock.picking", "button_validate", [[RET]])
    print(f"  button_validate -> {res}")
    if isinstance(res, dict) and res.get("res_model"):
        model, rid, ctx = res["res_model"], res.get("res_id"), res.get("context", {})
        if not rid:
            rid = execute(model, "create", [{}], {"context": ctx})
        for m in ("process", "button_validate", "action_confirm"):
            try:
                execute(model, m, [[rid]], {"context": ctx})
                print(f"    wizard {model}.{m}() OK")
                break
            except Exception as e:
                print(f"    {m}() -> {e}")

after = search_read("stock.picking", [("id", "=", RET)], ["name", "state"])[0]
print(f"Apres : {after['name']} state={after['state']}")

# Etat SO : livraison doit repasser a 0
so = search_read("sale.order", [("name", "=", "S00562")], ["id"])[0]
lines = search_read("sale.order.line", [("order_id", "=", so["id"])],
                    ["product_id", "product_uom_qty", "qty_delivered", "qty_invoiced"])
print("\n=== SO S00562 apres retour ===")
for l in lines:
    pid = l["product_id"][1][:38] if l.get("product_id") else "(note)"
    print(f"  {pid:38} | cmd={l['product_uom_qty']} livr={l['qty_delivered']} fact={l['qty_invoiced']}")

print("\n=== lots (stock apres retour) ===")
for lot_name in ("110A526C", "110526A", "190E126C"):
    for x in search_read("stock.lot", [("name", "=", lot_name)], ["name", "product_qty"]):
        print(f"  lot {x['name']} product_qty={x['product_qty']}")
