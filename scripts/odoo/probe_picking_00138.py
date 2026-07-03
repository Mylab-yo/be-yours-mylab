"""Sonde MYVO/OUT/00138 avant annulation : etat, moves, backorder, SO/facture liee."""
from _client import execute, search_read

NAME = "MYVO/OUT/00138"

pk = search_read("stock.picking", [("name", "=", NAME)],
                 ["id", "name", "state", "partner_id", "origin", "picking_type_id",
                  "scheduled_date", "date_done", "move_ids", "move_line_ids",
                  "backorder_id", "group_id"])
if not pk:
    raise SystemExit(f"Picking {NAME} introuvable")
pk = pk[0]
PID = pk["id"]
print(f"=== {pk['name']} (id={PID}) state={pk['state']} ===")
print(f"  partner={pk['partner_id']} origin={pk['origin']} type={pk['picking_type_id']}")
print(f"  scheduled={pk['scheduled_date']} date_done={pk.get('date_done')}")
print(f"  backorder_id={pk.get('backorder_id')} group_id={pk.get('group_id')}")

# backorders enfants (BL crees a partir de celui-ci)
children = search_read("stock.picking", [("backorder_id", "=", PID)],
                       ["id", "name", "state"])
if children:
    print(f"\n=== {len(children)} backorder(s) enfant ===")
    for c in children:
        print(f"  {c['name']} (id={c['id']}) state={c['state']}")

moves = search_read("stock.move", [("picking_id", "=", PID)],
                    ["id", "product_id", "product_uom_qty", "quantity", "state",
                     "has_tracking"])
print(f"\n=== {len(moves)} stock.move ===")
for m in moves:
    print(f"  move {m['id']} | {m['product_id'][1][:40]:40} | demande={m['product_uom_qty']} "
          f"reserve/done={m.get('quantity')} | state={m['state']} | track={m.get('has_tracking')}")

mls = search_read("stock.move.line", [("picking_id", "=", PID)],
                  ["id", "product_id", "quantity", "lot_id", "lot_name", "state"])
print(f"\n=== {len(mls)} stock.move.line ===")
for ml in mls:
    print(f"  ml {ml['id']} | {ml['product_id'][1][:36]:36} | qty={ml['quantity']} "
          f"| lot={ml.get('lot_id')}/{ml.get('lot_name')!r} | state={ml['state']}")

# SO d'origine + factures liees
if pk.get("origin"):
    so = search_read("sale.order", [("name", "=", pk["origin"])],
                     ["id", "name", "state", "invoice_ids", "picking_ids"])
    print(f"\n=== SO origine {pk['origin']} ===")
    for s in so:
        print(f"  {s['name']} (id={s['id']}) state={s['state']} "
              f"invoices={s.get('invoice_ids')} pickings={s.get('picking_ids')}")
        if s.get("invoice_ids"):
            inv = search_read("account.move", [("id", "in", s["invoice_ids"])],
                              ["id", "name", "state", "payment_state", "move_type"])
            for i in inv:
                print(f"    facture {i['name']} state={i['state']} "
                      f"pay={i.get('payment_state')} type={i['move_type']}")
