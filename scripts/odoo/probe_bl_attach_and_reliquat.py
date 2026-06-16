"""1) Le template id=27 attache-t-il le PDF du BL ?
   2) Photo des reliquats potentiels : BL ouverts non reserves (= rupture) vs reserves."""
from collections import Counter
from scripts.odoo._client import search_read, execute

print("=== 1) Template id=27 : pieces jointes / rapport ===")
fields = execute("mail.template", "fields_get", [], {"attributes": ["string"]})
attach_fields = [f for f in fields if "report" in f or "attachment" in f]
t = search_read("mail.template", [("id", "=", 27)], attach_fields)[0]
for f in attach_fields:
    if t.get(f):
        print(f"  {f} = {t[f]}")
print("  (si report_template_ids/report_name vide -> pas de PDF BL attache)")

print("\n=== 2) BL sortants ouverts : etat de reservation ===")
open_pk = search_read("stock.picking",
    [("picking_type_code", "=", "outgoing"), ("state", "in", ["confirmed", "assigned", "waiting"])],
    ["name", "state", "move_ids"], limit=2000)
print("  Repartition:", dict(Counter(p["state"] for p in open_pk)))
print("  assigned = stock dispo, expediable en entier")
print("  confirmed/waiting = au moins 1 produit en rupture -> candidat RELIQUAT")

print("\n=== 3) Detail d'un BL en rupture (confirmed) : demande vs reserve par ligne ===")
conf = [p for p in open_pk if p["state"] == "confirmed"][:1]
if conf:
    pid = conf[0]["id"]
    moves = search_read("stock.move", [("picking_id", "=", pid)],
        ["product_id", "product_uom_qty", "quantity", "state"], limit=50)
    print(f"  BL {conf[0]['name']} (id={pid}):")
    for m in moves:
        prod = m["product_id"][1] if m.get("product_id") else "?"
        dem = m.get("product_uom_qty")
        res = m.get("quantity")  # qty reservee/faite
        manque = (dem or 0) - (res or 0)
        flag = "  <-- RUPTURE" if manque > 0 else ""
        print(f"    {prod[:45]:<45} demande={dem} dispo/reserve={res} state={m.get('state')}{flag}")
