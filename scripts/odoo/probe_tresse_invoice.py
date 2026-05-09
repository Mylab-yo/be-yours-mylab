"""Read-only probe: invoice FAC/2026/00004 state."""
from scripts.odoo._client import search_read

invs = search_read("account.move", [("name", "=", "FAC/2026/00004")],
    ["id", "name", "state", "payment_state", "invoice_date", "amount_total",
     "amount_residual", "partner_id", "invoice_origin", "invoice_user_id",
     "is_move_sent", "ref"])
for inv in invs:
    print(f"=== {inv['name']} (id={inv['id']}) ===")
    for k, v in inv.items():
        print(f"  {k}: {v}")
    print()
    # Lines
    lines = search_read("account.move.line",
        [("move_id", "=", inv['id']), ("display_type", "in", (False, "product"))],
        ["id", "product_id", "quantity", "price_unit", "price_total"])
    print(f"  Lines ({len(lines)}):")
    for l in lines:
        print(f"    - {l['product_id']}  qty={l['quantity']}  pu={l['price_unit']}  total={l['price_total']}")
