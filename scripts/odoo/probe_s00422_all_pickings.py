"""Full picture: all pickings for SO S00422 (CENDREE) + the SO order lines."""
from scripts.odoo._client import search_read

so = search_read("sale.order", [("name", "=", "S00422")],
                 ["id", "name", "partner_id", "state", "amount_total"])
print(f"=== SO {so[0]['name']} (id={so[0]['id']}, state={so[0]['state']}) partner={so[0]['partner_id'][1]} ===")
lines = search_read("sale.order.line", [("order_id", "=", so[0]["id"])],
                    ["id", "product_id", "product_uom_qty", "qty_delivered", "name"])
print("--- SO lines (ordered / delivered) ---")
for l in lines:
    prod = l["product_id"][1] if l["product_id"] else "?(section)"
    print(f"  L#{l['id']:6d} | ordered={l['product_uom_qty']:7.1f} | delivered={l['qty_delivered']:7.1f} | {prod[:70]}")

# All pickings for this SO
pickings = search_read("stock.picking", [("origin", "=", "S00422")],
                       ["id", "name", "state", "scheduled_date", "date_done"])
print(f"\n=== {len(pickings)} pickings for S00422 ===")
for p in sorted(pickings, key=lambda x: x["name"]):
    print(f"\n--- {p['name']} (id={p['id']}, state={p['state']}, done={p['date_done']}) ---")
    moves = search_read("stock.move", [("picking_id", "=", p["id"])],
                        ["id", "product_id", "product_uom_qty", "quantity", "state"])
    for mv in moves:
        prod = mv["product_id"][1] if mv["product_id"] else "?"
        print(f"    mv#{mv['id']:6d} | demand={mv['product_uom_qty']:7.1f} | done={mv['quantity']:7.1f} | {prod[:60]}")
