"""1) Verifie l'etat des mails preview envoyes a Yoann.
   2) Dissseque la commande S00533 et ses BL (dont le reliquat)."""
from scripts.odoo._client import search_read

print("=== 1) Mails recents vers yoann@mylab-shop.com ===")
mails = search_read("mail.mail", [("email_to", "ilike", "yoann@mylab-shop.com")],
    ["id", "subject", "state", "date", "failure_reason"], limit=5)
for m in mails:
    print(f"  #{m['id']} state={m.get('state')} date={m.get('date')} "
          f"fail={m.get('failure_reason') or '-'} | {m.get('subject')}")
if not mails:
    print("  (aucun trouve par email_to ; ils sont peut-etre deja purges apres envoi)")

print("\n=== 2) Commande S00533 + ses BL ===")
so = search_read("sale.order", [("name", "=", "S00533")],
    ["id", "name", "state", "delivery_count", "picking_ids", "partner_id"], limit=1)
if not so:
    print("  S00533 introuvable")
else:
    so = so[0]
    print(f"  {so['name']} state={so['state']} delivery_count={so['delivery_count']} "
          f"pickings={so['picking_ids']} client={so['partner_id'][1]}")
    pks = search_read("stock.picking", [("id", "in", so["picking_ids"])],
        ["name", "state", "origin", "backorder_id", "carrier_id",
         "carrier_tracking_ref", "scheduled_date", "date_done"], limit=20)
    for p in sorted(pks, key=lambda x: x["id"]):
        bo = p["backorder_id"][1] if p.get("backorder_id") else "—"
        car = p["carrier_id"][1] if p.get("carrier_id") else "—"
        print(f"\n  >> {p['name']} (id={p['id']}) state={p['state']} backorder_de={bo}")
        print(f"     carrier={car} tracking={p.get('carrier_tracking_ref') or '—'} "
              f"done={(p.get('date_done') or '')[:16]}")
        moves = search_read("stock.move", [("picking_id", "=", p["id"])],
            ["product_id", "product_uom_qty", "quantity", "state"], limit=50)
        for mv in moves:
            prod = mv["product_id"][1] if mv.get("product_id") else "?"
            print(f"       {prod[:42]:<42} demande={mv.get('product_uom_qty')} "
                  f"fait/reserve={mv.get('quantity')} state={mv.get('state')}")
