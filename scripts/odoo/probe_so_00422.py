"""Probe state of S00422 to diagnose missing backorder (reliquat)."""
from scripts.odoo._client import search_read

# Find the sale order
sos = search_read(
    "sale.order",
    [("name", "=", "S00422")],
    ["id", "name", "state", "partner_id", "order_line", "picking_ids",
     "invoice_status", "amount_total", "date_order"],
)
if not sos:
    print("S00422 not found")
    raise SystemExit

so = sos[0]
print(f"=== Sale Order {so['name']} (id={so['id']}, state={so['state']}) ===")
print(f"  partner: {so['partner_id']}")
print(f"  amount_total: {so['amount_total']}")
print(f"  invoice_status: {so['invoice_status']}")
print(f"  date_order: {so['date_order']}")
print(f"  order_line count: {len(so['order_line'])}")
print(f"  picking_ids: {so['picking_ids']}")

# Read order lines
lines = search_read(
    "sale.order.line",
    [("order_id", "=", so["id"])],
    ["id", "product_id", "name", "product_uom_qty", "qty_delivered",
     "qty_invoiced", "qty_to_invoice", "price_subtotal", "state",
     "display_type", "move_ids"],
)
print(f"\n=== Sale Order Lines ({len(lines)}) ===")
for ln in lines:
    if ln.get("display_type"):
        # Section/note line
        print(f"  L#{ln['id']:5d} | [{ln['display_type']:8s}] {ln['name'][:60]}")
        continue
    prod = ln["product_id"][1] if ln["product_id"] else "?"
    print(f"  L#{ln['id']:5d} | ordered={ln['product_uom_qty']:7.2f} | delivered={ln['qty_delivered']:7.2f} | "
          f"invoiced={ln['qty_invoiced']:7.2f} | to_invoice={ln['qty_to_invoice']:7.2f} | "
          f"moves={len(ln.get('move_ids') or [])} | {prod[:45]}")

# Read pickings
if so["picking_ids"]:
    pickings = search_read(
        "stock.picking",
        [("id", "in", so["picking_ids"])],
        ["id", "name", "state", "origin", "backorder_id", "backorder_ids",
         "date_done", "scheduled_date", "picking_type_id"],
    )
    print(f"\n=== Pickings ({len(pickings)}) ===")
    for p in pickings:
        bo = p["backorder_id"][1] if p["backorder_id"] else "-"
        bos = len(p.get("backorder_ids") or [])
        ptype = p["picking_type_id"][1] if p["picking_type_id"] else "?"
        print(f"  P#{p['id']:4d} | {p['name']:25s} | state={p['state']:10s} | "
              f"type={ptype:30s} | backorder_of={bo} | has_backorders={bos} | "
              f"done={p.get('date_done')}")

    # For each picking, show moves
    for p in pickings:
        print(f"\n--- Moves of {p['name']} (id={p['id']}, state={p['state']}) ---")
        moves = search_read(
            "stock.move",
            [("picking_id", "=", p["id"])],
            ["id", "product_id", "product_uom_qty", "quantity", "state",
             "sale_line_id"],
        )
        for mv in moves:
            prod = mv["product_id"][1] if mv["product_id"] else "?"
            sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
            print(f"    mv#{mv['id']:5d} | demand={mv['product_uom_qty']:7.2f} | "
                  f"done={mv['quantity']:7.2f} | state={mv['state']:10s} | "
                  f"sol={sl} | {prod[:45]}")

# Check for orphan moves (moves linked to SO lines but maybe not in pickings)
print(f"\n=== All moves linked to SO lines (incl. cancelled/orphan) ===")
sol_ids = [ln["id"] for ln in lines if not ln.get("display_type")]
all_moves = search_read(
    "stock.move",
    [("sale_line_id", "in", sol_ids)],
    ["id", "product_id", "product_uom_qty", "quantity", "state",
     "sale_line_id", "picking_id"],
)
for mv in all_moves:
    prod = mv["product_id"][1] if mv["product_id"] else "?"
    sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
    pk = mv["picking_id"][1] if mv["picking_id"] else "NO PICKING"
    print(f"  mv#{mv['id']:5d} | sol={sl} | demand={mv['product_uom_qty']:7.2f} | "
          f"done={mv['quantity']:7.2f} | state={mv['state']:10s} | "
          f"picking={pk} | {prod[:40]}")
