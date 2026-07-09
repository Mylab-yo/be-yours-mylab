"""État complet SO S00566 (id 533) + tous ses pickings, pour savoir quoi 'recommencer'."""
from _client import search_read

so = search_read("sale.order", [("id", "=", 533)],
                 ["name", "state", "partner_id", "picking_ids", "invoice_status",
                  "amount_total", "date_order"])
print("=== SO ===")
print(" ", so[0] if so else "introuvable")

if so:
    pks = search_read("stock.picking", [("id", "in", so[0]["picking_ids"])],
                      ["id", "name", "state", "scheduled_date", "backorder_id", "origin"])
    print("\n=== pickings du SO ===")
    for p in pks:
        print(f"  id={p['id']} {p['name']} | state={p['state']} | "
              f"sched={p['scheduled_date']} | backorder={p['backorder_id']}")

    # lignes du SO
    sol = search_read("sale.order.line", [("order_id", "=", 533)],
                      ["product_id", "product_uom_qty", "qty_delivered"])
    print("\n=== lignes SO (produit / commandé / livré) ===")
    for l in sol:
        if l.get("product_id"):
            print(f"  {l['product_id'][1][:40]:40} cmd={l['product_uom_qty']} livré={l['qty_delivered']}")
