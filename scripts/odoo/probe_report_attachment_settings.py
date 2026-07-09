"""Probe attachment + attachment_use fields on the patched reports."""
from scripts.odoo._client import search_read

IDS = [412, 413, 449, 775, 507, 325, 327]

reports = search_read(
    "ir.actions.report",
    [("id", "in", IDS)],
    ["id", "name", "report_name", "attachment", "attachment_use",
     "print_report_name"],
)
print(f"{'ID':>4} | {'name':30s} | use_att | attachment expr")
print("-" * 100)
for r in sorted(reports, key=lambda x: x["id"]):
    print(f"{r['id']:>4} | {r['name'][:30]:30s} | {str(r['attachment_use']):>7} | {r['attachment']!r}")

# Cached attachments for sale.order
print("\n=== Cached attachments on sale.order (auto from report) ===")
atts = search_read(
    "ir.attachment",
    [("res_model", "=", "sale.order"), ("name", "ilike", "Devis")],
    ["id", "res_id", "name"],
    limit=10,
)
print(f"Found {len(atts)} attached PDFs starting with 'Devis'")
for a in atts[:5]:
    print(f"  att#{a['id']} | sale.order#{a['res_id']} | {a['name']!r}")
