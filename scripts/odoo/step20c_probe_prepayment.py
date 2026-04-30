"""Probe prepayment_percent unit + base.automation availability."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, execute

# 1. prepayment_percent details
print("[A] sale.order.prepayment_percent details:")
fields = execute("sale.order", "fields_get", ["prepayment_percent"], {})
print(f"    {fields['prepayment_percent']}")
print()

# 2. Check existing sale orders for sample values (read-only)
print("[B] Sample prepayment_percent values from real orders:")
orders = search_read(
    "sale.order",
    [("prepayment_percent", "!=", 0)],
    ["name", "prepayment_percent", "amount_total", "state"],
    limit=5,
)
for o in orders:
    print(f"    {o['name']}: prepayment_percent={o['prepayment_percent']}, "
          f"amount_total={o['amount_total']}, state={o['state']}")
if not orders:
    print("    (no orders with non-zero prepayment_percent)")
print()

# 3. base.automation availability (Odoo 17+ native automation)
print("[C] base.automation model:")
try:
    auto_fields = execute("base.automation", "fields_get",
                          ["name", "model_id", "trigger", "filter_domain",
                           "action_server_ids", "active"],
                          {"attributes": ["string", "type", "selection"]})
    for k, v in auto_fields.items():
        print(f"    {k}: type={v['type']}", end="")
        if v["type"] == "selection":
            print(f"  options={[s[0] for s in v.get('selection', [])][:10]}")
        else:
            print()
except Exception as e:
    print(f"    ERROR: {e}")
print()

# 4. ir.actions.server availability
print("[D] ir.actions.server model:")
try:
    srv_fields = execute("ir.actions.server", "fields_get",
                         ["name", "model_id", "state", "code"],
                         {"attributes": ["string", "type", "selection"]})
    if "state" in srv_fields:
        print(f"    state options: {[s[0] for s in srv_fields['state'].get('selection', [])]}")
except Exception as e:
    print(f"    ERROR: {e}")
print()

# 5. Existing automations on sale.order to model after
print("[E] Existing base.automation rules on sale.order:")
try:
    autos = search_read(
        "base.automation",
        [("model_id.model", "=", "sale.order")],
        ["name", "trigger", "filter_domain", "active"],
    )
    for a in autos:
        print(f"    [{a['id']}] {a['name']}  trigger={a['trigger']}  active={a['active']}")
    if not autos:
        print("    (none)")
except Exception as e:
    print(f"    ERROR: {e}")
