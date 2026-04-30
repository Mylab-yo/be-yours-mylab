"""Check why payment.provider list is empty despite payment_custom being installed.

In Odoo 18, payment_custom should create at least one provider on install.
Could be a multi-company filter issue.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, execute, UID

# 1. All providers across all companies (with company info)
print("[A] All payment.provider records (no company filter):")
providers = execute(
    "payment.provider", "search_read",
    [[]],  # no domain
    {"fields": ["id", "name", "code", "state", "company_id"],
     "context": {"active_test": False}},
)
if not providers:
    print("    (still 0 — payment_custom may need re-init)")
for p in providers:
    company = p["company_id"][1] if p["company_id"] else "—"
    print(f"    [{p['id']}] {p['name']:25s} code={p['code']:15s} state={p['state']:10s} company={company}")
print()

# 2. Multi-company info
print("[B] Companies on this Odoo:")
companies = search_read("res.company", [], ["id", "name"])
for c in companies:
    print(f"    [{c['id']}] {c['name']}")
print()

# 3. Current user's company
user = search_read("res.users", [("id", "=", UID)],
                   ["name", "company_id", "company_ids"])[0]
print(f"[C] User company:")
print(f"    Active company: {user['company_id']}")
print(f"    All companies: {user['company_ids']}")
print()

# 4. payment_custom module info
print("[D] payment_custom module install state + dependencies:")
mod = search_read(
    "ir.module.module",
    [("name", "=", "payment_custom")],
    ["state", "latest_version", "installed_version"],
)
print(f"    {mod[0] if mod else 'not found'}")
print()

# 5. Sale settings — is online_payment enabled?
print("[E] Sale config (res.config.settings is transient — using ir.default for sale model defaults):")
defaults = search_read(
    "ir.default",
    [("field_id.model", "=", "sale.order")],
    ["field_id", "json_value"],
    limit=20,
)
for d in defaults:
    print(f"    {d}")
