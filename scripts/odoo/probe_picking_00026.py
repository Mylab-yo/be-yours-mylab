"""Probe state of MYVO/OUT/00026 (P#35, origin S00422 but not linked to SO)."""
from scripts.odoo._client import search_read

p = search_read(
    "stock.picking",
    [("id", "=", 35)],
    ["id", "name", "state", "origin", "partner_id", "sale_id",
     "group_id", "backorder_id", "backorder_ids", "date_done",
     "scheduled_date", "picking_type_id", "move_ids"],
)[0]
print(f"=== Picking {p['name']} (id={p['id']}) ===")
print(f"  state: {p['state']}")
print(f"  origin: {p['origin']!r}")
print(f"  partner: {p['partner_id']}")
print(f"  sale_id: {p['sale_id']}")
print(f"  group_id: {p['group_id']}")
print(f"  backorder_id: {p['backorder_id']}")
print(f"  backorder_ids: {p['backorder_ids']}")
print(f"  date_done: {p['date_done']}")
print(f"  picking_type: {p['picking_type_id']}")
print(f"  move_ids: {len(p['move_ids'])}")

# Show moves
moves = search_read(
    "stock.move",
    [("picking_id", "=", 35)],
    ["id", "product_id", "product_uom_qty", "quantity", "state",
     "sale_line_id", "group_id"],
)
print(f"\n=== Moves of MYVO/OUT/00026 ({len(moves)}) ===")
for mv in moves:
    prod = mv["product_id"][1] if mv["product_id"] else "?"
    sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
    gr = mv["group_id"][1] if mv["group_id"] else "-"
    print(f"  mv#{mv['id']:5d} | demand={mv['product_uom_qty']:7.2f} | "
          f"done={mv['quantity']:7.2f} | state={mv['state']:10s} | "
          f"sol={sl} | group={gr} | {prod[:45]}")

# Compare with S00422 lines side by side
print(f"\n=== Comparison with S00422 lines ===")
so_lines = search_read(
    "sale.order.line",
    [("order_id", "=", 389)],
    ["id", "product_id", "product_uom_qty", "qty_delivered", "display_type"],
)
real_lines = [ln for ln in so_lines if not ln.get("display_type") and ln["product_uom_qty"] > 0]

# Build a map by product
from collections import defaultdict
picking_qty = defaultdict(float)
for mv in moves:
    if mv["product_id"]:
        picking_qty[mv["product_id"][0]] += mv["quantity"]

print(f"  {'Product':50s} | {'SO ordered':>10s} | {'Picking done':>12s} | {'Remaining':>10s}")
print(f"  {'-'*50}-+-{'-'*10}-+-{'-'*12}-+-{'-'*10}")
for ln in real_lines:
    if not ln["product_id"]:
        continue
    pid = ln["product_id"][0]
    pname = ln["product_id"][1]
    ordered = ln["product_uom_qty"]
    done = picking_qty.get(pid, 0)
    remaining = ordered - done
    flag = " *" if remaining > 0 else ""
    print(f"  {pname[:50]:50s} | {ordered:>10.2f} | {done:>12.2f} | {remaining:>10.2f}{flag}")
