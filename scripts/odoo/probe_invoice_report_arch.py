"""Read-only probe: dump the arch of the standard invoice document QWeb view
to pick a robust xpath anchor for the Switzerland origin note inheritance."""
from scripts.odoo._client import search_read

KEY = "account.report_invoice_document"

views = search_read(
    "ir.ui.view",
    [("key", "=", KEY)],
    ["id", "key", "name", "type", "inherit_id"],
)
print(f"=== Views matching key={KEY} ===")
for v in views:
    print(f"  id={v['id']} name={v['name']!r} type={v['type']} inherit_id={v['inherit_id']}")

# The base (non-inherited) view holds the full arch
base = [v for v in views if not v["inherit_id"]]
target = base[0] if base else views[0]
print(f"\n=== arch of view id={target['id']} ===")
arch = search_read("ir.ui.view", [("id", "=", target["id"])], ["arch_db"])
print(arch[0]["arch_db"])
