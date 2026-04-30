"""Probe Odoo instance to diagnose payment provider setup.

Read-only. Reports:
- Odoo version
- User groups for current UID
- Payment-related modules and their state
- Existing payment.provider records
- sale.order acompte field name (prepayment_percent vs other)
- Default sale email template
"""
import sys
import io
import xmlrpc.client
from _client import URL, DB, UID, API_KEY, search_read, execute

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

print(f"=== Odoo probe — UID={UID}, DB={DB} ===\n")

# ── 1. Odoo version ───────────────────────────────────────
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
ver = common.version()
print(f"[1] Odoo version: {ver.get('server_version')} ({ver.get('server_serie')})")
print(f"    Protocol: {ver.get('protocol_version')}\n")

# ── 2. Current user groups ────────────────────────────────
user = search_read("res.users", [("id", "=", UID)], ["name", "login", "groups_id"])[0]
print(f"[2] User: {user['name']} ({user['login']})")
group_ids = user["groups_id"]
groups = search_read("res.groups", [("id", "in", group_ids)],
                     ["name", "category_id", "full_name"])
admin_groups = [g for g in groups if "Settings" in g.get("full_name", "")
                or "Administration" in g.get("full_name", "")
                or "Technical" in g.get("full_name", "")]
print(f"    Total groups: {len(groups)}")
print(f"    Admin/Settings groups:")
for g in admin_groups:
    print(f"      - {g['full_name']}")
print()

# ── 3. Payment modules ────────────────────────────────────
print("[3] Payment-related modules:")
mods = search_read(
    "ir.module.module",
    [("name", "like", "payment")],
    ["name", "state", "shortdesc", "summary"],
)
for m in sorted(mods, key=lambda x: x["name"]):
    state = m["state"]
    marker = "✓" if state == "installed" else ("○" if state == "uninstalled" else f"[{state}]")
    print(f"    {marker} {m['name']:35s} {state:15s} {m['shortdesc']}")
print()

# Also check core deps
print("[3b] Core payment deps:")
core_deps = ["payment", "account", "account_payment", "sale", "website_sale",
             "sale_management", "portal"]
core = search_read("ir.module.module",
                   [("name", "in", core_deps)],
                   ["name", "state"])
for m in sorted(core, key=lambda x: x["name"]):
    marker = "✓" if m["state"] == "installed" else "○"
    print(f"    {marker} {m['name']:25s} {m['state']}")
print()

# ── 4. Existing payment providers ─────────────────────────
print("[4] payment.provider records:")
try:
    providers = search_read("payment.provider", [],
                            ["name", "code", "state", "company_id"])
    if not providers:
        print("    (none — explains why the list is empty)")
    for p in providers:
        company = p["company_id"][1] if p["company_id"] else "—"
        print(f"    [{p['id']}] {p['name']:20s} code={p['code']:15s} state={p['state']:10s} company={company}")
except xmlrpc.client.Fault as e:
    print(f"    ERROR reading payment.provider: {e.faultString[:200]}")
print()

# ── 5. sale.order acompte field ───────────────────────────
print("[5] sale.order field probe (acompte / prepayment):")
try:
    fields = execute("sale.order", "fields_get", [],
                     {"attributes": ["string", "type", "help"]})
    candidates = ["prepayment_percent", "require_payment", "require_signature",
                  "amount_total", "state"]
    for f in candidates:
        if f in fields:
            info = fields[f]
            print(f"    ✓ {f:25s} type={info['type']:10s} label={info['string']}")
        else:
            print(f"    ✗ {f:25s} NOT FOUND")
    # Also list any field with "prepay" or "down" in name
    related = [k for k in fields.keys() if "prepay" in k.lower() or "down" in k.lower()
               or "advance" in k.lower() or "deposit" in k.lower()]
    if related:
        print(f"    Related fields found: {related}")
except xmlrpc.client.Fault as e:
    print(f"    ERROR: {e.faultString[:200]}")
print()

# ── 6. Sale email template ────────────────────────────────
print("[6] sale.order email templates:")
try:
    templates = search_read(
        "mail.template",
        [("model", "=", "sale.order")],
        ["id", "name", "subject", "report_template_ids"],
    )
    for t in templates:
        print(f"    [{t['id']}] {t['name']}")
        print(f"        subject: {t['subject']}")
except xmlrpc.client.Fault as e:
    print(f"    ERROR: {e.faultString[:200]}")
print()

# ── 7. Sales config (settings) ────────────────────────────
print("[7] Sale config relevant settings (res.config.settings is transient — checking ir.config_parameter):")
try:
    params = search_read(
        "ir.config_parameter",
        [("key", "like", "sale")],
        ["key", "value"],
    )
    for p in params:
        if any(k in p["key"] for k in ["payment", "signature", "prepay", "down", "acompte"]):
            print(f"    {p['key']}: {p['value']}")
except xmlrpc.client.Fault as e:
    print(f"    ERROR: {e.faultString[:200]}")
print()

print("=== Probe done ===")
