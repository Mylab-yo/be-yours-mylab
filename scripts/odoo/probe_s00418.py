"""Read full state of sale order S00418 + linked invoices."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read

# Find SO by name
sos = search_read("sale.order",
                  [("name", "=", "S00418")],
                  ["id", "name", "state", "partner_id", "date_order",
                   "amount_untaxed", "amount_tax", "amount_total",
                   "pricelist_id", "invoice_ids", "invoice_status",
                   "order_line", "note", "validity_date",
                   "currency_id", "client_order_ref", "payment_term_id"],
                  limit=5)
print(f"Found {len(sos)} SO matching 'S00418'")
for so in sos:
    print(f"\n=== {so['name']} (id={so['id']}) ===")
    for k, v in so.items():
        if k != "order_line":
            print(f"  {k}: {v}")

if not sos:
    print("Not found, try ilike search")
    sos = search_read("sale.order",
                      [("name", "ilike", "418")],
                      ["id", "name", "state", "partner_id", "amount_total"],
                      limit=10)
    for so in sos:
        print(f"  {so}")
    sys.exit(0)

SO_ID = sos[0]["id"]
LINE_IDS = sos[0]["order_line"]

# Read all lines
print(f"\n=== Order lines ({len(LINE_IDS)} lines) ===")
lines = search_read("sale.order.line", [("id", "in", LINE_IDS)],
                    ["id", "sequence", "name", "product_id", "product_uom_qty",
                     "price_unit", "discount", "tax_id",
                     "price_subtotal", "price_tax", "price_total",
                     "display_type", "is_downpayment"],
                    limit=100)
lines.sort(key=lambda l: l.get("sequence") or 0)
print(f"{'#':>3} {'Seq':>4} {'Disp':<10} {'Down':<5} {'Product':<55} {'Qty':>6} {'Unit':>8} {'Disc%':>5} {'Sub':>9}")
print("-" * 130)
for i, line in enumerate(lines, 1):
    prod = line.get("product_id")
    prod_name = prod[1] if prod else "(no product)"
    print(f"{i:>3} {line.get('sequence', 0):>4} "
          f"{str(line.get('display_type') or ''):<10} "
          f"{str(line.get('is_downpayment', False)):<5} "
          f"{(prod_name or line.get('name', ''))[:55]:<55} "
          f"{line.get('product_uom_qty', 0):>6.2f} "
          f"{line.get('price_unit', 0):>8.2f} "
          f"{line.get('discount', 0):>5.2f} "
          f"{line.get('price_subtotal', 0):>9.2f}")
    if line.get("name") and prod and line["name"] != prod_name:
        print(f"     name: {line['name']!r}")

# Linked invoices
print(f"\n=== Linked invoices ({len(sos[0]['invoice_ids'])}) ===")
if sos[0]["invoice_ids"]:
    invs = search_read("account.move", [("id", "in", sos[0]["invoice_ids"])],
                       ["id", "name", "state", "move_type", "invoice_date",
                        "amount_untaxed", "amount_tax", "amount_total",
                        "amount_residual", "payment_state"],
                       limit=20)
    for inv in invs:
        print(f"  id={inv['id']:3} {inv['name']:25} type={inv['move_type']:15} state={inv['state']:8} pay={inv.get('payment_state')} total={inv['amount_total']} residual={inv['amount_residual']}")
