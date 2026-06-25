"""Check whether CRM is installed in Odoo + list lead/crm-ish models."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from scripts.odoo._client import search_read, execute

# module states
mods = search_read("ir.module.module",
                   [("name", "in", ["crm", "crm_iap_lead", "sales_team", "mail", "sale_crm"])],
                   ["name", "state", "shortdesc"])
print("=== Modules ===")
for m in sorted(mods, key=lambda x: x["name"]):
    print(f"  {m['name']:20} | {m['state']:12} | {m['shortdesc']}")

# does crm.lead model exist in ir.model?
print("\n=== ir.model entries matching crm/lead ===")
models = search_read("ir.model", ["|", ("model", "ilike", "crm"), ("model", "ilike", "lead")],
                     ["model", "name"])
for m in models:
    print(f"  {m['model']:30} | {m['name']}")

# sales team / sale.order exist?
print("\n=== sale.order count (sanity) ===")
try:
    print("  sale.order count =", execute("sale.order", "search_count", [[]]))
except Exception as e:
    print("  sale.order error:", e)
