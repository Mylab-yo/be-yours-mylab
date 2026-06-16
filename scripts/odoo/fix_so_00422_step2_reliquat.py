"""Step 2: re-trigger stock rule on un-procured S00422 lines to create reliquat picking."""
from scripts.odoo._client import search_read, execute

SO_ID = 389

# Re-read all sale.order.line ids that are real product lines (no display_type, qty > 0)
sols = search_read(
    "sale.order.line",
    [("order_id", "=", SO_ID), ("display_type", "=", False),
     ("product_uom_qty", ">", 0)],
    ["id", "name", "product_id", "product_uom_qty", "qty_delivered"],
)
sol_ids = [sl["id"] for sl in sols]
print(f"Lines to relaunch: {sol_ids}")
for sl in sols:
    print(f"  sol#{sl['id']} ordered={sl['product_uom_qty']:.2f} "
          f"delivered={sl['qty_delivered']:.2f} | {sl['name'][:55]}")

# Before: pickings count
so_before = search_read("sale.order", [("id", "=", SO_ID)],
                        ["picking_ids", "delivery_status"])[0]
print(f"\nBefore: picking_ids={so_before['picking_ids']} delivery_status={so_before['delivery_status']}")

# Call _action_launch_stock_rule on the lines (skip already-procured/delivered ones automatically)
print("\nCalling _action_launch_stock_rule...")
result = execute("sale.order.line", "_action_launch_stock_rule", [sol_ids])
print(f"  result: {result}")

# After
so_after = search_read("sale.order", [("id", "=", SO_ID)],
                       ["picking_ids", "delivery_status"])[0]
print(f"\nAfter: picking_ids={so_after['picking_ids']} delivery_status={so_after['delivery_status']}")

# List pickings now
if so_after['picking_ids']:
    pickings = search_read(
        "stock.picking",
        [("id", "in", so_after['picking_ids'])],
        ["id", "name", "state", "origin", "backorder_id", "scheduled_date", "date_done"],
    )
    for p in pickings:
        bo = p["backorder_id"][1] if p["backorder_id"] else "-"
        print(f"  P#{p['id']:5d} | {p['name']:25s} | state={p['state']:10s} | "
              f"origin={p['origin']!r:30s} | backorder_of={bo} | "
              f"sched={p['scheduled_date']} done={p['date_done']}")

# Show moves of new pickings (the reliquat)
new_picking_ids = [pid for pid in so_after['picking_ids'] if pid != 35]
if new_picking_ids:
    print(f"\n=== Moves of NEW picking(s) {new_picking_ids} (reliquat) ===")
    mvs = search_read(
        "stock.move",
        [("picking_id", "in", new_picking_ids)],
        ["id", "product_id", "product_uom_qty", "quantity", "state",
         "sale_line_id", "picking_id"],
    )
    for mv in mvs:
        prod = mv["product_id"][1] if mv["product_id"] else "?"
        sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
        pk = mv["picking_id"][1] if mv["picking_id"] else "?"
        print(f"  mv#{mv['id']:5d} | demand={mv['product_uom_qty']:7.2f} | "
              f"done={mv['quantity']:7.2f} | state={mv['state']:10s} | "
              f"sol={sl} | pk={pk} | {prod[:45]}")
