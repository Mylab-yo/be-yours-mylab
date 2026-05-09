"""Verify state after reset_so_s00418."""
from scripts.odoo._client import search_read

print("=== Facture FAC/2026/00004 ===")
inv = search_read("account.move", [("id", "=", 210)],
    ["name", "state", "payment_state", "amount_residual"])[0]
print(f"  {inv}")

print("\n=== Avoir ===")
cn = search_read("account.move", [("id", "=", 242)],
    ["name", "state", "payment_state", "amount_residual", "reversed_entry_id"])[0]
print(f"  {cn}")

print("\n=== SO S00418 ===")
so = search_read("sale.order", [("id", "=", 385)],
    ["name", "state", "locked", "invoice_status", "delivery_status"])[0]
print(f"  {so}")

print("\n=== SO lines (qty_delivered + qty_invoiced + qty_to_invoice) ===")
lines = search_read("sale.order.line", [("order_id", "=", 385)],
    ["id", "product_id", "product_uom_qty", "qty_delivered", "qty_invoiced", "qty_to_invoice"])
for l in lines:
    pn = l['product_id'][1] if l['product_id'] else "—"
    print(f"  {pn[:60]:60s}  cmd={l['product_uom_qty']:6.1f}  liv={l['qty_delivered']:6.1f}  fact={l['qty_invoiced']:6.1f}  a_fact={l['qty_to_invoice']:6.1f}")

print("\n=== All pickings of SO S00418 (final state) ===")
pickings = search_read("stock.picking",
    ["|", ("origin", "like", "S00418"), ("origin", "like", "Retour de MYVO/")],
    ["id", "name", "state", "origin"])
# Filter to relevant ones
for p in pickings:
    if p['origin'] and ('S00418' in p['origin'] or any(x in p['origin'] for x in ('OUT/00008', 'OUT/00037', 'OUT/00038', 'OUT/00039', 'OUT/00040', 'IN/00010', 'IN/00011', 'IN/00015', 'IN/00016'))):
        print(f"  [{p['id']:3d}] {p['name']:18s}  {p['state']:10s}  origin={p['origin']}")
