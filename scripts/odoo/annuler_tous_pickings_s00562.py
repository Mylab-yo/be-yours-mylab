"""Annule tous les pickings annulables de S00562 et fait l'etat des lieux.

- Les pickings 'done' (BL 00138 + retour 00018) ne peuvent pas etre annules,
  mais ils se neutralisent (sortie 35+1+1 puis retour 35+1+1 = stock net 0).
- Les pickings non termines (ex: nouveau BL 00196) sont annules via action_cancel.
"""
from _client import execute, search_read

# Tous les pickings du groupe procurement S00562 (id 113) ou origin S00562
pks = search_read("stock.picking",
                  ["|", ("group_id", "=", 113), ("origin", "in", ["S00562", "Retour de MYVO/OUT/00138"])],
                  ["id", "name", "state", "picking_type_code", "origin"])
pks.sort(key=lambda p: p["id"])
print("=== Pickings rattaches a S00562 ===")
for p in pks:
    print(f"  {p['name']:18} id={p['id']:4} type={p['picking_type_code']:9} state={p['state']:10} origin={p['origin']}")

# Annuler tout ce qui n'est pas done/cancel
print("\n=== Annulations ===")
for p in pks:
    if p["state"] in ("done", "cancel"):
        raison = "deja annule" if p["state"] == "cancel" else "VALIDE (done) : non annulable, neutralise par le retour"
        print(f"  {p['name']:18} -> saute ({raison})")
        continue
    execute("stock.picking", "action_cancel", [[p["id"]]])
    after = search_read("stock.picking", [("id", "=", p["id"])], ["state"])[0]
    print(f"  {p['name']:18} -> action_cancel, nouvel etat = {after['state']}")

# Etat final SO + stock
print("\n=== Etat final ===")
for p in search_read("stock.picking",
                     ["|", ("group_id", "=", 113), ("origin", "in", ["S00562", "Retour de MYVO/OUT/00138"])],
                     ["name", "state", "picking_type_code"]):
    print(f"  {p['name']:18} {p['picking_type_code']:9} {p['state']}")

so = search_read("sale.order", [("id", "=", 529)], ["name", "state", "locked", "invoice_status"])[0]
print(f"\nSO {so['name']} state={so['state']} locked={so['locked']} invoice_status={so['invoice_status']}")
for l in search_read("sale.order.line", [("order_id", "=", 529)],
                     ["product_id", "product_uom_qty", "qty_delivered", "qty_invoiced"]):
    pid = l["product_id"][1][:38] if l.get("product_id") else "(note)"
    print(f"  {pid:38} | cmd={l['product_uom_qty']} livr={l['qty_delivered']} fact={l['qty_invoiced']}")
