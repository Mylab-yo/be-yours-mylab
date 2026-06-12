"""Probe detail of invoice 456 + SO 525 before modifying billing address."""
from _client import search_read

inv = search_read(
    "account.move", [("id", "=", 456)],
    ["id", "name", "state", "payment_state", "partner_id", "partner_shipping_id",
     "commercial_partner_id", "invoice_date", "amount_total", "amount_residual",
     "invoice_origin", "ref"],
)
print("=== INVOICE 456 ===")
for k, v in inv[0].items():
    print(f"  {k}: {v}")

# any payments reconciled?
print("\n=== SO 525 ===")
so = search_read(
    "sale.order", [("id", "=", 525)],
    ["id", "name", "state", "partner_id", "partner_invoice_id",
     "partner_shipping_id", "invoice_status"],
)
for k, v in so[0].items():
    print(f"  {k}: {v}")

# existing child contacts of Maison Osmoz
print("\n=== CHILDREN OF 2138 ===")
kids = search_read(
    "res.partner", [("parent_id", "=", 2138)],
    ["id", "name", "type", "street", "zip", "city"],
)
for k in kids:
    print(" ", k)
