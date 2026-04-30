"""Get exact Stripe module info for direct UI URL."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read

mod = search_read(
    "ir.module.module",
    [("name", "=", "payment_stripe")],
    ["id", "name", "shortdesc", "state", "application", "category_id",
     "auto_install", "dependencies_id", "summary"],
)
if not mod:
    print("payment_stripe NOT FOUND")
else:
    m = mod[0]
    print(f"Module: payment_stripe")
    print(f"  ID:          {m['id']}")
    print(f"  State:       {m['state']}")
    print(f"  Application: {m['application']}")
    print(f"  Category:    {m['category_id'][1] if m['category_id'] else 'None'}")
    print(f"  Summary:     {m['summary']}")
    print()
    print(f"Direct URL to install:")
    print(f"  https://odoo.startec-paris.com/odoo/action-base.open_module_tree/{m['id']}")
    print()
    print(f"Or in Apps menu, remove all filters and search 'Stripe'.")
