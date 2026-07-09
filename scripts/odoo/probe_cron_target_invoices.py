"""List ALL invoices the followup cron currently targets (overdue, unpaid),
with their sale-order origin + Shopify refs, so we can cross-check which are
really unpaid (virement) vs falsely-unpaid (card already paid on Shopify)."""
import sys, io, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read

today = datetime.date.today().isoformat()

invs = search_read("account.move",
    [("move_type", "=", "out_invoice"), ("state", "=", "posted"),
     ("payment_state", "in", ["not_paid", "partial"]),
     ("invoice_date_due", "!=", False),
     ("invoice_date_due", "<", today)],
    ["id", "name", "partner_id", "amount_total", "amount_residual",
     "payment_state", "invoice_date_due", "invoice_origin", "ref",
     "x_followup_level"])

print(f"today={today}  cron-target invoices: {len(invs)}\n")

# Collect origins to fetch the sale orders
origins = sorted({i["invoice_origin"] for i in invs if i.get("invoice_origin")})
sos = search_read("sale.order", [("name", "in", origins)],
                  ["name", "client_order_ref", "origin", "source_id",
                   "x_followup_level"])
so_by_name = {s["name"]: s for s in sos}

for i in sorted(invs, key=lambda x: x["invoice_date_due"]):
    so = so_by_name.get(i.get("invoice_origin"), {})
    print(f"{i['name']} | due {i['invoice_date_due']} | "
          f"{i['amount_residual']:.2f}/{i['amount_total']:.2f}€ | "
          f"lvl={i.get('x_followup_level')} | {i['payment_state']}")
    print(f"    partner: {i['partner_id'][1]}")
    print(f"    origin={i.get('invoice_origin')} ref={i.get('ref')!r} "
          f"SO.client_order_ref={so.get('client_order_ref')!r} "
          f"SO.origin={so.get('origin')!r}")
