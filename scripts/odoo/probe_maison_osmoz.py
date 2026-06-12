"""Probe: find Maison Osmoz customer, their partners, last SO and invoice."""
from _client import search_read, execute

# 1. Find partners matching the customer (by email or name)
partners = search_read(
    "res.partner",
    ["|", "|",
     ("email", "ilike", "maisonosmoz"),
     ("name", "ilike", "osmoz"),
     ("name", "ilike", "akbulut")],
    ["id", "name", "email", "parent_id", "type", "street", "street2",
     "zip", "city", "country_id", "is_company"],
)
print("=== PARTNERS ===")
for p in partners:
    print(p)

# 2. Find last sale orders for these partners (and their commercial parents)
pids = [p["id"] for p in partners]
parent_ids = [p["parent_id"][0] for p in partners if p.get("parent_id")]
all_ids = list(set(pids + parent_ids))
print("\nall partner ids:", all_ids)

sos = search_read(
    "sale.order",
    [("partner_id", "in", all_ids)],
    ["id", "name", "partner_id", "partner_invoice_id", "partner_shipping_id",
     "state", "date_order", "amount_total", "invoice_ids"],
    limit=20,
)
print("\n=== SALE ORDERS ===")
for s in sorted(sos, key=lambda x: x["date_order"], reverse=True):
    print(s)

# 3. Find invoices
invs = search_read(
    "account.move",
    [("partner_id", "in", all_ids), ("move_type", "in", ["out_invoice", "out_refund"])],
    ["id", "name", "partner_id", "partner_shipping_id", "state",
     "invoice_date", "amount_total", "invoice_origin"],
    limit=20,
)
print("\n=== INVOICES ===")
for i in sorted(invs, key=lambda x: x.get("invoice_date") or "", reverse=True):
    print(i)
