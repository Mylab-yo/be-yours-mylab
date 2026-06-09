"""Find ALL ir.attachment with 'Devis' in name, sorted by create_date."""
from scripts.odoo._client import search_read

atts = search_read(
    "ir.attachment",
    [("name", "ilike", "Devis - S0056")],
    ["id", "name", "res_model", "res_id", "create_date"],
)
print(f"Found {len(atts)} attachments\n")
for a in sorted(atts, key=lambda x: x["create_date"], reverse=True):
    print(f"  att#{a['id']:5d} | {a['create_date']} | "
          f"res={a['res_model'] or 'NONE'}#{a['res_id']:>4} | {a['name']!r}")

# Also check after 13h today (after the patch)
print("\n=== Attachments created AFTER 13:00 today ===")
atts2 = search_read(
    "ir.attachment",
    [("name", "ilike", ".pdf"),
     ("create_date", ">=", "2026-06-09 13:00:00")],
    ["id", "name", "res_model", "res_id", "create_date"],
)
for a in sorted(atts2, key=lambda x: x["create_date"]):
    print(f"  att#{a['id']:5d} | {a['create_date']} | "
          f"res={a['res_model'] or 'NONE'}#{a['res_id']:>4} | {a['name']!r}")
